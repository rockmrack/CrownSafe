"""Check recalled products count in the database"""

import os

# Set environment
os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./babyshield_dev.db"

from core_infra.database import Base, SessionLocal, engine

print("=" * 70)
print("Recalled Products Database Check")
print("=" * 70)
print()

# Create tables if they don't exist
print("Creating tables if needed...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Tables ready")
except Exception as e:
    print(f"⚠️  Table creation: {e}")

print()

# Check EnhancedRecallDB
print("Checking Enhanced Recalls (recalls_enhanced)...")
try:
    from core_infra.enhanced_database_schema import EnhancedRecallDB

    db = SessionLocal()
    count = db.query(EnhancedRecallDB).count()
    print(f"✅ Enhanced Recalls: {count:,} products")

    if count > 0:
        # Show sample
        sample = db.query(EnhancedRecallDB).limit(3).all()
        print("\n   Sample recalls:")
        for recall in sample:
            print(f"   - {recall.product_name} ({recall.brand}) - {recall.source_agency}")

    db.close()
except Exception as e:
    print(f"⚠️  Enhanced recalls error: {e}")

print()

# Check LegacyRecallDB
print("Checking Legacy Recalls (recalls table)...")
try:
    from core_infra.database import LegacyRecallDB

    db = SessionLocal()
    count = db.query(LegacyRecallDB).count()
    print(f"✅ Legacy Recalls: {count:,} products")

    if count > 0:
        # Show sample
        sample = db.query(LegacyRecallDB).limit(3).all()
        print("\n   Sample recalls:")
        for recall in sample:
            product_name = recall.product_name or "Unknown"
            brand = recall.brand or "Unknown"
            print(f"   - {product_name} ({brand})")

    db.close()
except Exception as e:
    print(f"⚠️  Legacy recalls error: {e}")

print()

# Check Users
print("Checking Users...")
try:
    from core_infra.database import User

    db = SessionLocal()
    count = db.query(User).count()
    print(f"✅ Users: {count:,} users")
    db.close()
except Exception as e:
    print(f"⚠️  Users error: {e}")

print()
print("=" * 70)
print("Database Check Complete")
print("=" * 70)
print()
print("💡 To populate recalls, run:")
print("   python agents/recall_data_agent/main.py")
print()
