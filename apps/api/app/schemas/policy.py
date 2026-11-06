"""Validation-only simulator contracts with explicit illustrative money assumptions."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel, RequestModel


class PolicyParameters(RequestModel):
    high_threshold: float = Field(default=0.1036, ge=0, le=1)
    review_capacity_share: float = Field(default=0.08, gt=0, le=1)
    false_positive_cost_usd: float = Field(default=0, ge=0, le=1_000_000)
    false_negative_cost_usd: float = Field(default=20, ge=0, le=1_000_000)
    investigation_cost_usd: float = Field(default=4, ge=0, le=1_000_000)
    average_value_at_risk_usd: float = Field(default=100, ge=0, le=1_000_000)
    recovery_share: float = Field(default=0.7, ge=0, le=1)


class PolicyMetrics(ApiModel):
    rows: int
    positives: int
    tp: int
    fp: int
    tn: int
    fn: int
    flagged: int
    precision: float
    recall: float
    false_positive_rate: float
    flag_rate: float
    review_capacity_count: int
    capacity_utilization: float
    over_capacity: bool
    review_cost_usd: float
    false_positive_cost_usd: float
    missed_outcome_cost_usd: float
    residual_loss_usd: float
    estimated_recoverable_usd: float
    total_assumed_cost_usd: float


class CurvePoint(ApiModel):
    x: float
    y: float


class CalibrationPoint(ApiModel):
    mean_score: float
    adverse_rate: float
    count: int


class ThresholdPoint(ApiModel):
    threshold: float
    flagged: int
    precision: float
    recall: float
    total_assumed_cost_usd: float


class PolicySimulationOut(ApiModel):
    data_origin: Literal["SYNTHETIC_DEMO"] = "SYNTHETIC_DEMO"
    split: Literal["validation"] = "validation"
    model_version: str
    dataset_sha256: str
    validation_rows: int
    validation_start: datetime
    validation_end: datetime
    frozen_test_rows: int
    baseline_parameters: PolicyParameters
    proposed_parameters: PolicyParameters
    baseline: PolicyMetrics
    proposed: PolicyMetrics
    roc_auc: float
    average_precision: float
    brier: float
    roc_curve: list[CurvePoint]
    precision_recall_curve: list[CurvePoint]
    calibration: list[CalibrationPoint]
    thresholds: list[ThresholdPoint]
    limitations: list[str]


class CreatePolicyRequest(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    rationale: str = Field(min_length=10, max_length=4000)
    parameters: PolicyParameters


class DecidePolicyRequest(RequestModel):
    decision: Literal["APPROVED", "REJECTED"]


class PolicyDraftOut(ApiModel):
    id: uuid.UUID
    name: str
    rationale: str
    parameters: PolicyParameters
    model_version: str
    dataset_sha256: str
    snapshot_sha256: str
    status: str
    shadow_only: bool
    requested_by_user_id: uuid.UUID
    decided_by_user_id: uuid.UUID | None
    created_at: datetime
    submitted_at: datetime | None
    decided_at: datetime | None
