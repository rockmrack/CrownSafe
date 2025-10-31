"""Add Crown Safe models and remove baby-specific tables

Revision ID: crown_safe_v1
Revises:
Create Date: 2025-10-24

This migration:
1. Creates new Crown Safe tables for hair product safety analysis
2. Removes baby-specific tables (family_members, allergies)
3. Removes is_pregnant column from users table
4. Adds indexes for performance optimization
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "crown_safe_v1"
down_revision = "20251014_missing_tables"  # Points to last migration
branch_labels = None
depends_on = None


def upgrade():
    """Apply Crown Safe schema changes"""
    # ============================================
    # CROWN SAFE: Create new tables
    # ============================================

    # 1. Hair Profiles Table
    op.create_table(
        "hair_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hair_type", sa.String(length=50), nullable=False),
        sa.Column("porosity", sa.String(length=50), nullable=False),
        sa.Column("hair_state", sa.JSON(), nullable=True),
        sa.Column("hair_goals", sa.JSON(), nullable=True),
        sa.Column("sensitivities", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),  # One profile per user
    )
    op.create_index("ix_hair_profiles_user_id", "hair_profiles", ["user_id"])
    op.create_index("ix_hair_profiles_hair_type", "hair_profiles", ["hair_type"])

    # 2. Ingredients Table
    op.create_table(
        "ingredients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("inci_name", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("safety_level", sa.String(length=50), nullable=False),
        sa.Column("base_score", sa.Integer(), nullable=False),
        sa.Column("porosity_adjustments", sa.JSON(), nullable=True),
        sa.Column("curl_pattern_adjustments", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_ingredients_name", "ingredients", ["name"])
    op.create_index("ix_ingredients_category", "ingredients", ["category"])
    op.create_index("ix_ingredients_safety_level", "ingredients", ["safety_level"])

    # 3. Hair Products Table
    op.create_table(
        "hair_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=True),
        sa.Column("upc_barcode", sa.String(length=50), nullable=True),
        sa.Column("average_crown_score", sa.Float(), nullable=True),
        sa.Column("price_range", sa.String(length=10), nullable=True),
        sa.Column("affiliate_links", sa.JSON(), nullable=True),
        sa.Column("is_certified", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hair_products_product_name", "hair_products", ["product_name"])
    op.create_index("ix_hair_products_brand", "hair_products", ["brand"])
    op.create_index("ix_hair_products_upc_barcode", "hair_products", ["upc_barcode"], unique=True)
    op.create_index("ix_hair_products_category", "hair_products", ["category"])

    # 4. Product Scans Table
    op.create_table(
        "product_scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("ingredients_scanned", sa.JSON(), nullable=True),
        sa.Column("crown_score", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(length=50), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("alternatives", sa.JSON(), nullable=True),
        sa.Column("scan_date", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_scans_user_id", "product_scans", ["user_id"])
    op.create_index("ix_product_scans_scan_date", "product_scans", ["scan_date"])
    op.create_index("ix_product_scans_verdict", "product_scans", ["verdict"])

    # 5. Product Reviews Table
    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("crown_score_agreement", sa.Boolean(), nullable=True),
        sa.Column("helpful_votes", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["hair_products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_reviews_user_id", "product_reviews", ["user_id"])
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])
    op.create_index("ix_product_reviews_rating", "product_reviews", ["rating"])

    # 6. Brand Certifications Table
    op.create_table(
        "brand_certifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("brand_name", sa.String(length=255), nullable=False),
        sa.Column("certification_level", sa.String(length=50), nullable=False),
        sa.Column("annual_fee", sa.Float(), nullable=False),
        sa.Column("certified_products", sa.JSON(), nullable=True),
        sa.Column("certification_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("brand_name"),
    )
    op.create_index("ix_brand_certifications_brand_name", "brand_certifications", ["brand_name"])
    op.create_index("ix_brand_certifications_expiry_date", "brand_certifications", ["expiry_date"])

    # 7. Salon Accounts Table
    op.create_table(
        "salon_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("salon_name", sa.String(length=255), nullable=False),
        sa.Column("subscription_tier", sa.String(length=50), nullable=False),
        sa.Column("monthly_fee", sa.Float(), nullable=False),
        sa.Column("stylist_count", sa.Integer(), nullable=False, default=1),
        sa.Column("features_enabled", sa.JSON(), nullable=True),
        sa.Column("subscription_start", sa.Date(), nullable=False),
        sa.Column("subscription_end", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_salon_accounts_salon_name", "salon_accounts", ["salon_name"])
    op.create_index("ix_salon_accounts_subscription_tier", "salon_accounts", ["subscription_tier"])

    # 8. Market Insights Table
    op.create_table(
        "market_insights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_title", sa.String(length=255), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("purchase_count", sa.Integer(), nullable=False, default=0),
        sa.Column("insights_data", sa.JSON(), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_market_insights_report_type", "market_insights", ["report_type"])
    op.create_index("ix_market_insights_publication_date", "market_insights", ["publication_date"])

    # ============================================
    # LEGACY BABY CODE: Remove baby-specific tables
    # ============================================

    # Check if tables exist before dropping (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "allergies" in existing_tables:
        op.drop_table("allergies")
        print("Dropped table: allergies")

    if "family_members" in existing_tables:
        op.drop_table("family_members")
        print("Dropped table: family_members")

    # Remove is_pregnant column from users table if it exists
    if "users" in existing_tables:
        columns = [col["name"] for col in inspector.get_columns("users")]
        if "is_pregnant" in columns:
            op.drop_column("users", "is_pregnant")
            print("Removed column: users.is_pregnant")


def downgrade():
    """Rollback Crown Safe schema changes"""
    # Reverse order: recreate baby tables, drop Crown Safe tables

    # Recreate is_pregnant column
    op.add_column("users", sa.Column("is_pregnant", sa.Boolean(), nullable=False, server_default="false"))

    # Recreate family_members table
    op.create_table(
        "family_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Recreate allergies table
    op.create_table(
        "allergies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allergen", sa.String(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["member_id"], ["family_members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Drop Crown Safe tables (reverse order of creation)
    op.drop_index("ix_market_insights_publication_date", "market_insights")
    op.drop_index("ix_market_insights_report_type", "market_insights")
    op.drop_table("market_insights")

    op.drop_index("ix_salon_accounts_subscription_tier", "salon_accounts")
    op.drop_index("ix_salon_accounts_salon_name", "salon_accounts")
    op.drop_table("salon_accounts")

    op.drop_index("ix_brand_certifications_expiry_date", "brand_certifications")
    op.drop_index("ix_brand_certifications_brand_name", "brand_certifications")
    op.drop_table("brand_certifications")

    op.drop_index("ix_product_reviews_rating", "product_reviews")
    op.drop_index("ix_product_reviews_product_id", "product_reviews")
    op.drop_index("ix_product_reviews_user_id", "product_reviews")
    op.drop_table("product_reviews")

    op.drop_index("ix_product_scans_verdict", "product_scans")
    op.drop_index("ix_product_scans_scan_date", "product_scans")
    op.drop_index("ix_product_scans_user_id", "product_scans")
    op.drop_table("product_scans")

    op.drop_index("ix_hair_products_category", "hair_products")
    op.drop_index("ix_hair_products_upc_barcode", "hair_products")
    op.drop_index("ix_hair_products_brand", "hair_products")
    op.drop_index("ix_hair_products_product_name", "hair_products")
    op.drop_table("hair_products")

    op.drop_index("ix_ingredients_safety_level", "ingredients")
    op.drop_index("ix_ingredients_category", "ingredients")
    op.drop_index("ix_ingredients_name", "ingredients")
    op.drop_table("ingredients")

    op.drop_index("ix_hair_profiles_hair_type", "hair_profiles")
    op.drop_index("ix_hair_profiles_user_id", "hair_profiles")
    op.drop_table("hair_profiles")
