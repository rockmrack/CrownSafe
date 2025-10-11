"""enable pg_trgm extension for fuzzy search

Revision ID: 20251009_enable_pg_trgm
Revises: 20250924_chat_memory
Create Date: 2025-10-09 08:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251009_enable_pg_trgm"
down_revision = "20250924_chat_memory"
branch_labels = None
depends_on = None


def upgrade():
    """Enable pg_trgm extension for fuzzy text search"""
    # Execute raw SQL to enable the extension
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Optionally create indexes for better performance
    # These indexes will significantly speed up similarity searches
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm 
        ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm 
        ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm 
        ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);
    """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm 
        ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);
    """
    )


def downgrade():
    """Remove pg_trgm indexes and extension"""
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_recalls_hazard_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_recalls_description_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_recalls_brand_trgm;")
    op.execute("DROP INDEX IF EXISTS idx_recalls_product_trgm;")

    # Drop extension (this will cascade to remove anything dependent on it)
    op.execute("DROP EXTENSION IF EXISTS pg_trgm CASCADE;")
