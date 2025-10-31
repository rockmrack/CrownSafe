"""
Alembic migration: Add user_reports table for community unsafe product reporting

Revision ID: add_user_reports_table
Revises:
Create Date: 2025-10-12 15:45:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_user_reports_table"
down_revision = None  # Update this if you have previous migrations
branch_labels = None
depends_on = None


def upgrade():
    """Add user_reports table for community reporting of unsafe products"""

    # Create user_reports table
    op.create_table(
        "user_reports",
        sa.Column("report_id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("hazard_description", sa.Text(), nullable=False),
        sa.Column("barcode", sa.String(50), nullable=True),
        sa.Column("model_number", sa.String(100), nullable=True),
        sa.Column("lot_number", sa.String(100), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("manufacturer", sa.String(200), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="PENDING"),
        sa.Column("reporter_name", sa.String(100), nullable=True),
        sa.Column("reporter_email", sa.String(255), nullable=True),
        sa.Column("reporter_phone", sa.String(50), nullable=True),
        sa.Column("incident_date", sa.Date(), nullable=True),
        sa.Column("incident_description", sa.Text(), nullable=True),
        sa.Column("photos", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("report_id"),
    )

    # Create indexes for common queries
    op.create_index("idx_user_reports_user_id", "user_reports", ["user_id"])
    op.create_index("idx_user_reports_status", "user_reports", ["status"])
    op.create_index("idx_user_reports_severity", "user_reports", ["severity"])
    op.create_index("idx_user_reports_created_at", "user_reports", ["created_at"])
    op.create_index("idx_user_reports_barcode", "user_reports", ["barcode"])
    op.create_index("idx_user_reports_model_number", "user_reports", ["model_number"])


def downgrade():
    """Remove user_reports table"""
    op.drop_index("idx_user_reports_model_number", table_name="user_reports")
    op.drop_index("idx_user_reports_barcode", table_name="user_reports")
    op.drop_index("idx_user_reports_created_at", table_name="user_reports")
    op.drop_index("idx_user_reports_severity", table_name="user_reports")
    op.drop_index("idx_user_reports_status", table_name="user_reports")
    op.drop_index("idx_user_reports_user_id", table_name="user_reports")
    op.drop_table("user_reports")
