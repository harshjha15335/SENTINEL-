"""Merchant-bound dispute records and append-only response drafts.

A synchronized record is provider sourced only after a stored LIVE_SANDBOX payment reference
matches. Demo records have no provider dispute ID. No table enables external submission.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.core import _enum
from app.models.enums import DataOrigin


class Dispute(Base):
    __tablename__ = "disputes"
    __table_args__ = (UniqueConstraint("merchant_id", "provider_dispute_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE")
    )
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    provider_dispute_id: Mapped[str | None] = mapped_column(String(128))
    reason: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(64))
    response_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    data_origin: Mapped[DataOrigin] = mapped_column(_enum(DataOrigin, "data_origin"))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DisputeDraft(Base):
    __tablename__ = "dispute_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), index=True
    )
    merchant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("merchants.id"), index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    missing_information: Mapped[list[str]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
