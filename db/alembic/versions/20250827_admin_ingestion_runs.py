"""
Create ingestion_runs table for tracking data ingestion jobs

Revision ID: 20250827_admin_ingestion_runs
Revises: 20250826_search_trgm_indexes
Create Date: 2025-08-27 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "20250827_admin_ingestion_runs"
down_revision = "20250826_search_trgm_indexes"  # Previous migration from Task 2
branch_labels = None
depends_on = None


def upgrade():
    """Create ingestion_runs table and indexes"""

    # Detect database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # For PostgreSQL, ensure pgcrypto extension for UUID generation
    if not is_sqlite:
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Use appropriate types based on dialect
    if is_sqlite:
        # SQLite: Use String(36) for UUID compatibility
        id_type = sa.String(36)
        id_server_default = None
        json_type = sa.JSON()
    else:
        # PostgreSQL: Use native UUID and JSONB
        id_type = postgresql.UUID(as_uuid=True)
        id_server_default = sa.text("gen_random_uuid()")
        json_type = postgresql.JSONB

    # Create ingestion_runs table
    op.create_table(
        "ingestion_runs",
        sa.Column(
            "id",
            id_type,
            primary_key=True,
            server_default=id_server_default,
        ),
        sa.Column("agency", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),  # "delta" | "full"
        sa.Column(
            "status", sa.String(16), nullable=False
        ),  # "queued"|"running"|"success"|"failed"|"cancelled"
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "items_skipped", sa.Integer, nullable=False, server_default="0"
        ),  # Added
        sa.Column(
            "items_failed", sa.Integer, nullable=False, server_default="0"
        ),  # Added
        sa.Column("error_text", sa.Text, nullable=True),
        sa.Column("initiated_by", sa.String(128), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),  # Added
        sa.Column("metadata_json", json_type, nullable=True),  # Added for extra data
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_ingestion_runs_agency_started",
        "ingestion_runs",
        ["agency", "started_at"],
        unique=False,
    )

    op.create_index(
        "ix_ingestion_runs_status", "ingestion_runs", ["status"], unique=False
    )

    op.create_index(
        "ix_ingestion_runs_created_at", "ingestion_runs", ["created_at"], unique=False
    )

    # Add check constraints (PostgreSQL only - SQLite doesn't support ALTER TABLE ADD CONSTRAINT)
    if not is_sqlite:
        op.execute(
            """
            ALTER TABLE ingestion_runs 
            ADD CONSTRAINT check_mode CHECK (mode IN ('delta', 'full', 'incremental'))
        """
        )

        op.execute(
            """
            ALTER TABLE ingestion_runs 
            ADD CONSTRAINT check_status CHECK (
                status IN ('queued', 'running', 'success', 'failed', 'cancelled', 'partial')
            )
        """
        )


def downgrade():
    """Drop ingestion_runs table and indexes"""

    # Drop indexes
    op.drop_index("ix_ingestion_runs_created_at", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_agency_started", table_name="ingestion_runs")

    # Drop table
    op.drop_table("ingestion_runs")
