"""Add pg_trgm extension and search indexes

Revision ID: 20250826_search_trgm
Revises: add_subscription_unique_constraint
Create Date: 2025-01-26

"""

from sqlalchemy import text

from alembic import op

# revision identifiers
revision = "20250826_search_trgm"
down_revision = "add_subscription_unique_constraint"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    """Add pg_trgm extension and create optimized search indexes"""

    # 1) Enable pg_trgm extension for fuzzy matching
    print("Creating pg_trgm extension...")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Check which table exists
    connection = op.get_bind()

    # Check for recalls_enhanced
    result = connection.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recalls_enhanced');")
    )
    has_enhanced = result.scalar()

    # Check for recalls
    result = connection.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recalls');")
    )
    has_recalls = result.scalar()

    if has_enhanced:
        print("Creating indexes on recalls_enhanced table...")
        table = "recalls_enhanced"
    elif has_recalls:
        print("Creating indexes on recalls table...")
        table = "recalls"
    else:
        print("Warning: No recalls table found. Skipping index creation.")
        return

    # 2) Trigram GIN indexes for fuzzy text search (lowercased)
    print(f"Creating trigram indexes on {table}...")

    # Product name - primary search field
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_product_name_trgm
        ON {table} USING gin (lower(product_name) gin_trgm_ops);
    """
    )

    # Brand - commonly searched
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_brand_trgm
        ON {table} USING gin (lower(brand) gin_trgm_ops);
    """
    )

    # Description - for comprehensive search
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_description_trgm
        ON {table} USING gin (lower(description) gin_trgm_ops);
    """
    )

    # Hazard - for safety searches
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_hazard_trgm
        ON {table} USING gin (lower(hazard) gin_trgm_ops);
    """
    )

    # Check if title column exists
    result = connection.execute(
        text(
            f"""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = '{table}' AND column_name = 'title'
        );
    """
        )
    )
    has_title = result.scalar()

    if has_title:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_title_trgm
            ON {table} USING gin (lower(title) gin_trgm_ops);
        """
        )

    # 3) BTREE indexes for filters and sorting
    print(f"Creating BTREE indexes for filters on {table}...")

    # Agency filter
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_agency 
        ON {table} (source_agency);
    """
    )

    # Date sorting (DESC for most recent first)
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_recalldate 
        ON {table} (recall_date DESC);
    """
    )

    # Composite index for common query pattern
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_agency_date 
        ON {table} (source_agency, recall_date DESC);
    """
    )

    # Check for risk/severity columns
    result = connection.execute(
        text(
            f"""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = '{table}' 
        AND column_name IN ('risk_category', 'severity', 'hazard_category');
    """
        )
    )
    risk_columns = [row[0] for row in result]

    if "risk_category" in risk_columns:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_riskcategory 
            ON {table} (risk_category);
        """
        )

    if "severity" in risk_columns:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_severity 
            ON {table} (severity);
        """
        )

    if "hazard_category" in risk_columns:
        op.execute(
            f"""
            CREATE INDEX IF NOT EXISTS ix_{table}_hazard_category 
            ON {table} (hazard_category);
        """
        )

    # UPC index for barcode lookups
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_upc 
        ON {table} (upc) WHERE upc IS NOT NULL;
    """
    )

    # Model number index
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_model_number 
        ON {table} (model_number) WHERE model_number IS NOT NULL;
    """
    )

    # 4) Analyze the table for query planner
    print(f"Analyzing {table} for query optimization...")
    op.execute(f"ANALYZE {table};")

    print("✅ Search indexes created successfully!")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    """Remove search indexes (but keep pg_trgm extension)"""

    # Check which table exists
    connection = op.get_bind()

    result = connection.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recalls_enhanced');")
    )
    has_enhanced = result.scalar()

    result = connection.execute(
        text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'recalls');")
    )
    has_recalls = result.scalar()

    if has_enhanced:
        table = "recalls_enhanced"
    elif has_recalls:
        table = "recalls"
    else:
        return

    print(f"Dropping indexes from {table}...")

    # Drop all indexes
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_model_number;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_upc;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_hazard_category;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_severity;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_riskcategory;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_agency_date;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_recalldate;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_agency;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_hazard_trgm;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_description_trgm;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_brand_trgm;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_title_trgm;")
    op.execute(f"DROP INDEX IF EXISTS ix_{table}_product_name_trgm;")

    # Note: We leave pg_trgm extension installed as it may be used by other apps
