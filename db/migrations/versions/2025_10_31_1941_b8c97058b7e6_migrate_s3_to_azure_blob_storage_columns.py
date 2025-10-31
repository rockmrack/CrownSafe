"""migrate_s3_to_azure_blob_storage_columns

Revision ID: b8c97058b7e6
Revises: crown_safe_v1
Create Date: 2025-10-31 19:41:51.943449

Migrates all S3-related columns to Azure Blob Storage naming:
- s3_url → blob_url
- s3_bucket → blob_container
- s3_key → blob_name
- s3_presigned_url → blob_sas_url

This migration supports the AWS to Azure infrastructure migration.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b8c97058b7e6"
down_revision = "crown_safe_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename S3 columns to Azure Blob Storage equivalents"""
    # scan_history table
    with op.batch_alter_table("scan_history", schema=None) as batch_op:
        batch_op.alter_column("s3_url", new_column_name="blob_url")

    # content_snapshot table (if exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "content_snapshot" in inspector.get_table_names():
        with op.batch_alter_table("content_snapshot", schema=None) as batch_op:
            if "s3_bucket" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("s3_bucket", new_column_name="blob_container")
            if "s3_key" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("s3_key", new_column_name="blob_name")
            if "s3_presigned_url" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("s3_presigned_url", new_column_name="blob_sas_url")

    # image_jobs table (if exists)
    if "image_jobs" in inspector.get_table_names():
        with op.batch_alter_table("image_jobs", schema=None) as batch_op:
            if "s3_bucket" in [c["name"] for c in inspector.get_columns("image_jobs")]:
                batch_op.alter_column("s3_bucket", new_column_name="blob_container")
            if "s3_key" in [c["name"] for c in inspector.get_columns("image_jobs")]:
                batch_op.alter_column("s3_key", new_column_name="blob_name")


def downgrade() -> None:
    """Revert Azure Blob Storage columns back to S3 naming"""
    # scan_history table
    with op.batch_alter_table("scan_history", schema=None) as batch_op:
        batch_op.alter_column("blob_url", new_column_name="s3_url")

    # content_snapshot table (if exists)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "content_snapshot" in inspector.get_table_names():
        with op.batch_alter_table("content_snapshot", schema=None) as batch_op:
            if "blob_container" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("blob_container", new_column_name="s3_bucket")
            if "blob_name" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("blob_name", new_column_name="s3_key")
            if "blob_sas_url" in [c["name"] for c in inspector.get_columns("content_snapshot")]:
                batch_op.alter_column("blob_sas_url", new_column_name="s3_presigned_url")

    # image_jobs table (if exists)
    if "image_jobs" in inspector.get_table_names():
        with op.batch_alter_table("image_jobs", schema=None) as batch_op:
            if "blob_container" in [c["name"] for c in inspector.get_columns("image_jobs")]:
                batch_op.alter_column("blob_container", new_column_name="s3_bucket")
            if "blob_name" in [c["name"] for c in inspector.get_columns("image_jobs")]:
                batch_op.alter_column("blob_name", new_column_name="s3_key")
