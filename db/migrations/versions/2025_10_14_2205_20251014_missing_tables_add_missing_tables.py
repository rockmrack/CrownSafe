"""Add missing tables: incident_reports, image_jobs, and related tables

Revision ID: 20251014_missing_tables
Revises: 4eebd8426dad
Create Date: 2025-10-14

This migration adds all tables that were defined in models but missing from migrations.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "20251014_missing_tables"
down_revision = "20251014_users_tables"
branch_labels = None
depends_on = None


def upgrade():
    # ========================================================================
    # INCIDENT REPORTING TABLES
    # ========================================================================

    # Create incident_reports table
    op.create_table(
        "incident_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("reporter_email", sa.String(), nullable=True),
        sa.Column("reporter_phone", sa.String(), nullable=True),
        # Product information
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column("model_number", sa.String(), nullable=True),
        sa.Column("barcode", sa.String(), nullable=True),
        sa.Column("purchase_date", sa.DateTime(), nullable=True),
        sa.Column("purchase_location", sa.String(), nullable=True),
        # Incident details
        sa.Column(
            "incident_type",
            sa.Enum(
                "INJURY",
                "CHOKING_HAZARD",
                "SHARP_EDGES",
                "TOXIC_MATERIAL",
                "STRUCTURAL_FAILURE",
                "BURN_HAZARD",
                "STRANGULATION",
                "SUFFOCATION",
                "ALLERGIC_REACTION",
                "OTHER",
                name="incidenttype",
            ),
            nullable=False,
        ),
        sa.Column("incident_date", sa.DateTime(), nullable=False),
        sa.Column("incident_description", sa.Text(), nullable=False),
        sa.Column("injury_description", sa.Text(), nullable=True),
        # Severity
        sa.Column(
            "severity_level",
            sa.Enum("MINOR", "MODERATE", "SEVERE", "CRITICAL", name="severitylevel"),
            nullable=False,
        ),
        sa.Column("medical_attention_required", sa.Boolean(), nullable=True),
        sa.Column("hospital_visit", sa.Boolean(), nullable=True),
        sa.Column("child_age_months", sa.Integer(), nullable=True),
        # Evidence
        sa.Column("photo_urls", sa.JSON(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("receipt_url", sa.String(), nullable=True),
        # Reporting
        sa.Column("reported_to_manufacturer", sa.Boolean(), nullable=True),
        sa.Column("manufacturer_response", sa.Text(), nullable=True),
        sa.Column("reported_to_store", sa.Boolean(), nullable=True),
        sa.Column("store_response", sa.Text(), nullable=True),
        # Status
        sa.Column(
            "status",
            sa.Enum(
                "SUBMITTED",
                "UNDER_REVIEW",
                "VERIFIED",
                "FORWARDED_TO_AGENCY",
                "RESOLVED",
                "DUPLICATE",
                name="incidentstatus",
            ),
            nullable=True,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        # Agency
        sa.Column("forwarded_to_cpsc", sa.Boolean(), nullable=True),
        sa.Column("cpsc_case_number", sa.String(), nullable=True),
        sa.Column("forwarded_to_fda", sa.Boolean(), nullable=True),
        sa.Column("fda_case_number", sa.String(), nullable=True),
        # Clustering
        sa.Column("cluster_id", sa.String(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        # Metadata
        sa.Column("submission_ip", sa.String(), nullable=True),
        sa.Column("submission_user_agent", sa.String(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("forwarded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for incident_reports
    op.create_index(
        op.f("ix_incident_reports_barcode"),
        "incident_reports",
        ["barcode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_brand_name"),
        "incident_reports",
        ["brand_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_cluster_id"),
        "incident_reports",
        ["cluster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_created_at"),
        "incident_reports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_id"), "incident_reports", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_incident_reports_incident_type"),
        "incident_reports",
        ["incident_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_product_name"),
        "incident_reports",
        ["product_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_severity_level"),
        "incident_reports",
        ["severity_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_incident_reports_status"),
        "incident_reports",
        ["status"],
        unique=False,
    )

    # Create incident_clusters table
    op.create_table(
        "incident_clusters",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("brand_name", sa.String(), nullable=True),
        sa.Column(
            "incident_type",
            sa.Enum(
                "INJURY",
                "CHOKING_HAZARD",
                "SHARP_EDGES",
                "TOXIC_MATERIAL",
                "STRUCTURAL_FAILURE",
                "BURN_HAZARD",
                "STRANGULATION",
                "SUFFOCATION",
                "ALLERGIC_REACTION",
                "OTHER",
                name="incidenttype",
            ),
            nullable=False,
        ),
        # Statistics
        sa.Column("incident_count", sa.Integer(), nullable=True),
        sa.Column("severity_distribution", sa.JSON(), nullable=True),
        sa.Column("first_incident_date", sa.DateTime(), nullable=True),
        sa.Column("last_incident_date", sa.DateTime(), nullable=True),
        # Alerts
        sa.Column("alert_triggered", sa.Boolean(), nullable=True),
        sa.Column("alert_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("cpsc_notified", sa.Boolean(), nullable=True),
        sa.Column("cpsc_notified_at", sa.DateTime(), nullable=True),
        # Analysis
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("trending", sa.Boolean(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_incident_clusters_product_name"),
        "incident_clusters",
        ["product_name"],
        unique=False,
    )

    # Create agency_notifications table
    op.create_table(
        "agency_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("agency_name", sa.String(), nullable=False),
        sa.Column("notification_date", sa.DateTime(), nullable=False),
        sa.Column("case_number", sa.String(), nullable=True),
        sa.Column("response_received", sa.Boolean(), nullable=True),
        sa.Column("response_date", sa.DateTime(), nullable=True),
        sa.Column("response_summary", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incident_reports.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ========================================================================
    # VISUAL AGENT TABLES (IMAGE PROCESSING)
    # ========================================================================

    # Create image_jobs table
    op.create_table(
        "image_jobs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # S3/Storage info
        sa.Column("s3_bucket", sa.String(255), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("s3_presigned_url", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_type", sa.String(50), nullable=True),
        # Processing status
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "PROCESSING",
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                name="jobstatus",
            ),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Processing steps
        sa.Column("virus_scanned", sa.Boolean(), default=False),
        sa.Column("normalized", sa.Boolean(), default=False),
        sa.Column("barcode_extracted", sa.Boolean(), default=False),
        sa.Column("ocr_completed", sa.Boolean(), default=False),
        sa.Column("labels_extracted", sa.Boolean(), default=False),
        # Confidence
        sa.Column("confidence_score", sa.Float(), default=0.0),
        sa.Column(
            "confidence_level",
            sa.Enum("HIGH", "MEDIUM", "LOW", "UNCERTAIN", name="confidencelevel"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_jobs_user_id", "image_jobs", ["user_id"], unique=False)
    op.create_index("ix_image_jobs_status", "image_jobs", ["status"], unique=False)
    op.create_index(
        "ix_image_jobs_created_at", "image_jobs", ["created_at"], unique=False
    )
    op.create_index("ix_image_jobs_file_hash", "image_jobs", ["file_hash"], unique=True)

    # ========================================================================
    # SCAN HISTORY AND RELATED TABLES
    # ========================================================================

    # Create scan_history table
    op.create_table(
        "scan_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.String(50), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("scan_timestamp", sa.DateTime(), nullable=False),
        sa.Column("is_safe", sa.Boolean(), nullable=True),
        sa.Column("recall_found", sa.Boolean(), default=False),
        sa.Column("recall_count", sa.Integer(), default=0),
        sa.Column("safety_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scan_history_user_id", "scan_history", ["user_id"], unique=False
    )
    op.create_index(
        "ix_scan_history_barcode", "scan_history", ["barcode"], unique=False
    )
    op.create_index(
        "ix_scan_history_scan_timestamp",
        "scan_history",
        ["scan_timestamp"],
        unique=False,
    )

    # Create safety_reports table
    op.create_table(
        "safety_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("report_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_history.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ========================================================================
    # OTHER SUPPORTING TABLES
    # ========================================================================

    # Create share_tokens table
    op.create_table(
        "share_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("view_count", sa.Integer(), default=0),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scan_history.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_share_tokens_token", "share_tokens", ["token"], unique=True)

    # Create serial_verifications table
    op.create_table(
        "serial_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("manufacturer", sa.String(100), nullable=True),
        sa.Column("is_authentic", sa.Boolean(), nullable=True),
        sa.Column("verification_date", sa.DateTime(), nullable=False),
        sa.Column("verification_source", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_serial_verifications_serial_number",
        "serial_verifications",
        ["serial_number"],
        unique=False,
    )

    # Create privacy_requests table
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ingestion_runs table
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("records_processed", sa.Integer(), default=0),
        sa.Column("records_added", sa.Integer(), default=0),
        sa.Column("records_updated", sa.Integer(), default=0),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    print(
        "✅ Created all missing tables: incident_reports, image_jobs, scan_history, and related tables"
    )


def downgrade():
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("ingestion_runs")
    op.drop_table("privacy_requests")
    op.drop_table("serial_verifications")
    op.drop_table("share_tokens")
    op.drop_table("safety_reports")
    op.drop_table("scan_history")
    op.drop_table("image_jobs")
    op.drop_table("agency_notifications")
    op.drop_table("incident_clusters")

    # Drop incident_reports with indexes
    op.drop_index(op.f("ix_incident_reports_status"), table_name="incident_reports")
    op.drop_index(
        op.f("ix_incident_reports_severity_level"), table_name="incident_reports"
    )
    op.drop_index(
        op.f("ix_incident_reports_product_name"), table_name="incident_reports"
    )
    op.drop_index(
        op.f("ix_incident_reports_incident_type"), table_name="incident_reports"
    )
    op.drop_index(op.f("ix_incident_reports_id"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_created_at"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_cluster_id"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_brand_name"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_barcode"), table_name="incident_reports")
    op.drop_table("incident_reports")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS incidentstatus")
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS incidenttype")
    op.execute("DROP TYPE IF EXISTS confidencelevel")
    op.execute("DROP TYPE IF EXISTS jobstatus")

    print("✅ Dropped all tables and enums")
