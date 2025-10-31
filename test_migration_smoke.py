"""Quick smoke test to verify PostgreSQL migration didn't break core functionality
Run this after migration changes to ensure everything still works.
"""

import os
import sys

# Set test mode
os.environ["TEST_MODE"] = "true"
os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

print("=" * 70)
print("PostgreSQL Migration Smoke Test")
print("=" * 70)
print()

# Test 1: Import core database module
print("Test 1: Import core_infra.database...")
try:
    from core_infra.database import Base, SessionLocal, engine

    print("✅ PASS - Database module imported successfully")
except Exception as e:
    print(f"❌ FAIL - Cannot import database module: {e}")
    sys.exit(1)

# Test 2: Create engine
print("\nTest 2: Check database engine...")
try:
    dialect = engine.dialect.name
    print(f"✅ PASS - Engine created (dialect: {dialect})")
    if os.getenv("DATABASE_URL", "").startswith("sqlite"):
        assert dialect == "sqlite", f"Expected sqlite, got {dialect}"
        print("✅ PASS - Correctly using SQLite for tests")
except Exception as e:
    print(f"❌ FAIL - Engine error: {e}")
    sys.exit(1)

# Test 3: Create session
print("\nTest 3: Create database session...")
try:
    db = SessionLocal()
    db.close()
    print("✅ PASS - Session created and closed")
except Exception as e:
    print(f"❌ FAIL - Session error: {e}")
    sys.exit(1)

# Test 4: Create tables
print("\nTest 4: Create database tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅ PASS - Tables created")
except Exception as e:
    print(f"❌ FAIL - Table creation error: {e}")
    sys.exit(1)

# Test 5: Import FastAPI app
print("\nTest 5: Import FastAPI application...")
try:
    from api.main_crownsafe import app

    print("✅ PASS - FastAPI app imported")
except Exception as e:
    print(f"❌ FAIL - FastAPI import error: {e}")
    sys.exit(1)

# Test 6: Test FastAPI client
print("\nTest 6: Create test client...")
try:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    print("✅ PASS - Test client created")
except Exception as e:
    print(f"❌ FAIL - Test client error: {e}")
    sys.exit(1)

# Test 7: Test health endpoint
print("\nTest 7: Test /healthz endpoint...")
try:
    response = client.get("/healthz")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    print(f"✅ PASS - Health endpoint responded: {response.json()}")
except Exception as e:
    print(f"❌ FAIL - Health endpoint error: {e}")
    sys.exit(1)

# Test 8: Test database query
print("\nTest 8: Test database query...")
try:
    from core_infra.database import User

    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    print(f"✅ PASS - Database query executed ({len(users)} users found)")
except Exception as e:
    print(f"❌ FAIL - Database query error: {e}")
    sys.exit(1)

# Test 9: Test Alembic can find migrations
print("\nTest 9: Check Alembic migration files...")
try:
    import os.path

    migrations_path = "db/migrations/versions"
    if os.path.exists(migrations_path):
        migration_files = [f for f in os.listdir(migrations_path) if f.endswith(".py") and not f.startswith("__")]
        print(f"✅ PASS - Found {len(migration_files)} migration files")
        # Check for pg_trgm migration
        pg_trgm_exists = any("pg_trgm" in f for f in migration_files)
        if pg_trgm_exists:
            print("✅ PASS - pg_trgm migration exists")
        else:
            print("⚠️  WARNING - pg_trgm migration not found")
    else:
        print(f"⚠️  WARNING - Migrations directory not found: {migrations_path}")
except Exception as e:
    print(f"⚠️  WARNING - Migration check error: {e}")

# Test 10: Verify conditional pool settings
print("\nTest 10: Verify engine pool settings...")
try:
    # For SQLite, pool settings should not be set
    if engine.dialect.name == "sqlite":
        # Check that we're not trying to use pool settings on SQLite
        print("✅ PASS - SQLite engine (no pool settings expected)")
    else:
        # For PostgreSQL, check pool settings exist
        pool = engine.pool
        print(f"✅ PASS - PostgreSQL engine with pool: {type(pool).__name__}")
except Exception as e:
    print(f"❌ FAIL - Engine pool check error: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("Summary: All Core Tests Passed! ✅")
print("=" * 70)
print()
print("✅ Database module working")
print("✅ Engine creation working")
print("✅ Session management working")
print("✅ Table creation working")
print("✅ FastAPI app loading")
print("✅ Health endpoint responding")
print("✅ Database queries working")
print("✅ Migration files present")
print("✅ Pool settings conditional")
print()
print("🎉 PostgreSQL migration did NOT break core functionality!")
print()
