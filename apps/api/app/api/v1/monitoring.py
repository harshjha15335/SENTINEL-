"""Authenticated read-only monitoring and bounded provenance-backed network exploration."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.enums import DataOrigin, RiskBand
from app.schemas.monitoring import MonitoringOut, NetworkOut
from app.services import monitoring

router = APIRouter(tags=["monitoring"])


def boundary(as_of: datetime | None) -> datetime:
    now = datetime.now(UTC)
    if as_of is None:
        return now
    if as_of.tzinfo is None or as_of > now:
        raise DomainError("as_of must be timezone-aware and cannot be in the future")
    return as_of.astimezone(UTC)


@router.get("/monitoring/risk", response_model=MonitoringOut)
def risk_monitoring(
    response: Response,
    data_origin: DataOrigin,
    days: int = Query(default=30, ge=1, le=180),
    as_of: datetime | None = None,
    capacity: float = Query(default=0.08, gt=0, le=1),
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> MonitoringOut:
    response.headers["Cache-Control"] = "no-store"
    return monitoring.summary(
        db, principal.merchant_id, data_origin, days=days, as_of=boundary(as_of), capacity=capacity
    )


@router.get("/network", response_model=NetworkOut)
def relationship_network(
    response: Response,
    data_origin: DataOrigin,
    days: int = Query(default=90, ge=1, le=365),
    as_of: datetime | None = None,
    limit: int = Query(default=30, ge=1, le=60),
    payer: str | None = Query(default=None, max_length=64),
    risk_band: RiskBand | None = None,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> NetworkOut:
    response.headers["Cache-Control"] = "no-store"
    return monitoring.network(
        db,
        principal.merchant_id,
        data_origin,
        days=days,
        as_of=boundary(as_of),
        limit=limit,
        payer=payer,
        risk_band=risk_band,
    )
