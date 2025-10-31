"""Add composite indexes for performance optimization

Revision ID: 20251009_composite_indexes
Revises: fix_missing_columns
Create Date: 2025-10-09

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251009_composite_indexes"
down_revision = "fix_missing_columns"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add composite indexes to improve query performance.

    These indexes optimize common query patterns:
    1. Product name + brand + date searches
    2. Barcode/model number lookups
    3. Date-based queries with agency filtering
    """

    # Composite index for common recall searches
    # Optimizes queries like: WHERE product_name LIKE '%baby%' AND brand = 'XYZ'
    op.create_index(
        "idx_recalls_search_composite",
        "recalls_enhanced",
        ["product_name", "brand", "recall_date"],
        unique=False,
        postgresql_using="btree",
    )

    # Index for barcode and model number lookups
    # Optimizes: WHERE upc = '...' OR model_number = '...'
    op.create_index(
        "idx_recalls_identifiers",
        "recalls_enhanced",
        ["upc", "model_number"],
        unique=False,
    )

    # Index for date-based queries with agency filtering
    # Optimizes: WHERE recall_date > '...' AND source_agency = '...'
    op.create_index(
        "idx_recalls_date_agency",
        "recalls_enhanced",
        ["recall_date", "source_agency"],
        unique=False,
    )

    # Index for severity-based filtering (if column exists)
    # Optimizes: WHERE severity IN ('high', 'critical')
    op.create_index(
        "idx_recalls_severity",
        "recalls_enhanced",
        ["severity"],
        unique=False,
    )

    print("✅ Composite indexes created successfully")


def downgrade():
    """Remove composite indexes"""
    op.drop_index("idx_recalls_severity", table_name="recalls_enhanced")
    op.drop_index("idx_recalls_date_agency", table_name="recalls_enhanced")
    op.drop_index("idx_recalls_identifiers", table_name="recalls_enhanced")
    op.drop_index("idx_recalls_search_composite", table_name="recalls_enhanced")

    print("✅ Composite indexes removed")
