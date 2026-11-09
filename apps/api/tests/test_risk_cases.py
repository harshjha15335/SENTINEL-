import json
import math
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, RiskAssessment, Transaction
from app.models.enums import CaseStatus, DataOrigin, Role, TransactionStatus
from app.services.risk.model import ARTIFACT_ROOT, RiskModel, get_model
from app.services.risk.scoring import score_transaction
from tests.conftest import Tenant, login

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _txn(
    db: Session,
    tenant: Tenant,
    *,
    at: datetime,
    amount: int = 2500,
    payer: str | None = "PAYER-1",
    origin: DataOrigin = DataOrigin.SYNTHETIC_DEMO,
) -> Transaction:
    txn = Transaction(
        merchant_id=tenant.merchant.id,
        quantity=1,
        amount_minor=amount,
        currency="USD",
        status=TransactionStatus.CAPTURED,
        payer_reference=payer,
        create_idempotency_key=f"test-{uuid.uuid4()}",
        paypal_request_id=f"test-{uuid.uuid4()}",
        provider_summary={},
        data_origin=origin,
        occurred_at=at,
    )
    db.add(txn)
    db.flush()
    return txn


def _capture(client: TestClient, csrf: str, product_id: uuid.UUID, key: str) -> dict[str, object]:
    order = client.post(
        "/api/v1/paypal/orders",
        json={"product_id": str(product_id), "quantity": 1},
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
    ).json()
    cap = client.post(
        f"/api/v1/paypal/orders/{order['paypal_order_id']}/capture",
        headers={"X-CSRF-Token": csrf},
    )
    assert cap.status_code == 200, cap.text
    result: dict[str, object] = cap.json()
    return result


def test_serving_model_reproduces_training_predictions() -> None:
    model = get_model()
    golden = json.loads((ARTIFACT_ROOT / model.version / "golden.json").read_text())
    predictions = model.predict([g["features"] for g in golden])
    for g, p in zip(golden, predictions, strict=True):
        assert p.probability == pytest.approx(g["probability"], abs=1e-9)


def test_explanation_adds_up_to_model_output() -> None:
    model = get_model()
    golden = json.loads((ARTIFACT_ROOT / model.version / "golden.json").read_text())
    (p,) = model.predict([golden[0]["features"]])
    margin = p.base_value + sum(c.contribution for c in p.contributions)
    assert margin == pytest.approx(math.log(p.raw_probability / (1 - p.raw_probability)), abs=1e-4)
    assert len(p.contributions) == 12


def test_tampered_artifact_is_refused(tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = ARTIFACT_ROOT / get_model().version
    for name in ("metadata.json", "booster.json"):
        (tmp_path / name).write_bytes((src / name).read_bytes())
    (tmp_path / "booster.json").write_bytes((src / "booster.json").read_bytes() + b" ")
    with pytest.raises(RuntimeError, match="digest"):
        RiskModel(tmp_path)


def test_capture_is_scored_in_shadow_mode(app_client: TestClient, tenant: Tenant) -> None:
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    txn = _capture(app_client, csrf, tenant.product.id, "risk-key-000000000001")
    resp = app_client.get(f"/api/v1/transactions/{txn['id']}/risk")
    assert resp.status_code == 200, resp.text
    a = resp.json()
    assert a["assessment_type"] == "MODEL_GENERATED"
    assert a["policy_mode"] == "SHADOW"
    assert a["data_origin"] == "SIMULATED"
    assert a["model_version"] == "operational-v1"
    assert 0 <= a["risk_score"] <= 1
    assert a["feature_snapshot"]["merchant_history_insufficient"] == 1.0
    assert any("trained on synthetic data only" in note for note in a["limitations"])
    # The payment itself is untouched by scoring.
    assert txn["status"] == "CAPTURED"


def test_features_use_only_earlier_same_origin_history(db: Session, tenant: Tenant) -> None:
    for i in range(12):
        _txn(db, tenant, at=T0 - timedelta(days=1, minutes=i), amount=1000)
    _txn(db, tenant, at=T0 - timedelta(minutes=20), payer="PAYER-1")
    # Same payer, but other origins or later in time: must be invisible.
    _txn(db, tenant, at=T0 - timedelta(minutes=10), origin=DataOrigin.SIMULATED)
    _txn(db, tenant, at=T0 + timedelta(minutes=5))
    target = _txn(db, tenant, at=T0, amount=5000)
    db.commit()

    a = score_transaction(db, target, trigger="test", actor_id=None)
    f = a.feature_snapshot
    assert f["cust_prior_txn_count_90d"] == 13  # 12 history rows share PAYER-1, plus one
    assert f["cust_txn_count_1h"] == 1
    assert f["merchant_history_insufficient"] == 0.0
    assert f["amount_vs_merchant_median"] == pytest.approx(5.0)
    assert a.data_origin is DataOrigin.SYNTHETIC_DEMO


def test_high_band_opens_one_case(
    db: Session, tenant: Tenant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RiskModel, "band", lambda self, p: "HIGH")
    target = _txn(db, tenant, at=T0)
    db.commit()
    score_transaction(db, target, trigger="test", actor_id=None)
    score_transaction(db, target, trigger="test", actor_id=None)
    db.commit()
    cases = db.scalars(select(Case).where(Case.transaction_id == target.id)).all()
    assert len(cases) == 1
    assert cases[0].status is CaseStatus.OPEN
    assert cases[0].data_origin is DataOrigin.SYNTHETIC_DEMO
    assert len(db.scalars(select(RiskAssessment)).all()) == 2


def test_viewer_cannot_rescore(app_client: TestClient, db: Session, tenant: Tenant) -> None:
    target = _txn(db, tenant, at=T0)
    db.commit()
    csrf = login(app_client, tenant.users[Role.VIEWER].email)
    resp = app_client.post(f"/api/v1/transactions/{target.id}/risk", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 403


def test_uncaptured_order_is_not_scorable(
    app_client: TestClient, db: Session, tenant: Tenant
) -> None:
    target = _txn(db, tenant, at=T0)
    target.occurred_at = None
    target.status = TransactionStatus.ORDER_CREATED
    db.commit()
    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    resp = app_client.post(f"/api/v1/transactions/{target.id}/risk", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "not_scorable"


def test_model_card_reports_training_metadata(app_client: TestClient, tenant: Tenant) -> None:
    login(app_client, tenant.users[Role.VIEWER].email)
    card = app_client.get("/api/v1/risk/model").json()
    meta = get_model().metadata
    assert card["test_metrics"]["pr_auc"] == meta["test_metrics"]["pr_auc"]
    assert card["thresholds"] == meta["thresholds"]
    assert card["training_data"].startswith("SYNTHETIC_DEMO")
    assert len(card["features"]) == 12
    # Review capacity: recorded 9.4% test flag rate vs the 8% validation assumption.
    cap = card["review_capacity"]
    assert cap["capacity_share"] == meta["cost_assumptions"]["review_capacity_share"]
    assert cap["test_flag_rate"] == meta["test_metrics"]["flag_rate"]
    assert cap["exceeded"] is True
    assert cap["policy_mode"] == "SHADOW"
    assert "not re-tuned" in cap["message"]


def test_case_workflow_and_audit(
    app_client: TestClient, db: Session, tenant: Tenant, other_tenant: Tenant
) -> None:
    target = _txn(db, tenant, at=T0)
    db.commit()

    viewer_csrf = login(app_client, tenant.users[Role.VIEWER].email)
    denied = app_client.post(
        "/api/v1/cases",
        json={"transaction_id": str(target.id), "reason": "Customer called"},
        headers={"X-CSRF-Token": viewer_csrf},
    )
    assert denied.status_code == 403

    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    opened = app_client.post(
        "/api/v1/cases",
        json={"transaction_id": str(target.id), "reason": "Customer called about this order"},
        headers={"X-CSRF-Token": csrf},
    )
    assert opened.status_code == 201, opened.text
    case = opened.json()
    assert case["status"] == "IN_REVIEW"
    assert case["data_origin"] == "SYNTHETIC_DEMO"
    assert case["notes"][0]["body"] == "Customer called about this order"

    dup = app_client.post(
        "/api/v1/cases",
        json={"transaction_id": str(target.id), "reason": "again"},
        headers={"X-CSRF-Token": csrf},
    )
    assert dup.status_code == 409

    queue = app_client.get("/api/v1/cases", params={"status": "IN_REVIEW"}).json()
    assert queue["total"] == 1

    note = app_client.post(
        f"/api/v1/cases/{case['id']}/notes",
        json={"body": "Payer history looks normal"},
        headers={"X-CSRF-Token": csrf},
    )
    assert note.status_code == 201

    no_note = app_client.post(
        f"/api/v1/cases/{case['id']}/resolve",
        json={"resolution": "LEGITIMATE", "note": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert no_note.status_code == 422

    resolved = app_client.post(
        f"/api/v1/cases/{case['id']}/resolve",
        json={"resolution": "LEGITIMATE", "note": "Known customer, verified by phone"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["status"] == "RESOLVED"
    assert [a["action"] for a in body["audit"]] == [
        "case.opened",
        "case.note_added",
        "case.resolved",
    ]
    # Note text never lands in the audit log.
    assert "Payer history" not in json.dumps(body["audit"])

    again = app_client.post(
        f"/api/v1/cases/{case['id']}/resolve",
        json={"resolution": "LEGITIMATE", "note": "twice"},
        headers={"X-CSRF-Token": csrf},
    )
    assert again.status_code == 409

    # Resolving never touched the payment.
    db.expire_all()
    assert db.get(Transaction, target.id).status is TransactionStatus.CAPTURED  # type: ignore[union-attr]

    login(app_client, other_tenant.users[Role.ADMIN].email)
    assert app_client.get(f"/api/v1/cases/{case['id']}").status_code == 404
    assert app_client.get("/api/v1/cases").json()["total"] == 0


def test_claim_respects_assignee(
    app_client: TestClient, db: Session, tenant: Tenant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RiskModel, "band", lambda self, p: "HIGH")
    target = _txn(db, tenant, at=T0)
    db.commit()
    score_transaction(db, target, trigger="test", actor_id=None)
    db.commit()
    case_id = db.scalar(select(Case.id).where(Case.transaction_id == target.id))

    csrf = login(app_client, tenant.users[Role.ANALYST].email)
    claimed = app_client.post(f"/api/v1/cases/{case_id}/claim", headers={"X-CSRF-Token": csrf})
    assert claimed.status_code == 200
    assert claimed.json()["assignee"]["email"] == tenant.users[Role.ANALYST].email

    admin_csrf = login(app_client, tenant.users[Role.ADMIN].email)
    taken = app_client.post(f"/api/v1/cases/{case_id}/claim", headers={"X-CSRF-Token": admin_csrf})
    assert taken.status_code == 409


def test_dashboard_splits_risk_and_cases_by_origin(
    app_client: TestClient, db: Session, tenant: Tenant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(RiskModel, "band", lambda self, p: "HIGH")
    synthetic = _txn(db, tenant, at=T0)
    simulated = _txn(db, tenant, at=T0, origin=DataOrigin.SIMULATED, payer="P2")
    db.commit()
    score_transaction(db, synthetic, trigger="test", actor_id=None)
    score_transaction(db, simulated, trigger="test", actor_id=None)
    db.commit()
    login(app_client, tenant.users[Role.VIEWER].email)
    summary = app_client.get("/api/v1/dashboard/summary").json()
    origins = sorted(r["data_origin"] for r in summary["open_cases_by_origin"])
    assert origins == ["SIMULATED", "SYNTHETIC_DEMO"]
    assert all(r["count"] == 1 for r in summary["risk_bands_by_origin"])


def test_demo_load_matches_offline_evaluation(db: Session, tenant: Tenant) -> None:
    from app.services.demo.loader import load_scenario

    sandbox = _txn(db, tenant, at=T0, origin=DataOrigin.LIVE_SANDBOX)
    db.commit()
    first = load_scenario(db, tenant.merchant.id, seed=2026)
    second = load_scenario(db, tenant.merchant.id, seed=2026)
    assert first == second  # re-running replaces, never duplicates

    # Serving the stored rows through the API path gives the same HIGH count as the offline
    # test-split evaluation (true positives + false positives at the chosen threshold).
    cm = get_model().metadata["test_metrics"]["confusion_matrix"]
    assert first.scored == get_model().metadata["split"]["test_rows"]
    assert first.bands["HIGH"] == cm["tp"] + cm["fp"]
    assert first.cases_opened == first.bands["HIGH"]

    db.expire_all()
    assert db.get(Transaction, sandbox.id) is not None
    synthetic = db.scalars(
        select(Transaction).where(Transaction.data_origin == DataOrigin.SYNTHETIC_DEMO)
    ).all()
    assert len(synthetic) == first.transactions
    assert all(t.payer_reference and t.payer_reference.startswith("SYN-") for t in synthetic)
