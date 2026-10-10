"""Train and evaluate the Track B operational risk model.

    PYTHONPATH=apps/api:ml apps/api/.venv/bin/python -m sentinel_ml.train_operational

Steps: synthetic scenario -> past-only features -> chronological 60/20/20 split ->
rule baseline, logistic regression, XGBoost (small grid, selected on validation PR-AUC) ->
calibration fitted on validation -> cost-based threshold chosen on validation ->
one evaluation on the untouched test split -> artifact + report.

Every number in the report is computed here. Nothing is typed in by hand.
"""

import argparse
import hashlib
import json
import platform
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from app.services.risk.features import FEATURE_NAMES
from sentinel_ml.dataset import chronological_split, load

ROOT = Path(__file__).resolve().parents[1]
# The API package ships the serving artifact so the container image needs nothing else.
SERVING_DIR = ROOT.parent / "apps" / "api" / "app" / "risk_models"
MODEL_VERSION = "operational-v1"

# Decision-cost assumptions (illustrative, documented, not measured):
REVIEW_COST = 4.00  # analyst minutes per manual review, in dollars
CHARGEBACK_FEE = 20.00  # fee added to the lost amount when an adverse payment is missed
REVIEW_CAPACITY = 0.08  # at most 8% of payments can be reviewed
REVIEW_PREVENTS = 0.7  # share of adverse losses a review is assumed to prevent


LIMITATIONS = [
    "Trained and evaluated only on SENTINEL's synthetic demo scenario; "
    "not validated on real PayPal payments.",
    "Labels are generated ground truth with deliberate noise; "
    "scores are not fraud probabilities for live traffic.",
    "Features cover payment amount, payer velocity and prior refunds/disputes only; "
    "no device, card, IP or PayPal-internal signals.",
    "Calibration and thresholds use the validation split; test metrics come from one evaluation.",
]


@dataclass
class Candidate:
    name: str
    model: Any
    valid_scores: np.ndarray


def rule_scores(frame: pd.DataFrame) -> np.ndarray:
    """Transparent rules baseline: count of simple red flags (0-4)."""
    return (
        (frame["cust_txn_count_1h"] >= 2).astype(int)
        + (frame["amount_vs_merchant_median"] >= 4).astype(int)
        + ((frame["is_new_customer"] == 1) & (frame["amount_log"] > np.log1p(200))).astype(int)
        + (frame["cust_prior_refund_count_90d"] >= 2).astype(int)
    ).to_numpy(dtype=float)


def decision_cost(y: np.ndarray, flagged: np.ndarray, amounts_minor: np.ndarray) -> float:
    loss = amounts_minor / 100 + CHARGEBACK_FEE
    reviewed_cost = flagged.sum() * REVIEW_COST
    missed = ((y == 1) & ~flagged) * loss
    caught_residual = ((y == 1) & flagged) * loss * (1 - REVIEW_PREVENTS)
    return float(reviewed_cost + missed.sum() + caught_residual.sum())


def choose_threshold(y: np.ndarray, p: np.ndarray, amounts: np.ndarray) -> tuple[float, float]:
    """Lowest expected cost on VALIDATION, subject to review capacity."""
    best = (1.0, float("inf"))
    for thr in np.unique(np.round(p, 4)):
        flagged = p >= thr
        if flagged.mean() > REVIEW_CAPACITY:
            continue
        cost = decision_cost(y, flagged, amounts)
        if cost < best[1]:
            best = (float(thr), cost)
    return best


def metrics(y: np.ndarray, p: np.ndarray, thr: float, amounts: np.ndarray) -> dict[str, Any]:
    flagged = p >= thr
    tn, fp, fn, tp = confusion_matrix(y, flagged, labels=[0, 1]).ravel()
    k = int(np.floor(REVIEW_CAPACITY * len(y)))
    top = np.argsort(-p)[:k]
    at_cap = np.zeros_like(flagged)
    at_cap[top] = True
    baseline_cost = decision_cost(y, np.zeros_like(flagged), amounts)
    return {
        "rows": len(y),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "threshold": thr,
        "precision": float(precision_score(y, flagged, zero_division=0)),
        "recall": float(recall_score(y, flagged, zero_division=0)),
        "f1": float(f1_score(y, flagged, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "flag_rate": float(flagged.mean()),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, np.clip(p, 0, 1))),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
        "precision_at_capacity": float(y[at_cap].mean()) if k else 0.0,
        "recall_at_capacity": float(y[at_cap].sum() / y.sum()) if y.sum() else 0.0,
        "expected_cost": decision_cost(y, flagged, amounts),
        "expected_cost_no_review": baseline_cost,
    }


def export_artifact(
    model: Any,
    calibrated: CalibratedClassifierCV,
    X: np.ndarray,
    expected: np.ndarray,
    out_dir: Path,
) -> dict[str, Any]:
    """Write the booster as XGBoost JSON and the Platt parameters as plain numbers.

    The API loads these without unpickling anything. Before writing, the exported form is
    checked to reproduce the calibrated model's test predictions exactly.
    """
    if not isinstance(model, XGBClassifier):
        raise SystemExit(
            "Only an XGBoost model can be exported for serving; extend export_artifact."
        )
    (calibrator,) = calibrated.calibrated_classifiers_[0].calibrators
    a, b = float(calibrator.a_), float(calibrator.b_)
    model.get_booster().save_model(out_dir / "booster.json")
    raw = model.predict_proba(X)[:, 1]
    reproduced = 1.0 / (1.0 + np.exp(a * raw + b))
    gap = float(np.max(np.abs(reproduced - expected)))
    if gap > 1e-6:  # XGBoost predicts in float32
        raise SystemExit(f"exported calibration does not reproduce predictions (max gap {gap})")
    golden = [
        {
            "features": dict(zip(FEATURE_NAMES, map(float, X[i]), strict=True)),
            "probability": float(expected[i]),
        }
        for i in range(5)
    ]
    (out_dir / "golden.json").write_text(json.dumps(golden, indent=2))
    return {
        "method": "platt",
        "formula": "1 / (1 + exp(a * p_raw + b))",
        "a": a,
        "b": b,
    }


def train(seed: int, out_dir: Path) -> dict[str, Any]:
    frame, data_meta = load(seed)
    train_df, valid_df, test_df = chronological_split(frame)
    assert train_df["occurred_at"].max() <= valid_df["occurred_at"].min()
    assert valid_df["occurred_at"].max() <= test_df["occurred_at"].min()
    cols = list(FEATURE_NAMES)
    Xtr, ytr = train_df[cols].to_numpy(), train_df["label"].to_numpy()
    Xva, yva = valid_df[cols].to_numpy(), valid_df["label"].to_numpy()
    Xte, yte = test_df[cols].to_numpy(), test_df["label"].to_numpy()
    amt_va, amt_te = (
        valid_df["amount_minor"].to_numpy(),
        test_df["amount_minor"].to_numpy(),
    )

    candidates: list[Candidate] = []
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced"))
    lr.fit(Xtr, ytr)
    candidates.append(Candidate("logistic_regression", lr, lr.predict_proba(Xva)[:, 1]))

    pos_weight = float((ytr == 0).sum() / max((ytr == 1).sum(), 1))
    grid = [(d, n, lr_) for d in (2, 3, 4) for n in (150, 300) for lr_ in (0.05, 0.1)]
    best_xgb: Candidate | None = None
    for depth, n_est, rate in grid:
        m = XGBClassifier(
            max_depth=depth,
            n_estimators=n_est,
            learning_rate=rate,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=3,
            reg_lambda=1.0,
            scale_pos_weight=pos_weight,
            eval_metric="aucpr",
            random_state=seed,
            n_jobs=1,
        )
        m.fit(Xtr, ytr)
        s = m.predict_proba(Xva)[:, 1]
        if best_xgb is None or average_precision_score(yva, s) > average_precision_score(
            yva, best_xgb.valid_scores
        ):
            best_xgb = Candidate(f"xgboost(depth={depth},n={n_est},lr={rate})", m, s)
    assert best_xgb is not None
    candidates.append(best_xgb)

    comparison = {
        "rules_baseline": {
            "valid_pr_auc": float(average_precision_score(yva, rule_scores(valid_df))),
            "valid_roc_auc": float(roc_auc_score(yva, rule_scores(valid_df))),
        }
    }
    for c in candidates:
        comparison[c.name] = {
            "valid_pr_auc": float(average_precision_score(yva, c.valid_scores)),
            "valid_roc_auc": float(roc_auc_score(yva, c.valid_scores)),
        }
    chosen = max(candidates, key=lambda c: average_precision_score(yva, c.valid_scores))

    # Calibration on validation only (the base model is frozen; it never sees validation labels).
    calibrated = CalibratedClassifierCV(FrozenEstimator(chosen.model), method="sigmoid")
    calibrated.fit(Xva, yva)
    p_va = calibrated.predict_proba(Xva)[:, 1]
    threshold, valid_cost = choose_threshold(yva, p_va, amt_va)
    review_band = float(np.quantile(p_va, 0.80))  # MEDIUM: top 20% of validation scores

    # Single evaluation on the untouched test split.
    started = time.perf_counter()
    p_te = calibrated.predict_proba(Xte)[:, 1]
    latency_ms = (time.perf_counter() - started) / len(Xte) * 1000
    test_metrics = metrics(yte, p_te, threshold, amt_te)
    test_metrics["latency_ms_per_row_batch"] = latency_ms
    rules_test = rule_scores(test_df)
    rules_metrics = metrics(yte, rules_test / 4, 0.5, amt_te)

    out_dir.mkdir(parents=True, exist_ok=True)
    calibration = export_artifact(chosen.model, calibrated, Xte, p_te, out_dir)
    meta: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(UTC).isoformat(),
        "track": "B (operational, synthetic-trained)",
        "chosen_model": chosen.name,
        "features": cols,
        "dataset": data_meta,
        "split": {
            "method": "chronological 60/20/20 by occurred_at",
            "train_rows": len(train_df),
            "valid_rows": len(valid_df),
            "test_rows": len(test_df),
            "train_end": train_df["occurred_at"].max().isoformat(),
            "test_start": test_df["occurred_at"].min().isoformat(),
        },
        "calibration": "sigmoid (Platt) fitted on validation split",
        "calibration_params": calibration,
        "artifact": {
            "format": "XGBoost native JSON booster + Platt parameters (no pickle)",
            "booster_file": "booster.json",
            "booster_sha256": hashlib.sha256((out_dir / "booster.json").read_bytes()).hexdigest(),
        },
        "thresholds": {"high": threshold, "medium": min(review_band, threshold)},
        "threshold_selection": "minimum expected cost on validation within review capacity",
        "cost_assumptions": {
            "review_cost_usd": REVIEW_COST,
            "chargeback_fee_usd": CHARGEBACK_FEE,
            "review_capacity_share": REVIEW_CAPACITY,
            "review_prevents_share": REVIEW_PREVENTS,
        },
        "validation_comparison": comparison,
        "validation_cost_at_threshold": valid_cost,
        "test_metrics": test_metrics,
        "test_metrics_rules_baseline": rules_metrics,
        "limitations": LIMITATIONS,
        "versions": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    return meta


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=SERVING_DIR / MODEL_VERSION)
    args = parser.parse_args()
    meta = train(args.seed, args.out)
    print(
        json.dumps(
            {k: meta[k] for k in ("chosen_model", "validation_comparison", "thresholds")},
            indent=2,
        )
    )
    print(json.dumps(meta["test_metrics"], indent=2))
    print(json.dumps({"rules_test": meta["test_metrics_rules_baseline"]}, indent=2))


if __name__ == "__main__":
    main()
