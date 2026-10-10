"""Leakage, reproducibility and training/serving parity checks for the Track B model.

PYTHONPATH=apps/api:ml apps/api/.venv/bin/pytest ml/tests
"""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import numpy as np
import pytest
import shap
import xgboost as xgb

from app.services.demo.scenario import generate
from app.services.risk.features import FEATURE_NAMES, compute_features
from app.services.risk.model import ARTIFACT_ROOT, get_model
from sentinel_ml.dataset import build_frame, chronological_split, to_view
from sentinel_ml.train_operational import MODEL_VERSION, train


@pytest.fixture(scope="module")
def txns():  # type: ignore[no-untyped-def]
    return generate(2026)


def test_scenario_is_deterministic(txns) -> None:  # type: ignore[no-untyped-def]
    again = generate(2026)
    assert [(t.ref, t.amount_minor, t.occurred_at, t.adverse) for t in txns] == [
        (t.ref, t.amount_minor, t.occurred_at, t.adverse) for t in again
    ]
    other = generate(7)
    assert [t.amount_minor for t in other[:50]] != [t.amount_minor for t in txns[:50]]


def test_features_ignore_rows_at_or_after_the_target(txns) -> None:  # type: ignore[no-untyped-def]
    views = [to_view(t) for t in txns[:400]]
    target = views[300]
    past = [v for v in views if v.occurred_at < target.occurred_at]
    payer_all = [v for v in views if v.payer_reference == target.payer_reference]
    payer_past = [v for v in payer_all if v.occurred_at < target.occurred_at]
    assert compute_features(target, payer_all, views) == compute_features(target, payer_past, past)


def test_refund_counts_only_when_it_happened_before(txns) -> None:  # type: ignore[no-untyped-def]
    base = to_view(txns[0])
    target = replace(base, occurred_at=base.occurred_at + timedelta(days=2))
    refunded_later = replace(base, refunded_at=target.occurred_at + timedelta(hours=1))
    refunded_before = replace(base, refunded_at=target.occurred_at - timedelta(hours=1))
    assert compute_features(target, [refunded_later], [])["cust_prior_refund_count_90d"] == 0
    assert compute_features(target, [refunded_before], [])["cust_prior_refund_count_90d"] == 1


def test_split_is_chronological_and_disjoint(txns) -> None:  # type: ignore[no-untyped-def]
    frame = build_frame(txns)
    tr, va, te = chronological_split(frame)
    assert len(tr) + len(va) + len(te) == len(frame)
    assert tr["occurred_at"].max() <= va["occurred_at"].min()
    assert va["occurred_at"].max() <= te["occurred_at"].min()
    assert not set(tr["ref"]) & set(te["ref"])


def test_dataset_rows_match_serving_feature_function(txns) -> None:  # type: ignore[no-untyped-def]
    frame = build_frame(txns).set_index("ref")
    ordered = sorted(txns, key=lambda x: (x.occurred_at, x.ref))
    i = 2500
    target = ordered[i]
    history = [to_view(t) for t in ordered[:i]]
    payer = [h for h in history if h.payer_reference == target.payer_reference]
    expected = compute_features(to_view(target), payer, history[-400:])
    row = frame.loc[target.ref]
    assert {k: float(row[k]) for k in FEATURE_NAMES} == expected


def test_xgboost_contributions_equal_shap_tree_explainer() -> None:
    model = get_model()
    golden = json.loads((ARTIFACT_ROOT / model.version / "golden.json").read_text())
    data = np.array([[g["features"][n] for n in FEATURE_NAMES] for g in golden])
    booster = xgb.Booster()
    booster.load_model(ARTIFACT_ROOT / model.version / "booster.json")
    shap_values = shap.TreeExplainer(booster).shap_values(data)
    ours = np.array(
        [
            [
                c.contribution
                for c in sorted(p.contributions, key=lambda c: FEATURE_NAMES.index(c.feature))
            ]
            for p in model.predict([g["features"] for g in golden])
        ]
    )
    assert np.allclose(shap_values, ours, atol=1e-4)


def test_committed_artifact_is_reproducible(tmp_path: Path) -> None:
    meta = train(2026, tmp_path)
    committed = json.loads((ARTIFACT_ROOT / MODEL_VERSION / "metadata.json").read_text())
    assert meta["chosen_model"] == committed["chosen_model"]
    assert meta["thresholds"] == committed["thresholds"]
    assert meta["test_metrics"]["pr_auc"] == pytest.approx(committed["test_metrics"]["pr_auc"])
    assert meta["artifact"]["booster_sha256"] == committed["artifact"]["booster_sha256"]
    # Thresholds come from validation: the test split never influences them.
    assert meta["threshold_selection"].endswith("on validation within review capacity")
