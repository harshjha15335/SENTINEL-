import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import EmailStr, Field

from app.models.enums import (
    CasePriority,
    CaseResolution,
    CaseSource,
    CaseStatus,
    DataOrigin,
    EventProcessing,
    EventVerification,
    PolicyDecision,
    RiskBand,
    Role,
    TransactionStatus,
)
from app.schemas.common import ApiModel, RequestModel


class LoginRequest(RequestModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class MerchantOut(ApiModel):
    id: uuid.UUID
    name: str
    environment: str


class MeOut(ApiModel):
    id: uuid.UUID
    email: str
    role: Role
    merchant: MerchantOut


class SessionOut(ApiModel):
    user: MeOut
    csrf_token: str
    expires_at: datetime


class ProductOut(ApiModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str
    price_minor: int
    currency: str


class CreateOrderRequest(RequestModel):
    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=10)


class TransactionOut(ApiModel):
    id: uuid.UUID
    paypal_order_id: str | None
    paypal_capture_id: str | None
    amount_minor: int
    currency: str
    quantity: int
    status: TransactionStatus
    provider_status: str | None
    payer_reference: str | None
    data_origin: DataOrigin
    product_name: str | None = None
    failure_reason: str | None
    occurred_at: datetime | None
    created_at: datetime
    updated_at: datetime
    risk_score: float | None = None
    risk_band: RiskBand | None = None


class PaymentEventOut(ApiModel):
    id: uuid.UUID
    provider_event_id: str
    provider_event_type: str
    verification_status: EventVerification
    processing_status: EventProcessing
    data_origin: DataOrigin
    delivery_count: int
    received_at: datetime
    processed_at: datetime | None
    error_reason: str | None


class AuditOut(ApiModel):
    id: uuid.UUID
    actor_type: str
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    correlation_id: str | None
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime


class TransactionDetailOut(TransactionOut):
    provider_summary: dict[str, Any]
    events: list[PaymentEventOut]
    audit: list[AuditOut]


class OrderCreatedOut(ApiModel):
    transaction_id: uuid.UUID
    paypal_order_id: str
    status: TransactionStatus
    data_origin: DataOrigin


class PayPalStatusOut(ApiModel):
    mode: Literal["sandbox", "fixture"]
    credentials_configured: bool
    token_check: Literal["ok", "failed", "not_attempted"]
    token_error: str | None
    client_id: str | None
    webhook_id_configured: bool
    data_origin: DataOrigin


class OriginTotals(ApiModel):
    data_origin: DataOrigin
    captured_count: int
    captured_amount_minor: int
    currency: str


class OriginCount(ApiModel):
    data_origin: DataOrigin
    key: str
    count: int


class DashboardSummaryOut(ApiModel):
    transactions_total: int
    by_status: dict[str, int]
    captured_by_origin: list[OriginTotals]
    webhook_events: dict[str, int]
    recent: list[TransactionOut]
    open_cases_by_origin: list[OriginCount]
    risk_bands_by_origin: list[OriginCount]


class RiskContributionOut(ApiModel):
    feature: str
    label: str
    value: float
    contribution: float


class RiskExplanationOut(ApiModel):
    method: str
    space: str
    base_value: float
    raw_probability: float
    contributions: list[RiskContributionOut]


class RiskAssessmentOut(ApiModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    model_version: str
    feature_version: str
    risk_score: float
    risk_band: RiskBand
    policy_decision: PolicyDecision
    policy_mode: str
    thresholds: dict[str, float]
    feature_snapshot: dict[str, float]
    explanation: RiskExplanationOut
    limitations: list[str]
    data_origin: DataOrigin
    trigger: str
    created_at: datetime
    assessment_type: Literal["MODEL_GENERATED"] = "MODEL_GENERATED"


class ModelMetricsOut(ApiModel):
    rows: int
    positives: int
    prevalence: float
    threshold: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    flag_rate: float
    pr_auc: float
    roc_auc: float
    brier: float
    expected_cost: float
    expected_cost_no_review: float


class ModelCardOut(ApiModel):
    model_version: str
    feature_version: str
    track: str
    chosen_model: str
    trained_at: str
    training_data: str
    split: dict[str, Any]
    calibration: str
    thresholds: dict[str, float]
    threshold_selection: str
    cost_assumptions: dict[str, float]
    validation_comparison: dict[str, dict[str, float]]
    test_metrics: ModelMetricsOut
    test_metrics_rules_baseline: ModelMetricsOut
    features: list[dict[str, str]]
    limitations: list[str]


class UserRefOut(ApiModel):
    id: uuid.UUID
    email: str


class CaseOut(ApiModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    risk_assessment_id: uuid.UUID | None
    source: CaseSource
    status: CaseStatus
    priority: CasePriority
    title: str
    assignee: UserRefOut | None
    due_at: datetime
    resolution: CaseResolution | None
    resolution_note: str | None
    resolved_at: datetime | None
    data_origin: DataOrigin
    created_at: datetime
    updated_at: datetime
    transaction: TransactionOut


class CaseNoteOut(ApiModel):
    id: uuid.UUID
    author: UserRefOut | None
    body: str
    created_at: datetime


class CaseDetailOut(CaseOut):
    notes: list[CaseNoteOut]
    assessment: RiskAssessmentOut | None
    audit: list[AuditOut]


class OpenCaseRequest(RequestModel):
    transaction_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=2000)


class CaseNoteRequest(RequestModel):
    body: str = Field(min_length=1, max_length=4000)


class ResolveCaseRequest(RequestModel):
    resolution: CaseResolution
    note: str = Field(min_length=3, max_length=4000)
