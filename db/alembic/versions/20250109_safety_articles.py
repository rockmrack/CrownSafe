"""Add safety articles table for Safety Hub

Revision ID: 20250109_safety_articles
Revises: 20250109_incident_reports
Create Date: 2025-01-09

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision = "20250109_safety_articles"
down_revision = "20250109_incident_reports"
branch_labels = None
depends_on = None


def upgrade():
    # Create safety_articles table
    op.create_table(
        "safety_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_agency", sa.String(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("article_url", sa.String(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for better query performance
    op.create_index(
        op.f("ix_safety_articles_article_id"),
        "safety_articles",
        ["article_id"],
        unique=True,
    )
    op.create_index(op.f("ix_safety_articles_id"), "safety_articles", ["id"], unique=False)
    op.create_index(
        op.f("ix_safety_articles_is_featured"),
        "safety_articles",
        ["is_featured"],
        unique=False,
    )
    op.create_index(
        op.f("ix_safety_articles_source_agency"),
        "safety_articles",
        ["source_agency"],
        unique=False,
    )


def downgrade():
    # Drop indexes
    op.drop_index(op.f("ix_safety_articles_source_agency"), table_name="safety_articles")
    op.drop_index(op.f("ix_safety_articles_is_featured"), table_name="safety_articles")
    op.drop_index(op.f("ix_safety_articles_id"), table_name="safety_articles")
    op.drop_index(op.f("ix_safety_articles_article_id"), table_name="safety_articles")

    # Drop table
    op.drop_table("safety_articles")
