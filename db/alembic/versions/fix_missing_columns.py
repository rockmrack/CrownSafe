"""Add missing severity and risk_category columns.

Revision ID: fix_missing_columns
Revises:
Create Date: 2025-08-27

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_missing_columns"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add severity column
    op.add_column("recalls_enhanced", sa.Column("severity", sa.String(50), nullable=True))

    # Add risk_category column
    op.add_column("recalls_enhanced", sa.Column("risk_category", sa.String(100), nullable=True))

    # Set defaults
    op.execute("UPDATE recalls_enhanced SET severity = 'medium' WHERE severity IS NULL")
    op.execute("UPDATE recalls_enhanced SET risk_category = 'general' WHERE risk_category IS NULL")


def downgrade() -> None:
    op.drop_column("recalls_enhanced", "severity")
    op.drop_column("recalls_enhanced", "risk_category")
