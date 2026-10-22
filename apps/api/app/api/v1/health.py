from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.deps import Principal, admin_only
from app.core.config import get_settings
from app.db.session import get_db
from app.models import PaymentEvent, RiskScoringJob, Transaction, WorkerHealth

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        version = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        checks["database"] = "ok"
        checks["migration"] = str(version)
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
    settings = get_settings()
    checks["paypal_mode"] = settings.paypal_mode.value
    checks["paypal_credentials"] = (
        "configured" if settings.paypal_credentials_configured else "missing"
    )
    ok = checks["database"] == "ok"
    if ok and settings.require_workers_ready:
        required = ["pipeline", "supabase_bridge"]
        for name in required:
            worker = db.get(WorkerHealth, name)
            healthy = (
                worker is not None
                and worker.status == "HEALTHY"
                and (datetime.now(UTC) - worker.heartbeat_at).total_seconds() < 45
            )
            checks[name] = "ok" if healthy else "not_ready"
            ok = ok and healthy
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, 200 if ok else 503
    )


@router.get("/operations/webhooks")
def webhook_operations(
    principal: Principal = Depends(admin_only), db: Session = Depends(get_db)
) -> dict[str, object]:
    jobs = db.execute(
        select(RiskScoringJob.status, func.count())
        .join(Transaction, Transaction.id == RiskScoringJob.transaction_id)
        .where(Transaction.merchant_id == principal.merchant_id)
        .group_by(RiskScoringJob.status)
    ).all()
    events = db.execute(
        select(PaymentEvent.processing_status, func.count())
        .where(PaymentEvent.merchant_id == principal.merchant_id)
        .group_by(PaymentEvent.processing_status)
    ).all()
    workers = db.scalars(select(WorkerHealth)).all()
    return {
        "scoring_jobs": {status: count for status, count in jobs},
        "events": {status.value: count for status, count in events},
        "workers": [
            {
                "name": w.name,
                "status": w.status,
                "heartbeat_at": w.heartbeat_at.isoformat(),
                "processed": w.processed,
                "failures": w.failures,
                "last_error": w.last_error,
            }
            for w in workers
        ],
        "exhausted_events": db.scalar(
            select(func.count())
            .select_from(PaymentEvent)
            .where(
                PaymentEvent.merchant_id == principal.merchant_id,
                PaymentEvent.processing_status == "FAILED",
                PaymentEvent.attempts >= 5,
            )
        ),
    }
