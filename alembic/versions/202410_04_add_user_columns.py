"""Add missing columns to users table

Revision ID: 202410_04_002
Revises: 202410_04_001
Create Date: 2025-10-04 09:05:00.000000

COPILOT AUDIT FIX: Replace runtime schema modifications with proper migrations
This migration adds columns that were previously being added at runtime by ensure_user_columns()
"""

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

from alembic import op

# revision identifiers, used by Alembic.
revision = "202410_04_002"
down_revision = "202410_04_001"
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to users table"""
    # Check if table exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "users" in inspector.get_table_names():
        existing_columns = {col["name"] for col in inspector.get_columns("users")}

        # Add hashed_password column if it doesn't exist
        if "hashed_password" not in existing_columns:
            op.add_column(
                "users",
                sa.Column("hashed_password", sa.Text(), nullable=False, server_default=""),
            )
            # Remove the server_default so future inserts must provide a value
            op.alter_column("users", "hashed_password", server_default=None)
        # Add is_pregnant column if it doesn't exist
        if "is_pregnant" not in existing_columns:
            op.add_column(
                "users",
                sa.Column(
                    "is_pregnant",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )

        # Add is_active column if it doesn't exist
        if "is_active" not in existing_columns:
            op.add_column(
                "users",
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
            )

        # Handle is_subscribed column migration
        if "is_subscribed" not in existing_columns:
            if "is_premium" in existing_columns:
                # Migrate from is_premium to is_subscribed
                op.add_column(
                    "users",
                    sa.Column(
                        "is_subscribed",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    ),
                )
                op.execute("UPDATE users SET is_subscribed = is_premium")
            else:
                # Just add is_subscribed
                op.add_column(
                    "users",
                    sa.Column(
                        "is_subscribed",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("false"),
                    ),
                )


def downgrade():
    """Remove added columns from users table"""
    # Note: This doesn't remove is_premium if it existed before
    op.drop_column("users", "is_active")
    op.drop_column("users", "is_pregnant")
    op.drop_column("users", "hashed_password")
    # Only drop is_subscribed if it was migrated (not if it already existed)
    try:
        op.drop_column("users", "is_subscribed")
    except (OperationalError, ProgrammingError):
        pass  # Column may not exist or may have existed before migration
