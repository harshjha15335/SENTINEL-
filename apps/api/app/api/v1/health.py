from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

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
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, 200 if ok else 503
    )
