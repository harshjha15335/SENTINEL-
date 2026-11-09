"""Starting, executing and reading investigation runs.

Concurrency policy: at most one QUEUED/RUNNING run per case. Starting locks the case row and a
partial unique index backs the rule, so a second start returns 409 with the active run's id.
Runs left active longer than ``investigation_stale_seconds`` (for example after a crash) are
marked FAILED/ABANDONED before a new one starts. A failed run never changes the case or earlier
runs; completed findings are kept forever.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic_ai import RunContext, capture_run_messages
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
)
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelResponse,
    ToolCallPart,
)
from pydantic_ai.models import Model, ModelRequestParameters, StreamedResponse
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage, UsageLimits
from pydantic_core import to_json
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.config import get_settings
from app.core.errors import ConflictError, NotFoundError
from app.db.session import get_sessionmaker
from app.models import InvestigationRun
from app.models.enums import (
    InvestigationErrorCategory,
    InvestigationMode,
    InvestigationStatus,
)
from app.services import audit
from app.services.cases import get_case
from app.services.investigation.agent import (
    PROMPT_VERSION,
    READ_ONLY_TOOLS,
    USER_PROMPT,
    AgentDeps,
    build_agent,
)
from app.services.investigation.deterministic import build_summary
from app.services.investigation.diagnostics import extract_safe_diagnostics
from app.services.investigation.provider import ProviderSpec, resolve_provider
from app.services.investigation.schemas import InvestigationFindings
from app.services.investigation.toolbox import CaseToolbox
from app.services.investigation.validation import FindingsRejected, validate_findings

log = logging.getLogger(__name__)

DETERMINISTIC_PROMPT_VERSION = "deterministic-v1"
_ACTIVE = (InvestigationStatus.QUEUED, InvestigationStatus.RUNNING)


class InvestigationFailed(Exception):
    def __init__(self, category: InvestigationErrorCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.denied_calls: list[dict[str, Any]] = []
        self.usage: dict[str, Any] = {}


def _expire_stale(db: Session, case_id: uuid.UUID) -> None:
    cutoff = datetime.now(UTC) - timedelta(seconds=get_settings().investigation_stale_seconds)
    db.execute(
        update(InvestigationRun)
        .where(
            InvestigationRun.case_id == case_id,
            InvestigationRun.status.in_(_ACTIVE),
            InvestigationRun.created_at < cutoff,
        )
        .values(
            status=InvestigationStatus.FAILED,
            error_category=InvestigationErrorCategory.ABANDONED,
            error_message="The run did not finish in time and was abandoned.",
            completed_at=datetime.now(UTC),
        )
    )


def start(
    db: Session, principal: Principal, case_id: uuid.UUID, *, deterministic: bool = False
) -> InvestigationRun:
    """Create a QUEUED run for an authorised case. The caller schedules ``execute``."""
    case = get_case(db, principal.merchant_id, case_id, lock=True)
    _expire_stale(db, case.id)
    active = db.scalar(
        select(InvestigationRun.id).where(
            InvestigationRun.case_id == case.id, InvestigationRun.status.in_(_ACTIVE)
        )
    )
    if active is not None:
        db.rollback()
        raise ConflictError(
            "An investigation is already running for this case", details={"run_id": str(active)}
        )
    spec = None if deterministic else resolve_provider()
    run = InvestigationRun(
        merchant_id=case.merchant_id,
        case_id=case.id,
        transaction_id=case.transaction_id,
        initiated_by_user_id=principal.user.id,
        status=InvestigationStatus.QUEUED,
        mode=InvestigationMode.AI_AGENT if spec else InvestigationMode.DETERMINISTIC,
        provider=spec.provider if spec else "none",
        model_name=spec.model_name if spec else "deterministic",
        prompt_version=PROMPT_VERSION if spec else DETERMINISTIC_PROMPT_VERSION,
        tool_calls=[],
        source_refs=[],
        usage={
            "deterministic_reason": None
            if spec
            else ("requested" if deterministic else "provider_unavailable")
        },
        data_origin=case.data_origin,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("An investigation is already running for this case") from exc
    audit.record_for_case(
        db,
        case,
        "investigation.requested",
        principal.user.id,
        entity_type="investigation_run",
        entity_id=run.id,
        mode=run.mode.value,
        provider=run.provider,
        model_name=run.model_name,
    )
    db.commit()
    return run


def execute(run_id: uuid.UUID) -> None:
    """Run a QUEUED investigation with its own database session (background task)."""
    with get_sessionmaker()() as db:
        run = db.get(InvestigationRun, run_id)
        if run is None or run.status is not InvestigationStatus.QUEUED:
            return
        run.status = InvestigationStatus.RUNNING
        run.started_at = datetime.now(UTC)
        db.commit()
        t0 = time.perf_counter()
        merchant_id, case_id = run.merchant_id, run.case_id
        box: CaseToolbox | None = None
        findings: InvestigationFindings | None = None
        failure: InvestigationFailed | None = None
        usage: dict[str, Any] = dict(run.usage or {})
        denied: list[dict[str, Any]] = []
        try:
            # Scope comes from the run row the server created, never from the model.
            case = get_case(db, merchant_id, case_id)
            box = CaseToolbox(db=db, case=case)
            if run.mode is InvestigationMode.DETERMINISTIC:
                findings = build_summary(box)
                validate_findings(findings, box)
            else:
                spec = resolve_provider()
                if spec is None:
                    raise InvestigationFailed(
                        InvestigationErrorCategory.PROVIDER_UNAVAILABLE,
                        "The AI provider is no longer configured.",
                    )
                findings, usage_out, denied = _run_agent(box, spec)
                usage.update(usage_out)
        except InvestigationFailed as exc:
            failure = exc
            denied = exc.denied_calls
            usage.update(exc.usage)
        except FindingsRejected as exc:
            failure = InvestigationFailed(
                InvestigationErrorCategory.UNSUPPORTED_ASSERTION, str(exc)
            )
        except NotFoundError:
            failure = InvestigationFailed(
                InvestigationErrorCategory.INTERNAL, "The case is no longer available."
            )
        except Exception:
            log.exception("investigation run failed", extra={"data": {"run_id": str(run_id)}})
            failure = InvestigationFailed(
                InvestigationErrorCategory.INTERNAL, "The investigation failed unexpectedly."
            )
        db.rollback()  # discard anything a failed tool left pending; tools never write
        run = db.get(InvestigationRun, run_id)
        if run is None:
            return
        calls = [c.as_json() for c in box.calls] if box else []
        run.tool_calls = calls + denied
        run.source_refs = [{"kind": k, "id": i} for k, i in sorted(box.refs)] if box else []
        run.usage = usage
        run.completed_at = datetime.now(UTC)
        run.duration_ms = int((time.perf_counter() - t0) * 1000)
        if failure is None and findings is not None:
            run.status = InvestigationStatus.COMPLETED
            run.findings = findings.model_dump(mode="json")
        else:
            failure = failure or InvestigationFailed(
                InvestigationErrorCategory.INTERNAL, "No findings were produced."
            )
            run.status = InvestigationStatus.FAILED
            run.error_category = failure.category
            run.error_message = failure.message[:2000]
        case = get_case(db, merchant_id, case_id)
        audit.record_for_case(
            db,
            case,
            "investigation.completed" if failure is None else "investigation.failed",
            None,
            entity_type="investigation_run",
            entity_id=run.id,
            mode=run.mode.value,
            status=run.status.value,
            error_category=run.error_category.value if run.error_category else None,
            tool_calls=len(run.tool_calls),
            duration_ms=run.duration_ms,
        )
        db.commit()


def _run_agent(
    box: CaseToolbox, spec: ProviderSpec
) -> tuple[InvestigationFindings, dict[str, Any], list[dict[str, Any]]]:
    settings = get_settings()
    model = _InputBudgetModel(
        spec.build(),
        max_input_bytes=settings.ai_max_input_bytes,
        total_input_bytes_limit=settings.ai_total_input_bytes_limit,
    )
    agent = build_agent(model)
    run_usage = RunUsage()
    deps = AgentDeps(box=box)
    limits = UsageLimits(
        request_limit=settings.ai_request_limit,
        tool_calls_limit=settings.ai_tool_calls_limit,
        total_tokens_limit=settings.ai_total_tokens_limit,
    )

    async def go() -> Any:
        return await asyncio.wait_for(
            agent.run(
                USER_PROMPT,
                deps=deps,
                usage_limits=limits,
                usage=run_usage,
                model_settings={
                    "timeout": settings.ai_timeout_seconds,
                    "temperature": 1.0 if spec.provider == "google" else 0.0,
                    "max_tokens": settings.ai_max_output_tokens,
                },
            ),
            timeout=settings.ai_timeout_seconds,
        )

    try:
        with capture_run_messages() as messages:
            try:
                result = asyncio.run(go())
                findings: InvestigationFindings = result.output
                validate_findings(findings, box)  # defence in depth after the output validator
            except FindingsRejected as exc:
                raise InvestigationFailed(
                    InvestigationErrorCategory.UNSUPPORTED_ASSERTION, str(exc)
                ) from exc
            except TimeoutError as exc:
                raise InvestigationFailed(
                    InvestigationErrorCategory.PROVIDER_TIMEOUT,
                    "The AI provider did not finish within "
                    f"{settings.ai_timeout_seconds:g} seconds.",
                ) from exc
            except UsageLimitExceeded as exc:
                raise InvestigationFailed(
                    InvestigationErrorCategory.BUDGET_EXCEEDED,
                    "The investigation exceeded its request, tool-call, token or input budget.",
                ) from exc
            except ModelHTTPError as exc:
                safe_diag = extract_safe_diagnostics(exc, spec.provider)
                category = (
                    InvestigationErrorCategory.PROVIDER_UNAVAILABLE
                    if exc.status_code in (401, 403)
                    else InvestigationErrorCategory.PROVIDER_ERROR
                )
                fail = InvestigationFailed(
                    category, f"The AI provider returned HTTP {exc.status_code}."
                )
                fail.usage["diagnostic"] = safe_diag
                raise fail from exc
            except ModelAPIError as exc:
                raise InvestigationFailed(
                    InvestigationErrorCategory.PROVIDER_ERROR,
                    "The AI provider could not be reached.",
                ) from exc
            except UnexpectedModelBehavior as exc:
                if deps.last_rejection:
                    raise InvestigationFailed(
                        InvestigationErrorCategory.UNSUPPORTED_ASSERTION,
                        "The AI output was rejected after retries: " + deps.last_rejection,
                    ) from exc
                raise InvestigationFailed(
                    InvestigationErrorCategory.INVALID_OUTPUT,
                    "The AI output did not match the required findings schema after retries.",
                ) from exc
    except InvestigationFailed as exc:
        # Preserve attempted mutation/unknown tools even when the agent fails or exhausts
        # its budget; failed runs need the same read-only audit trail as completed runs.
        exc.denied_calls = _denied_calls(box, list(messages))
        snapshot = _usage_snapshot(run_usage, model, complete=False)
        snapshot.update(exc.usage)
        exc.usage = snapshot
        raise
    denied = _denied_calls(box, list(messages))

    return findings, _usage_snapshot(result.usage, model, complete=True), denied


class _InputBudgetModel(WrapperModel):
    """Bound every nonstreaming investigation request before the provider call.

    Includes the initial prompt, accumulated history, instructions and all schemas. Rejects
    oversized context without truncating source facts. The bound is on local UTF-8 input,
    not exact provider tokens or the provider-specific wire representation.
    """

    def __init__(self, model: Model, *, max_input_bytes: int, total_input_bytes_limit: int):
        super().__init__(model)
        self.max_input_bytes = max_input_bytes
        self.total_input_bytes_limit = total_input_bytes_limit
        self.input_bytes = 0
        self.max_request_input_bytes = 0
        self.requests_attempted = 0
        self.requests_rejected = 0

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        size = (
            len(ModelMessagesTypeAdapter.dump_json(messages))
            + len(to_json(model_request_parameters))
            + len(to_json(model_settings))
        )
        if size > self.max_input_bytes or self.input_bytes + size > self.total_input_bytes_limit:
            self.requests_rejected += 1
            raise UsageLimitExceeded("The next request would exceed the local input byte budget.")
        self.input_bytes += size
        self.max_request_input_bytes = max(self.max_request_input_bytes, size)
        self.requests_attempted += 1
        return await self.wrapped.request(messages, model_settings, model_request_parameters)

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
        run_context: RunContext[Any] | None = None,
    ) -> AsyncIterator[StreamedResponse]:
        # Investigations use nonstreaming calls. Fail closed if a future caller attempts
        # a streaming path, rather than inheriting WrapperModel's unguarded delegation.
        self.requests_rejected += 1
        raise UsageLimitExceeded("Streaming investigations are disabled by the input budget guard.")
        yield  # pragma: no cover — makes this an async context manager; never reached


def _usage_snapshot(usage: RunUsage, model: _InputBudgetModel, *, complete: bool) -> dict[str, Any]:
    return {
        "requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "model_requests_attempted": model.requests_attempted,
        "input_bytes": model.input_bytes,
        "max_request_input_bytes": model.max_request_input_bytes,
        "input_requests_rejected": model.requests_rejected,
        # Missing/failed provider responses may carry no usage; never imply zero billing.
        "token_usage_available": bool(usage.input_tokens or usage.output_tokens),
        "usage_complete": complete and bool(usage.input_tokens or usage.output_tokens),
    }


def _denied_calls(box: CaseToolbox, messages: list[Any]) -> list[dict[str, Any]]:
    """Tool calls the model attempted that do not exist (for example a refund tool)."""
    out = []
    for m in messages:
        if not isinstance(m, ModelResponse):
            continue
        for part in m.parts:
            if isinstance(part, ToolCallPart) and part.tool_name not in READ_ONLY_TOOLS:
                if part.tool_name == "final_result":
                    continue
                out.append(
                    {
                        "name": part.tool_name[:64],
                        "arguments": {},
                        "outcome": "denied",
                        "duration_ms": 0,
                        "records": [],
                        "note": "No such tool. The investigation has read-only tools only.",
                    }
                )
    return out


def list_runs(db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID) -> list[InvestigationRun]:
    case = get_case(db, merchant_id, case_id)
    return list(
        db.scalars(
            select(InvestigationRun)
            .where(
                InvestigationRun.case_id == case.id,
                InvestigationRun.merchant_id == merchant_id,
            )
            .order_by(InvestigationRun.created_at.desc())
        ).unique()
    )


def get_run(
    db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID, run_id: uuid.UUID
) -> InvestigationRun:
    run = db.scalar(
        select(InvestigationRun).where(
            InvestigationRun.id == run_id,
            InvestigationRun.case_id == case_id,
            InvestigationRun.merchant_id == merchant_id,
        )
    )
    if run is None:
        raise NotFoundError("Investigation not found")
    return run


def latest_completed(
    db: Session, merchant_id: uuid.UUID, case_id: uuid.UUID
) -> InvestigationRun | None:
    return db.scalar(
        select(InvestigationRun)
        .where(
            InvestigationRun.case_id == case_id,
            InvestigationRun.merchant_id == merchant_id,
            InvestigationRun.status == InvestigationStatus.COMPLETED,
        )
        .order_by(InvestigationRun.completed_at.desc())
        .limit(1)
    )
