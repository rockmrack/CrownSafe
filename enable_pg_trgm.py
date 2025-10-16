#!/usr/bin/env python3
"""
Enable pg_trgm extension on production database.
Run this script from within the ECS container or a machine with DB access.
"""

import os
import sys

try:
    import psycopg2
except ImportError:
    print("❌ psycopg2 not installed. Installing...")
    os.system("pip install psycopg2-binary")
    import psycopg2

# Database connection details
DB_HOST = "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com"
DB_NAME = "babyshield_db"
DB_USER = "babyshield_user"
DB_PASSWORD = os.getenv("DB_PASSWORD")
if DB_PASSWORD is None:
    print("❌ Environment variable DB_PASSWORD must be set. Exiting.")
    sys.exit(1)
DB_PORT = 5432


def enable_pg_trgm():
    """Enable pg_trgm extension and create indexes."""
    try:
        print(f"🔌 Connecting to {DB_HOST}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            connect_timeout=10,
        )
        cur = conn.cursor()

        # Enable pg_trgm extension
        print("📦 Enabling pg_trgm extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        conn.commit()
        print("✅ pg_trgm extension enabled!")

        # Verify extension is enabled
        cur.execute(
            "SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';"
        )
        result = cur.fetchone()
        if result:
            print(f"✅ Verified: pg_trgm version {result[1]} is active")

        # Create trigram indexes for better search performance
        print("\n📊 Creating trigram indexes...")

        indexes = [
            ("idx_recalls_title_trgm", "recalls", "title"),
            ("idx_recalls_description_trgm", "recalls", "description"),
            ("idx_recalls_product_name_trgm", "recalls", "product_name"),
        ]

        for idx_name, table, column in indexes:
            try:
                print(f"   Creating {idx_name}...")
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} 
                    ON {table} USING gin ({column} gin_trgm_ops);
                """
                )
                conn.commit()
                print(f"   ✅ {idx_name} created")
            except Exception as e:
                print(f"   ⚠️  {idx_name} - {str(e)}")
                conn.rollback()

        print("\n🎉 All done! Search should now work properly.")

        cur.close()
        conn.close()

    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 This script must run from:")
        print("   1. Inside the ECS container")
        print("   2. A machine with access to the RDS security group")
        print("   3. Via AWS Systems Manager Session Manager")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    enable_pg_trgm()
