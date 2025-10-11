"""Add incident reporting tables

Revision ID: 20250109_incident_reports
Revises: 20250108_share_tokens
Create Date: 2025-01-09

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "20250109_incident_reports"
down_revision = "20250108_share_tokens"
branch_labels = None
depends_on = None


def upgrade():
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
    op.create_index(op.f("ix_incident_reports_id"), "incident_reports", ["id"], unique=False)
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
        op.f("ix_incident_reports_status"), "incident_reports", ["status"], unique=False
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
        sa.Column("agency", sa.String(), nullable=False),
        sa.Column("cluster_id", sa.String(), nullable=True),
        # Notification details
        sa.Column("notification_type", sa.String(), nullable=True),
        sa.Column("incident_count", sa.Integer(), nullable=True),
        sa.Column("severity_summary", sa.JSON(), nullable=True),
        # Communication
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("sent_via", sa.String(), nullable=True),
        sa.Column("response_received", sa.Boolean(), nullable=True),
        sa.Column("response_date", sa.DateTime(), nullable=True),
        sa.Column("agency_case_number", sa.String(), nullable=True),
        # Metadata
        sa.Column("notification_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["incident_clusters.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("agency_notifications")
    op.drop_index(op.f("ix_incident_clusters_product_name"), table_name="incident_clusters")
    op.drop_table("incident_clusters")

    op.drop_index(op.f("ix_incident_reports_status"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_severity_level"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_product_name"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_incident_type"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_id"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_created_at"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_cluster_id"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_brand_name"), table_name="incident_reports")
    op.drop_index(op.f("ix_incident_reports_barcode"), table_name="incident_reports")
    op.drop_table("incident_reports")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS incidenttype")
    op.execute("DROP TYPE IF EXISTS severitylevel")
    op.execute("DROP TYPE IF EXISTS incidentstatus")
