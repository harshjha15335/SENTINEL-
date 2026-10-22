"""Merchant-scoped operations; global inbox aggregates require explicit operator scope."""

from contextlib import suppress
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, admin_only
from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    InvestigationRun,
    PaymentEvent,
    RiskScoringJob,
    StoredBlob,
    Transaction,
    WorkerHealth,
)
from app.models.enums import (
    EventProcessing,
    EventVerification,
    InvestigationMode,
    InvestigationStatus,
)
from app.schemas.operations import (
    InboxSnapshot,
    IntegrationStatus,
    OperationsOut,
    StageCount,
    StorageStatus,
    WorkerStatus,
)
from app.services.readiness import readiness, worker_fresh

router = APIRouter(tags=["operations"])


@router.get("/operations/webhooks", response_model=OperationsOut)
def webhook_operations(
    response: Response,
    principal: Principal = Depends(admin_only),
    db: Session = Depends(get_db),
) -> OperationsOut:
    response.headers["Cache-Control"] = "no-store"
    now, settings = datetime.now(UTC), get_settings()
    ok, checks = readiness(db)
    jobs = db.execute(
        select(Transaction.data_origin, RiskScoringJob.status, func.count())
        .join(Transaction, Transaction.id == RiskScoringJob.transaction_id)
        .where(Transaction.merchant_id == principal.merchant_id)
        .group_by(Transaction.data_origin, RiskScoringJob.status)
    ).all()
    events = db.execute(
        select(PaymentEvent.data_origin, PaymentEvent.processing_status, func.count())
        .where(PaymentEvent.merchant_id == principal.merchant_id)
        .group_by(PaymentEvent.data_origin, PaymentEvent.processing_status)
    ).all()
    investigations = db.execute(
        select(InvestigationRun.data_origin, InvestigationRun.status, func.count())
        .where(InvestigationRun.merchant_id == principal.merchant_id)
        .group_by(InvestigationRun.data_origin, InvestigationRun.status)
    ).all()
    workers = db.scalars(select(WorkerHealth).order_by(WorkerHealth.name)).all()
    bridge = next((w for w in workers if w.name == "supabase_bridge"), None)
    inbox = None
    authorized = settings.operations_inbox_merchant_id == principal.merchant_id
    if authorized and bridge and bridge.inbox_snapshot:
        with suppress(ValidationError):
            inbox = InboxSnapshot.model_validate(bridge.inbox_snapshot)
    files, size = db.execute(
        select(func.count(), func.coalesce(func.sum(func.octet_length(StoredBlob.body)), 0)).where(
            StoredBlob.key.startswith(str(principal.merchant_id) + "/")
        )
    ).one()
    return OperationsOut(
        observed_at=now,
        api="running",
        ready=ok,
        checks=checks,
        workers=[
            WorkerStatus(
                name=w.name,
                status=w.status,
                fresh=worker_fresh(w, now),
                heartbeat_at=w.heartbeat_at,
                last_success_at=w.last_success_at,
                processed=w.processed,
                failures=w.failures,
                last_error=w.last_error,
            )
            for w in workers
        ],
        events=[StageCount(data_origin=o, status=s.value, count=n) for o, s, n in events],
        scoring_jobs=[StageCount(data_origin=o, status=s, count=n) for o, s, n in jobs],
        investigations=[
            StageCount(data_origin=o, status=s.value, count=n) for o, s, n in investigations
        ],
        exhausted_events=db.scalar(
            select(func.count())
            .select_from(PaymentEvent)
            .where(
                PaymentEvent.merchant_id == principal.merchant_id,
                PaymentEvent.processing_status == EventProcessing.FAILED,
                PaymentEvent.attempts >= 5,
            )
        )
        or 0,
        inbox_scope="installation_aggregate" if authorized else "not_authorized",
        inbox_fresh=inbox is not None and 0 <= (now - inbox.observed_at).total_seconds() < 90,
        inbox=inbox,
        storage=StorageStatus(
            backend=settings.storage_backend.value,
            database_query="ok",
            stored_files=files,
            stored_bytes=size,
            durability="Database-backed; hosted backup policy must be verified separately."
            if settings.storage_backend.value == "database"
            else "Local disk; durable hosting is not established.",
        ),
        integrations=IntegrationStatus(
            paypal_mode=settings.paypal_mode.value,
            paypal_credentials_configured=settings.paypal_credentials_configured,
            webhook_id_configured=bool(settings.paypal_webhook_id),
            last_verified_event_at=db.scalar(
                select(func.max(PaymentEvent.received_at)).where(
                    PaymentEvent.merchant_id == principal.merchant_id,
                    PaymentEvent.verification_status == EventVerification.VERIFIED,
                )
            ),
            ai_provider=settings.ai_provider.value,
            ai_configured=settings.ai_configured,
            last_completed_ai_run_at=db.scalar(
                select(func.max(InvestigationRun.completed_at)).where(
                    InvestigationRun.merchant_id == principal.merchant_id,
                    InvestigationRun.mode == InvestigationMode.AI_AGENT,
                    InvestigationRun.status == InvestigationStatus.COMPLETED,
                )
            ),
            verification_note=(
                "Configuration is not provider verification. No provider request is made by this "
                "page. A verified webhook does not prove payment completion."
            ),
        ),
    )
