"""create pg_trgm extension.

Revision ID: 20251012_create_pg_trgm
Revises: bcef138c88a2
Create Date: 2025-10-12 00:00:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251012_create_pg_trgm"
down_revision = "bcef138c88a2"  # Points to previous head
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the pg_trgm extension if not exists (PostgreSQL only)
    # Skip this operation on SQLite databases
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    else:
        print(f"Skipping pg_trgm extension creation on {conn.dialect.name}")


def downgrade() -> None:
    # Drop the extension (safe operation if exists, PostgreSQL only)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    else:
        print(f"Skipping pg_trgm extension drop on {conn.dialect.name}")
