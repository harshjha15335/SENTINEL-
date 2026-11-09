"""Phase 4 records: investigation runs, evidence, evidence packets and approvals.

All of these hang off an existing ``Case`` and carry the case's ``merchant_id``; every query
filters by the principal's merchant. Deleting a case (for example when the synthetic demo is
reloaded) removes its Phase 4 records with it.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.core import User, _enum
from app.models.enums import (
    ApprovalActionType,
    ApprovalDecisionValue,
    ApprovalStatus,
    DataOrigin,
    EvidenceCategory,
    ExecutionStatus,
    ExtractionStatus,
    InvestigationErrorCategory,
    InvestigationMode,
    InvestigationStatus,
    Role,
)


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _case_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)


def _merchant_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False)


class InvestigationRun(Base):
    """One attempt to investigate a case. Append-only history: a new run never edits an old one.

    At most one QUEUED/RUNNING run per case (partial unique index). ``findings`` is set only on
    COMPLETED runs and has passed server-side validation against ``source_refs``.
    """

    __tablename__ = "investigation_runs"
    __table_args__ = (
        Index(
            "uq_investigation_runs_active_per_case",
            "case_id",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
        Index("ix_investigation_runs_case_created", "case_id", "created_at"),
        CheckConstraint(
            "(status = 'COMPLETED') = (findings IS NOT NULL)", name="findings_when_completed"
        ),
        CheckConstraint(
            "(status = 'FAILED') = (error_category IS NOT NULL)", name="error_when_failed"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        _enum(InvestigationStatus, "investigation_status"), nullable=False
    )
    mode: Mapped[InvestigationMode] = mapped_column(
        _enum(InvestigationMode, "investigation_mode"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    findings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    error_category: Mapped[InvestigationErrorCategory | None] = mapped_column(
        _enum(InvestigationErrorCategory, "investigation_error_category")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, "data_origin"), nullable=False
    )
    created_at: Mapped[datetime] = _created()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    initiated_by: Mapped[User | None] = relationship(lazy="joined")


class EvidenceArtifact(Base):
    """A merchant-uploaded file attached to a case. Untrusted data, MERCHANT_PROVIDED origin.

    The bytes live in the storage backend under ``storage_key`` (generated server-side, never
    derived from the filename). ``extracted_text`` is plain text for search and quoting; it is
    never used as instructions.
    """

    __tablename__ = "evidence_artifacts"
    __table_args__ = (
        UniqueConstraint("case_id", "sha256"),
        CheckConstraint("size_bytes > 0", name="size_positive"),
        CheckConstraint("char_length(sha256) = 64", name="sha256_hex"),
    )

    id: Mapped[uuid.UUID] = _pk()
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    category: Mapped[EvidenceCategory] = mapped_column(
        _enum(EvidenceCategory, "evidence_category"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    original_filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        _enum(ExtractionStatus, "extraction_status"), nullable=False
    )
    extraction_note: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, "data_origin"), nullable=False, default=DataOrigin.MERCHANT_PROVIDED
    )
    created_at: Mapped[datetime] = _created()

    uploaded_by: Mapped[User | None] = relationship(lazy="joined")


class StoredBlob(Base):
    """Bytes for the ``database`` storage backend (deployments without a persistent disk)."""

    __tablename__ = "stored_blobs"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    body: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = _created()


class EvidencePacket(Base):
    """A generated PDF evidence packet. Generating one is not submitting anything to PayPal."""

    __tablename__ = "evidence_packets"

    id: Mapped[uuid.UUID] = _pk()
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    investigation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="SET NULL")
    )
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    contents: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = _created()

    generated_by: Mapped[User | None] = relationship(lazy="joined")


class ApprovalRequest(Base):
    """A request for a second person to approve an action on a case.

    ``action_snapshot`` is built by the server when the request is created and cannot change
    afterwards (database trigger). Approval records intent; it never moves money in Phase 4.
    """

    __tablename__ = "approval_requests"
    __table_args__ = (
        Index(
            "uq_approval_requests_pending_action",
            "case_id",
            "action_type",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index("ix_approval_requests_merchant_status", "merchant_id", "status"),
        CheckConstraint(
            "(status = 'PENDING') = (decided_at IS NULL)", name="decided_at_when_decided"
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    case_id: Mapped[uuid.UUID] = _case_fk()
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[ApprovalActionType] = mapped_column(
        _enum(ApprovalActionType, "approval_action_type"), nullable=False
    )
    action_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    required_roles: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(
        _enum(ApprovalStatus, "approval_status"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    investigation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigation_runs.id", ondelete="SET NULL")
    )
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, "data_origin"), nullable=False
    )
    created_at: Mapped[datetime] = _created()
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requested_by: Mapped[User | None] = relationship(lazy="joined")
    decision: Mapped["ApprovalDecision | None"] = relationship(
        lazy="joined", back_populates="request", uselist=False
    )
    execution: Mapped["ActionExecution | None"] = relationship(lazy="joined", uselist=False)


class ApprovalDecision(Base):
    """The one decision on a request. Unique per request; rows cannot be updated (trigger)."""

    __tablename__ = "approval_decisions"

    id: Mapped[uuid.UUID] = _pk()
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    decision: Mapped[ApprovalDecisionValue] = mapped_column(
        _enum(ApprovalDecisionValue, "approval_decision_value"), nullable=False
    )
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    decided_by_role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = _created()

    decided_by: Mapped[User | None] = relationship(lazy="joined")
    request: Mapped[ApprovalRequest] = relationship(back_populates="decision")


class ActionExecution(Base):
    """What the backend did after an approval. One per approved request.

    For PREPARE_REFUND the status is NOT_EXECUTED and ``provider_called`` is always false in
    Phase 4: the approved intent is recorded for a later, separately protected execution step.
    """

    __tablename__ = "action_executions"
    __table_args__ = (
        CheckConstraint("provider_called = false", name="no_provider_calls_in_phase4"),
    )

    id: Mapped[uuid.UUID] = _pk()
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    merchant_id: Mapped[uuid.UUID] = _merchant_fk()
    action_type: Mapped[ApprovalActionType] = mapped_column(
        _enum(ApprovalActionType, "approval_action_type"), nullable=False
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        _enum(ExecutionStatus, "execution_status"), nullable=False
    )
    provider_called: Mapped[bool] = mapped_column(nullable=False, default=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = _created()
