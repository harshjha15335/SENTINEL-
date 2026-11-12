"""Public viewer access to an isolated, pre-provisioned synthetic judge tenant.

Only operator-side provision() may seed data. The public login endpoint only issues
short-lived VIEWER sessions after verifying the tenant contains no provider data.
"""

import secrets

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import Case, EvidencePacket, InvestigationRun, Merchant, Transaction, User
from app.models.enums import DataOrigin, InvestigationStatus, MerchantEnvironment, Role
from app.services.demo.judge import FRESH_VERSION, JUDGE_EMAIL, MERCHANT, prepare


def demo_viewer(db: Session) -> User | None:
    merchant = db.scalar(select(Merchant).where(Merchant.name == MERCHANT))
    if (
        merchant is None
        or merchant.environment is not MerchantEnvironment.DEMO
        or merchant.status != "ACTIVE"
    ):
        return None
    viewer = db.scalar(select(User).where(User.email == JUDGE_EMAIL))
    if viewer is None or viewer.merchant_id != merchant.id or viewer.role is not Role.VIEWER:
        return None
    # Do not make any records accessible if a provider-origin record has
    # accidentally entered the judge tenant.
    invalid = db.scalar(
        select(Transaction.id)
        .where(
            Transaction.merchant_id == merchant.id,
            Transaction.data_origin != DataOrigin.SYNTHETIC_DEMO,
            or_(
                Transaction.data_origin != DataOrigin.SIMULATED,
                func.coalesce(
                    Transaction.provider_summary["judge_scenario_version"].as_string(), ""
                )
                != FRESH_VERSION,
            ),
        )
        .limit(1)
    )
    if invalid is not None:
        return None
    # A guest must open an already prepared, cited, read-only demonstration;
    # the public auth request never generates a payment, case or investigation.
    prepared = db.scalar(
        select(Case.id)
        .join(EvidencePacket, EvidencePacket.case_id == Case.id)
        .join(
            InvestigationRun,
            and_(
                InvestigationRun.case_id == Case.id,
                InvestigationRun.status == InvestigationStatus.COMPLETED,
            ),
        )
        .where(
            Case.merchant_id == merchant.id,
            Case.data_origin == DataOrigin.SYNTHETIC_DEMO,
        )
        .limit(1)
    )
    return viewer if prepared is not None else None


def provision(db: Session) -> None:
    """Idempotent, operator-side pre-deploy preparation; no public signup."""
    if db.scalar(select(User.id).where(User.email == JUDGE_EMAIL)) is None:
        # An unguessable random password is never logged or stored in an env var.
        # Guest access uses a scoped session, never this password.
        prepare(db, password=secrets.token_urlsafe(40))
    if demo_viewer(db) is None:
        raise ValueError("The isolated synthetic judge workspace is not fully prepared")
