"""Operational risk features. One implementation, used by training and by live inference.

Every feature is computed only from events strictly before the transaction being scored:
- prior transactions of the same payer reference (``customer_history``),
- prior transaction amounts of the same merchant *and data origin* (``merchant_recent``),
- refunds and disputes whose own timestamp precedes the scored transaction.

History is always scoped to one data origin so synthetic demo data can never shift the
features of a live sandbox payment (docs/ML_METHODOLOGY.md).

Unavailable signals (device, card or IP fingerprints, PayPal-internal risk data) are not
modelled: SENTINEL does not observe them.
"""

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

FEATURE_VERSION = "op-features-v1"
LOOKBACK = timedelta(days=90)
MIN_MERCHANT_HISTORY = 10
MERCHANT_WINDOW = 200
HOURS_CAP = 720.0


@dataclass(frozen=True)
class TxnView:
    """The minimal, provenance-safe view of a transaction that features may read."""

    occurred_at: datetime
    amount_minor: int
    payer_reference: str | None
    refunded_at: datetime | None = None
    disputed_at: datetime | None = None


FEATURE_NAMES: tuple[str, ...] = (
    "amount_log",
    "amount_vs_merchant_median",
    "merchant_history_insufficient",
    "merchant_txn_count_1h",
    "is_new_customer",
    "cust_prior_txn_count_90d",
    "cust_txn_count_1h",
    "cust_txn_count_24h",
    "cust_amount_24h_log",
    "hours_since_cust_prev",
    "cust_prior_refund_count_90d",
    "cust_prior_dispute_count_90d",
)

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "amount_log": "Payment amount (log scale)",
    "amount_vs_merchant_median": "Amount relative to this merchant's recent median",
    "merchant_history_insufficient": "Fewer than 10 prior merchant payments to compare against",
    "merchant_txn_count_1h": "Merchant payments in the previous hour",
    "is_new_customer": "No earlier payment from this payer in 90 days",
    "cust_prior_txn_count_90d": "Earlier payments from this payer (90 days)",
    "cust_txn_count_1h": "Payments from this payer in the previous hour",
    "cust_txn_count_24h": "Payments from this payer in the previous 24 hours",
    "cust_amount_24h_log": "Amount paid by this payer in the previous 24 hours (log scale)",
    "hours_since_cust_prev": "Hours since this payer's previous payment",
    "cust_prior_refund_count_90d": "Refunds to this payer before this payment (90 days)",
    "cust_prior_dispute_count_90d": "Disputes by this payer before this payment (90 days)",
}


def compute_features(
    target: TxnView,
    customer_history: Sequence[TxnView],
    merchant_recent: Sequence[TxnView],
) -> dict[str, float]:
    """Return the feature vector for ``target``. Inputs may contain future rows; they are
    filtered here so callers cannot leak the future by accident."""
    t = target.occurred_at
    start = t - LOOKBACK
    cust = [h for h in customer_history if start <= h.occurred_at < t]
    if target.payer_reference is None:
        cust = []
    merch = sorted((m for m in merchant_recent if m.occurred_at < t), key=lambda m: m.occurred_at)
    merch_amounts = [m.amount_minor for m in merch[-MERCHANT_WINDOW:]]

    insufficient = len(merch_amounts) < MIN_MERCHANT_HISTORY
    ratio = 1.0
    if not insufficient:
        median = statistics.median(merch_amounts)
        ratio = target.amount_minor / median if median > 0 else 1.0

    hour_ago = t - timedelta(hours=1)
    day_ago = t - timedelta(hours=24)
    cust_1h = [h for h in cust if h.occurred_at >= hour_ago]
    cust_24h = [h for h in cust if h.occurred_at >= day_ago]
    prev = max((h.occurred_at for h in cust), default=None)
    hours_since = HOURS_CAP if prev is None else min((t - prev).total_seconds() / 3600, HOURS_CAP)

    return {
        "amount_log": math.log1p(target.amount_minor / 100),
        "amount_vs_merchant_median": round(ratio, 6),
        "merchant_history_insufficient": float(insufficient),
        "merchant_txn_count_1h": float(sum(1 for m in merch if m.occurred_at >= hour_ago)),
        "is_new_customer": float(not cust),
        "cust_prior_txn_count_90d": float(len(cust)),
        "cust_txn_count_1h": float(len(cust_1h)),
        "cust_txn_count_24h": float(len(cust_24h)),
        "cust_amount_24h_log": math.log1p(sum(h.amount_minor for h in cust_24h) / 100),
        "hours_since_cust_prev": round(hours_since, 4),
        "cust_prior_refund_count_90d": float(
            sum(1 for h in cust if h.refunded_at is not None and start <= h.refunded_at < t)
        ),
        "cust_prior_dispute_count_90d": float(
            sum(1 for h in cust if h.disputed_at is not None and start <= h.disputed_at < t)
        ),
    }
