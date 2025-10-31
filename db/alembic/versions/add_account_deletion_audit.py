"""Add account deletion audit table

Revision ID: add_account_deletion_audit
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_account_deletion_audit"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create account_deletion_audit table
    op.create_table(
        "account_deletion_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_account_deletion_audit_user_id"),
        "account_deletion_audit",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_deletion_audit_jti"),
        "account_deletion_audit",
        ["jti"],
        unique=False,
    )


def downgrade():
    # Drop account_deletion_audit table
    op.drop_index(op.f("ix_account_deletion_audit_jti"), table_name="account_deletion_audit")
    op.drop_index(op.f("ix_account_deletion_audit_user_id"), table_name="account_deletion_audit")
    op.drop_table("account_deletion_audit")
