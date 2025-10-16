#!/usr/bin/env python3
"""
Emergency pg_trgm enablement script for AWS CloudShell
Uses direct database connection (works if security group allows CloudShell)
"""

import os
import sys

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2...")
    os.system("pip3 install psycopg2-binary --quiet")
    import psycopg2

# Database connection details
DB_CONFIG = {
    "host": "babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com",
    "port": 5432,
    "database": "postgres",
    "user": "babyshield_user",
    "password": "MandarunLabadiena25!",
    "sslmode": "require",
    "connect_timeout": 10,
}

print("=" * 60)
print("  Emergency pg_trgm Enablement Script")
print("=" * 60)
print()

print("Attempting to connect to production database...")
print(f"Host: {DB_CONFIG['host']}")
print(f"Database: {DB_CONFIG['database']}")
print()

try:
    # Try to connect
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    print("✓ Connected successfully!")
    print()

    # Enable extension
    print("Step 1: Enabling pg_trgm extension...")
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    print("✓ Extension enabled")
    print()

    # Verify
    print("Step 2: Verifying extension...")
    cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';")
    result = cursor.fetchone()
    if result:
        print(f"✓ pg_trgm version {result[1]} is installed")
    print()

    # Test similarity
    print("Step 3: Testing similarity function...")
    cursor.execute("SELECT similarity('baby', 'baby');")
    score = cursor.fetchone()[0]
    print(f"✓ similarity('baby', 'baby') = {score}")
    print()

    # Create indexes
    print("Step 4: Creating GIN indexes...")
    indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm "
            "ON recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm "
            "ON recalls_enhanced USING gin (lower(brand) gin_trgm_ops);"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm "
            "ON recalls_enhanced USING gin (lower(description) gin_trgm_ops);"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm "
            "ON recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);"
        ),
    ]

    for idx_sql in indexes:
        idx_name = idx_sql.split("idx_recalls_")[1].split(" ON")[0]
        cursor.execute(idx_sql)
        print(f"✓ Created index: {idx_name}")

    print()
    print("=" * 60)
    print("  ✓ SUCCESS - pg_trgm is now enabled!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Test search: curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\")
    print('                    -H "Content-Type: application/json" \\')
    print('                    -d \'{"query":"baby","limit":5}\'')
    print("  2. Expected: 'total' > 0 (not 0)")
    print()

    cursor.close()
    conn.close()
    sys.exit(0)

except psycopg2.OperationalError as e:
    print(f"❌ Connection failed: {e}")
    print()
    print("This means CloudShell cannot reach the RDS database.")
    print("Possible solutions:")
    print()
    print("1. Add CloudShell IP to RDS security group")
    print("   - Find your CloudShell IP: curl -s https://checkip.amazonaws.com")
    print("   - Add it to the RDS security group inbound rules (port 5432)")
    print()
    print("2. Use the Admin API endpoint instead (EASIER):")
    print("   - Run: ./enable_pg_trgm_via_api_cloudshell.sh")
    print("   - Or use the manual curl commands in CLOUDSHELL_COMMANDS.md")
    print()
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
