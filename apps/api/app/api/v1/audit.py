from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, admin_only
from app.db.session import get_db
from app.models import AuditEvent
from app.schemas.api import AuditOut
from app.schemas.common import Page

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditOut])
def list_audit(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    principal: Principal = Depends(admin_only),
    db: Session = Depends(get_db),
) -> Page[AuditOut]:
    stmt = select(AuditEvent).where(AuditEvent.merchant_id == principal.merchant_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset))
    return Page(
        items=[AuditOut.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )
