import threading
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import ConflictError
from app.db.session import get_sessionmaker
from app.models import ActionExecution, ApprovalDecision, ApprovalRequest, Case, Transaction
from app.models.enums import (
    ApprovalDecisionValue,
    CasePriority,
    CaseStatus,
    Role,
    TransactionStatus,
)
from app.services import approvals
from tests.conftest import Tenant
from tests.phase4 import client_for, make_case


def _create(client, h, case_id, action, **extra):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/cases/{case_id}/approvals",
        json={"action_type": action, "justification": "Analyst reasoning", **extra},
        headers=h,
    )


def _decide(client, h, case_id, approval_id, verb, comment="Checked the snapshot"):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/cases/{case_id}/approvals/{approval_id}/{verb}",
        json={"comment": comment},
        headers=h,
    )


@pytest.fixture
def no_refunds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any attempt to move money fails the test loudly."""
    from app.services.paypal.fixture import FixturePayPalGateway
    from app.services.paypal.sandbox import SandboxPayPalGateway

    def boom(*a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("no refund may be executed in Phase 4")

    monkeypatch.setattr(FixturePayPalGateway, "refund_capture", boom)
    monkeypatch.setattr(SandboxPayPalGateway, "refund_capture", boom)


def test_refund_approval_records_intent_and_never_executes(
    db: Session, tenant: Tenant, no_refunds: None
) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    admin, dh = client_for(tenant, Role.ADMIN)

    # The client cannot supply an amount.
    assert _create(analyst, ah, case.id, "PREPARE_REFUND", amount_minor=1).status_code == 422

    created = _create(analyst, ah, case.id, "PREPARE_REFUND")
    assert created.status_code == 201, created.text
    req = created.json()
    assert req["status"] == "PENDING"
    assert req["required_roles"] == ["ADMIN"]
    snap = req["action_snapshot"]
    assert snap["amount_minor"] == 4200 and snap["currency"] == "USD"
    assert snap["paypal_executable"] is False  # synthetic payment: nothing to refund at PayPal
    assert len(req["snapshot_sha256"]) == 64

    # The requester (and analysts in general) cannot approve a refund.
    assert _decide(analyst, ah, case.id, req["id"], "approve").status_code == 403

    approved = _decide(admin, dh, case.id, req["id"], "approve")
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "APPROVED"
    assert body["decision"]["decided_by_role"] == "ADMIN"
    assert body["execution"]["status"] == "NOT_EXECUTED"
    assert body["execution"]["provider_called"] is False
    assert "no PayPal request was made" in body["execution"]["detail"]["effect"]

    db.expire_all()
    txn = db.get(Transaction, case.transaction_id)
    assert txn is not None and txn.status is TransactionStatus.CAPTURED and txn.refunded_at is None

    # Repeated decisions are refused.
    assert _decide(admin, dh, case.id, req["id"], "approve").status_code == 409
    assert _decide(admin, dh, case.id, req["id"], "reject").status_code == 409

    history = analyst.get(f"/api/v1/cases/{case.id}/approvals").json()
    assert [h["status"] for h in history] == ["APPROVED"]
    timeline = {a["action"] for a in analyst.get(f"/api/v1/cases/{case.id}").json()["audit"]}
    assert {"approval.requested", "approval.approved", "action.execution_recorded"} <= timeline


def test_manual_review_approval_changes_only_the_case(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    admin, dh = client_for(tenant, Role.ADMIN)
    analyst, ah = client_for(tenant, Role.ANALYST)
    req = _create(admin, dh, case.id, "MANUAL_REVIEW").json()
    assert req["required_roles"] == ["ADMIN", "ANALYST"]
    # Nobody decides their own request, whatever their role.
    assert _decide(admin, dh, case.id, req["id"], "approve").status_code == 403
    done = _decide(analyst, ah, case.id, req["id"], "approve").json()
    assert done["execution"]["status"] == "COMPLETED_INTERNAL"
    db.expire_all()
    c = db.get(Case, case.id)
    assert c is not None and c.priority is CasePriority.HIGH and c.status is CaseStatus.IN_REVIEW


def test_reject_and_duplicate_pending(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    admin, dh = client_for(tenant, Role.ADMIN)
    req = _create(analyst, ah, case.id, "MANUAL_REVIEW").json()
    assert _create(analyst, ah, case.id, "MANUAL_REVIEW").status_code == 409
    rejected = _decide(admin, dh, case.id, req["id"], "reject", "Not needed").json()
    assert rejected["status"] == "REJECTED"
    assert rejected["execution"] is None
    assert rejected["decision"]["comment"] == "Not needed"
    # A new request may be made once the earlier one is decided.
    assert _create(analyst, ah, case.id, "MANUAL_REVIEW").status_code == 201


def test_packet_approval_snapshots_the_exact_packet(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    admin, dh = client_for(tenant, Role.ADMIN)
    assert _create(analyst, ah, case.id, "EVIDENCE_PACKET_INTERNAL").status_code == 422
    assert (
        _create(analyst, ah, case.id, "EVIDENCE_PACKET_INTERNAL", packet_id=str(uuid.uuid4()))
    ).status_code == 404
    packet = analyst.post(f"/api/v1/cases/{case.id}/packets", headers=ah).json()
    req = _create(analyst, ah, case.id, "EVIDENCE_PACKET_INTERNAL", packet_id=packet["id"]).json()
    assert req["action_snapshot"]["packet_sha256"] == packet["sha256"]
    done = _decide(admin, dh, case.id, req["id"], "approve").json()
    assert done["execution"]["detail"]["packet_sha256"] == packet["sha256"]
    assert "Not submitted to PayPal" in done["execution"]["detail"]["effect"]


def test_viewer_and_cross_merchant_cannot_request_or_decide(
    db: Session, tenant: Tenant, other_tenant: Tenant
) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    req = _create(analyst, ah, case.id, "MANUAL_REVIEW").json()

    viewer, vh = client_for(tenant, Role.VIEWER)
    assert _create(viewer, vh, case.id, "MANUAL_REVIEW").status_code == 403
    assert _decide(viewer, vh, case.id, req["id"], "approve").status_code == 403
    assert viewer.get(f"/api/v1/cases/{case.id}/approvals").status_code == 200

    other, oh = client_for(other_tenant, Role.ADMIN)
    assert _decide(other, oh, case.id, req["id"], "approve").status_code == 404
    own = make_case(db, other_tenant, payer="SYN-PAYER-7")
    assert _decide(other, oh, own.id, req["id"], "approve").status_code == 404
    assert _create(other, oh, case.id, "MANUAL_REVIEW").status_code == 404


def test_refund_requires_a_captured_payment(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant, status=TransactionStatus.REFUNDED)
    analyst, ah = client_for(tenant, Role.ANALYST)
    assert _create(analyst, ah, case.id, "PREPARE_REFUND").status_code == 409


def test_concurrent_decisions_produce_exactly_one(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    req = _create(analyst, ah, case.id, "PREPARE_REFUND").json()
    admin_id = tenant.users[Role.ADMIN].id
    outcomes: list[str] = []
    barrier = threading.Barrier(6)

    def attempt(i: int) -> None:
        with get_sessionmaker()() as s:
            user = s.get(type(tenant.users[Role.ADMIN]), admin_id)
            principal = Principal(user=user, session=None)  # type: ignore[arg-type]
            decision = ApprovalDecisionValue.APPROVED if i % 2 else ApprovalDecisionValue.REJECTED
            barrier.wait()
            try:
                approvals.decide(
                    s, principal, case.id, uuid.UUID(req["id"]), decision=decision, comment="race"
                )
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["conflict"] * 5 + ["ok"]
    assert len(db.scalars(select(ApprovalDecision)).all()) == 1
    assert len(db.scalars(select(ActionExecution)).all()) <= 1


def test_snapshots_and_decisions_are_immutable_in_the_database(db: Session, tenant: Tenant) -> None:
    case = make_case(db, tenant)
    analyst, ah = client_for(tenant, Role.ANALYST)
    admin, dh = client_for(tenant, Role.ADMIN)
    req = _create(analyst, ah, case.id, "PREPARE_REFUND").json()

    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            text(
                "UPDATE approval_requests SET action_snapshot = "
                "jsonb_set(action_snapshot, '{amount_minor}', '999999') WHERE id = :id"
            ),
            {"id": req["id"]},
        )
    db.rollback()

    _decide(admin, dh, case.id, req["id"], "approve")
    with pytest.raises(DBAPIError, match="cannot be modified"):
        db.execute(text("UPDATE approval_decisions SET decision = 'REJECTED'"))
    db.rollback()
    with pytest.raises(DBAPIError, match="already decided"):
        db.execute(text("UPDATE approval_requests SET status = 'REJECTED'"))
    db.rollback()
    with pytest.raises(DBAPIError, match="no_provider_calls_in_phase4"):
        db.execute(text("UPDATE action_executions SET provider_called = true"))
    db.rollback()
    row = db.scalar(select(ApprovalRequest))
    assert row is not None and row.action_snapshot["amount_minor"] == 4200
