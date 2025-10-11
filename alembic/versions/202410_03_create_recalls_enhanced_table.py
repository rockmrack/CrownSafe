"""Create recalls_enhanced table for 39-agency coverage

Revision ID: 202410_03_001
Revises:
Create Date: 2025-10-03 09:00:00.000000

This migration creates the core recalls_enhanced table that supports
all 39 international regulatory agencies with comprehensive product identifiers.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "202410_03_001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create recalls_enhanced table with comprehensive schema"""
    # Check if table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "recalls_enhanced" not in inspector.get_table_names():
        op.create_table(
            "recalls_enhanced",
            # PRIMARY IDENTIFIERS
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("recall_id", sa.String(), unique=True, index=True, nullable=False),
            # PRODUCT IDENTIFIERS
            sa.Column("product_name", sa.String(), index=True, nullable=False),
            sa.Column("brand", sa.String(), index=True, nullable=True),
            sa.Column("manufacturer", sa.String(), nullable=True),
            sa.Column("model_number", sa.String(), index=True, nullable=True),
            # RETAIL IDENTIFIERS (Barcodes)
            sa.Column("upc", sa.String(), index=True, nullable=True),
            sa.Column("ean_code", sa.String(), index=True, nullable=True),
            sa.Column("gtin", sa.String(), index=True, nullable=True),
            sa.Column("article_number", sa.String(), index=True, nullable=True),
            # BATCH/LOT IDENTIFIERS
            sa.Column("lot_number", sa.String(), index=True, nullable=True),
            sa.Column("batch_number", sa.String(), index=True, nullable=True),
            sa.Column("serial_number", sa.String(), index=True, nullable=True),
            sa.Column("part_number", sa.String(), index=True, nullable=True),
            # DATE IDENTIFIERS
            sa.Column("expiry_date", sa.Date(), index=True, nullable=True),
            sa.Column("best_before_date", sa.Date(), index=True, nullable=True),
            sa.Column("production_date", sa.Date(), index=True, nullable=True),
            # PHARMACEUTICAL IDENTIFIERS
            sa.Column("ndc_number", sa.String(), index=True, nullable=True),
            sa.Column("din_number", sa.String(), index=True, nullable=True),
            # VEHICLE IDENTIFIERS
            sa.Column("vehicle_make", sa.String(), index=True, nullable=True),
            sa.Column("vehicle_model", sa.String(), index=True, nullable=True),
            sa.Column("model_year", sa.String(), index=True, nullable=True),
            sa.Column("vin_range", sa.String(), nullable=True),
            # REGIONAL REGISTRY CODES
            sa.Column("registry_codes", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            # GEOGRAPHIC/DISTRIBUTION
            sa.Column("country", sa.String(), nullable=True),
            sa.Column("regions_affected", postgresql.JSON(astext_type=sa.Text()), nullable=True),
            # RECALL METADATA
            sa.Column("recall_date", sa.Date(), index=True, nullable=False),
            sa.Column("source_agency", sa.String(), index=True, nullable=True),
            sa.Column("hazard", sa.Text(), nullable=True),
            sa.Column("hazard_category", sa.String(), index=True, nullable=True),
            sa.Column("severity", sa.String(length=50), nullable=True),
            sa.Column("risk_category", sa.String(length=100), nullable=True),
            sa.Column("recall_reason", sa.Text(), nullable=True),
            sa.Column("remedy", sa.Text(), nullable=True),
            sa.Column("recall_class", sa.String(), nullable=True),
            # DESCRIPTIVE FIELDS
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("manufacturer_contact", sa.String(), nullable=True),
            sa.Column("url", sa.String(), nullable=True),
            # SEARCH OPTIMIZATION
            sa.Column("search_keywords", sa.Text(), nullable=True),
            sa.Column("agency_specific_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        )

        # Create additional indexes for performance
        op.create_index("idx_recalls_severity", "recalls_enhanced", ["severity"])
        op.create_index("idx_recalls_risk_category", "recalls_enhanced", ["risk_category"])
        op.create_index("idx_recalls_hazard_category", "recalls_enhanced", ["hazard_category"])


def downgrade():
    """Drop recalls_enhanced table"""
    op.drop_table("recalls_enhanced")
