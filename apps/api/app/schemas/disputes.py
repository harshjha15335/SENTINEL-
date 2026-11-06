import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.models.enums import DataOrigin
from app.schemas.common import ApiModel, RequestModel


class CreateDemoDispute(RequestModel):
    case_id: uuid.UUID
    reason: Literal["ITEM_NOT_RECEIVED", "SIGNIFICANTLY_NOT_AS_DESCRIBED", "UNAUTHORISED"] = (
        "ITEM_NOT_RECEIVED"
    )


class AssignDispute(RequestModel):
    user_id: uuid.UUID | None


class DisputeOut(ApiModel):
    id: uuid.UUID
    transaction_id: uuid.UUID
    case_id: uuid.UUID
    provider_dispute_id: str | None
    reason: str
    status: str
    stage: str
    response_due_at: datetime | None
    assigned_user_id: uuid.UUID | None
    data_origin: DataOrigin
    last_synced_at: datetime | None
    created_at: datetime
    external_submission_enabled: Literal[False] = False


class DisputeDraftOut(ApiModel):
    id: uuid.UUID
    dispute_id: uuid.UUID
    body: str
    citations: list[dict[str, Any]]
    missing_information: list[str]
    created_at: datetime
    generated_by_ai: Literal[False] = False
    label: str = "Deterministic response draft — requires human review"


class DisputeChecklistOut(ApiModel):
    key: str
    label: str
    provided: bool
    evidence_ids: list[str]


class DisputeDetailOut(ApiModel):
    dispute: DisputeOut
    checklist: list[DisputeChecklistOut]
    drafts: list[DisputeDraftOut]
    limitations: list[str]


class DisputeSyncOut(ApiModel):
    synchronized: int = Field(ge=0)
    scope: str = (
        "Only this merchant's single matched LIVE_SANDBOX captures; first provider page only"
    )
    submission_enabled: Literal[False] = False
