"""
Create privacy_requests table for DSAR tracking

Revision ID: 20250827_privacy_requests  
Revises: 20250827_admin_ingestion_runs
Create Date: 2025-08-27 01:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20250827_privacy_requests"
down_revision = "20250827_admin_ingestion_runs"  # Previous migration
branch_labels = None
depends_on = None


def upgrade():
    """Create privacy_requests table for GDPR/CCPA compliance"""

    # Ensure pgcrypto extension for UUID generation
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Create privacy_requests table
    op.create_table(
        "privacy_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "kind", sa.String(16), nullable=False
        ),  # "export" | "delete" | "rectify" | "access"
        sa.Column("email", sa.String(320), nullable=False),  # Max email length per RFC
        sa.Column("email_hash", sa.String(64), nullable=False),  # SHA-256 hash for searching
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="queued"
        ),  # queued|verifying|processing|done|rejected|expired
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),  # Added
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True
        ),  # Added for data export links
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),  # Added
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column("jurisdiction", sa.String(32), nullable=True),  # gdpr|ccpa|pipeda|other
        sa.Column("source", sa.String(32), nullable=True),  # ios|android|web|email|api
        sa.Column("ip_address", sa.String(45), nullable=True),  # Added for audit
        sa.Column("user_agent", sa.Text, nullable=True),  # Added for audit
        sa.Column(
            "verification_token", sa.String(128), nullable=True
        ),  # Added for email verification
        sa.Column("export_url", sa.Text, nullable=True),  # Added for download links
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),  # Added for flexibility
    )

    # Create indexes for efficient querying
    op.create_index("ix_privacy_email_hash", "privacy_requests", ["email_hash"], unique=False)

    op.create_index("ix_privacy_status", "privacy_requests", ["status"], unique=False)

    op.create_index("ix_privacy_submitted_at", "privacy_requests", ["submitted_at"], unique=False)

    op.create_index("ix_privacy_kind_status", "privacy_requests", ["kind", "status"], unique=False)

    # Add check constraints
    op.execute(
        """
        ALTER TABLE privacy_requests 
        ADD CONSTRAINT check_kind CHECK (
            kind IN ('export', 'delete', 'rectify', 'access', 'restrict', 'object')
        )
    """
    )

    op.execute(
        """
        ALTER TABLE privacy_requests 
        ADD CONSTRAINT check_status CHECK (
            status IN ('queued', 'verifying', 'processing', 'done', 'rejected', 'expired', 'cancelled')
        )
    """
    )

    op.execute(
        """
        ALTER TABLE privacy_requests 
        ADD CONSTRAINT check_jurisdiction CHECK (
            jurisdiction IS NULL OR 
            jurisdiction IN ('gdpr', 'ccpa', 'pipeda', 'lgpd', 'appi', 'uk_gdpr', 'other')
        )
    """
    )

    op.execute(
        """
        ALTER TABLE privacy_requests 
        ADD CONSTRAINT check_source CHECK (
            source IS NULL OR 
            source IN ('ios', 'android', 'web', 'email', 'api', 'admin')
        )
    """
    )


def downgrade():
    """Drop privacy_requests table and indexes"""

    # Drop indexes
    op.drop_index("ix_privacy_kind_status", table_name="privacy_requests")
    op.drop_index("ix_privacy_submitted_at", table_name="privacy_requests")
    op.drop_index("ix_privacy_status", table_name="privacy_requests")
    op.drop_index("ix_privacy_email_hash", table_name="privacy_requests")

    # Drop table
    op.drop_table("privacy_requests")
