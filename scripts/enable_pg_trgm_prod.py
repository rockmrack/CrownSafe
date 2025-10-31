#!/usr/bin/env python3
"""Enable pg_trgm extension in production PostgreSQL."""

import os
import sys

import psycopg2


# Connection details
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
    "sslmode": os.getenv("BABYSHIELD_DB_SSLMODE", "require"),
}


def enable_pg_trgm():
    """Enable pg_trgm extension and create indexes"""
    try:
        print("🔌 Connecting to PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        print("✅ Connected successfully!")
        print()

        # Enable extension
        print("📦 Enabling pg_trgm extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        print("✅ Extension enabled!")

        # Verify extension
        cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';")
        result = cursor.fetchone()
        if result:
            print(f"✅ Verified: pg_trgm version {result[1]}")

        print()
        print("📊 Creating GIN indexes for better performance...")

        # Create indexes
        indexes = [
            ("idx_recalls_product_trgm", "product_name"),
            ("idx_recalls_brand_trgm", "brand"),
            ("idx_recalls_description_trgm", "description"),
            ("idx_recalls_hazard_trgm", "hazard"),
        ]

        for idx_name, column_name in indexes:
            print(f"  Creating {idx_name}...")
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS {idx_name}
                ON recalls_enhanced USING gin (lower({column_name}) gin_trgm_ops);
            """,
            )
            print(f"  ✅ {idx_name} created")

        print()
        print("🧪 Testing similarity function...")
        cursor.execute("SELECT similarity('baby', 'baby');")
        score = cursor.fetchone()[0]
        print(f"  similarity('baby', 'baby') = {score} (expected: 1.0)")

        cursor.execute("SELECT similarity('baby', 'babe');")
        score = cursor.fetchone()[0]
        print(f"  similarity('baby', 'babe') = {score} (expected: ~0.75)")

        print()
        print("✅ SUCCESS: pg_trgm extension is now enabled and configured!")
        print()
        print("🧪 Next step: Test the search endpoint:")
        print("   curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\")
        print('        -H "Content-Type: application/json" \\')
        print('        -d \'{"query":"baby","limit":10}\'')

        cursor.close()
        conn.close()
        return 0

    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   - Check database connection details")
        print("   - Verify network connectivity to RDS")
        print("   - Check security group rules")
        print("   - Verify user has SUPERUSER or CREATE EXTENSION privileges")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(enable_pg_trgm())
