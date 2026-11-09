"""Provision a private read-only demo tenant without touching merchant workspaces.

This is an operator CLI, never a public registration route. Its curator password is random and
not returned. The judge gets VIEWER access to prebuilt, explicitly synthetic material only.
"""

import io
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.auth.passwords import hash_password, verify_password
from app.models import (
    ApprovalRequest,
    Case,
    EvidenceArtifact,
    EvidencePacket,
    InvestigationRun,
    Merchant,
    Product,
    Transaction,
    User,
    UserSession,
)
from app.models.enums import (
    ApprovalActionType,
    DataOrigin,
    EvidenceCategory,
    InvestigationStatus,
    MerchantEnvironment,
    RiskBand,
    Role,
    TransactionStatus,
)
from app.services import approvals, audit, packets
from app.services.demo.loader import load_scenario
from app.services.evidence import service as evidence
from app.services.investigation import runner
from app.services.risk.scoring import score_transaction

MERCHANT = "SENTINEL isolated judge demo"
JUDGE_EMAIL = "judge@sentinel-demo.example"
CURATOR_EMAIL = "curator@sentinel-demo.example"
FRESH_VERSION = "judge-fresh-v1"


def prepare(db: Session, *, password: str, fresh: bool = False) -> dict[str, str]:
    if len(password) < 16:
        raise ValueError("Judge password must be at least 16 characters; supply it securely")
    merchant = db.scalar(select(Merchant).where(Merchant.name == MERCHANT))
    if merchant is None:
        merchant = Merchant(name=MERCHANT, environment=MerchantEnvironment.DEMO)
        db.add(merchant)
        db.flush()
    if merchant.environment is not MerchantEnvironment.DEMO:
        raise ValueError("Reserved demo merchant is not a DEMO workspace")
    users = {}
    for email, role in ((JUDGE_EMAIL, Role.VIEWER), (CURATOR_EMAIL, Role.ANALYST)):
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                merchant_id=merchant.id,
                email=email,
                role=role,
                password_hash=hash_password(
                    password if role is Role.VIEWER else secrets.token_urlsafe(48)
                ),
            )
            db.add(user)
            db.flush()
        elif user.merchant_id != merchant.id or user.role is not role:
            raise ValueError("Reserved demo identity conflicts with an existing account")
        elif role is Role.VIEWER and not verify_password(user.password_hash, password):
            raise ValueError("Existing judge password differs; this command never rotates it")
        users[role] = user
    db.commit()
    if (
        db.scalar(select(Transaction.id).where(Transaction.merchant_id == merchant.id).limit(1))
        is None
    ):
        load_scenario(db, merchant.id, seed=2026)
    # Refuse to reuse a workspace containing actual merchant/provider records.
    if db.scalar(
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
    ):
        raise ValueError("Demo workspace contains non-synthetic transactions")
    case: Case | None
    if fresh:
        case = _fresh_case(db, merchant)
    else:
        case = db.scalar(
            select(Case)
            .where(Case.merchant_id == merchant.id, Case.data_origin == DataOrigin.SYNTHETIC_DEMO)
            .order_by(Case.created_at, Case.id)
            .limit(1)
        )
    if case is None:
        raise ValueError("Synthetic scenario produced no review case")
    # A trusted operator invokes existing domain services; no browser session or public bypass
    # is created for the internal curator. Its random password is discarded.
    principal = Principal(user=users[Role.ANALYST], session=UserSession())
    if (
        db.scalar(select(EvidenceArtifact.id).where(EvidenceArtifact.case_id == case.id).limit(1))
        is None
    ):
        out = io.BytesIO()
        canvas = Canvas(out)
        canvas.drawString(40, 780, "SYNTHETIC DEMO DOCUMENT - NOT DELIVERY OR PAYMENT PROOF")
        canvas.drawString(
            40, 760, "Illustrative review attachment for the isolated judge workspace."
        )
        canvas.save()
        evidence.upload(
            db,
            principal,
            case.id,
            data=out.getvalue(),
            declared_type="application/pdf",
            filename="synthetic-demo-document.pdf",
            category=EvidenceCategory.OTHER,
            description=(
                "Synthetic demonstration attachment. No merchant or provider fact is established."
            ),
        )
    completed = db.scalar(
        select(InvestigationRun)
        .where(
            InvestigationRun.case_id == case.id,
            InvestigationRun.status == InvestigationStatus.COMPLETED,
        )
        .limit(1)
    )
    if completed is None:
        run = runner.start(db, principal, case.id, deterministic=True)
        runner.execute(run.id)
        db.expire_all()
        completed = db.get(InvestigationRun, run.id)
        if completed is None or completed.status is not InvestigationStatus.COMPLETED:
            raise ValueError("Deterministic demo investigation failed")
    packet = db.scalar(select(EvidencePacket).where(EvidencePacket.case_id == case.id).limit(1))
    if packet is None:
        packet = packets.generate(db, principal, case.id)
    if (
        db.scalar(select(ApprovalRequest.id).where(ApprovalRequest.case_id == case.id).limit(1))
        is None
    ):
        approvals.create(
            db,
            principal,
            case.id,
            action=ApprovalActionType.EVIDENCE_PACKET_INTERNAL,
            packet_id=packet.id,
            justification="DEMO: independent administrator review required; no PayPal submission.",
        )
    return {
        "merchant_id": str(merchant.id),
        "case_id": str(case.id),
        "judge_email": JUDGE_EMAIL,
        "role": Role.VIEWER.value,
        "data_origin": case.data_origin.value,
    }


def _fresh_case(db: Session, merchant: Merchant) -> Case:
    """Append a daily explicit fixture scenario; never rewrite earlier cases or audit times.

    Every dated version has its own payer reference and 20 prior SIMULATED history rows. No
    order/capture/refund request is made. The frozen model decides whether the target is HIGH.
    A repeat on the same UTC day retains the original scenario and its original deadline.
    """
    now = datetime.now(UTC)
    version = f"{FRESH_VERSION}-{now:%Y%m%d}"
    existing = db.scalar(
        select(Transaction).where(
            Transaction.merchant_id == merchant.id,
            Transaction.create_idempotency_key == version,
        )
    )
    if existing is not None:
        case = db.scalar(select(Case).where(Case.transaction_id == existing.id))
        if case is None:
            raise ValueError(
                "Existing fresh fixture has no review case; inspect without overwriting"
            )
        return case
    products = []
    for sku, name, amount in (
        ("JUDGE-HISTORY", "Demonstration history item", 1000),
        ("JUDGE-REVIEW", "Demonstration review bundle", 500000),
    ):
        product = db.scalar(
            select(Product).where(Product.merchant_id == merchant.id, Product.sku == sku)
        )
        if product is None:
            product = Product(
                merchant_id=merchant.id,
                sku=sku,
                name=name,
                description="Explicitly simulated judge fixture. Not a PayPal payment.",
                price_minor=amount,
                currency="USD",
            )
            db.add(product)
            db.flush()
        elif product.price_minor != amount or product.currency != "USD":
            raise ValueError("Judge fixture catalog conflicts with its recorded price/currency")
        products.append(product)
    target_at = now - timedelta(minutes=1)
    payer = f"SIM-JUDGE-PAYER-{now:%Y%m%d}"
    for i in range(20):
        ref = f"{version}-history-{i}"
        at = target_at - timedelta(minutes=i + 2)
        db.add(
            Transaction(
                merchant_id=merchant.id,
                product_id=products[0].id,
                quantity=1,
                amount_minor=1000,
                currency="USD",
                status=TransactionStatus.REFUNDED,
                provider_status="FIXTURE_ONLY",
                payer_reference=payer,
                create_idempotency_key=ref,
                paypal_request_id=ref,
                provider_summary={"judge_scenario_version": FRESH_VERSION, "fixture": True},
                data_origin=DataOrigin.SIMULATED,
                occurred_at=at,
                refunded_at=at + timedelta(seconds=30),
            )
        )
    txn = Transaction(
        merchant_id=merchant.id,
        product_id=products[1].id,
        quantity=1,
        paypal_order_id=f"SIM-JUDGE-ORDER-{uuid.uuid4().hex[:16]}",
        paypal_capture_id=f"SIM-JUDGE-CAPTURE-{uuid.uuid4().hex[:16]}",
        amount_minor=500000,
        currency="USD",
        status=TransactionStatus.CAPTURED,
        provider_status="FIXTURE_ONLY",
        payer_reference=payer,
        create_idempotency_key=version,
        paypal_request_id=version,
        provider_summary={"judge_scenario_version": FRESH_VERSION, "fixture": True},
        data_origin=DataOrigin.SIMULATED,
        occurred_at=target_at,
    )
    db.add(txn)
    db.flush()
    assessment = score_transaction(db, txn, trigger="judge_fixture", actor_id=None)
    if assessment.risk_band is not RiskBand.HIGH:
        db.rollback()
        raise ValueError("Frozen model did not flag this fixture HIGH; never force the score")
    case = db.scalar(select(Case).where(Case.transaction_id == txn.id))
    if case is None:
        raise ValueError("Frozen model HIGH fixture did not produce a review case")
    audit.record(
        db,
        action="demo.fixture.created",
        entity_type="case",
        entity_id=case.id,
        merchant_id=merchant.id,
        actor_id=None,
        actor_type="SYSTEM",
        metadata={
            "scenario_version": FRESH_VERSION,
            "data_origin": DataOrigin.SIMULATED.value,
            "transaction_id": str(txn.id),
            "provider_called": False,
        },
    )
    db.commit()
    return case
