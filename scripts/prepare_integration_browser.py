"""Prepare fixture-only browser data in an explicitly isolated integration database.

Run with PYTHONPATH=apps/api. Seed passwords and SENTINEL_JUDGE_PASSWORD must be
provided privately. No provider calls or payment execution are performed.
"""

import os

from app.auth.deps import Principal
from app.cli import demo_load, seed
from app.core.config import AIProvider, PayPalMode, get_settings
from app.db.session import get_sessionmaker
from app.models import Case, Transaction, User, UserSession
from app.models.enums import TransactionStatus
from app.models.refunds import RefundRequest
from app.services import disputes, refunds
from app.services.demo.judge import prepare
from sqlalchemy import select
from sqlalchemy.engine import make_url


def main() -> None:
    settings = get_settings()
    url = make_url(settings.database_url)
    if (
        url.host not in {"127.0.0.1", "localhost"}
        or not (url.database or "").endswith("_integration_browser_test")
        or settings.paypal_mode is not PayPalMode.FIXTURE
        or settings.ai_provider is not AIProvider.NONE
        or settings.refund_execution_enabled
    ):
        raise RuntimeError(
            "Requires isolated loopback integration-browser DB, fixture mode, AI none"
        )
    seed()
    demo_load(2026, if_empty=True)
    with get_sessionmaker()() as db:
        prepare(db, password=os.environ.get("SENTINEL_JUDGE_PASSWORD", ""))
        user = db.scalar(
            select(User).where(User.email == "curator@sentinel-demo.example")
        )
        assert user is not None
        case = db.scalar(
            select(Case)
            .join(Transaction, Transaction.id == Case.transaction_id)
            .where(
                Case.merchant_id == user.merchant_id,
                Transaction.status == TransactionStatus.CAPTURED,
            )
            .order_by(Case.created_at, Case.id)
        )
        assert case is not None
        principal = Principal(user=user, session=UserSession())
        if (
            db.scalar(
                select(RefundRequest.id).where(
                    RefundRequest.merchant_id == user.merchant_id
                )
            )
            is None
        ):
            refunds.create(db, principal, case.id, amount_minor=1)
        dispute = disputes.create_demo(
            db, principal, case.id, "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
        )
        disputes.draft(db, principal, dispute.id)
    print(
        "Prepared labelled local judge refund request and dispute draft; no provider calls."
    )


if __name__ == "__main__":
    main()
