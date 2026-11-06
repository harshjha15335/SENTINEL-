"""Refund execution tests always inject in-memory gateways; no provider requests."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.auth.deps import Principal
from app.core.config import get_settings
from app.core.errors import ConflictError, PermissionDeniedError
from app.db.session import get_sessionmaker
from app.models import User, UserSession
from app.models.enums import DataOrigin, Role, TransactionStatus
from app.models.refunds import RefundRequest
from app.services import refunds
from app.services.paypal.types import PayPalError, PayPalErrorKind, RefundResult
from tests.phase4 import make_case


def principal(tenant, role):
    return Principal(user=tenant.users[role], session=UserSession())


class Provider:
    name = "sandbox"
    data_origin = DataOrigin.LIVE_SANDBOX

    def __init__(self, *, fail=None, status="COMPLETED"):
        self.calls = []
        self.fail = fail
        self.status = status

    def refund_capture(self, capture_id, *, amount, request_id, note):
        self.calls.append((capture_id, amount, request_id))
        if self.fail:
            raise self.fail
        return RefundResult("8MC585209K746392H" + str(len(self.calls)), self.status, amount)

    def get_capture(self, capture_id):
        return {
            "id": capture_id,
            "status": "COMPLETED",
            "amount": {"value": "42.00", "currency_code": "USD"},
        }

    def get_refund(self, refund_id):
        return {
            "id": refund_id,
            "status": "COMPLETED",
            "amount": {"value": "10.00", "currency_code": "USD"},
        }


def approved(db, tenant, monkeypatch, *, amount=1000):
    # These LIVE_SANDBOX-shaped records are unit-test fixtures, not real provider evidence.
    case = make_case(db, tenant, origin=DataOrigin.LIVE_SANDBOX)
    case.transaction.paypal_capture_id = "1A23456789012345B"
    db.commit()
    req = refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=amount)
    refunds.decide(
        db, principal(tenant, Role.ADMIN), req.id, decision="APPROVED", digest=req.snapshot_sha256
    )
    monkeypatch.setattr(refunds, "enabled", lambda: True)
    return req, case


def test_partial_and_full_balance_reservations_and_rejection(db, tenant):
    case = make_case(db, tenant)
    analyst = principal(tenant, Role.ANALYST)
    one = refunds.create(db, analyst, case.id, amount_minor=1000)
    full = refunds.create(db, analyst, case.id, amount_minor=None)
    assert full.amount_minor == 3200
    with pytest.raises(refunds.InvalidRefund):
        refunds.create(db, analyst, case.id, amount_minor=1)
    db.rollback()
    refunds.decide(
        db, principal(tenant, Role.ADMIN), one.id, decision="REJECTED", digest=one.snapshot_sha256
    )
    assert refunds.reserved_amount(db, case.transaction) == 3200


def test_independent_approval_and_default_disabled(db, tenant):
    case = make_case(db, tenant)
    admin = principal(tenant, Role.ADMIN)
    req = refunds.create(db, admin, case.id, amount_minor=100)
    with pytest.raises(PermissionDeniedError, match="own refund"):
        refunds.decide(db, admin, req.id, decision="APPROVED", digest=req.snapshot_sha256)
    with pytest.raises(PermissionDeniedError, match="disabled"):
        refunds.execute(db, admin, req.id, digest=req.snapshot_sha256, gateway=Provider())


def test_viewer_and_cross_merchant_denied(db, tenant, other_tenant):
    case = make_case(db, tenant)
    with pytest.raises(PermissionDeniedError):
        refunds.create(db, principal(tenant, Role.VIEWER), case.id, amount_minor=100)
    req = refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=100)
    from app.core.errors import NotFoundError

    with pytest.raises(NotFoundError):
        refunds.get(db, other_tenant.merchant.id, req.id)


def test_partial_completion_duplicate_execution_and_final_balance(db, tenant, monkeypatch):
    req, case = approved(db, tenant, monkeypatch)
    gateway = Provider()
    result = refunds.execute(
        db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
    )
    assert result.status == "SUCCEEDED" and result.submission_started
    assert case.transaction.status is TransactionStatus.PARTIALLY_REFUNDED
    refunds.execute(
        db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
    )
    assert len(gateway.calls) == 1
    assert gateway.calls[0][2] == req.request_key
    assert refunds.reserved_amount(db, case.transaction) == 1000


def test_timeout_reserves_balance_and_never_blindly_resubmits(db, tenant, monkeypatch):
    req, case = approved(db, tenant, monkeypatch)
    gateway = Provider(fail=PayPalError(PayPalErrorKind.NETWORK, "sanitized timeout"))
    result = refunds.execute(
        db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
    )
    assert result.status == "RECONCILIATION_REQUIRED"
    assert refunds.reserved_amount(db, case.transaction) == 1000
    with pytest.raises(ConflictError, match="never resubmitted"):
        refunds.execute(
            db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
        )
    with pytest.raises(ConflictError, match="unknown"):
        refunds.reconcile(db, principal(tenant, Role.ADMIN), req.id, gateway=gateway)
    assert len(gateway.calls) == 1


def test_provider_pending_is_read_only_reconciled(db, tenant, monkeypatch):
    req, _case = approved(db, tenant, monkeypatch)
    gateway = Provider(status="PENDING")
    refunds.execute(
        db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
    )
    assert req.status == "RECONCILIATION_REQUIRED" and req.provider_refund_id
    refunds.reconcile(db, principal(tenant, Role.ADMIN), req.id, gateway=gateway)
    assert req.status == "SUCCEEDED" and len(gateway.calls) == 1


def test_synthetic_never_executes_and_snapshot_mismatch(db, tenant, monkeypatch):
    case = make_case(db, tenant)
    req = refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=100)
    with pytest.raises(ConflictError, match="snapshot"):
        refunds.decide(
            db, principal(tenant, Role.ADMIN), req.id, decision="APPROVED", digest="0" * 64
        )
    refunds.decide(
        db, principal(tenant, Role.ADMIN), req.id, decision="APPROVED", digest=req.snapshot_sha256
    )
    monkeypatch.setattr(refunds, "enabled", lambda: True)
    gateway = Provider()
    with pytest.raises(PermissionDeniedError, match="genuine sandbox"):
        refunds.execute(
            db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
        )
    assert gateway.calls == []


def test_simultaneous_requests_cannot_overreserve(db, tenant):
    case = make_case(db, tenant)
    case_id, user_id = case.id, tenant.users[Role.ANALYST].id
    barrier = Barrier(2)

    def attempt():
        with get_sessionmaker()() as session:
            user = session.get(User, user_id)
            barrier.wait(timeout=10)
            try:
                refunds.create(
                    session, Principal(user=user, session=UserSession()), case_id, amount_minor=2500
                )
                return "created"
            except refunds.InvalidRefund:
                session.rollback()
                return "denied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == ["created", "denied"]
    assert db.scalar(select(func.sum(RefundRequest.amount_minor))) == 2500


def test_external_unknown_partial_refund_cannot_be_spent_again(db, tenant):
    case = make_case(db, tenant)
    case.transaction.status = TransactionStatus.PARTIALLY_REFUNDED
    case.transaction.refunded_at = datetime.now(UTC)
    db.commit()
    with pytest.raises(ConflictError, match="unknown"):
        refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=100)


def test_production_execution_stays_disabled(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "refund_execution_enabled", True, raising=False)
    assert refunds.enabled() is False


def test_external_partial_refund_after_request_blocks_execution(db, tenant, monkeypatch):
    req, case = approved(db, tenant, monkeypatch)
    case.transaction.status = TransactionStatus.PARTIALLY_REFUNDED
    case.transaction.refunded_at = datetime.now(UTC)
    db.commit()
    gateway = Provider()
    assert refunds.balance_known(db, case.transaction) is False
    with pytest.raises(ConflictError, match="unknown"):
        refunds.execute(
            db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
        )
    assert gateway.calls == []


def test_provider_unsynchronized_partial_refund_blocks_submission(db, tenant, monkeypatch):
    req, _case = approved(db, tenant, monkeypatch)
    gateway = Provider()
    monkeypatch.setattr(
        gateway,
        "get_capture",
        lambda identity: {
            "id": identity,
            "status": "PARTIALLY_REFUNDED",
            "amount": {"value": "42.00", "currency_code": "USD"},
        },
    )
    with pytest.raises(ConflictError, match="unsynchronized"):
        refunds.execute(
            db, principal(tenant, Role.ADMIN), req.id, digest=req.snapshot_sha256, gateway=gateway
        )
    assert gateway.calls == []


def test_partial_then_remaining_full_refund_never_exceeds_capture(db, tenant, monkeypatch):
    req, case = approved(db, tenant, monkeypatch)
    gateway = Provider()
    admin = principal(tenant, Role.ADMIN)
    refunds.execute(db, admin, req.id, digest=req.snapshot_sha256, gateway=gateway)
    final = refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=None)
    assert final.amount_minor == 3200
    refunds.decide(db, admin, final.id, decision="APPROVED", digest=final.snapshot_sha256)
    refunds.execute(db, admin, final.id, digest=final.snapshot_sha256, gateway=gateway)
    assert case.transaction.status is TransactionStatus.REFUNDED
    assert refunds.balance_known(db, case.transaction) is True
    assert sum(call[1].amount_minor for call in gateway.calls) == 4200
    with pytest.raises(ConflictError):
        refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=1)


def test_concurrent_execution_refreshes_locked_row_before_mutation(db, tenant, monkeypatch):
    req, _case = approved(db, tenant, monkeypatch)
    refund_id, digest, admin_id = req.id, req.snapshot_sha256, tenant.users[Role.ADMIN].id
    barrier = Barrier(2)
    original_get = refunds.get

    def get_with_initial_barrier(*args, **kwargs):
        row = original_get(*args, **kwargs)
        if not kwargs.get("lock"):
            barrier.wait(timeout=10)
        return row

    monkeypatch.setattr(refunds, "get", get_with_initial_barrier)
    gateway = Provider()

    def attempt():
        with get_sessionmaker()() as session:
            user = session.get(User, admin_id)
            try:
                refunds.execute(
                    session,
                    Principal(user=user, session=UserSession()),
                    refund_id,
                    digest=digest,
                    gateway=gateway,
                )
                return "accepted"
            except ConflictError:
                session.rollback()
                return "locked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert "accepted" in results and len(gateway.calls) == 1


def test_refund_api_enforces_roles_tenant_and_explicit_confirmation(
    db, tenant, other_tenant, app_client
):
    from tests.conftest import login

    case = make_case(db, tenant)
    csrf = login(app_client, tenant.users[Role.VIEWER].email)
    endpoint = f"/api/v1/cases/{case.id}/refunds"
    assert (
        app_client.post(
            endpoint, json={"amount_minor": 100}, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    assert app_client.post(endpoint, json={"amount_minor": 100}).status_code == 403
    response = app_client.post(endpoint, json={"amount_minor": 100}, headers={"X-CSRF-Token": csrf})
    assert response.status_code == 201
    refund = response.json()
    csrf = login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get(f"/api/v1/refunds/{refund['id']}").status_code == 404
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    assert (
        app_client.post(
            f"/api/v1/refunds/{refund['id']}/execute",
            json={"confirm": False, "snapshot_sha256": refund["snapshot_sha256"]},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 422
    )


def test_refund_snapshot_and_decision_are_database_immutable(db, tenant, monkeypatch):
    from sqlalchemy import update
    from sqlalchemy.exc import DBAPIError

    req, _case = approved(db, tenant, monkeypatch)
    identity = req.id
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(update(RefundRequest).where(RefundRequest.id == identity).values(amount_minor=1))
        db.commit()
    db.rollback()
    with pytest.raises(DBAPIError, match="immutable"):
        db.execute(
            update(RefundRequest)
            .where(RefundRequest.id == identity)
            .values(decided_by_role="VIEWER")
        )
        db.commit()
    db.rollback()


def test_financial_refund_ledger_cannot_be_removed_by_case_delete(db, tenant):
    from sqlalchemy import delete
    from sqlalchemy.exc import DBAPIError

    from app.models import Case

    case = make_case(db, tenant)
    refunds.create(db, principal(tenant, Role.ANALYST), case.id, amount_minor=100)
    with pytest.raises(DBAPIError):
        db.execute(delete(Case).where(Case.id == case.id))
        db.commit()
    db.rollback()
    assert db.scalar(select(func.count()).select_from(RefundRequest)) == 1
