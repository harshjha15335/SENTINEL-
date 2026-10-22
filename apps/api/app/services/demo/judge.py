"""Provision a private read-only demo tenant without touching merchant workspaces.

This is an operator CLI, never a public registration route. Its curator password is random and
not returned. The judge gets VIEWER access to prebuilt, explicitly synthetic material only.
"""

import io
import secrets

from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
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
    Role,
)
from app.services import approvals, packets
from app.services.demo.loader import load_scenario
from app.services.evidence import service as evidence
from app.services.investigation import runner

MERCHANT = "SENTINEL isolated judge demo"
JUDGE_EMAIL = "judge@sentinel-demo.example"
CURATOR_EMAIL = "curator@sentinel-demo.example"


def prepare(db: Session, *, password: str) -> dict[str, str]:
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
        )
        .limit(1)
    ):
        raise ValueError("Demo workspace contains non-synthetic transactions")
    case = db.scalar(
        select(Case)
        .where(Case.merchant_id == merchant.id)
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
        "data_origin": DataOrigin.SYNTHETIC_DEMO.value,
    }
