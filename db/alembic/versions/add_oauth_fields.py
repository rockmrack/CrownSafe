"""Add OAuth fields to users table

Revision ID: add_oauth_fields
Revises: fix_missing_columns
Create Date: 2025-08-27

"""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_oauth_fields"
down_revision = "fix_missing_columns"
branch_labels = None
depends_on = None


def upgrade():
    """Add OAuth provider fields to users table"""
    # Add provider_id column (hashed provider + subject)
    op.add_column(
        "users",
        sa.Column("provider_id", sa.String(255), nullable=True, unique=True, index=True),
    )

    # Add provider_type column (apple, google, email)
    op.add_column("users", sa.Column("provider_type", sa.String(50), nullable=True))

    # Add last_login timestamp
    op.add_column("users", sa.Column("last_login", sa.DateTime, nullable=True))

    # Add created_at timestamp
    op.add_column(
        "users",
        sa.Column("created_at", sa.DateTime, nullable=True, default=datetime.utcnow),
    )

    # Make email nullable for OAuth users (they might not provide email)
    op.alter_column("users", "email", existing_type=sa.String(), nullable=True)

    # Create index on provider_id for faster OAuth lookups
    op.create_index("ix_users_provider_id", "users", ["provider_id"])


def downgrade():
    """Remove OAuth fields from users table"""
    # Drop index
    op.drop_index("ix_users_provider_id", "users")

    # Remove columns
    op.drop_column("users", "provider_id")
    op.drop_column("users", "provider_type")
    op.drop_column("users", "last_login")
    op.drop_column("users", "created_at")

    # Make email required again
    op.alter_column("users", "email", existing_type=sa.String(), nullable=False)
