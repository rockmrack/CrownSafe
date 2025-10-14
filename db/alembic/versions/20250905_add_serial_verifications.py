"""add serial_verifications table

Revision ID: 20250905_add_serial_verifications
Revises: 20250904_add_report_records
Create Date: 2025-09-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20250905_add_serial_verifications"
down_revision = "20250904_add_report_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "serial_verifications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gtin", sa.String(length=32), nullable=True),
        sa.Column("lot_number", sa.String(length=128), nullable=True),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("manufacturer", sa.String(length=256), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="unknown"
        ),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column(
            "verification_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_index(
        "ix_serial_verifications_gtin", "serial_verifications", ["gtin"], unique=False
    )
    op.create_index(
        "ix_serial_verifications_lot_number",
        "serial_verifications",
        ["lot_number"],
        unique=False,
    )
    op.create_index(
        "ix_serial_verifications_serial_number",
        "serial_verifications",
        ["serial_number"],
        unique=False,
    )
    op.create_index(
        "ix_serial_verifications_gtin_lot",
        "serial_verifications",
        ["gtin", "lot_number"],
        unique=False,
    )
    op.create_index(
        "ix_serial_verifications_gtin_serial",
        "serial_verifications",
        ["gtin", "serial_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_serial_verifications_gtin_serial", table_name="serial_verifications"
    )
    op.drop_index("ix_serial_verifications_gtin_lot", table_name="serial_verifications")
    op.drop_index(
        "ix_serial_verifications_serial_number", table_name="serial_verifications"
    )
    op.drop_index(
        "ix_serial_verifications_lot_number", table_name="serial_verifications"
    )
    op.drop_index("ix_serial_verifications_gtin", table_name="serial_verifications")
    op.drop_table("serial_verifications")
