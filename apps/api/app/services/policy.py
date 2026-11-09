"""Reconstruct validation predictions with frozen inference only; never fit or score test rows."""

import hashlib
import json
import math
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal
from app.core.errors import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from app.models.enums import Role
from app.models.policy import PolicyDraft
from app.schemas.policy import (
    CalibrationPoint,
    CurvePoint,
    PolicyMetrics,
    PolicyParameters,
    PolicySimulationOut,
    ThresholdPoint,
)
from app.services import audit
from app.services.demo.scenario import generate
from app.services.risk.features import TxnView, compute_features
from app.services.risk.model import get_model


class PolicyDataUnavailable(DomainError):
    status_code = 503
    code = "policy_data_unavailable"


@dataclass(frozen=True)
class ValidationData:
    scores: tuple[float, ...]
    labels: tuple[int, ...]
    start: datetime
    end: datetime
    model_version: str
    sha256: str
    test_rows: int


@lru_cache(maxsize=1)
def validation_data() -> ValidationData:
    model = get_model()
    meta = model.metadata
    rows = generate(int(meta["dataset"]["seed"]))
    digest = hashlib.sha256(
        json.dumps(
            [(t.ref, t.amount_minor, t.occurred_at.isoformat(), t.adverse) for t in rows]
        ).encode()
    ).hexdigest()
    if digest != meta["dataset"]["sha256"] or len(rows) != meta["dataset"]["rows"]:
        raise PolicyDataUnavailable("Synthetic scenario no longer matches the frozen model dataset")
    train_n = int(meta["split"]["train_rows"])
    valid_n = int(meta["split"]["valid_rows"])
    stop = train_n + valid_n
    if stop >= len(rows) or rows[stop].occurred_at.isoformat() != meta["split"]["test_start"]:
        raise PolicyDataUnavailable("Frozen chronological split does not match the scenario")
    payer: dict[str, list[TxnView]] = defaultdict(list)
    history: list[TxnView] = []
    features = []
    for i, txn in enumerate(rows[:stop]):
        view = TxnView(
            txn.occurred_at, txn.amount_minor, txn.payer_reference, txn.refunded_at, txn.disputed_at
        )
        if i >= train_n:
            features.append(compute_features(view, payer[txn.payer_reference], history[-400:]))
        payer[txn.payer_reference].append(view)
        history.append(view)
    predictions = model.predict(features)
    return ValidationData(
        tuple(p.probability for p in predictions),
        tuple(int(t.adverse) for t in rows[train_n:stop]),
        rows[train_n].occurred_at,
        rows[stop - 1].occurred_at,
        model.version,
        digest,
        len(rows) - stop,
    )


def metrics(data: ValidationData, params: PolicyParameters) -> PolicyMetrics:
    tp = fp = tn = fn = 0
    for score, label in zip(data.scores, data.labels, strict=True):
        is_flagged = score >= params.high_threshold
        tp += int(is_flagged and label == 1)
        fp += int(is_flagged and label == 0)
        tn += int(not is_flagged and label == 0)
        fn += int(not is_flagged and label == 1)
    n, flagged = len(data.scores), tp + fp
    capacity = max(1, math.floor(n * params.review_capacity_share))
    review_cost = flagged * params.investigation_cost_usd
    fp_cost = fp * params.false_positive_cost_usd
    missed_cost = fn * params.false_negative_cost_usd
    residual_loss = (fn + tp * (1 - params.recovery_share)) * params.average_value_at_risk_usd
    return PolicyMetrics(
        rows=n,
        positives=tp + fn,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        flagged=flagged,
        precision=tp / flagged if flagged else 0,
        recall=tp / (tp + fn) if tp + fn else 0,
        false_positive_rate=fp / (fp + tn) if fp + tn else 0,
        flag_rate=flagged / n if n else 0,
        review_capacity_count=capacity,
        capacity_utilization=flagged / capacity,
        over_capacity=flagged > capacity,
        review_cost_usd=round(review_cost, 2),
        false_positive_cost_usd=round(fp_cost, 2),
        missed_outcome_cost_usd=round(missed_cost, 2),
        residual_loss_usd=round(residual_loss, 2),
        estimated_recoverable_usd=round(
            tp * params.recovery_share * params.average_value_at_risk_usd, 2
        ),
        total_assumed_cost_usd=round(review_cost + fp_cost + missed_cost + residual_loss, 2),
    )


def curves(data: ValidationData) -> tuple[list[CurvePoint], list[CurvePoint], float, float]:
    # Aggregate tied scores before advancing either curve, matching threshold semantics.
    groups: dict[float, list[int]] = defaultdict(list)
    for score, label in zip(data.scores, data.labels, strict=True):
        groups[score].append(label)
    positives = sum(data.labels)
    negatives = len(data.labels) - positives
    roc = [CurvePoint(x=0, y=0)]
    pr = [CurvePoint(x=0, y=1)]
    tp = fp = 0
    ap = auc = previous_recall = previous_fpr = 0.0
    for score in sorted(groups, reverse=True):
        labels = groups[score]
        tp += sum(labels)
        fp += len(labels) - sum(labels)
        recall = tp / positives if positives else 0
        fpr = fp / negatives if negatives else 0
        precision = tp / (tp + fp)
        ap += (recall - previous_recall) * precision
        auc += (fpr - previous_fpr) * (recall + previous_recall) / 2
        roc.append(CurvePoint(x=fpr, y=recall))
        pr.append(CurvePoint(x=recall, y=precision))
        previous_recall, previous_fpr = recall, fpr
    return roc, pr, auc, ap


def simulate(params: PolicyParameters) -> PolicySimulationOut:
    data = validation_data()
    model = get_model()
    baseline_params = params.model_copy(update={"high_threshold": model.high_threshold})
    roc, pr, auc, ap = curves(data)
    calibration = []
    for i in range(10):
        indices = [j for j, s in enumerate(data.scores) if min(int(s * 10), 9) == i]
        if indices:
            calibration.append(
                CalibrationPoint(
                    mean_score=sum(data.scores[j] for j in indices) / len(indices),
                    adverse_rate=sum(data.labels[j] for j in indices) / len(indices),
                    count=len(indices),
                )
            )
    thresholds = []
    for threshold in sorted(
        {i / 50 for i in range(51)} | {model.high_threshold, params.high_threshold}
    ):
        m = metrics(data, params.model_copy(update={"high_threshold": threshold}))
        thresholds.append(
            ThresholdPoint(
                threshold=threshold,
                flagged=m.flagged,
                precision=m.precision,
                recall=m.recall,
                total_assumed_cost_usd=m.total_assumed_cost_usd,
            )
        )
    return PolicySimulationOut(
        model_version=data.model_version,
        dataset_sha256=data.sha256,
        validation_rows=len(data.scores),
        validation_start=data.start,
        validation_end=data.end,
        frozen_test_rows=data.test_rows,
        baseline_parameters=baseline_params,
        proposed_parameters=params,
        baseline=metrics(data, baseline_params),
        proposed=metrics(data, params),
        roc_auc=auc,
        average_precision=ap,
        brier=sum((s - y) ** 2 for s, y in zip(data.scores, data.labels, strict=True))
        / len(data.scores),
        roc_curve=roc,
        precision_recall_curve=pr,
        calibration=calibration,
        thresholds=thresholds,
        limitations=[
            (
                "SYNTHETIC_DEMO validation rows reconstructed from the digest-checked "
                "frozen scenario; inference only, no fitting or test scoring."
            ),
            (
                "Calibration was already fitted on this validation split; validation "
                "calibration is descriptive, not an independent generalization estimate."
            ),
            (
                "All flagged rows are assumed reviewed in the illustrative cost model. "
                "Capacity overload is shown separately; no automatic production "
                "activation occurs."
            ),
            (
                "USD costs, average value at risk and recoverable share are user "
                "assumptions, not measured loss or recovered money."
            ),
            (
                "The frozen held-out test benchmark remains unchanged and is never used "
                "by the interactive simulator."
            ),
        ],
    )


def snapshot_hash(
    parameters: dict[str, float],
    model: str,
    dataset: str,
    *,
    name: str,
    rationale: str,
    merchant_id: uuid.UUID,
    requested_by_user_id: uuid.UUID,
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "parameters": parameters,
                "model": model,
                "dataset": dataset,
                "name": name,
                "rationale": rationale,
                "merchant_id": str(merchant_id),
                "requested_by_user_id": str(requested_by_user_id),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def create(
    db: Session, principal: Principal, *, name: str, rationale: str, params: PolicyParameters
) -> PolicyDraft:
    if principal.role not in (Role.ADMIN, Role.ANALYST):
        raise PermissionDeniedError("Operator role required")
    data = validation_data()
    parameters = {k: float(v) for k, v in params.model_dump().items()}
    row = PolicyDraft(
        merchant_id=principal.merchant_id,
        requested_by_user_id=principal.user.id,
        name=name,
        rationale=rationale,
        parameters=parameters,
        model_version=data.model_version,
        dataset_sha256=data.sha256,
        snapshot_sha256=snapshot_hash(
            parameters,
            data.model_version,
            data.sha256,
            name=name,
            rationale=rationale,
            merchant_id=principal.merchant_id,
            requested_by_user_id=principal.user.id,
        ),
        status="DRAFT",
        shadow_only=True,
    )
    db.add(row)
    db.flush()
    audit.record(
        db,
        action="policy.draft.created",
        entity_type="policy_draft",
        entity_id=row.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
        actor_type="USER",
        metadata={"shadow_only": True, "snapshot_sha256": row.snapshot_sha256},
    )
    db.commit()
    return row


def get_draft(db: Session, principal: Principal, ident: uuid.UUID) -> PolicyDraft:
    row = db.scalar(
        select(PolicyDraft)
        .where(PolicyDraft.id == ident, PolicyDraft.merchant_id == principal.merchant_id)
        .with_for_update()
    )
    if row is None:
        raise NotFoundError("Policy draft not found")
    if (
        snapshot_hash(
            row.parameters,
            row.model_version,
            row.dataset_sha256,
            name=row.name,
            rationale=row.rationale,
            merchant_id=row.merchant_id,
            requested_by_user_id=row.requested_by_user_id,
        )
        != row.snapshot_sha256
    ):
        raise ConflictError("Policy snapshot integrity check failed")
    return row


def submit(db: Session, principal: Principal, ident: uuid.UUID) -> PolicyDraft:
    if principal.role not in (Role.ADMIN, Role.ANALYST):
        raise PermissionDeniedError("Operator role required")
    row = get_draft(db, principal, ident)
    if row.requested_by_user_id != principal.user.id:
        raise PermissionDeniedError("Only the requester can submit this draft")
    if row.status != "DRAFT":
        raise ConflictError("Only a draft can be submitted")
    row.status = "PENDING_APPROVAL"
    row.submitted_at = datetime.now(UTC)
    audit.record(
        db,
        action="policy.submitted",
        entity_type="policy_draft",
        entity_id=row.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
        actor_type="USER",
        metadata={"shadow_only": True},
    )
    db.commit()
    return row


def decide(db: Session, principal: Principal, ident: uuid.UUID, decision: str) -> PolicyDraft:
    if principal.role is not Role.ADMIN:
        raise PermissionDeniedError("Administrator role required")
    if decision not in ("APPROVED", "REJECTED"):
        raise ConflictError("Invalid policy decision")
    row = get_draft(db, principal, ident)
    if row.requested_by_user_id == principal.user.id:
        raise PermissionDeniedError("Independent administrator required")
    if row.status != "PENDING_APPROVAL":
        raise ConflictError("Policy is not awaiting a decision")
    row.status = decision
    row.decided_by_user_id = principal.user.id
    row.decided_at = datetime.now(UTC)
    audit.record(
        db,
        action="policy.decided",
        entity_type="policy_draft",
        entity_id=row.id,
        merchant_id=principal.merchant_id,
        actor_id=principal.user.id,
        actor_type="USER",
        metadata={"decision": decision, "shadow_only": True},
    )
    db.commit()
    return row
