import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import EmailStr, Field

from app.models.enums import DataOrigin, EventProcessing, EventVerification, Role, TransactionStatus
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


class DashboardSummaryOut(ApiModel):
    transactions_total: int
    by_status: dict[str, int]
    captured_by_origin: list[OriginTotals]
    webhook_events: dict[str, int]
    recent: list[TransactionOut]
