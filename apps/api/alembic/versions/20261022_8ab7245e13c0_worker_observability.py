"""Add nullable worker observability fields; no business rows are rewritten.

Revision ID: 8ab7245e13c0
Revises: 22ad61c52593
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "8ab7245e13c0"
down_revision = "22ad61c52593"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("worker_health", sa.Column("last_success_at", sa.DateTime(timezone=True)))
    op.add_column("worker_health", sa.Column("inbox_snapshot", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("worker_health", "inbox_snapshot")
    op.drop_column("worker_health", "last_success_at")
