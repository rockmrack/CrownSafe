"""add chat memory tables.

Revision ID: 20250924_chat_memory
Revises: 20250905_add_serial_verifications
Create Date: 2025-09-24 20:15:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers
revision = "20250924_chat_memory"
down_revision = "20250905_add_serial_verifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Detect database dialect
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    # Use appropriate types based on dialect
    if is_sqlite:
        uuid_type = sa.String(36)
        json_type = sa.JSON()
        now_func = sa.text("CURRENT_TIMESTAMP")
        jsonb_default = sa.text("'[]'")
    else:
        uuid_type = postgresql.UUID(as_uuid=True)
        json_type = postgresql.JSONB(astext_type=sa.Text())
        now_func = sa.text("now()")
        jsonb_default = sa.text("'[]'::jsonb")

    op.create_table(
        "user_profile",
        sa.Column("user_id", uuid_type, primary_key=True),
        sa.Column(
            "consent_personalization",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false") if not is_sqlite else sa.text("0"),
        ),
        sa.Column(
            "memory_paused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false") if not is_sqlite else sa.text("0"),
        ),
        sa.Column(
            "allergies",
            json_type,
            nullable=False,
            server_default=jsonb_default,
        ),
        sa.Column("pregnancy_trimester", sa.SmallInteger(), nullable=True),
        sa.Column("pregnancy_due_date", sa.Date(), nullable=True),
        sa.Column("child_birthdate", sa.Date(), nullable=True),
        sa.Column("erase_requested_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
    )
    op.create_table(
        "conversation",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, nullable=True),
        sa.Column("scan_id", sa.String(length=64), nullable=True),
        sa.Column(
            "started_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
        sa.Column(
            "last_activity_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
    )
    op.create_index("ix_conversation_user_id", "conversation", ["user_id"])
    op.create_table(
        "conversation_message",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", uuid_type, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=now_func,
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),  # 'user' | 'assistant'
        sa.Column("intent", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("content", json_type, nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversation.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_message_conversation_id", "conversation_message", ["conversation_id"])
    op.create_index("ix_message_role", "conversation_message", ["role"])
    op.create_index("ix_message_trace", "conversation_message", ["trace_id"])
    op.create_index(
        "ix_message_content_gin",
        "conversation_message",
        [sa.text("content")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_message_content_gin", table_name="conversation_message")
    op.drop_index("ix_message_trace", table_name="conversation_message")
    op.drop_index("ix_message_role", table_name="conversation_message")
    op.drop_index("ix_message_conversation_id", table_name="conversation_message")
    op.drop_table("conversation_message")
    op.drop_index("ix_conversation_user_id", table_name="conversation")
    op.drop_table("conversation")
    op.drop_table("user_profile")
