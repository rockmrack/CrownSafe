"""Add share tokens table for result sharing

Revision ID: 20250108_share_tokens
Revises: 20250108_scan_history
Create Date: 2025-01-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20250108_share_tokens"
down_revision = "20250108_scan_history"
branch_labels = None
depends_on = None


def upgrade():
    # Create share_tokens table
    op.create_table(
        "share_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(100), nullable=False),
        # What is being shared
        sa.Column("share_type", sa.String(50), nullable=False),
        sa.Column("content_id", sa.String(100), nullable=False),
        # Share metadata
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        # Access control
        sa.Column("max_views", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("password_protected", sa.Boolean(), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        # Share settings
        sa.Column("allow_download", sa.Boolean(), nullable=True),
        sa.Column("show_personal_info", sa.Boolean(), nullable=True),
        # Content snapshot
        sa.Column("content_snapshot", sa.JSON(), nullable=True),
        # Tracking
        sa.Column("last_accessed", sa.DateTime(), nullable=True),
        sa.Column("access_log", sa.JSON(), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(op.f("ix_share_tokens_token"), "share_tokens", ["token"], unique=True)
    op.create_index(
        op.f("ix_share_tokens_created_by"), "share_tokens", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_share_tokens_content_id"), "share_tokens", ["content_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_share_tokens_content_id"), table_name="share_tokens")
    op.drop_index(op.f("ix_share_tokens_created_by"), table_name="share_tokens")
    op.drop_index(op.f("ix_share_tokens_token"), table_name="share_tokens")
    op.drop_table("share_tokens")
