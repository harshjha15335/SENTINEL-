from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.v1.monitoring import router
from app.models import Case, RiskAssessment
from app.models.enums import (
    CasePriority,
    CaseSource,
    CaseStatus,
    DataOrigin,
    PolicyDecision,
    RiskBand,
    Role,
)
from app.services import monitoring
from tests.conftest import login
from tests.test_risk_cases import T0, _txn


@pytest.fixture
def monitor_client(app_client):
    if not any(
        getattr(route, "path", None) == "/api/v1/monitoring/risk" for route in app_client.app.routes
    ):
        app_client.app.include_router(router, prefix="/api/v1")
    return app_client


def assessment(db, txn, at, score, *, version="test-model"):
    band = RiskBand.HIGH if score >= 0.5 else RiskBand.LOW
    row = RiskAssessment(
        merchant_id=txn.merchant_id,
        transaction_id=txn.id,
        model_version=version,
        feature_version="test-features",
        risk_score=score,
        risk_band=band,
        policy_decision=PolicyDecision.ESCALATE if band is RiskBand.HIGH else PolicyDecision.ALLOW,
        policy_mode="SHADOW",
        thresholds={},
        feature_snapshot={"amount_log": 2.0},
        explanation={},
        limitations=[],
        data_origin=txn.data_origin,
        trigger="test",
        created_at=at,
    )
    db.add(row)
    db.flush()
    return row


def test_monitoring_is_authenticated_scoped_and_past_only(
    monitor_client: TestClient, db, tenant, other_tenant
):
    assert (
        monitor_client.get("/api/v1/monitoring/risk?data_origin=SYNTHETIC_DEMO").status_code == 401
    )
    own = _txn(db, tenant, at=T0 - timedelta(days=1))
    prior = _txn(db, tenant, at=T0 - timedelta(days=8))
    _txn(db, other_tenant, at=T0 - timedelta(days=1))
    _txn(db, tenant, at=T0 - timedelta(days=1), origin=DataOrigin.SIMULATED)
    _txn(db, tenant, at=T0 + timedelta(days=1))
    assessment(db, own, T0 - timedelta(hours=2), 0.7)
    assessment(db, own, T0 + timedelta(hours=2), 0.1, version="future-model")
    assessment(db, prior, T0 - timedelta(days=7), 0.2)
    db.commit()
    login(monitor_client, tenant.users[Role.VIEWER].email)
    r = monitor_client.get(
        "/api/v1/monitoring/risk",
        params={"data_origin": "SYNTHETIC_DEMO", "days": 7, "as_of": T0.isoformat()},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["current_transactions"] == 1 and data["reference_transactions"] == 1
    assert data["current_scored"] == 1 and data["reference_scored"] == 1
    assert data["risk_bands"] == {"HIGH": 1}
    assert data["model_versions"] == {"test-model": 1}
    assert data["score_psi"] is None
    assert r.headers["cache-control"] == "no-store"
    assert data["current_window"]["end"].startswith("2026-09-01")


def test_empty_monitoring_never_fabricates_calibration_or_zero_drift(db, tenant):
    result = monitoring.summary(
        db, tenant.merchant.id, DataOrigin.LIVE_SANDBOX, days=7, as_of=T0, capacity=0.08
    )
    assert result.current_transactions == 0
    assert result.high_flag_rate is None and result.score_psi is None
    assert result.resolution_rate is None and result.oldest_pending_hours is None
    assert result.calibration_status.startswith("Unavailable")


def test_fixed_score_psi_is_finite_symmetric_and_requires_samples():
    assert monitoring.population_stability([0.1] * 29, [0.8] * 30) is None
    assert monitoring.population_stability([0.1] * 30, [0.1] * 30) == pytest.approx(0)
    left = monitoring.population_stability([0.1] * 30, [0.8] * 30)
    right = monitoring.population_stability([0.8] * 30, [0.1] * 30)
    assert left is not None and left > 0 and left == pytest.approx(right)
    assert monitoring.score_counts([0, 1, 0.55]) == [1, 0, 0, 0, 0, 1, 0, 0, 0, 1]


def test_graph_bounds_explains_sources_and_excludes_other_origins(db, tenant, other_tenant):
    own = [
        _txn(db, tenant, at=T0 - timedelta(hours=i + 1), payer="SAME-REFERENCE") for i in range(4)
    ]
    _txn(db, other_tenant, at=T0 - timedelta(hours=1), payer="SAME-REFERENCE")
    _txn(
        db, tenant, at=T0 - timedelta(hours=1), payer="SAME-REFERENCE", origin=DataOrigin.SIMULATED
    )
    future = _txn(db, tenant, at=T0 + timedelta(hours=1), payer="SAME-REFERENCE")
    case = Case(
        merchant_id=tenant.merchant.id,
        transaction_id=own[0].id,
        source=CaseSource.MANUAL,
        status=CaseStatus.OPEN,
        priority=CasePriority.HIGH,
        title="Recorded review",
        due_at=T0,
        data_origin=DataOrigin.SYNTHETIC_DEMO,
        created_at=T0 - timedelta(minutes=20),
    )
    db.add(case)
    assessment(db, own[0], T0 - timedelta(minutes=30), 0.8)
    assessment(db, own[1], T0 - timedelta(minutes=30), 0.1)
    db.commit()
    result = monitoring.network(
        db, tenant.merchant.id, DataOrigin.SYNTHETIC_DEMO, days=7, as_of=T0, limit=3
    )
    assert result.transaction_count == 3 and result.truncated
    assert result.repeated_payer_groups == 1
    assert len(result.nodes) <= 3 * 3 + 1
    assert str(future.id) not in {str(n.record_id) for n in result.nodes}
    assert all(e.data_origin is DataOrigin.SYNTHETIC_DEMO for e in result.edges)
    assert all(e.explanation and e.transaction_id in {t.id for t in own} for e in result.edges)
    assert any(n.kind == "case" and n.record_id == case.id for n in result.nodes)
    none = monitoring.network(
        db,
        tenant.merchant.id,
        DataOrigin.SYNTHETIC_DEMO,
        days=7,
        as_of=T0,
        limit=3,
        payer="UNKNOWN",
    )
    assert none.transaction_count == 0 and none.edges == []
    high = monitoring.network(
        db,
        tenant.merchant.id,
        DataOrigin.SYNTHETIC_DEMO,
        days=7,
        as_of=T0,
        limit=3,
        risk_band=RiskBand.HIGH,
    )
    assert high.transaction_count == 1
    assert [n.record_id for n in high.nodes if n.kind == "transaction"] == [own[0].id]


def test_monitoring_query_bounds_and_invalid_times(monitor_client, tenant):
    login(monitor_client, tenant.users[Role.VIEWER].email)
    assert monitor_client.get("/api/v1/network?data_origin=SIMULATED&limit=61").status_code == 422
    assert (
        monitor_client.get("/api/v1/monitoring/risk?data_origin=SIMULATED&days=181").status_code
        == 422
    )
    assert (
        monitor_client.get(
            "/api/v1/monitoring/risk?data_origin=SIMULATED&as_of=2099-01-01T00:00:00Z"
        ).status_code
        == 400
    )
    assert (
        monitor_client.get(
            "/api/v1/monitoring/risk?data_origin=SIMULATED&as_of=2026-01-01T00:00:00"
        ).status_code
        == 400
    )
