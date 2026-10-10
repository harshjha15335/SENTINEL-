"""Score a stored transaction with the operational model and record the assessment.

The history fed to ``compute_features`` mirrors training exactly: the payer's earlier payments
(90 days) and the merchant's last ``MERCHANT_HISTORY_LIMIT`` earlier payments, both restricted
to the same merchant and the same data origin as the scored transaction.

Scoring is decision support. It writes an assessment and, for HIGH, opens a review case. It
never blocks, captures or refunds a payment.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app.core.errors import DomainError, NotFoundError
from app.models import RiskAssessment, Transaction
from app.models.enums import DataOrigin, PolicyDecision, RiskBand
from app.services import audit
from app.services.risk.features import LOOKBACK, TxnView, compute_features
from app.services.risk.model import Prediction, RiskModel, get_model

log = logging.getLogger("sentinel.risk")

MERCHANT_HISTORY_LIMIT = 400  # training uses the merchant's last 400 earlier payments

_DECISIONS = {
    RiskBand.LOW: PolicyDecision.ALLOW,
    RiskBand.MEDIUM: PolicyDecision.REVIEW,
    RiskBand.HIGH: PolicyDecision.ESCALATE,
}


class NotScorableError(DomainError):
    status_code = 409
    code = "not_scorable"


def _view(t: Transaction) -> TxnView:
    assert t.occurred_at is not None
    return TxnView(t.occurred_at, t.amount_minor, t.payer_reference, t.refunded_at, t.disputed_at)


def load_history(db: Session, txn: Transaction) -> tuple[list[TxnView], list[TxnView]]:
    assert txn.occurred_at is not None
    t = txn.occurred_at
    scope = (
        Transaction.merchant_id == txn.merchant_id,
        Transaction.data_origin == txn.data_origin,
        Transaction.occurred_at.is_not(None),
        Transaction.occurred_at < t,
        Transaction.id != txn.id,
    )
    merchant = list(
        db.scalars(
            select(Transaction)
            .where(*scope)
            .order_by(Transaction.occurred_at.desc())
            .limit(MERCHANT_HISTORY_LIMIT)
        ).unique()
    )
    payer: list[Transaction] = []
    if txn.payer_reference:
        payer = list(
            db.scalars(
                select(Transaction).where(
                    *scope,
                    Transaction.payer_reference == txn.payer_reference,
                    Transaction.occurred_at >= t - LOOKBACK,
                )
            ).unique()
        )
    return [_view(p) for p in payer], [_view(m) for m in reversed(merchant)]


def instance_limitations(txn: Transaction, features: dict[str, float]) -> list[str]:
    notes = []
    if features["merchant_history_insufficient"]:
        notes.append(
            "Fewer than 10 earlier payments of this origin exist, so the amount comparison "
            "falls back to a neutral value."
        )
    if txn.payer_reference is None:
        notes.append("No payer reference was recorded, so payer-history features are empty.")
    if txn.data_origin is not DataOrigin.SYNTHETIC_DEMO:
        notes.append(
            "The model was trained on synthetic data only. For this payment the score shows "
            "how the pipeline works; it is not a validated risk estimate."
        )
    return notes


def build_assessment(
    txn: Transaction,
    features: dict[str, float],
    prediction: Prediction,
    model: RiskModel,
    *,
    trigger: str,
    actor_id: uuid.UUID | None,
) -> RiskAssessment:
    band = RiskBand(model.band(prediction.probability))
    explanation: dict[str, Any] = {
        "method": "xgboost_tree_shap",
        "space": "log_odds_before_calibration",
        "base_value": prediction.base_value,
        "raw_probability": prediction.raw_probability,
        "contributions": [
            {
                "feature": c.feature,
                "label": c.label,
                "value": c.value,
                "contribution": c.contribution,
            }
            for c in prediction.contributions
        ],
    }
    return RiskAssessment(
        merchant_id=txn.merchant_id,
        transaction_id=txn.id,
        model_version=model.version,
        feature_version=model.feature_version,
        risk_score=prediction.probability,
        risk_band=band,
        policy_decision=_DECISIONS[band],
        policy_mode="SHADOW",
        thresholds={"medium": model.medium_threshold, "high": model.high_threshold},
        feature_snapshot=features,
        explanation=explanation,
        limitations=model.limitations + instance_limitations(txn, features),
        data_origin=txn.data_origin,
        trigger=trigger,
        created_by_user_id=actor_id,
    )


def score_transaction(
    db: Session,
    txn: Transaction,
    *,
    trigger: str,
    actor_id: uuid.UUID | None,
    open_case_on_high: bool = True,
) -> RiskAssessment:
    """Score ``txn`` and add the assessment (and a case, if HIGH) to the session. No commit."""
    if txn.occurred_at is None:
        raise NotScorableError("Only payments with a capture attempt can be scored")
    model = get_model()
    customer, merchant = load_history(db, txn)
    features = compute_features(_view(txn), customer, merchant)
    (prediction,) = model.predict([features])
    assessment = build_assessment(
        txn, features, prediction, model, trigger=trigger, actor_id=actor_id
    )
    db.add(assessment)
    db.flush()
    audit.record(
        db,
        action="risk.assessment.created",
        entity_type="transaction",
        entity_id=txn.id,
        merchant_id=txn.merchant_id,
        actor_id=actor_id,
        actor_type="USER" if actor_id else "SYSTEM",
        metadata={
            "assessment_id": str(assessment.id),
            "model_version": model.version,
            "risk_band": assessment.risk_band.value,
            "policy_decision": assessment.policy_decision.value,
            "trigger": trigger,
        },
    )
    if open_case_on_high and assessment.risk_band is RiskBand.HIGH:
        from app.services.cases import open_from_assessment  # avoid an import cycle

        open_from_assessment(db, txn, assessment)
    return assessment


def score_after_capture(db: Session, txn_id: uuid.UUID) -> None:
    """Best-effort scoring right after a capture. A scoring failure never affects the payment."""
    try:
        txn = db.get(Transaction, txn_id)
        if txn is None or txn.occurred_at is None:
            return
        score_transaction(db, txn, trigger="capture", actor_id=None)
        db.commit()
    except Exception:
        db.rollback()
        log.exception("risk scoring after capture failed", extra={"data": {"txn": str(txn_id)}})


def latest_for(db: Session, merchant_id: uuid.UUID, txn_id: uuid.UUID) -> RiskAssessment | None:
    return db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.transaction_id == txn_id, RiskAssessment.merchant_id == merchant_id)
        .order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc())
        .limit(1)
    )


def latest_map(
    db: Session, merchant_id: uuid.UUID, txn_ids: list[uuid.UUID]
) -> dict[uuid.UUID, RiskAssessment]:
    if not txn_ids:
        return {}
    rows = db.scalars(
        select(RiskAssessment)
        .where(
            RiskAssessment.merchant_id == merchant_id, RiskAssessment.transaction_id.in_(txn_ids)
        )
        .order_by(
            RiskAssessment.transaction_id,
            RiskAssessment.created_at.desc(),
            RiskAssessment.id.desc(),
        )
        .ext(distinct_on(RiskAssessment.transaction_id))
    )
    return {r.transaction_id: r for r in rows}


def get_transaction(db: Session, merchant_id: uuid.UUID, txn_id: uuid.UUID) -> Transaction:
    txn = db.scalar(
        select(Transaction).where(Transaction.id == txn_id, Transaction.merchant_id == merchant_id)
    )
    if txn is None:
        raise NotFoundError("Transaction not found")
    return txn
