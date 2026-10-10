"""Load the synthetic demo scenario into a merchant's workspace as SYNTHETIC_DEMO records.

Every row is labelled SYNTHETIC_DEMO and carries ``SYN-`` references, so it can never be
mistaken for a PayPal sandbox payment. Re-running replaces only the merchant's SYNTHETIC_DEMO
rows; sandbox and simulated records are never touched.

Only payments in the model's held-out test window are scored, so the demo shows out-of-sample
assessments. Earlier payments are loaded as history for the features.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Product, Transaction
from app.models.enums import DataOrigin, RiskBand, TransactionStatus
from app.services import audit
from app.services.cases import open_from_assessment
from app.services.demo.scenario import SCENARIO_VERSION, generate
from app.services.risk.features import TxnView, compute_features
from app.services.risk.model import get_model
from app.services.risk.scoring import MERCHANT_HISTORY_LIMIT, build_assessment


@dataclass(frozen=True)
class LoadResult:
    transactions: int
    scored: int
    cases_opened: int
    bands: dict[str, int]


def load_scenario(db: Session, merchant_id: uuid.UUID, *, seed: int) -> LoadResult:
    now = datetime.now(UTC)
    model = get_model()
    test_start = datetime.fromisoformat(model.metadata["split"]["test_start"])
    products = {
        p.sku: p.id for p in db.scalars(select(Product).where(Product.merchant_id == merchant_id))
    }

    db.execute(
        delete(Transaction).where(
            Transaction.merchant_id == merchant_id,
            Transaction.data_origin == DataOrigin.SYNTHETIC_DEMO,
        )
    )

    def known(ts: datetime | None) -> datetime | None:
        # Outcomes dated after "now" have not happened yet; do not record them.
        return ts if ts is not None and ts <= now else None

    by_payer: dict[str, list[TxnView]] = defaultdict(list)
    merchant: list[TxnView] = []
    to_score: list[tuple[Transaction, dict[str, float]]] = []
    rows = generate(seed)
    for s in rows:
        view = TxnView(
            s.occurred_at, s.amount_minor, s.payer_reference, s.refunded_at, s.disputed_at
        )
        txn = Transaction(
            merchant_id=merchant_id,
            product_id=products.get(s.sku),
            quantity=s.quantity,
            amount_minor=s.amount_minor,
            currency="USD",
            status=TransactionStatus.REFUNDED
            if known(s.refunded_at)
            else TransactionStatus.CAPTURED,
            provider_status="SYNTHETIC",
            payer_reference=s.payer_reference,
            create_idempotency_key=f"synthetic-{s.ref}",
            paypal_request_id=f"synthetic-{s.ref}",
            provider_summary={"scenario": SCENARIO_VERSION, "seed": seed, "ref": s.ref},
            data_origin=DataOrigin.SYNTHETIC_DEMO,
            occurred_at=s.occurred_at,
            refunded_at=known(s.refunded_at),
            disputed_at=known(s.disputed_at),
        )
        db.add(txn)
        if s.occurred_at >= test_start:
            features = compute_features(
                view, by_payer[s.payer_reference], merchant[-MERCHANT_HISTORY_LIMIT:]
            )
            to_score.append((txn, features))
        by_payer[s.payer_reference].append(view)
        merchant.append(view)
    db.flush()

    predictions = model.predict([f for _, f in to_score])
    bands: dict[str, int] = defaultdict(int)
    cases = 0
    for (txn, features), prediction in zip(to_score, predictions, strict=True):
        assessment = build_assessment(
            txn, features, prediction, model, trigger="demo_load", actor_id=None
        )
        db.add(assessment)
        bands[assessment.risk_band.value] += 1
        if assessment.risk_band is RiskBand.HIGH:
            db.flush()
            if open_from_assessment(db, txn, assessment, now=now) is not None:
                cases += 1

    audit.record(
        db,
        action="demo.scenario.loaded",
        entity_type="merchant",
        entity_id=merchant_id,
        merchant_id=merchant_id,
        actor_id=None,
        actor_type="SYSTEM",
        metadata={
            "scenario": SCENARIO_VERSION,
            "seed": seed,
            "transactions": len(rows),
            "scored": len(to_score),
            "model_version": model.version,
        },
    )
    db.commit()
    return LoadResult(len(rows), len(to_score), cases, dict(bands))
