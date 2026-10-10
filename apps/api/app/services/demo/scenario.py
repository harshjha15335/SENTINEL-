"""Deterministic synthetic demo scenario (SYNTHETIC_DEMO).

Generates a PayPal-merchant-shaped transaction history with documented ground-truth labels so
the risk model, review queue and policy lab have something to work on that a simple sandbox
checkout cannot produce. Nothing here describes real people or real PayPal outcomes.

Behaviour archetypes (fixed proportions, documented in docs/ML_METHODOLOGY.md):
- ``regular``:      occasional purchases; adverse outcome rarely (0.6%).
- ``high_value``:   legitimate but large, infrequent orders; adverse 2% (ambiguous cases).
- ``burst_fraud``:  new payer, several payments within minutes, often high value; adverse 55%.
- ``quiet_fraud``:  single ordinary-looking payment; adverse 45% (deliberately hard to catch).
- ``refund_abuse``: frequent refunds, later disputes; adverse 20%.
- ``busy_legit``:   legitimate payer with rapid repeat purchases; adverse 1% (false-positive bait).

The label ``adverse`` means "a dispute or chargeback followed this payment". Labels are noisy on
purpose; a perfect model on this data would indicate a bug, not skill.
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

SCENARIO_VERSION = "demo-scenario-v1"
DEFAULT_SEED = 2026
START = datetime(2026, 5, 1, tzinfo=UTC)
DAYS = 150

# (sku, unit price in cents) mirrors the seeded catalogue.
CATALOGUE = [
    ("NW-API-STARTER", 1900),
    ("NW-HW-KIT", 8950),
    ("NW-TEAM", 24900),
    ("NW-ENT-AUDIT", 120000),
]

ARCHETYPES = {
    "regular": 0.80,
    "high_value": 0.05,
    "burst_fraud": 0.03,
    "quiet_fraud": 0.03,
    "refund_abuse": 0.03,
    "busy_legit": 0.06,
}


@dataclass
class SyntheticTxn:
    ref: str
    payer_reference: str
    archetype: str
    sku: str
    quantity: int
    amount_minor: int
    occurred_at: datetime
    refunded_at: datetime | None = None
    disputed_at: datetime | None = None
    adverse: bool = False
    tags: list[str] = field(default_factory=list)


def _pick_item(
    rng: random.Random, weights: tuple[float, float, float, float]
) -> tuple[str, int, int]:
    sku, price = rng.choices(CATALOGUE, weights=weights)[0]
    qty = 1 if price > 50000 else rng.choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
    return sku, price, qty


def generate(seed: int = DEFAULT_SEED, n_customers: int = 3000) -> list[SyntheticTxn]:
    rng = random.Random(seed)  # noqa: S311 - reproducible demo data, not security
    names = list(ARCHETYPES)
    weights = [ARCHETYPES[n] for n in names]
    txns: list[SyntheticTxn] = []
    end = START + timedelta(days=DAYS)

    def first_time() -> datetime:
        return START + timedelta(seconds=rng.uniform(0, DAYS * 86400 * 0.97))

    for c in range(n_customers):
        archetype = rng.choices(names, weights=weights)[0]
        payer = f"SYN-PAYER-{c:05d}"
        events: list[tuple[datetime, tuple[float, float, float, float]]] = []
        t = first_time()
        if archetype == "regular":
            for _ in range(rng.randint(1, 6)):
                events.append((t, (0.55, 0.25, 0.18, 0.02)))
                t += timedelta(days=rng.expovariate(1 / 18))
        elif archetype == "high_value":
            for _ in range(rng.randint(1, 3)):
                events.append((t, (0.05, 0.15, 0.4, 0.4)))
                t += timedelta(days=rng.expovariate(1 / 30))
        elif archetype == "burst_fraud":
            for _ in range(rng.randint(2, 7)):
                events.append((t, (0.15, 0.25, 0.35, 0.25)))
                t += timedelta(minutes=rng.uniform(0.5, 25))
        elif archetype == "quiet_fraud":
            events.append((t, (0.3, 0.3, 0.3, 0.1)))
        elif archetype == "refund_abuse":
            for _ in range(rng.randint(3, 8)):
                events.append((t, (0.35, 0.35, 0.28, 0.02)))
                t += timedelta(days=rng.expovariate(1 / 6))
        else:  # busy_legit
            for _ in range(rng.randint(3, 9)):
                events.append((t, (0.7, 0.2, 0.1, 0.0)))
                t += timedelta(minutes=rng.uniform(2, 240))

        for i, (when, w) in enumerate(events):
            if when >= end:
                break
            sku, price, qty = _pick_item(rng, w)
            txn = SyntheticTxn(
                ref=f"SYN-TXN-{c:05d}-{i:02d}",
                payer_reference=payer,
                archetype=archetype,
                sku=sku,
                quantity=qty,
                amount_minor=price * qty,
                occurred_at=when.replace(microsecond=0),
            )
            p_adverse = {
                "regular": 0.006,
                "high_value": 0.02,
                "burst_fraud": 0.55,
                "quiet_fraud": 0.45,
                "refund_abuse": 0.20 if i >= 2 else 0.03,
                "busy_legit": 0.01,
            }[archetype]
            txn.adverse = rng.random() < p_adverse
            p_refund = {"refund_abuse": 0.7, "regular": 0.03, "busy_legit": 0.05}.get(
                archetype, 0.02
            )
            if rng.random() < p_refund:
                txn.refunded_at = when + timedelta(days=rng.uniform(1, 10))
            if txn.adverse:
                txn.disputed_at = when + timedelta(days=rng.uniform(3, 45))
            txns.append(txn)

    txns.sort(key=lambda x: (x.occurred_at, x.ref))
    return txns
