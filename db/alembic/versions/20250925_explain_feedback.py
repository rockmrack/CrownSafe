"""add explain feedback table.

Revision ID: 20250925_explain_feedback
Revises: 20250924_chat_memory
Create Date: 2025-09-25 10:00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "20250925_explain_feedback"
down_revision = "20250924_chat_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Detect database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Use appropriate types based on dialect
    if is_sqlite:
        uuid_type = sa.String(36)
        now_func = sa.text("CURRENT_TIMESTAMP")
    else:
        uuid_type = postgresql.UUID(as_uuid=True)
        now_func = sa.text("now()")

    op.create_table(
        "explain_feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("scan_id", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("helpful", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),  # optional category
        sa.Column("comment", sa.Text(), nullable=True),  # optional freeform
        sa.Column("platform", sa.String(length=32), nullable=True),  # ios|android|web
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("jurisdiction_code", sa.String(length=8), nullable=True),  # e.g. EU/US
    )
    op.create_index("ix_explain_feedback_scan_id", "explain_feedback", ["scan_id"])
    op.create_index("ix_explain_feedback_created_at", "explain_feedback", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_explain_feedback_created_at", table_name="explain_feedback")
    op.drop_index("ix_explain_feedback_scan_id", table_name="explain_feedback")
    op.drop_table("explain_feedback")
