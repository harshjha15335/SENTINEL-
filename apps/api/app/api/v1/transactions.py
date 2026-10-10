import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.db.session import get_db
from app.models.enums import DataOrigin, TransactionStatus
from app.schemas.api import TransactionDetailOut, TransactionOut
from app.schemas.common import Page
from app.services.transactions import get_detail, list_transactions, to_out

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=Page[TransactionOut])
def list_(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: TransactionStatus | None = None,
    data_origin: DataOrigin | None = None,
    q: str | None = Query(None, max_length=64),
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> Page[TransactionOut]:
    rows, total = list_transactions(
        db,
        principal.merchant_id,
        limit=limit,
        offset=offset,
        status=status,
        data_origin=data_origin,
        q=q,
    )
    return Page(items=[to_out(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
def detail(
    transaction_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> TransactionDetailOut:
    return get_detail(db, principal.merchant_id, transaction_id)
