import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "bcef138c88a2"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("report_records"):
        print("report_records already exists; skipping")
        return

    op.create_table(
        "report_records",
        sa.Column("report_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_report_records_user_id", "report_records", ["user_id"])
    op.create_index("ix_report_records_report_type", "report_records", ["report_type"])
    op.create_index("ix_report_records_created_at", "report_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_report_records_created_at", table_name="report_records")
    op.drop_index("ix_report_records_report_type", table_name="report_records")
    op.drop_index("ix_report_records_user_id", table_name="report_records")
    op.drop_table("report_records")
