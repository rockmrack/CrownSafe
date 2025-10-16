"""Add scan history and safety reports tables

Revision ID: 20250108_scan_history
Revises: 20250905_add_serial_verifications
Create Date: 2025-01-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20250108_scan_history"
down_revision = "20250905_add_serial_verifications"
branch_labels = None
depends_on = None


def upgrade():
    # Create scan_history table
    op.create_table(
        "scan_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.String(100), nullable=True),
        sa.Column("scan_timestamp", sa.DateTime(), nullable=True),
        # Product information
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("barcode", sa.String(100), nullable=True),
        sa.Column("model_number", sa.String(100), nullable=True),
        sa.Column("upc_gtin", sa.String(100), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        # Scan details
        sa.Column("scan_type", sa.String(50), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("barcode_format", sa.String(50), nullable=True),
        # Safety results
        sa.Column("verdict", sa.String(100), nullable=True),
        sa.Column("risk_level", sa.String(50), nullable=True),
        sa.Column("recalls_found", sa.Integer(), nullable=True),
        sa.Column("recall_ids", sa.JSON(), nullable=True),
        sa.Column("agencies_checked", sa.String(100), nullable=True),
        # Additional safety info
        sa.Column("allergen_alerts", sa.JSON(), nullable=True),
        sa.Column("pregnancy_warnings", sa.JSON(), nullable=True),
        sa.Column("age_warnings", sa.JSON(), nullable=True),
        # Report generation
        sa.Column("included_in_reports", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_history_user_id"), "scan_history", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_scan_history_scan_id"), "scan_history", ["scan_id"], unique=True
    )
    op.create_index(
        op.f("ix_scan_history_scan_timestamp"),
        "scan_history",
        ["scan_timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_history_barcode"), "scan_history", ["barcode"], unique=False
    )

    # Create safety_reports table
    op.create_table(
        "safety_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.String(100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Report details
        sa.Column("report_type", sa.String(50), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=True),
        sa.Column("period_end", sa.DateTime(), nullable=True),
        # Summary statistics
        sa.Column("total_scans", sa.Integer(), nullable=True),
        sa.Column("unique_products", sa.Integer(), nullable=True),
        sa.Column("recalls_found", sa.Integer(), nullable=True),
        sa.Column("high_risk_products", sa.Integer(), nullable=True),
        # Report content
        sa.Column("report_data", sa.JSON(), nullable=True),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("s3_url", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_safety_reports_report_id"),
        "safety_reports",
        ["report_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_safety_reports_user_id"), "safety_reports", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_safety_reports_user_id"), table_name="safety_reports")
    op.drop_index(op.f("ix_safety_reports_report_id"), table_name="safety_reports")
    op.drop_table("safety_reports")

    op.drop_index(op.f("ix_scan_history_barcode"), table_name="scan_history")
    op.drop_index(op.f("ix_scan_history_scan_timestamp"), table_name="scan_history")
    op.drop_index(op.f("ix_scan_history_scan_id"), table_name="scan_history")
    op.drop_index(op.f("ix_scan_history_user_id"), table_name="scan_history")
    op.drop_table("scan_history")
