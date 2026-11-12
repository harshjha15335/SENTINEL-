"""Readiness is schema compatibility and fresh essential workers, not provider success."""

from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import PayPalMode, get_settings
from app.models import WorkerHealth


@lru_cache
def expected_revision() -> str:
    return str(
        ScriptDirectory(str(Path(__file__).resolve().parents[2] / "alembic")).get_current_head()
    )


def worker_fresh(worker: WorkerHealth, now: datetime) -> bool:
    return 0 <= (now - worker.heartbeat_at).total_seconds() < 45


def readiness(db: Session) -> tuple[bool, dict[str, str]]:
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        versions = set(db.scalars(text("SELECT version_num FROM alembic_version")))
        checks["database"] = "ok"
        checks["migration"] = next(iter(versions)) if len(versions) == 1 else "incompatible"
        checks["schema"] = "ok" if versions == {expected_revision()} else "incompatible"
    except Exception as exc:
        db.rollback()
        checks["database"] = "error: " + type(exc).__name__
        checks["schema"] = "unavailable"
    settings = get_settings()
    checks["paypal_mode"] = settings.paypal_mode.value
    checks["paypal_credentials"] = (
        "configured" if settings.paypal_credentials_configured else "missing"
    )
    checks["paypal_provider_verification"] = "unverified_by_readiness"
    checks["ai_provider_verification"] = "unverified_by_readiness"
    ok = checks["database"] == "ok" and checks["schema"] == "ok"
    checks["supabase_configuration"] = "configured" if settings.supabase_configured else "absent"
    if ok and settings.require_workers_ready:
        # Sandbox and every configured integration retain the bridge gate.
        # A genuinely absent fixture integration has no heartbeat to fabricate.
        if not settings.bridge_required:
            checks["supabase_bridge"] = "not_required_fixture_mode"
        names = ("pipeline", "supabase_bridge") if settings.bridge_required else ("pipeline",)
        for name in names:
            worker = db.get(WorkerHealth, name)
            healthy = (
                worker is not None
                and worker.status == "HEALTHY"
                and worker_fresh(worker, datetime.now(UTC))
            )
            checks[name] = "ok" if healthy else "not_ready"
            ok = ok and healthy
        ok = ok and settings.worker_configuration_ready
        if settings.paypal_mode is PayPalMode.SANDBOX:
            ok = ok and settings.paypal_credentials_configured
    return ok, checks
