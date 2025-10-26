"""
Add is_active column to users table in POSTGRES database
This script connects to the CORRECT database that production uses.
"""

import os
import sys

import psycopg2


# Production database connection - POSTGRES database (not babyshield_db!)
def _require_env(var_name: str) -> str:
    """Return the value of the required environment variable."""

    value = os.getenv(var_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {var_name}")
    return value


DB_CONFIG = {
    "host": _require_env("BABYSHIELD_DB_HOST"),
    "port": int(os.getenv("BABYSHIELD_DB_PORT", "5432")),
    "database": _require_env("BABYSHIELD_DB_NAME"),
    "user": _require_env("BABYSHIELD_DB_USER"),
    "password": _require_env("BABYSHIELD_DB_PASSWORD"),
}


def main():
    print("🔗 Connecting to POSTGRES database...")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Database: {DB_CONFIG['database']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connected successfully!\n")

        with conn.cursor() as cur:
            # Check current database
            cur.execute("SELECT current_database(), current_schema();")
            db_name, schema = cur.fetchone()
            print(f"📍 Current database: {db_name}")
            print(f"📍 Current schema: {schema}\n")

            # Check if is_active column exists
            cur.execute(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND table_schema = 'public'
                AND column_name = 'is_active';
            """
            )
            exists = cur.fetchone()

            if exists:
                print("✅ is_active column already exists in users table!")
            else:
                print("➕ Adding is_active column to users table...")
                cur.execute(
                    """
                    ALTER TABLE users 
                    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT true;
                """
                )
                conn.commit()
                print("✅ Column added successfully!\n")

            # Verify all columns
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position;
            """
            )
            columns = cur.fetchall()

            print("📋 Current columns in users table:")
            for col in columns:
                indicator = "✅" if col[0] == "is_active" else "  "
                print(f"{indicator} {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

            # Count records
            cur.execute("SELECT COUNT(*) FROM users;")
            count = cur.fetchone()[0]
            print(f"\n📊 Total users in table: {count}")

            print("\n🎉 Done! The is_active column is now available in production.")

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()
            print("🔌 Connection closed.")


if __name__ == "__main__":
    main()
