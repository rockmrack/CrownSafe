"""Create recalls_enhanced table

Revision ID: 001
Revises:
Create Date: 2024-08-22 01:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the recalls_enhanced table with comprehensive schema"""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        print("Skipping Postgres-only migration on", bind.dialect.name)
        return

    # Check if table already exists (for idempotency)
    connection = op.get_bind()
    table_exists = connection.execute(
        text(
            """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'recalls_enhanced'
        );
    """,
        ),
    ).scalar()

    if table_exists:
        print("Table 'recalls_enhanced' already exists, skipping creation")
        return

    # Create the recalls_enhanced table
    op.create_table(
        "recalls_enhanced",
        # ================================
        # 🔑 PRIMARY IDENTIFIERS (Core)
        # ================================
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("recall_id", sa.String(), nullable=False, index=True),
        # ================================
        # 📦 PRODUCT IDENTIFIERS (Universal)
        # ================================
        sa.Column("product_name", sa.String(), nullable=False, index=True),
        sa.Column("brand", sa.String(), nullable=True, index=True),
        sa.Column("manufacturer", sa.String(), nullable=True),
        sa.Column("model_number", sa.String(), nullable=True, index=True),
        # ================================
        # 🏷️ RETAIL IDENTIFIERS (Global Barcodes)
        # ================================
        sa.Column("upc", sa.String(), nullable=True, index=True),
        sa.Column("ean_code", sa.String(), nullable=True, index=True),
        sa.Column("gtin", sa.String(), nullable=True, index=True),
        sa.Column("article_number", sa.String(), nullable=True, index=True),
        # ================================
        # 🔢 BATCH/LOT IDENTIFIERS (Food/Pharma Critical)
        # ================================
        sa.Column("lot_number", sa.String(), nullable=True, index=True),
        sa.Column("batch_number", sa.String(), nullable=True, index=True),
        sa.Column("serial_number", sa.String(), nullable=True, index=True),
        sa.Column("part_number", sa.String(), nullable=True, index=True),
        # ================================
        # 📅 DATE IDENTIFIERS (Expiry/Production Critical)
        # ================================
        sa.Column("expiry_date", sa.Date(), nullable=True, index=True),
        sa.Column("best_before_date", sa.Date(), nullable=True, index=True),
        sa.Column("production_date", sa.Date(), nullable=True, index=True),
        # ================================
        # 💊 PHARMACEUTICAL IDENTIFIERS (FDA/Health Agencies)
        # ================================
        sa.Column("ndc_number", sa.String(), nullable=True, index=True),
        sa.Column("din_number", sa.String(), nullable=True, index=True),
        # ================================
        # 🚗 VEHICLE IDENTIFIERS (NHTSA/Transport Agencies)
        # ================================
        sa.Column("vehicle_make", sa.String(), nullable=True, index=True),
        sa.Column("vehicle_model", sa.String(), nullable=True, index=True),
        sa.Column("model_year", sa.String(), nullable=True, index=True),
        sa.Column("vin_range", sa.String(), nullable=True),
        # ================================
        # 🌎 REGIONAL REGISTRY CODES (Latin America/International)
        # ================================
        sa.Column("registry_codes", JSON, nullable=True),
        # ================================
        # 📍 GEOGRAPHIC/DISTRIBUTION (Enhanced)
        # ================================
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("regions_affected", JSON, nullable=True),
        # ================================
        # ⚠️ RECALL METADATA (Enhanced)
        # ================================
        sa.Column("recall_date", sa.Date(), nullable=False, index=True),
        sa.Column("source_agency", sa.String(), nullable=True, index=True),
        sa.Column("hazard", sa.Text(), nullable=True),
        sa.Column("hazard_category", sa.String(), nullable=True, index=True),
        sa.Column("recall_reason", sa.Text(), nullable=True),
        sa.Column("remedy", sa.Text(), nullable=True),
        sa.Column("recall_class", sa.String(), nullable=True),
        # ================================
        # 📄 DESCRIPTIVE FIELDS (Enhanced)
        # ================================
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manufacturer_contact", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        # ================================
        # 🔍 SEARCH OPTIMIZATION
        # ================================
        sa.Column("search_keywords", sa.Text(), nullable=True),  # Concatenated searchable fields
        # ================================
        # 🛠️ TECHNICAL FIELDS
        # ================================
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("agency_specific_data", JSON, nullable=True),  # Raw agency data
        # ================================
        # 📊 STATUS & CLASSIFICATION
        # ================================
        sa.Column("status", sa.String(), nullable=True, default="open"),  # open/closed
        # Unique constraint on recall_id and source_agency combination
        sa.UniqueConstraint("recall_id", name="uq_recall_id"),
    )

    # Create performance indexes
    print("Creating performance indexes...")

    # Core search indexes
    op.create_index("idx_recalls_enhanced_source_agency", "recalls_enhanced", ["source_agency"])
    op.create_index("idx_recalls_enhanced_recall_date", "recalls_enhanced", ["recall_date"])
    op.create_index("idx_recalls_enhanced_status", "recalls_enhanced", ["status"])

    # Composite index for common search pattern (agency + date)
    op.create_index(
        "idx_recalls_enhanced_agency_date",
        "recalls_enhanced",
        ["source_agency", "recall_date"],
    )

    # Full-text search index for product search (PostgreSQL specific)
    op.execute(
        text(
            """
        CREATE INDEX idx_recalls_enhanced_product_search 
        ON recalls_enhanced 
        USING GIN (to_tsvector('english', 
            COALESCE(product_name, '') || ' ' || 
            COALESCE(brand, '') || ' ' || 
            COALESCE(model_number, '') || ' ' || 
            COALESCE(description, '')
        ))
    """,
        ),
    )

    # Create trigram indexes for LIKE searches (requires pg_trgm extension)
    try:
        op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        op.execute(
            text(
                "CREATE INDEX idx_recalls_enhanced_product_name_trgm ON recalls_enhanced USING gin (product_name gin_trgm_ops)",  # noqa: E501
            ),
        )
        op.execute(
            text("CREATE INDEX idx_recalls_enhanced_brand_trgm ON recalls_enhanced USING gin (brand gin_trgm_ops)"),
        )
        op.execute(
            text(
                "CREATE INDEX idx_recalls_enhanced_model_trgm ON recalls_enhanced USING gin (model_number gin_trgm_ops)",
            ),
        )
        print("Created trigram indexes for fuzzy search optimization")
    except Exception as e:
        print(f"Warning: Could not create trigram indexes (pg_trgm extension may not be available): {e}")

    print("Successfully created recalls_enhanced table with all indexes")


def downgrade() -> None:
    """Drop the recalls_enhanced table"""
    op.drop_table("recalls_enhanced")
