"""Add severity and risk_category columns to recalls_enhanced

Revision ID: 202410_04_001
Revises: 
Create Date: 2025-10-04 09:00:00.000000

COPILOT AUDIT FIX: Replace runtime schema modifications with proper migrations
This migration adds columns that were previously being added at runtime by fix_database.py
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "202410_04_001"
down_revision = None  # Update this to the latest revision ID if there are existing migrations
branch_labels = None
depends_on = None


def upgrade():
    """Add severity and risk_category columns to recalls_enhanced table"""
    # Check if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "recalls_enhanced" in inspector.get_table_names():
        existing_columns = {col["name"] for col in inspector.get_columns("recalls_enhanced")}

        # Add severity column if it doesn't exist
        if "severity" not in existing_columns:
            op.add_column(
                "recalls_enhanced", sa.Column("severity", sa.String(length=50), nullable=True)
            )
            # Set default value for existing rows
            op.execute("UPDATE recalls_enhanced SET severity = 'medium' WHERE severity IS NULL")

        # Add risk_category column if it doesn't exist
        if "risk_category" not in existing_columns:
            op.add_column(
                "recalls_enhanced", sa.Column("risk_category", sa.String(length=100), nullable=True)
            )
            # Set default value for existing rows
            op.execute(
                "UPDATE recalls_enhanced SET risk_category = 'general' WHERE risk_category IS NULL"
            )

        # Create indexes for better query performance
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("recalls_enhanced")}
        if "idx_recalls_severity" not in existing_indexes:
            op.create_index("idx_recalls_severity", "recalls_enhanced", ["severity"])

        if "idx_recalls_risk_category" not in existing_indexes:
            op.create_index("idx_recalls_risk_category", "recalls_enhanced", ["risk_category"])


def downgrade():
    """Remove severity and risk_category columns from recalls_enhanced table"""
    # Drop indexes first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("recalls_enhanced")}
    if "idx_recalls_severity" in existing_indexes:
        op.drop_index("idx_recalls_severity", table_name="recalls_enhanced")

    if "idx_recalls_risk_category" in existing_indexes:
        op.drop_index("idx_recalls_risk_category", table_name="recalls_enhanced")

    # Drop columns
    op.drop_column("recalls_enhanced", "risk_category")
    op.drop_column("recalls_enhanced", "severity")
