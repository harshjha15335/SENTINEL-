"""investigations evidence approvals

Revision ID: f3742645a803
Revises: 67fa573a3cac
Create Date: 2026-10-11 05:27:54.083335

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

ENUMS = {
    # Types created by earlier migrations; never re-create them here.
    "data_origin": postgresql.ENUM(name="data_origin", create_type=False),
    "user_role": postgresql.ENUM(name="user_role", create_type=False),
    "evidence_category": postgresql.ENUM(
        "INVOICE",
        "SHIPPING_PROOF",
        "DELIVERY_CONFIRMATION",
        "CUSTOMER_COMMUNICATION",
        "REFUND_POLICY",
        "OTHER",
        name="evidence_category",
        create_type=False,
    ),
    "extraction_status": postgresql.ENUM(
        "EXTRACTED",
        "NO_TEXT",
        "NOT_SUPPORTED",
        "FAILED",
        name="extraction_status",
        create_type=False,
    ),
    "investigation_status": postgresql.ENUM(
        "QUEUED", "RUNNING", "COMPLETED", "FAILED", name="investigation_status", create_type=False
    ),
    "investigation_mode": postgresql.ENUM(
        "AI_AGENT", "DETERMINISTIC", name="investigation_mode", create_type=False
    ),
    "investigation_error_category": postgresql.ENUM(
        "PROVIDER_UNAVAILABLE",
        "PROVIDER_TIMEOUT",
        "PROVIDER_ERROR",
        "INVALID_OUTPUT",
        "UNSUPPORTED_ASSERTION",
        "BUDGET_EXCEEDED",
        "ABANDONED",
        "INTERNAL",
        name="investigation_error_category",
        create_type=False,
    ),
    "approval_action_type": postgresql.ENUM(
        "MANUAL_REVIEW",
        "EVIDENCE_PACKET_INTERNAL",
        "PREPARE_REFUND",
        name="approval_action_type",
        create_type=False,
    ),
    "approval_status": postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", name="approval_status", create_type=False
    ),
    "execution_status": postgresql.ENUM(
        "COMPLETED_INTERNAL", "NOT_EXECUTED", name="execution_status", create_type=False
    ),
    "approval_decision_value": postgresql.ENUM(
        "APPROVED", "REJECTED", name="approval_decision_value", create_type=False
    ),
}
NEW_TYPES = [
    "evidence_category",
    "extraction_status",
    "investigation_status",
    "investigation_mode",
    "investigation_error_category",
    "approval_action_type",
    "approval_status",
    "execution_status",
    "approval_decision_value",
]

# Approval snapshots are immutable once written, and decisions are append-only. Enforced in the
# database so no code path (or manual UPDATE) can rewrite what a reviewer approved.
IMMUTABILITY_SQL = """
CREATE FUNCTION approval_request_immutable() RETURNS trigger AS $$
BEGIN
  IF NEW.action_snapshot IS DISTINCT FROM OLD.action_snapshot
     OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
     OR NEW.action_type IS DISTINCT FROM OLD.action_type
     OR NEW.case_id IS DISTINCT FROM OLD.case_id
     OR NEW.merchant_id IS DISTINCT FROM OLD.merchant_id
     OR NEW.requested_by_user_id IS DISTINCT FROM OLD.requested_by_user_id
     OR NEW.required_roles IS DISTINCT FROM OLD.required_roles THEN
    RAISE EXCEPTION 'approval request snapshot is immutable';
  END IF;
  IF OLD.status <> 'PENDING' AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'approval request already decided';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER approval_requests_immutable BEFORE UPDATE ON approval_requests
  FOR EACH ROW EXECUTE FUNCTION approval_request_immutable();
CREATE FUNCTION approval_decision_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'approval decisions cannot be modified';
END $$ LANGUAGE plpgsql;
CREATE TRIGGER approval_decisions_append_only BEFORE UPDATE ON approval_decisions
  FOR EACH ROW EXECUTE FUNCTION approval_decision_append_only();
"""

# revision identifiers, used by Alembic.
revision: str = "f3742645a803"
down_revision: str | Sequence[str] | None = "67fa573a3cac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    for name in NEW_TYPES:
        ENUMS[name].create(bind, checkfirst=False)
    op.create_table(
        "stored_blobs",
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("body", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_stored_blobs")),
    )
    op.create_table(
        "evidence_artifacts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=True),
        sa.Column("category", ENUMS["evidence_category"], nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(length=200), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("extraction_status", ENUMS["extraction_status"], nullable=False),
        sa.Column("extraction_note", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("data_origin", ENUMS["data_origin"], nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(sha256) = 64", name=op.f("ck_evidence_artifacts_sha256_hex")
        ),
        sa.CheckConstraint("size_bytes > 0", name=op.f("ck_evidence_artifacts_size_positive")),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_evidence_artifacts_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_evidence_artifacts_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_evidence_artifacts_uploaded_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_artifacts")),
        sa.UniqueConstraint("case_id", "sha256", name=op.f("uq_evidence_artifacts_case_id_sha256")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_evidence_artifacts_storage_key")),
    )
    op.create_index(
        op.f("ix_evidence_artifacts_case_id"), "evidence_artifacts", ["case_id"], unique=False
    )
    op.create_table(
        "investigation_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("initiated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("status", ENUMS["investigation_status"], nullable=False),
        sa.Column("mode", ENUMS["investigation_mode"], nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_category", ENUMS["investigation_error_category"], nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("data_origin", ENUMS["data_origin"], nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "(status = 'COMPLETED') = (findings IS NOT NULL)",
            name=op.f("ck_investigation_runs_findings_when_completed"),
        ),
        sa.CheckConstraint(
            "(status = 'FAILED') = (error_category IS NOT NULL)",
            name=op.f("ck_investigation_runs_error_when_failed"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_investigation_runs_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_user_id"],
            ["users.id"],
            name=op.f("fk_investigation_runs_initiated_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_investigation_runs_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_investigation_runs_transaction_id_transactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_investigation_runs")),
    )
    op.create_index(
        "ix_investigation_runs_case_created",
        "investigation_runs",
        ["case_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigation_runs_case_id"), "investigation_runs", ["case_id"], unique=False
    )
    op.create_index(
        "uq_investigation_runs_active_per_case",
        "investigation_runs",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), nullable=False),
        sa.Column("action_type", ENUMS["approval_action_type"], nullable=False),
        sa.Column("action_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column("required_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("status", ENUMS["approval_status"], nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(), nullable=True),
        sa.Column("investigation_run_id", sa.UUID(), nullable=True),
        sa.Column("data_origin", ENUMS["data_origin"], nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(status = 'PENDING') = (decided_at IS NULL)",
            name=op.f("ck_approval_requests_decided_at_when_decided"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_approval_requests_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["investigation_run_id"],
            ["investigation_runs.id"],
            name=op.f("fk_approval_requests_investigation_run_id_investigation_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_approval_requests_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            name=op.f("fk_approval_requests_requested_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("fk_approval_requests_transaction_id_transactions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_requests")),
    )
    op.create_index(
        op.f("ix_approval_requests_case_id"), "approval_requests", ["case_id"], unique=False
    )
    op.create_index(
        "ix_approval_requests_merchant_status",
        "approval_requests",
        ["merchant_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_approval_requests_pending_action",
        "approval_requests",
        ["case_id", "action_type"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_table(
        "evidence_packets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("case_id", sa.UUID(), nullable=False),
        sa.Column("investigation_run_id", sa.UUID(), nullable=True),
        sa.Column("generated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=200), nullable=False),
        sa.Column("contents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name=op.f("fk_evidence_packets_case_id_cases"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["generated_by_user_id"],
            ["users.id"],
            name=op.f("fk_evidence_packets_generated_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["investigation_run_id"],
            ["investigation_runs.id"],
            name=op.f("fk_evidence_packets_investigation_run_id_investigation_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_evidence_packets_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_packets")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_evidence_packets_storage_key")),
    )
    op.create_index(
        op.f("ix_evidence_packets_case_id"), "evidence_packets", ["case_id"], unique=False
    )
    op.create_table(
        "action_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("approval_request_id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("action_type", ENUMS["approval_action_type"], nullable=False),
        sa.Column("status", ENUMS["execution_status"], nullable=False),
        sa.Column("provider_called", sa.Boolean(), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider_called = false", name=op.f("ck_action_executions_no_provider_calls_in_phase4")
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["approval_requests.id"],
            name=op.f("fk_action_executions_approval_request_id_approval_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_action_executions_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_executions")),
        sa.UniqueConstraint(
            "approval_request_id", name=op.f("uq_action_executions_approval_request_id")
        ),
    )
    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("approval_request_id", sa.UUID(), nullable=False),
        sa.Column("merchant_id", sa.UUID(), nullable=False),
        sa.Column("decision", ENUMS["approval_decision_value"], nullable=False),
        sa.Column("decided_by_user_id", sa.UUID(), nullable=True),
        sa.Column("decided_by_role", ENUMS["user_role"], nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("snapshot_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["approval_request_id"],
            ["approval_requests.id"],
            name=op.f("fk_approval_decisions_approval_request_id_approval_requests"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["users.id"],
            name=op.f("fk_approval_decisions_decided_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_approval_decisions_merchant_id_merchants"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_decisions")),
        sa.UniqueConstraint(
            "approval_request_id", name=op.f("uq_approval_decisions_approval_request_id")
        ),
    )
    op.execute(IMMUTABILITY_SQL)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS approval_decisions_append_only ON approval_decisions")
    op.execute("DROP TRIGGER IF EXISTS approval_requests_immutable ON approval_requests")
    op.execute("DROP FUNCTION IF EXISTS approval_decision_append_only()")
    op.execute("DROP FUNCTION IF EXISTS approval_request_immutable()")
    op.drop_table("approval_decisions")
    op.drop_table("action_executions")
    op.drop_index(op.f("ix_evidence_packets_case_id"), table_name="evidence_packets")
    op.drop_table("evidence_packets")
    op.drop_index(
        "uq_approval_requests_pending_action",
        table_name="approval_requests",
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.drop_index("ix_approval_requests_merchant_status", table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_case_id"), table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index(
        "uq_investigation_runs_active_per_case",
        table_name="investigation_runs",
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    op.drop_index(op.f("ix_investigation_runs_case_id"), table_name="investigation_runs")
    op.drop_index("ix_investigation_runs_case_created", table_name="investigation_runs")
    op.drop_table("investigation_runs")
    op.drop_index(op.f("ix_evidence_artifacts_case_id"), table_name="evidence_artifacts")
    op.drop_table("evidence_artifacts")
    op.drop_table("stored_blobs")
    bind = op.get_bind()
    for name in reversed(NEW_TYPES):
        ENUMS[name].drop(bind, checkfirst=False)
