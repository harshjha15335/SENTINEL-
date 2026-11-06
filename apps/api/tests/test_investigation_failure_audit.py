"""Offline agent failure coverage; no database fixtures or provider requests are needed."""

import asyncio
import uuid
from contextlib import nullcontext
from types import SimpleNamespace
from typing import cast

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from app.core.config import AIProvider, Settings
from app.models.enums import (
    InvestigationErrorCategory,
    InvestigationMode,
    InvestigationStatus,
)
from app.services.investigation import runner
from app.services.investigation.provider import ProviderSpec, resolve_provider
from app.services.investigation.toolbox import CaseToolbox


@pytest.mark.parametrize(
    ("failure", "category"),
    [
        ("budget", InvestigationErrorCategory.BUDGET_EXCEEDED),
        ("timeout", InvestigationErrorCategory.PROVIDER_TIMEOUT),
        ("authentication", InvestigationErrorCategory.PROVIDER_UNAVAILABLE),
        ("rate_limit", InvestigationErrorCategory.PROVIDER_ERROR),
        ("invalid_output", InvestigationErrorCategory.INVALID_OUTPUT),
    ],
)
def test_denied_tool_attempt_survives_agent_failure(monkeypatch, failure, category):
    settings = SimpleNamespace(
        ai_request_limit=1 if failure == "budget" else 12,
        ai_tool_calls_limit=24,
        ai_total_tokens_limit=120_000,
        ai_timeout_seconds=0.1 if failure == "timeout" else 10,
    )
    monkeypatch.setattr(runner, "get_settings", lambda: settings)
    calls = 0

    async def respond(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            return ModelResponse(
                parts=[ToolCallPart("refund_payment", {"secret": "untrusted-private-argument"})]
            )
        if failure == "timeout":
            await asyncio.sleep(5)
        if failure in ("authentication", "rate_limit"):
            raise ModelHTTPError(
                401 if failure == "authentication" else 429,
                "scripted",
                {"secret": "private-provider-response"},
            )
        return ModelResponse(parts=[])

    spec = ProviderSpec("test", "scripted", lambda: FunctionModel(respond))
    # No registered tool is called, so the toolbox never needs a session or case.
    box = cast(CaseToolbox, SimpleNamespace())
    with pytest.raises(runner.InvestigationFailed) as caught:
        runner._run_agent(box, spec)
    error = caught.value
    assert error.category == category
    assert [call["name"] for call in error.denied_calls] == ["refund_payment"]
    assert error.denied_calls[0]["outcome"] == "denied"
    assert error.denied_calls[0]["arguments"] == {}
    assert "untrusted-private-argument" not in str(error.denied_calls)
    assert "private-provider-response" not in error.message


@pytest.mark.parametrize("provider", [AIProvider.ANTHROPIC, AIProvider.OPENAI])
def test_supported_sdk_builds_offline_with_explicit_model(provider):
    settings = Settings(
        _env_file=None,
        hosted_deployment=False,
        allow_webhook_fixtures=False,
        paypal_client_id=None,
        paypal_client_secret=None,
        ai_provider=provider,
        ai_model="offline-explicit-model",
        ai_api_key="offline-dummy-key",
    )
    spec = resolve_provider(settings)
    assert spec is not None
    model = spec.build()
    assert spec.provider == provider.value
    assert model.model_name == "offline-explicit-model"


def test_execute_persists_denied_attempts_on_failed_run(monkeypatch):
    run = SimpleNamespace(
        id=uuid.uuid4(),
        merchant_id=uuid.uuid4(),
        case_id=uuid.uuid4(),
        status=InvestigationStatus.QUEUED,
        mode=InvestigationMode.AI_AGENT,
        usage={},
    )
    commits = []
    session = SimpleNamespace(
        get=lambda model, key: run,
        commit=lambda: commits.append(run.status),
        rollback=lambda: None,
    )
    box = SimpleNamespace(calls=[], refs=set())
    failure = runner.InvestigationFailed(
        InvestigationErrorCategory.BUDGET_EXCEEDED, "Budget exceeded."
    )
    failure.denied_calls = [{"name": "refund_payment", "outcome": "denied", "arguments": {}}]

    def fail(*args):
        raise failure

    monkeypatch.setattr(runner, "get_sessionmaker", lambda: lambda: nullcontext(session))
    monkeypatch.setattr(runner, "get_case", lambda *args: object())
    monkeypatch.setattr(runner, "CaseToolbox", lambda **kwargs: box)
    monkeypatch.setattr(runner, "resolve_provider", lambda: object())
    monkeypatch.setattr(runner, "_run_agent", fail)
    monkeypatch.setattr(runner.audit, "record_for_case", lambda *args, **kwargs: None)
    runner.execute(run.id)
    assert commits == [InvestigationStatus.RUNNING, InvestigationStatus.FAILED]
    assert run.error_category == InvestigationErrorCategory.BUDGET_EXCEEDED
    assert run.tool_calls == failure.denied_calls
