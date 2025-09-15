from alembic import op
import sqlalchemy as sa


revision = "20250904_add_report_records"
down_revision = "20250827_privacy_requests"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "report_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("report_id", sa.String(64), unique=True, nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_report_records_user_created", "report_records", ["user_id", "created_at"])
    op.create_index("ix_report_records_type_created", "report_records", ["report_type", "created_at"])


def downgrade():
    op.drop_index("ix_report_records_type_created", table_name="report_records")
    op.drop_index("ix_report_records_user_created", table_name="report_records")
    op.drop_table("report_records")


