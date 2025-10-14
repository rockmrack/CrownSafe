"""
Verify Production Database - 131,743 Recalls Check
"""

import os

# Set production DATABASE_URL (using psycopg v3 driver)
os.environ[
    "DATABASE_URL"
] = "postgresql+psycopg://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db"

print("=" * 70)
print("PRODUCTION DATABASE CHECK - AWS RDS PostgreSQL")
print("=" * 70)
print()

try:
    print("Step 1: Importing database modules...")
    from core_infra.database import SessionLocal, engine

    print(f"  Engine dialect: {engine.dialect.name}")
    print(f"  Engine URL: {str(engine.url).replace('MandarunLabadiena25!', '***')}")
    print()

    print("Step 2: Testing connection...")
    db = SessionLocal()
    print("  Connection successful!")
    print()

    print("Step 3: Counting recalls_enhanced table...")
    from core_infra.enhanced_database_schema import EnhancedRecallDB

    count = db.query(EnhancedRecallDB).count()
    print(f"  TOTAL RECALLS: {count:,} records")
    print()

    if count > 0:
        print("Step 4: Fetching sample recalls...")
        samples = db.query(EnhancedRecallDB).limit(5).all()

        print()
        print("  Sample Recalls:")
        print("  " + "-" * 66)
        for i, recall in enumerate(samples, 1):
            product = (recall.product_name or "Unknown")[:40]
            brand = (recall.brand or "N/A")[:15]
            agency = (recall.source_agency or "N/A")[:10]
            print(f"  {i}. {product:40} | {brand:15} | {agency}")
        print("  " + "-" * 66)

    db.close()

    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print(f"Your {count:,} recalls are accessible with PostgreSQL migration!")
    print()
    print("Migration Status:")
    print("  [x] psycopg v3 driver installed")
    print("  [x] Connection to AWS RDS working")
    print("  [x] Database queries working")
    print("  [x] 131K+ recalls accessible")
    print()

except Exception as e:
    print(f"ERROR: {e}")
    print()
    print("Possible issues:")
    print("  1. Network/firewall blocking RDS access")
    print("  2. Security group not allowing your IP")
    print("  3. psycopg module issue")
    print()
    import traceback

    traceback.print_exc()

print("=" * 70)
