from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.db.session import get_db
from app.models import Case, PaymentEvent, RiskAssessment, Transaction
from app.models.enums import CaseStatus, TransactionStatus
from app.schemas.api import DashboardSummaryOut, OriginCount, OriginTotals
from app.services.transactions import list_transactions, to_out_many

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
    open_cases = db.execute(
        select(Case.data_origin, Case.priority, func.count())
        .where(Case.merchant_id == mid, Case.status != CaseStatus.RESOLVED)
        .group_by(Case.data_origin, Case.priority)
    ).all()
    # Latest assessment per transaction, counted by band within each origin.
    latest = (
        select(RiskAssessment.transaction_id, RiskAssessment.data_origin, RiskAssessment.risk_band)
        .where(RiskAssessment.merchant_id == mid)
        .order_by(
            RiskAssessment.transaction_id,
            RiskAssessment.created_at.desc(),
            RiskAssessment.id.desc(),
        )
        .ext(distinct_on(RiskAssessment.transaction_id))
        .subquery()
    )
    bands = db.execute(
        select(latest.c.data_origin, latest.c.risk_band, func.count()).group_by(
            latest.c.data_origin, latest.c.risk_band
        )
    ).all()
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
        recent=to_out_many(db, mid, recent),
        open_cases_by_origin=[
            OriginCount(data_origin=o, key=p.value, count=n) for o, p, n in open_cases
        ],
        risk_bands_by_origin=[
            OriginCount(data_origin=o, key=b.value, count=n) for o, b, n in bands
        ],
    )
