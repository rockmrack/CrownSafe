#!/usr/bin/env python3
"""PostgreSQL Migration Verification Script

Tests database connectivity and validates migration success.
Run this after setting DATABASE_URL to verify PostgreSQL setup.

Usage:
    export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"
    python verify_postgres_migration.py
"""

import os
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError


def check_database_url():
    """Verify DATABASE_URL is set and formatted correctly"""
    print("=" * 70)
    print("Step 1: Check DATABASE_URL Configuration")
    print("=" * 70)

    db_url = os.getenv("DATABASE_URL")

    if not db_url:
        print("❌ FAIL: DATABASE_URL environment variable not set")
        print("\nPlease set DATABASE_URL:")
        print('  export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"')
        return None

    print("✅ DATABASE_URL is set")

    # Mask password for display
    display_url = db_url
    if "@" in display_url and "://" in display_url:
        parts = display_url.split("://")
        if len(parts) == 2:
            scheme = parts[0]
            rest = parts[1]
            if "@" in rest:
                creds, host_db = rest.split("@", 1)
                if ":" in creds:
                    user, _ = creds.split(":", 1)
                    display_url = f"{scheme}://{user}:****@{host_db}"

    print(f"   URL: {display_url}")

    # Check if it's PostgreSQL
    if db_url.startswith("postgresql"):
        print("✅ URL uses PostgreSQL driver")

        if "psycopg" in db_url and "psycopg2" not in db_url:
            print("✅ Using psycopg v3 driver (recommended)")
        elif "psycopg2" in db_url:
            print("⚠️  WARNING: Using psycopg2 (legacy). Recommend upgrading to psycopg v3")
        else:
            print("⚠️  WARNING: PostgreSQL driver not specified. Default may be used.")

    elif db_url.startswith("sqlite"):
        print("⚠️  WARNING: Using SQLite (not recommended for production)")
        print("   Production should use PostgreSQL with psycopg v3")
        return db_url  # Still allow SQLite for testing

    else:
        print(f"❌ FAIL: Unsupported database type: {db_url.split(':')[0]}")
        return None

    print()
    return db_url


def test_connection(db_url):
    """Test database connection"""
    print("=" * 70)
    print("Step 2: Test Database Connection")
    print("=" * 70)

    try:
        # Create engine without pool for initial test
        engine = create_engine(db_url, pool_pre_ping=True, echo=False)

        print("Connecting to database...")
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("✅ Connection successful!")
            print(f"   Database version: {version[:80]}...")

            # Check dialect
            dialect = engine.dialect.name
            print(f"   SQLAlchemy dialect: {dialect}")

            return engine

    except OperationalError as e:
        print("❌ FAIL: Cannot connect to database")
        print(f"   Error: {str(e)[:200]}")
        print("\nTroubleshooting:")
        print("  1. Verify PostgreSQL is running")
        print("  2. Check credentials in DATABASE_URL")
        print("  3. Ensure host/port are correct")
        print("  4. Check firewall rules")
        return None

    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {type(e).__name__}")
        print(f"   {str(e)[:200]}")
        return None

    finally:
        print()


def check_extensions(engine):
    """Check PostgreSQL extensions"""
    print("=" * 70)
    print("Step 3: Check PostgreSQL Extensions")
    print("=" * 70)

    if engine.dialect.name != "postgresql":
        print("⚠️  SKIP: Not a PostgreSQL database")
        print()
        return

    try:
        with engine.connect() as conn:
            # Check pg_trgm extension
            result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname='pg_trgm'"))
            extensions = [row[0] for row in result]

            if "pg_trgm" in extensions:
                print("✅ pg_trgm extension is installed")
                print("   (Required for fuzzy text search and product name matching)")
            else:
                print("⚠️  WARNING: pg_trgm extension NOT installed")
                print("   This extension is required for optimal recall matching.")
                print("\n   To fix, run:")
                print('   psql "$DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"')
                print("   Or run Alembic migration:")
                print("   alembic -c db/alembic.ini upgrade head")

    except Exception as e:
        print(f"⚠️  Could not check extensions: {str(e)[:100]}")

    finally:
        print()


def check_tables(engine):
    """Check if tables exist"""
    print("=" * 70)
    print("Step 4: Check Database Tables")
    print("=" * 70)

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            print("⚠️  WARNING: No tables found")
            print("   Run Alembic migrations to create tables:")
            print("   alembic -c db/alembic.ini upgrade head")
        else:
            print(f"✅ Found {len(tables)} tables")

            # Check for key tables
            expected_tables = [
                "users",
                "enhanced_recalls",
                "legacy_recalls",
                "alembic_version",
            ]

            missing_tables = []
            for table in expected_tables:
                if table in tables:
                    print(f"   ✅ {table}")
                else:
                    print(f"   ❌ {table} (missing)")
                    missing_tables.append(table)

            if missing_tables:
                print("\n⚠️  Some tables are missing. Run migrations:")
                print("   alembic -c db/alembic.ini upgrade head")

    except Exception as e:
        print(f"⚠️  Could not check tables: {str(e)[:100]}")

    finally:
        print()


def check_alembic_version(engine):
    """Check Alembic migration version"""
    print("=" * 70)
    print("Step 5: Check Alembic Migration Status")
    print("=" * 70)

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()

            if version:
                print(f"✅ Current migration version: {version}")
            else:
                print("⚠️  No migration version found")
                print("   Run initial migration:")
                print("   alembic -c db/alembic.ini upgrade head")

    except Exception as e:
        if "relation" in str(e).lower() and "alembic_version" in str(e).lower():
            print("⚠️  alembic_version table does not exist")
            print("   Run Alembic migrations:")
            print("   alembic -c db/alembic.ini upgrade head")
        else:
            print(f"⚠️  Could not check migration version: {str(e)[:100]}")

    finally:
        print()


def check_psycopg_version():
    """Check psycopg version"""
    print("=" * 70)
    print("Step 6: Check psycopg Driver Version")
    print("=" * 70)

    try:
        import psycopg

        print(f"✅ psycopg v3 installed: {psycopg.__version__}")
        print("   (Recommended driver for PostgreSQL)")
    except ImportError:
        print("⚠️  psycopg v3 not found")

        try:
            import psycopg2

            print(f"⚠️  Using legacy psycopg2: {psycopg2.__version__}")
            print("   Recommend upgrading to psycopg v3:")
            print('   pip install "psycopg[binary]>=3.1"')
        except ImportError:
            print("❌ FAIL: No PostgreSQL driver installed")
            print('   Install psycopg v3: pip install "psycopg[binary]>=3.1"')

    finally:
        print()


def main():
    """Run all verification checks"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "PostgreSQL Migration Verification" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Step 1: Check DATABASE_URL
    db_url = check_database_url()
    if not db_url:
        sys.exit(1)

    # Step 2: Test connection
    engine = test_connection(db_url)
    if not engine:
        sys.exit(1)

    # Step 3-5: Check PostgreSQL-specific features
    check_extensions(engine)
    check_tables(engine)
    check_alembic_version(engine)

    # Step 6: Check driver version
    check_psycopg_version()

    # Summary
    print("=" * 70)
    print("Verification Summary")
    print("=" * 70)

    if engine.dialect.name == "postgresql":
        print("✅ PostgreSQL connection working")
        print("✅ Migration verification complete")
        print("\nNext steps:")
        print("  1. If tables are missing, run: alembic -c db/alembic.ini upgrade head")
        print("  2. If pg_trgm is missing, ensure migration ran successfully")
        print("  3. Start application: python core/startup.py")
        print("  4. Test API: curl http://localhost:8001/healthz")
    else:
        print("⚠️  Not using PostgreSQL (using SQLite)")
        print("   For production, set DATABASE_URL to PostgreSQL:")
        print('   export DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"')

    print()
    print("✅ Verification script completed successfully!")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {e!s}")
        sys.exit(1)
