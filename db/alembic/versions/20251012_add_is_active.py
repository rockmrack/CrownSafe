"""Add is_active column to users table.

Revision ID: 20251012_add_is_active
Revises: 20251012_user_reports
Create Date: 2025-10-12 16:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251012_add_is_active"
down_revision = "20251012_create_pg_trgm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_active column to users table."""
    # Check if column exists first (PostgreSQL)
    from sqlalchemy import inspect

    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("users")]

    if "is_active" not in columns:
        op.add_column(
            "users",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        )


def downgrade() -> None:
    """Remove is_active column from users table."""
    op.drop_column("users", "is_active")
