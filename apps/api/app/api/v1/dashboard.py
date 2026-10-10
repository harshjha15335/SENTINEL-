from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.db.session import get_db
from app.models import PaymentEvent, Transaction
from app.models.enums import TransactionStatus
from app.schemas.api import DashboardSummaryOut, OriginTotals
from app.services.transactions import list_transactions, to_out

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryOut)
def summary(
    principal: Principal = Depends(any_member), db: Session = Depends(get_db)
) -> DashboardSummaryOut:
    mid = principal.merchant_id
    by_status = dict(
        db.execute(
            select(Transaction.status, func.count())
            .where(Transaction.merchant_id == mid)
            .group_by(Transaction.status)
        ).all()
    )
    # Totals are split by origin and currency so sandbox and simulated money never mix.
    captured = db.execute(
        select(
            Transaction.data_origin,
            Transaction.currency,
            func.count(),
            func.coalesce(func.sum(Transaction.amount_minor), 0),
        )
        .where(Transaction.merchant_id == mid, Transaction.status == TransactionStatus.CAPTURED)
        .group_by(Transaction.data_origin, Transaction.currency)
    ).all()
    events = dict(
        db.execute(
            select(PaymentEvent.processing_status, func.count())
            .where(PaymentEvent.merchant_id == mid)
            .group_by(PaymentEvent.processing_status)
        ).all()
    )
    recent, total = list_transactions(
        db, mid, limit=8, offset=0, status=None, data_origin=None, q=None
    )
    return DashboardSummaryOut(
        transactions_total=total,
        by_status={k.value: v for k, v in by_status.items()},
        captured_by_origin=[
            OriginTotals(data_origin=o, currency=c, captured_count=n, captured_amount_minor=int(s))
            for o, c, n, s in captured
        ],
        webhook_events={k.value: v for k, v in events.items()},
        recent=[to_out(r) for r in recent],
    )
