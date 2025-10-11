"""Add monitoring and notification tables

Revision ID: 20250105_monitoring_notifications
Revises: 20250904_add_report_records
Create Date: 2025-01-05

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250105_monitoring_notifications"
down_revision = "20250904_add_report_records"
branch_labels = None
depends_on = None


def upgrade():
    # Create password_reset_tokens table
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),  # Fixed: Integer not String
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    # Create device_tokens table
    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(500), nullable=False, unique=True),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("device_name", sa.String(200), nullable=True),
        sa.Column("device_model", sa.String(100), nullable=True),
        sa.Column("app_version", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_used", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("quiet_hours_start", sa.String(5), nullable=True),
        sa.Column("quiet_hours_end", sa.String(5), nullable=True),
        sa.Column("notification_types", sa.JSON(), nullable=True),
    )
    op.create_index("ix_device_tokens_user_id", "device_tokens", ["user_id"])
    op.create_index("ix_device_tokens_token", "device_tokens", ["token"])

    # Create notification_history table
    op.create_table(
        "notification_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column(
            "device_token_id",
            sa.Integer(),
            sa.ForeignKey("device_tokens.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(10), default="normal"),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("related_product_id", sa.String(200), nullable=True),
        sa.Column("related_recall_id", sa.String(200), nullable=True),
    )
    op.create_index("ix_notification_history_user_id", "notification_history", ["user_id"])
    op.create_index("ix_notification_history_sent_at", "notification_history", ["sent_at"])

    # Create monitored_products table
    op.create_table(
        "monitored_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_name", sa.String(500), nullable=True),
        sa.Column("brand_name", sa.String(200), nullable=True),
        sa.Column("model_number", sa.String(200), nullable=True),
        sa.Column("upc_code", sa.String(50), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("source_job_id", sa.String(36), nullable=True),
        sa.Column("added_via", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("check_frequency_hours", sa.Integer(), default=24),
        sa.Column("last_checked", sa.DateTime(), nullable=True),
        sa.Column("next_check", sa.DateTime(), nullable=False),
        sa.Column("recall_status", sa.String(50), default="safe"),
        sa.Column("last_recall_id", sa.String(200), nullable=True),
        sa.Column("recalls_found", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
    )
    op.create_index("ix_monitored_products_user_id", "monitored_products", ["user_id"])
    op.create_index("ix_monitored_products_upc_code", "monitored_products", ["upc_code"])

    # Create monitoring_runs table
    op.create_table(
        "monitoring_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("products_checked", sa.Integer(), default=0),
        sa.Column("new_recalls_found", sa.Integer(), default=0),
        sa.Column("notifications_sent", sa.Integer(), default=0),
        sa.Column("errors_count", sa.Integer(), default=0),
        sa.Column("status", sa.String(20), default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("run_details", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_table("monitoring_runs")
    op.drop_table("monitored_products")
    op.drop_table("notification_history")
    op.drop_table("device_tokens")
    op.drop_table("password_reset_tokens")
