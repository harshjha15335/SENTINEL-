"""Track B dataset: synthetic scenario -> past-only features, built chronologically.

Uses ``app.services.risk.features.compute_features`` (the same function the API calls at
inference time), feeding it each payer's prior rows and the merchant's prior rows.
"""

import hashlib
import json
from collections import defaultdict

import pandas as pd

from app.services.demo.scenario import SCENARIO_VERSION, SyntheticTxn, generate
from app.services.risk.features import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    TxnView,
    compute_features,
)


def to_view(t: SyntheticTxn) -> TxnView:
    return TxnView(t.occurred_at, t.amount_minor, t.payer_reference, t.refunded_at, t.disputed_at)


def build_frame(txns: list[SyntheticTxn]) -> pd.DataFrame:
    by_payer: dict[str, list[TxnView]] = defaultdict(list)
    merchant: list[TxnView] = []
    rows = []
    for t in sorted(txns, key=lambda x: (x.occurred_at, x.ref)):
        view = to_view(t)
        feats = compute_features(view, by_payer[t.payer_reference], merchant[-400:])
        rows.append(
            {
                "ref": t.ref,
                "occurred_at": t.occurred_at,
                "archetype": t.archetype,
                "amount_minor": t.amount_minor,
                "label": int(t.adverse),
                **feats,
            }
        )
        by_payer[t.payer_reference].append(view)
        merchant.append(view)
    return pd.DataFrame(rows)


def load(seed: int) -> tuple[pd.DataFrame, dict[str, object]]:
    txns = generate(seed)
    frame = build_frame(txns)
    digest = hashlib.sha256(
        json.dumps(
            [(t.ref, t.amount_minor, t.occurred_at.isoformat(), t.adverse) for t in txns]
        ).encode()
    ).hexdigest()
    meta = {
        "scenario_version": SCENARIO_VERSION,
        "feature_version": FEATURE_VERSION,
        "seed": seed,
        "rows": len(frame),
        "positives": int(frame["label"].sum()),
        "prevalence": float(frame["label"].mean()),
        "sha256": digest,
        "features": list(FEATURE_NAMES),
    }
    return frame, meta


def chronological_split(
    frame: pd.DataFrame, train: float = 0.6, valid: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split by time: earliest rows train, next validate, latest test. No shuffling."""
    ordered = frame.sort_values(["occurred_at", "ref"]).reset_index(drop=True)
    n = len(ordered)
    a, b = int(n * train), int(n * (train + valid))
    return ordered.iloc[:a], ordered.iloc[a:b], ordered.iloc[b:]
