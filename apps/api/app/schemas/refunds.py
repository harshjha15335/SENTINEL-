"""Refund amounts are minor units; execution needs exact snapshot confirmation."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DataOrigin


class RefundCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount_minor: int | None = Field(default=None, strict=True, gt=0)


class RefundDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APPROVED", "REJECTED"]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RefundExecute(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: Literal[True]
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RefundOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    case_id: uuid.UUID
    transaction_id: uuid.UUID
    amount_minor: int
    currency: str
    data_origin: DataOrigin
    status: str
    requested_by_user_id: uuid.UUID
    decided_by_user_id: uuid.UUID | None
    decided_by_role: str | None
    snapshot_sha256: str
    request_key: str
    provider_refund_id: str | None
    provider_status: str | None
    submission_started: bool
    error_category: str | None
    attempts: int
    created_at: datetime
    decided_at: datetime | None
    execution_started_at: datetime | None
    completed_at: datetime | None


class RefundHistoryOut(BaseModel):
    items: list[RefundOut]
    captured_amount_minor: int
    reserved_amount_minor: int
    available_amount_minor: int
    currency: str
    balance_known: bool
    execution_enabled: bool
    limitation: str
