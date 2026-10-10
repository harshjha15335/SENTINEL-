import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import AuditEvent, PaymentEvent, Transaction
from app.models.enums import DataOrigin, TransactionStatus
from app.schemas.api import AuditOut, PaymentEventOut, TransactionDetailOut, TransactionOut


def to_out(txn: Transaction) -> TransactionOut:
    out = TransactionOut.model_validate(txn)
    out.product_name = txn.product.name if txn.product else None
    return out


def list_transactions(
    db: Session,
    merchant_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
    status: TransactionStatus | None,
    data_origin: DataOrigin | None,
    q: str | None,
) -> tuple[list[Transaction], int]:
    stmt = select(Transaction).where(Transaction.merchant_id == merchant_id)
    if status:
        stmt = stmt.where(Transaction.status == status)
    if data_origin:
        stmt = stmt.where(Transaction.data_origin == data_origin)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            Transaction.paypal_order_id.ilike(like) | Transaction.paypal_capture_id.ilike(like)
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Transaction.created_at.desc()).limit(limit).offset(offset))
    return list(rows.unique()), total


def get_detail(db: Session, merchant_id: uuid.UUID, txn_id: uuid.UUID) -> TransactionDetailOut:
    txn = db.scalar(
        select(Transaction).where(Transaction.id == txn_id, Transaction.merchant_id == merchant_id)
    )
    if txn is None:
        raise NotFoundError("Transaction not found")
    events = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.transaction_id == txn.id)
        .order_by(PaymentEvent.received_at)
    )
    audit_rows = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.merchant_id == merchant_id,
            AuditEvent.entity_type == "transaction",
            AuditEvent.entity_id == str(txn.id),
        )
        .order_by(AuditEvent.created_at)
    )
    base: dict[str, Any] = to_out(txn).model_dump()
    return TransactionDetailOut(
        **base,
        provider_summary=txn.provider_summary,
        events=[PaymentEventOut.model_validate(e) for e in events],
        audit=[AuditOut.model_validate(a) for a in audit_rows],
    )
