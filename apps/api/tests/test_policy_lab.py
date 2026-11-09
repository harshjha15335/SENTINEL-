"""Validation-only inference, honest cost assumptions, and shadow governance isolation."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models import AuditEvent
from app.models.enums import Role
from app.models.policy import PolicyDraft
from app.schemas.policy import PolicyParameters
from app.services import policy
from app.services.policy import ValidationData, curves, metrics, simulate, validation_data
from app.services.risk.model import ARTIFACT_ROOT, get_model
from tests.conftest import login


def small_data():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return ValidationData(
        (0.9, 0.8, 0.2, 0.1), (1, 0, 1, 0), now, now + timedelta(days=1), "unit-model", "a" * 64, 1
    )


def test_confusion_costs_and_capacity_are_explicit():
    p = PolicyParameters(
        high_threshold=0.5,
        review_capacity_share=0.25,
        false_positive_cost_usd=3,
        false_negative_cost_usd=10,
        investigation_cost_usd=2,
        average_value_at_risk_usd=100,
        recovery_share=0.5,
    )
    m = metrics(small_data(), p)
    assert (m.tp, m.fp, m.tn, m.fn) == (1, 1, 1, 1)
    assert m.precision == 0.5 and m.recall == 0.5
    assert m.review_capacity_count == 1 and m.over_capacity and m.capacity_utilization == 2
    assert m.review_cost_usd == 4 and m.false_positive_cost_usd == 3
    assert m.missed_outcome_cost_usd == 10 and m.residual_loss_usd == 150
    assert m.total_assumed_cost_usd == 167 and m.estimated_recoverable_usd == 50
    assert metrics(small_data(), p.model_copy(update={"high_threshold": 1})).flagged == 0
    assert metrics(small_data(), p.model_copy(update={"high_threshold": 0})).flagged == 4


def test_roc_pr_handle_ties_and_calculate_real_areas():
    roc, _pr, auc, ap = curves(small_data())
    assert roc[0].x == 0 and roc[-1].x == 1 and roc[-1].y == 1
    assert auc == 0.75 and ap == pytest.approx((1 + 2 / 3) / 2)
    tied = ValidationData((0.5, 0.5), (1, 0), small_data().start, small_data().end, "unit", "x", 0)
    _, _, auc, ap = curves(tied)
    assert auc == 0.5 and ap == 0.5


def test_simulator_only_infers_validation_and_preserves_artifacts(monkeypatch):
    model = get_model()
    before = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ARTIFACT_ROOT / model.version).glob("*.json")
    }
    predict = model.predict
    compute = policy.compute_features
    seen = []
    calls = []

    def spy_predict(rows):
        calls.append(len(rows))
        return predict(rows)

    def spy_compute(view, payer, history):
        seen.append(view.occurred_at)
        return compute(view, payer, history)

    monkeypatch.setattr(model, "predict", spy_predict)
    monkeypatch.setattr(policy, "compute_features", spy_compute)
    validation_data.cache_clear()
    result = simulate(PolicyParameters())
    assert calls == [model.metadata["split"]["valid_rows"]]
    assert len(seen) == 1810
    assert all(t < datetime.fromisoformat(model.metadata["split"]["test_start"]) for t in seen)
    assert result.validation_rows == 1810 and result.frozen_test_rows == 1811
    assert result.dataset_sha256 == model.metadata["dataset"]["sha256"]
    assert result.roc_auc == pytest.approx(0.8468170070992651)
    assert result.average_precision == pytest.approx(0.3784291013067555)
    assert model.high_threshold == 0.1036
    assert before == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (ARTIFACT_ROOT / model.version).glob("*.json")
    }
    validation_data.cache_clear()


def test_dataset_mismatch_fails_closed(monkeypatch):
    validation_data.cache_clear()
    monkeypatch.setattr(policy, "generate", lambda seed: [])
    with pytest.raises(policy.PolicyDataUnavailable):
        validation_data()
    validation_data.cache_clear()


def test_policy_api_roles_shadow_approval_and_cross_merchant(app_client, db, tenant, other_tenant):
    assert app_client.get("/api/v1/policy-lab/drafts").status_code == 401
    csrf = login(app_client, tenant.users[Role.VIEWER].email)
    assert app_client.get("/api/v1/policy-lab/simulate?high_threshold=0.2").status_code == 200
    body = {
        "name": "Validation proposal",
        "rationale": "Lower threshold for capacity comparison",
        "parameters": PolicyParameters().model_dump(),
    }
    assert (
        app_client.post(
            "/api/v1/policy-lab/drafts", json=body, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    # Missing CSRF is rejected even for administrators.
    assert app_client.post("/api/v1/policy-lab/drafts", json=body).status_code == 403
    response = app_client.post(
        "/api/v1/policy-lab/drafts", json=body, headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 201, response.text
    ident = response.json()["id"]
    digest = response.json()["snapshot_sha256"]
    assert response.json()["shadow_only"] is True
    submit = app_client.post(
        f"/api/v1/policy-lab/drafts/{ident}/submit", headers={"X-CSRF-Token": csrf}
    )
    assert submit.status_code == 200 and submit.json()["status"] == "PENDING_APPROVAL"
    assert (
        app_client.post(
            f"/api/v1/policy-lab/drafts/{ident}/decide",
            json={"decision": "APPROVED"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    othercsrf = login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get("/api/v1/policy-lab/drafts").json() == []
    assert (
        app_client.post(
            f"/api/v1/policy-lab/drafts/{ident}/decide",
            json={"decision": "APPROVED"},
            headers={"X-CSRF-Token": othercsrf},
        ).status_code
        == 404
    )
    # Make an analyst request so a different existing administrator can decide.
    analystcsrf = login(app_client, tenant.users[Role.ANALYST].email)
    response = app_client.post(
        "/api/v1/policy-lab/drafts", json=body, headers={"X-CSRF-Token": analystcsrf}
    )
    second = response.json()["id"]
    assert (
        app_client.post(
            f"/api/v1/policy-lab/drafts/{second}/submit", headers={"X-CSRF-Token": analystcsrf}
        ).status_code
        == 200
    )
    csrf = login(app_client, tenant.users[Role.ADMIN].email)
    approved = app_client.post(
        f"/api/v1/policy-lab/drafts/{second}/decide",
        json={"decision": "APPROVED"},
        headers={"X-CSRF-Token": csrf},
    )
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    assert approved.json()["shadow_only"] is True
    assert (
        app_client.post(
            f"/api/v1/policy-lab/drafts/{second}/decide",
            json={"decision": "REJECTED"},
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 409
    )
    assert get_model().high_threshold == 0.1036
    row = db.scalar(select(PolicyDraft).where(PolicyDraft.id == ident))
    assert row.snapshot_sha256 == digest
    actions = list(
        db.scalars(select(AuditEvent.action).where(AuditEvent.entity_type == "policy_draft"))
    )
    assert "policy.submitted" in actions and "policy.decided" in actions
    assert body["rationale"] not in str(list(db.scalars(select(AuditEvent.metadata_))))


def test_policy_submitted_snapshot_is_database_immutable(app_client, db, tenant):
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    body = {
        "name": "Immutable",
        "rationale": "Validation what-if policy proposal",
        "parameters": PolicyParameters().model_dump(),
    }
    response = app_client.post(
        "/api/v1/policy-lab/drafts", json=body, headers={"X-CSRF-Token": csrf}
    )
    ident = response.json()["id"]
    assert (
        app_client.post(
            f"/api/v1/policy-lab/drafts/{ident}/submit", headers={"X-CSRF-Token": csrf}
        ).status_code
        == 200
    )
    with pytest.raises(DBAPIError):
        db.execute(
            text("update policy_drafts set rationale='tampered' where id=:id"), {"id": ident}
        )
        db.commit()
    db.rollback()
