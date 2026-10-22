from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.readiness import readiness

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> JSONResponse:
    ok, checks = readiness(db)
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, 200 if ok else 503
    )
