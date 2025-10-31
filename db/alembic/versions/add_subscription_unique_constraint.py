"""add subscription unique constraint

Revision ID: add_subscription_unique_constraint
Revises: add_subscription_tables
Create Date: 2024-01-25

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "add_subscription_unique_constraint"
down_revision = "add_subscription_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add unique constraint for subscription UPSERT operations"""

    # Add unique constraint for subscription UPSERT
    # This allows us to use ON CONFLICT (user_id, original_transaction_id)
    op.create_unique_constraint(
        "uq_subscription_user_transaction",
        "subscriptions",
        ["user_id", "original_transaction_id"],
    )

    # Add updated_at column if it doesn't exist
    try:
        op.add_column("subscriptions", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE subscriptions SET updated_at = created_at WHERE updated_at IS NULL")
    except Exception:
        pass  # Column might already exist

    # Add updated_at column to recalls if it doesn't exist
    try:
        op.add_column("recalls", sa.Column("updated_at", sa.DateTime(), nullable=True))
        op.execute("UPDATE recalls SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    except Exception:
        pass  # Column might already exist

    print("✅ Added unique constraints for UPSERT operations")


def downgrade() -> None:
    """Remove unique constraint"""
    op.drop_constraint("uq_subscription_user_transaction", "subscriptions", type_="unique")

    # Optionally remove updated_at columns
    # op.drop_column('subscriptions', 'updated_at')
    # op.drop_column('recalls', 'updated_at')
