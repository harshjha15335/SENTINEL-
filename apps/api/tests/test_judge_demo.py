from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.models import ApprovalRequest, AuditEvent, Case, Transaction, User
from app.models.enums import DataOrigin, Role
from app.services.demo.judge import FRESH_VERSION, JUDGE_EMAIL, prepare
from tests.conftest import PASSWORD


def test_isolated_judge_demo_is_read_only_and_repeatable(db, app_client: TestClient, other_tenant):
    result = prepare(db, password=PASSWORD)
    counts = (
        db.scalar(select(func.count()).select_from(Transaction)),
        db.scalar(select(func.count()).select_from(Case)),
    )
    assert prepare(db, password=PASSWORD) == result
    assert counts == (
        db.scalar(select(func.count()).select_from(Transaction)),
        db.scalar(select(func.count()).select_from(Case)),
    )
    user = db.scalar(select(User).where(User.email == JUDGE_EMAIL))
    assert user.role is Role.VIEWER and user.merchant_id != other_tenant.merchant.id
    assert (
        db.scalar(
            select(Transaction.id)
            .where(
                Transaction.merchant_id == user.merchant_id,
                Transaction.data_origin != DataOrigin.SYNTHETIC_DEMO,
            )
            .limit(1)
        )
        is None
    )
    response = app_client.post(
        "/api/v1/auth/login", json={"email": JUDGE_EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 200
    headers = {"X-CSRF-Token": response.json()["csrf_token"]}
    case = result["case_id"]
    assert app_client.get("/api/v1/demo/scenario").json()["case_id"] == case
    evidence = app_client.get(f"/api/v1/cases/{case}/evidence").json()["items"][0]
    assert evidence["verified"] is False and "Synthetic" in evidence["description"]
    assert (
        app_client.get(f"/api/v1/cases/{case}/evidence/{evidence['id']}/download").status_code
        == 200
    )
    packet = app_client.get(f"/api/v1/cases/{case}/packets").json()[0]
    assert (
        app_client.get(f"/api/v1/cases/{case}/packets/{packet['id']}/download").status_code == 200
    )
    assert (
        app_client.post(
            f"/api/v1/cases/{case}/investigations", headers=headers, json={"mode": "deterministic"}
        ).status_code
        == 403
    )
    assert app_client.get("/api/v1/operations/webhooks").status_code == 403
    assert (
        db.scalar(select(ApprovalRequest).where(ApprovalRequest.case_id == case)).status.value
        == "PENDING"
    )


def test_judge_scenario_is_not_a_public_or_cross_workspace_route(app_client, other_tenant):
    from tests.conftest import login

    assert app_client.get("/api/v1/demo/scenario").status_code == 401
    login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get("/api/v1/demo/scenario").status_code == 404


def test_fresh_demo_appends_mapped_fixture_without_rewriting_history(db, app_client):
    original = prepare(db, password=PASSWORD)
    old_case = db.get(Case, original["case_id"])
    before = datetime.now(UTC)
    old_case.created_at = before - timedelta(days=8)
    old_case.due_at = before - timedelta(days=7)
    db.commit()
    old_case_values = (old_case.created_at, old_case.due_at, old_case.status)
    old_ids = set(db.scalars(select(Transaction.id)))
    old_audit = {
        row.id: (row.created_at, row.action, row.metadata_)
        for row in db.scalars(select(AuditEvent))
    }

    fresh = prepare(db, password=PASSWORD, fresh=True)
    assert fresh["case_id"] != original["case_id"]
    assert fresh["data_origin"] == DataOrigin.SIMULATED.value
    case = db.get(Case, fresh["case_id"])
    txn = db.get(Transaction, case.transaction_id)
    assert case.due_at > before + timedelta(hours=23)
    assert before - timedelta(minutes=2) <= txn.occurred_at <= datetime.now(UTC)
    assert txn.product is not None and txn.product.name == "Demonstration review bundle"
    assert txn.product.price_minor == txn.amount_minor
    assert txn.provider_summary["judge_scenario_version"] == FRESH_VERSION
    assert case.risk_assessment_id is not None
    assert len(set(db.scalars(select(Transaction.id))) - old_ids) == 21
    db.refresh(old_case)
    assert (old_case.created_at, old_case.due_at, old_case.status) == old_case_values
    assert all(
        (
            db.get(AuditEvent, identity).created_at,
            db.get(AuditEvent, identity).action,
            db.get(AuditEvent, identity).metadata_,
        )
        == values
        for identity, values in old_audit.items()
    )

    assert prepare(db, password=PASSWORD, fresh=True) == fresh
    assert len(set(db.scalars(select(Transaction.id))) - old_ids) == 21
    response = app_client.post(
        "/api/v1/auth/login", json={"email": JUDGE_EMAIL, "password": PASSWORD}
    )
    assert response.status_code == 200
    scenario = app_client.get("/api/v1/demo/scenario").json()
    assert scenario["case_id"] == fresh["case_id"]
    assert scenario["scenario_version"] == FRESH_VERSION
    assert scenario["investigation_mode"] == "DETERMINISTIC"
    assert app_client.get("/api/v1/operations/webhooks").status_code == 403
