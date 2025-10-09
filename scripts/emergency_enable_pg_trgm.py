#!/usr/bin/env python3
"""
EMERGENCY: Enable pg_trgm extension directly on production database
This bypasses the application startup code
"""

import psycopg2
import sys
import os

# Get DATABASE_URL from environment or use direct connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres",
)

print("=" * 60)
print("EMERGENCY pg_trgm Enablement Script")
print("=" * 60)
print()

try:
    print("🔌 Connecting to production database...")
    print(f"   Host: babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com")
    print(f"   Database: postgres")
    print()

    # Parse connection string
    if DATABASE_URL.startswith("postgresql://"):
        conn = psycopg2.connect(DATABASE_URL, sslmode="require", connect_timeout=10)
    else:
        conn = psycopg2.connect(
            host="babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
            port=5432,
            database="postgres",
            user="babyshield_user",
            password="MandarunLabadiena25!",
            sslmode="require",
            connect_timeout=10,
        )

    conn.autocommit = True
    cursor = conn.cursor()

    print("✅ Connected successfully!")
    print()

    # Check if extension already exists
    print("🔍 Checking if pg_trgm is already enabled...")
    cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';")
    result = cursor.fetchone()

    if result:
        print(f"✅ pg_trgm is ALREADY enabled (version {result[1]})")
        print("   Extension exists but searches are still failing!")
        print()
        print("🔧 This means the application code has a bug or:")
        print("   1. SearchService is not using pg_trgm correctly")
        print("   2. There's a permission issue")
        print("   3. The similarity() function path is wrong")
        print()
    else:
        print("❌ pg_trgm is NOT enabled")
        print()
        print("📦 Enabling pg_trgm extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        print("✅ Extension enabled!")
        print()

    # Verify similarity function works
    print("🧪 Testing similarity function...")
    try:
        cursor.execute("SELECT similarity('baby', 'baby');")
        score = cursor.fetchone()[0]
        print(f"✅ similarity('baby', 'baby') = {score} (expected: 1.0)")

        cursor.execute("SELECT similarity('baby', 'babe');")
        score = cursor.fetchone()[0]
        print(f"✅ similarity('baby', 'babe') = {score} (expected: ~0.75)")
        print()
        print("✅ similarity() function is working correctly!")
    except Exception as e:
        print(f"❌ similarity() function test FAILED: {e}")
        print()

    # Check indexes
    print()
    print("📊 Checking GIN indexes...")
    cursor.execute(
        """
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'recalls_enhanced' 
        AND indexname LIKE '%trgm%'
        ORDER BY indexname;
    """
    )
    indexes = cursor.fetchall()

    if indexes:
        print(f"✅ Found {len(indexes)} trgm indexes:")
        for idx_name, idx_def in indexes:
            print(f"   - {idx_name}")
    else:
        print("❌ No trgm indexes found!")
        print()
        print("📦 Creating GIN indexes...")

        indexes_to_create = [
            "CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);",
            "CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);",
        ]

        for idx_sql in indexes_to_create:
            print(f"   Creating {idx_sql.split('idx_recalls_')[1].split(' ON')[0]}...")
            cursor.execute(idx_sql)

        print("✅ All indexes created!")

    print()
    print("=" * 60)
    print("✅ SUCCESS: Database is configured correctly")
    print("=" * 60)
    print()
    print("🔍 Next steps:")
    print("   1. Test search endpoint again")
    print("   2. If still failing, check SearchService code")
    print("   3. Verify DATABASE_URL in ECS task definition")
    print()

    cursor.close()
    conn.close()
    sys.exit(0)

except psycopg2.OperationalError as e:
    print(f"❌ Connection Error: {e}")
    print()
    print("💡 This script must run from a location that can reach RDS:")
    print("   - EC2 instance in same VPC")
    print("   - Bastion host")
    print("   - VPN connection")
    print("   - Or temporarily open security group to your IP")
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
