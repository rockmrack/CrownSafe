#!/usr/bin/env python3
"""
Initialize test database with all required tables and migrations.
This script is used in CI/CD to ensure the database is properly set up before running tests.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with all required tables"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        logger.warning("DATABASE_URL not set, skipping database initialization")
        return

    logger.info(
        f"Initializing database at {database_url.split('@')[1] if '@' in database_url else database_url}"
    )

    try:
        # First, run Alembic migrations to ensure all tables are created
        logger.info("Running Alembic migrations...")
        alembic_ini_path_db = project_root / "db" / "alembic.ini"

        if alembic_ini_path_db.exists():
            try:
                # Run alembic upgrade head from db directory (script_location in alembic.ini is relative)
                result = subprocess.run(
                    ["alembic", "upgrade", "head"],
                    cwd=str(project_root / "db"),
                    capture_output=True,
                    text=True,
                    env={
                        **os.environ,
                        "DATABASE_URL": database_url,
                    },  # Ensure DATABASE_URL is passed
                )
                if result.returncode == 0:
                    logger.info("✓ Alembic migrations completed successfully")
                    logger.info(f"Migration output: {result.stdout}")
                else:
                    logger.warning(f"Alembic migrations had issues: {result.stderr}")
                    logger.warning(f"Return code: {result.returncode}")
                    # Continue anyway and try SQLAlchemy Base.metadata.create_all
            except Exception as e:
                logger.warning(f"Could not run Alembic migrations: {e}")
                # Continue with SQLAlchemy fallback
        else:
            logger.warning(f"No alembic.ini found at {alembic_ini_path_db}")

        engine = create_engine(database_url, echo=False)

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")

        # Check if pg_trgm extension is available (PostgreSQL only)
        if database_url.startswith("postgresql"):
            try:
                with engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                    conn.commit()
                    logger.info("✓ pg_trgm extension enabled")
            except Exception as e:
                logger.warning(f"Could not enable pg_trgm extension: {e}")

        # Import models to ensure they're registered
        from core_infra.database import Base, User, FamilyMember
        from core_infra.enhanced_database_schema import EnhancedRecallDB

        # Create all tables
        Base.metadata.create_all(engine)
        logger.info("✓ All tables created")

        # Check inspector for created tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"✓ Created {len(tables)} tables: {', '.join(tables[:10])}")

        # Verify critical tables exist
        critical_tables = ["users", "recalls_enhanced"]
        missing_tables = [t for t in critical_tables if t not in tables]

        if missing_tables:
            logger.error(f"✗ Missing critical tables: {missing_tables}")
            return False

        logger.info("✓ All critical tables verified")

        # Check if severity column exists in recalls_enhanced
        if "recalls_enhanced" in tables:
            columns = [col["name"] for col in inspector.get_columns("recalls_enhanced")]
            if "severity" not in columns:
                logger.warning(
                    "⚠ 'severity' column missing from recalls_enhanced, adding it now"
                )
                try:
                    with engine.connect() as conn:
                        conn.execute(
                            text(
                                "ALTER TABLE recalls_enhanced ADD COLUMN IF NOT EXISTS severity VARCHAR(50)"
                            )
                        )
                        conn.execute(
                            text(
                                "ALTER TABLE recalls_enhanced ADD COLUMN IF NOT EXISTS risk_category VARCHAR(100)"
                            )
                        )
                        conn.execute(
                            text(
                                "UPDATE recalls_enhanced SET severity = 'medium' WHERE severity IS NULL"
                            )
                        )
                        conn.execute(
                            text(
                                "UPDATE recalls_enhanced SET risk_category = 'general' WHERE risk_category IS NULL"
                            )
                        )
                        conn.commit()
                        logger.info(
                            "✓ Added missing severity and risk_category columns"
                        )
                except Exception as e:
                    logger.warning(f"Could not add severity column: {e}")
            else:
                logger.info("✓ severity column exists in recalls_enhanced")

        logger.info("✅ Database initialization complete")
        return True

    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
