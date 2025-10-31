"""Add ingredient and safety tables for real data.

Revision ID: add_ingredient_safety_tables
Revises: add_account_deletion_audit
Create Date: 2025-09-20 18:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_ingredient_safety_tables"
down_revision = "add_account_deletion_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_ingredients table
    op.create_table(
        "product_ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("upc", sa.String(length=50), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=False),
        sa.Column("allergens", sa.JSON(), nullable=True),
        sa.Column("nutritional_info", sa.JSON(), nullable=True),
        sa.Column("pregnancy_safe", sa.Boolean(), nullable=True),
        sa.Column("baby_safe", sa.Boolean(), nullable=True),
        sa.Column("toddler_safe", sa.Boolean(), nullable=True),
        sa.Column("data_source", sa.String(length=100), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_product_ingredients_upc", "product_ingredients", ["upc"], unique=True)
    op.create_index("idx_product_ingredients_name", "product_ingredients", ["product_name"])
    op.create_index("idx_product_ingredients_brand", "product_ingredients", ["brand"])
    op.create_index("idx_product_ingredients_category", "product_ingredients", ["category"])
    op.create_index(
        "idx_product_safety",
        "product_ingredients",
        ["pregnancy_safe", "baby_safe", "toddler_safe"],
    )
    op.create_index("idx_product_updated", "product_ingredients", ["last_updated"])

    # Create ingredient_safety table
    op.create_table(
        "ingredient_safety",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingredient_name", sa.String(length=200), nullable=False),
        sa.Column("alternative_names", sa.JSON(), nullable=True),
        sa.Column("pregnancy_risk_level", sa.String(length=20), nullable=True),
        sa.Column("pregnancy_risk_reason", sa.Text(), nullable=True),
        sa.Column("pregnancy_source", sa.String(length=200), nullable=True),
        sa.Column("baby_risk_level", sa.String(length=20), nullable=True),
        sa.Column("baby_risk_reason", sa.Text(), nullable=True),
        sa.Column("baby_source", sa.String(length=200), nullable=True),
        sa.Column("common_allergen", sa.Boolean(), nullable=True),
        sa.Column("allergen_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("data_source", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_ingredient_safety_name",
        "ingredient_safety",
        ["ingredient_name"],
        unique=True,
    )
    op.create_index("idx_ingredient_pregnancy_risk", "ingredient_safety", ["pregnancy_risk_level"])
    op.create_index("idx_ingredient_baby_risk", "ingredient_safety", ["baby_risk_level"])
    op.create_index(
        "idx_ingredient_allergen",
        "ingredient_safety",
        ["common_allergen", "allergen_type"],
    )
    op.create_index("idx_ingredient_updated", "ingredient_safety", ["last_updated"])


def downgrade() -> None:
    op.drop_table("ingredient_safety")
    op.drop_table("product_ingredients")
