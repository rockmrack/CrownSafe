"""Add subscription tables for mobile IAP

Revision ID: add_subscription_tables
Revises:
Create Date: 2024-11-24

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_subscription_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "plan",
            sa.Enum("MONTHLY", "ANNUAL", name="subscriptionplan"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "EXPIRED",
                "CANCELLED",
                "PENDING",
                "FAILED",
                name="subscriptionstatus",
            ),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.Enum("APPLE", "GOOGLE", name="paymentprovider"),
            nullable=False,
        ),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("original_transaction_id", sa.String(length=200), nullable=True),
        sa.Column("latest_receipt", sa.String(length=5000), nullable=True),
        sa.Column("receipt_data", sa.String(length=10000), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_user_active", "subscriptions", ["user_id", "status"], unique=False)
    op.create_index("idx_expires_at", "subscriptions", ["expires_at"], unique=False)
    op.create_index("idx_transaction_id", "subscriptions", ["original_transaction_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)

    # Create receipt_validations table
    op.create_table(
        "receipt_validations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "provider",
            sa.Enum("APPLE", "GOOGLE", name="paymentprovider"),
            nullable=False,
        ),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("receipt_hash", sa.String(length=64), nullable=True),
        sa.Column("transaction_id", sa.String(length=200), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("validation_response", sa.String(length=5000), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("validated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["subscriptions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for receipt_validations
    op.create_index("idx_receipt_hash", "receipt_validations", ["receipt_hash"], unique=False)
    op.create_index(
        "idx_user_validations",
        "receipt_validations",
        ["user_id", "validated_at"],
        unique=False,
    )

    # Add is_admin column to users table if it doesn't exist
    try:
        op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=True))
        # Set default value for existing records
        op.execute("UPDATE users SET is_admin = false WHERE is_admin IS NULL")
        # Make it non-nullable
        op.alter_column("users", "is_admin", nullable=False, server_default="false")
    except:
        # Column might already exist
        pass


def downgrade():
    # Drop indexes
    op.drop_index("idx_user_validations", table_name="receipt_validations")
    op.drop_index("idx_receipt_hash", table_name="receipt_validations")

    # Drop receipt_validations table
    op.drop_table("receipt_validations")

    # Drop indexes for subscriptions
    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_index("idx_transaction_id", table_name="subscriptions")
    op.drop_index("idx_expires_at", table_name="subscriptions")
    op.drop_index("idx_user_active", table_name="subscriptions")

    # Drop subscriptions table
    op.drop_table("subscriptions")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS subscriptionplan")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
    op.execute("DROP TYPE IF EXISTS paymentprovider")

    # Remove is_admin column if we added it
    try:
        op.drop_column("users", "is_admin")
    except:
        pass
