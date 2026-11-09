import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member, operator
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.schemas.api import ModelCardOut, ReviewCapacityOut, RiskAssessmentOut
from app.services.risk.features import FEATURE_DESCRIPTIONS, FEATURE_NAMES
from app.services.risk.model import get_model
from app.services.risk.scoring import get_transaction, latest_for, score_transaction

router = APIRouter(tags=["risk"])


@router.get("/risk/model", response_model=ModelCardOut)
def model_card(principal: Principal = Depends(any_member)) -> ModelCardOut:
    """The serving model's card. Every metric is read from the training run's metadata."""
    meta: dict[str, Any] = get_model().metadata
    return ModelCardOut(
        model_version=meta["model_version"],
        feature_version=meta["dataset"]["feature_version"],
        track=meta["track"],
        chosen_model=meta["chosen_model"],
        trained_at=meta["trained_at"],
        training_data=(
            f"SYNTHETIC_DEMO scenario {meta['dataset']['scenario_version']} "
            f"(seed {meta['dataset']['seed']}, {meta['dataset']['rows']} payments)"
        ),
        split=meta["split"],
        calibration=meta["calibration"],
        thresholds=meta["thresholds"],
        threshold_selection=meta["threshold_selection"],
        cost_assumptions=meta["cost_assumptions"],
        validation_comparison=meta["validation_comparison"],
        test_metrics=meta["test_metrics"],
        test_metrics_rules_baseline=meta["test_metrics_rules_baseline"],
        features=[{"name": n, "label": FEATURE_DESCRIPTIONS[n]} for n in FEATURE_NAMES],
        limitations=meta["limitations"],
        review_capacity=review_capacity(meta),
    )


def review_capacity(meta: dict[str, Any]) -> ReviewCapacityOut:
    """Compare the validation-time capacity assumption with the recorded test flag rate.

    Both numbers come from the training run's metadata. The threshold is not changed: tuning it
    on the test window would leak the test set, so the policy stays in shadow mode instead.
    """
    capacity = float(meta["cost_assumptions"]["review_capacity_share"])
    flagged = float(meta["test_metrics"]["flag_rate"])
    exceeded = flagged > capacity
    return ReviewCapacityOut(
        capacity_share=capacity,
        test_flag_rate=flagged,
        exceeded=exceeded,
        excess_share=max(0.0, flagged - capacity),
        message=(
            f"On the held-out test window the high threshold flagged {flagged:.1%} of payments, "
            f"above the {capacity:.0%} review capacity assumed on validation. Expect more cases "
            "than planned. The threshold was not re-tuned on test data; the policy stays in "
            "shadow mode."
            if exceeded
            else f"Test-window flag rate {flagged:.1%} is within the {capacity:.0%} capacity."
        ),
    )


@router.get("/transactions/{transaction_id}/risk", response_model=RiskAssessmentOut)
def latest(
    transaction_id: uuid.UUID,
    principal: Principal = Depends(any_member),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    get_transaction(db, principal.merchant_id, transaction_id)
    row = latest_for(db, principal.merchant_id, transaction_id)
    if row is None:
        raise NotFoundError("This payment has not been scored")
    return RiskAssessmentOut.model_validate(row)


@router.post("/transactions/{transaction_id}/risk", response_model=RiskAssessmentOut)
def rescore(
    transaction_id: uuid.UUID,
    principal: Principal = Depends(operator),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    txn = get_transaction(db, principal.merchant_id, transaction_id)
    row = score_transaction(db, txn, trigger="manual", actor_id=principal.user.id)
    db.commit()
    return RiskAssessmentOut.model_validate(row)
