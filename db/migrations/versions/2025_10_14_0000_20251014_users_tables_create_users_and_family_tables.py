"""Create users and family_members tables

Revision ID: 20251014_users_tables
Revises: 001
Create Date: 2025-10-14

Creates the foundational users table and family_members/allergies tables.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision = "20251014_users_tables"
down_revision = "4eebd8426dad"  # Insert after the last existing migration
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False, server_default=""),
        sa.Column("is_subscribed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_pregnant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_stripe_customer_id", "users", ["stripe_customer_id"], unique=True)

    # Create family_members table
    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_members_id", "family_members", ["id"], unique=False)

    # Create allergies table
    op.create_table(
        "allergies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allergen", sa.String(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["family_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_allergies_id", "allergies", ["id"], unique=False)

    print("✅ Created users, family_members, and allergies tables")


def downgrade():
    op.drop_table("allergies")
    op.drop_table("family_members")
    op.drop_table("users")
    print("✅ Dropped users, family_members, and allergies tables")
