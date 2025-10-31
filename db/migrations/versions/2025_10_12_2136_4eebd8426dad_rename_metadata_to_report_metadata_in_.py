"""rename_metadata_to_report_metadata_in_user_reports.

Revision ID: 4eebd8426dad
Revises: 20251012_create_pg_trgm
Create Date: 2025-10-12 21:36:25.466101

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4eebd8426dad"
down_revision = "20251012_user_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename 'metadata' column to 'report_metadata' in user_reports table
    # 'metadata' is a reserved attribute in SQLAlchemy
    op.alter_column(
        "user_reports",
        "metadata",
        new_column_name="report_metadata",
        existing_type=sa.JSON(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert: Rename 'report_metadata' back to 'metadata'
    op.alter_column(
        "user_reports",
        "report_metadata",
        new_column_name="metadata",
        existing_type=sa.JSON(),
        existing_nullable=True,
    )
