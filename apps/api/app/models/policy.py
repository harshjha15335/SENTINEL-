"""Shadow-only policy proposals. Approval never changes the serving model threshold."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PolicyDraft(Base):
    __tablename__ = "policy_drafts"
    __table_args__ = (
        CheckConstraint(
            "status in ('DRAFT','PENDING_APPROVAL','APPROVED','REJECTED')", name="policy_status"
        ),
        CheckConstraint(
            "decided_by_user_id is null or decided_by_user_id <> requested_by_user_id",
            name="policy_independent_decider",
        ),
        CheckConstraint("shadow_only = true", name="policy_shadow_only"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), index=True
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(120))
    rationale: Mapped[str] = mapped_column(Text)
    parameters: Mapped[dict[str, float]] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(80))
    dataset_sha256: Mapped[str] = mapped_column(String(64))
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    shadow_only: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
