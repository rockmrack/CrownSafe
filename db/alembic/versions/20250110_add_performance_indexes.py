"""Add performance indexes for recall queries

Revision ID: 20250110_add_performance_indexes
Revises: 20250105_monitoring_notifications
Create Date: 2025-01-10

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20250110_add_performance_indexes"
down_revision = "20250105_monitoring_notifications"
branch_labels = None
depends_on = None


def upgrade():
    # Add indexes for recalls_enhanced table
    op.create_index("idx_recalls_enhanced_recall_id", "recalls_enhanced", ["recall_id"])
    op.create_index("idx_recalls_enhanced_upc", "recalls_enhanced", ["upc"])
    op.create_index("idx_recalls_enhanced_model_number", "recalls_enhanced", ["model_number"])
    op.create_index("idx_recalls_enhanced_source_agency", "recalls_enhanced", ["source_agency"])
    op.create_index("idx_recalls_enhanced_brand", "recalls_enhanced", ["brand"])
    op.create_index("idx_recalls_enhanced_product_name", "recalls_enhanced", ["product_name"])
    op.create_index("idx_recalls_enhanced_recall_date", "recalls_enhanced", ["recall_date"])
    op.create_index("idx_recalls_enhanced_serial_number", "recalls_enhanced", ["serial_number"])
    op.create_index("idx_recalls_enhanced_lot_number", "recalls_enhanced", ["lot_number"])

    # Add indexes for recalls table (legacy)
    op.create_index("idx_recalls_recall_id", "recalls", ["recall_id"])
    op.create_index("idx_recalls_upc", "recalls", ["upc"])
    op.create_index("idx_recalls_model_number", "recalls", ["model_number"])
    op.create_index("idx_recalls_source_agency", "recalls", ["source_agency"])
    op.create_index("idx_recalls_brand", "recalls", ["brand"])
    op.create_index("idx_recalls_product_name", "recalls", ["product_name"])
    op.create_index("idx_recalls_recall_date", "recalls", ["recall_date"])

    # Add composite indexes for common query patterns
    op.create_index(
        "idx_recalls_enhanced_agency_date",
        "recalls_enhanced",
        ["source_agency", "recall_date"],
    )
    op.create_index(
        "idx_recalls_enhanced_brand_model",
        "recalls_enhanced",
        ["brand", "model_number"],
    )
    op.create_index("idx_recalls_enhanced_upc_serial", "recalls_enhanced", ["upc", "serial_number"])

    # Add indexes for users table (if not already present)
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_created_at", "users", ["created_at"])


def downgrade():
    # Drop indexes for recalls_enhanced table
    op.drop_index("idx_recalls_enhanced_recall_id", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_upc", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_model_number", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_source_agency", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_brand", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_product_name", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_recall_date", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_serial_number", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_lot_number", "recalls_enhanced")

    # Drop indexes for recalls table (legacy)
    op.drop_index("idx_recalls_recall_id", "recalls")
    op.drop_index("idx_recalls_upc", "recalls")
    op.drop_index("idx_recalls_model_number", "recalls")
    op.drop_index("idx_recalls_source_agency", "recalls")
    op.drop_index("idx_recalls_brand", "recalls")
    op.drop_index("idx_recalls_product_name", "recalls")
    op.drop_index("idx_recalls_recall_date", "recalls")

    # Drop composite indexes
    op.drop_index("idx_recalls_enhanced_agency_date", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_brand_model", "recalls_enhanced")
    op.drop_index("idx_recalls_enhanced_upc_serial", "recalls_enhanced")

    # Drop user indexes
    op.drop_index("idx_users_email", "users")
    op.drop_index("idx_users_created_at", "users")
