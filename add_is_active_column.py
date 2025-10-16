"""
Quick script to add is_active column to users table
"""

from core_infra.database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        # Add the column if it doesn't exist
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true"
            )
        )
        conn.commit()
        print("✅ Column 'is_active' added successfully to users table")

        # Verify it was added
        result = conn.execute(
            text(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'users' AND column_name = 'is_active'"
            )
        )
        row = result.fetchone()
        if row:
            print(f"✅ Verified: {row}")
        else:
            print("❌ Column not found after adding")

except Exception as e:
    print(f"❌ Error: {e}")
