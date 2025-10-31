"""Task 16: Secure Database Connection with Read-Only User
Implements separate connections for read and write operations.
"""

import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# ========================= CONNECTION STRINGS =========================


def get_database_url(mode: str = "readonly") -> str:
    """Get database URL based on operation mode.

    Modes:
    - readonly: For SELECT queries (default)
    - write: For INSERT, UPDATE, DELETE
    - admin: For migrations and DDL
    """
    base_url = os.environ.get("DATABASE_URL", "")

    if mode == "readonly":
        # Try dedicated readonly URL first
        readonly_url = os.environ.get("DATABASE_URL_READONLY")
        if readonly_url:
            logger.debug("Using dedicated readonly database connection")
            return readonly_url

        # Fallback to main URL (for backwards compatibility)
        logger.warning("No DATABASE_URL_READONLY found, using main DATABASE_URL")
        return base_url

    if mode == "write":
        # Use main database URL for writes
        return base_url

    if mode == "admin":
        # Try dedicated admin URL for migrations
        admin_url = os.environ.get("DATABASE_URL_ADMIN")
        if admin_url:
            logger.debug("Using admin database connection")
            return admin_url

        # Fallback to main URL
        logger.warning("No DATABASE_URL_ADMIN found, using main DATABASE_URL")
        return base_url

    raise ValueError(f"Invalid database mode: {mode}")


# ========================= ENGINE CONFIGURATION =========================

# Connection pool settings for different user types
READONLY_POOL_SETTINGS = {
    "pool_size": 20,  # More connections for read-heavy workload
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600,  # Recycle connections after 1 hour
    "pool_pre_ping": True,  # Test connections before using
}

WRITE_POOL_SETTINGS = {
    "pool_size": 10,  # Fewer connections for writes
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

ADMIN_POOL_SETTINGS = {
    "pool_size": 2,  # Minimal connections for admin
    "max_overflow": 3,
    "pool_timeout": 30,
    "pool_recycle": 300,  # Recycle more frequently
    "pool_pre_ping": True,
}


# ========================= ENGINE CREATION =========================


def create_secure_engine(mode: str = "readonly") -> Engine:
    """Create a secure SQLAlchemy engine with appropriate settings."""
    database_url = get_database_url(mode)

    if not database_url:
        raise ValueError(f"No database URL configured for mode: {mode}")

    # Select pool settings based on mode
    if mode == "readonly":
        pool_settings = READONLY_POOL_SETTINGS
        connect_args = {
            "options": "-c default_transaction_read_only=on -c statement_timeout=30000",  # 30s timeout
        }
    elif mode == "write":
        pool_settings = WRITE_POOL_SETTINGS
        connect_args = {"options": "-c statement_timeout=60000"}  # 60s timeout for writes
    else:  # admin
        pool_settings = ADMIN_POOL_SETTINGS
        connect_args = {}

    # Create engine
    engine = create_engine(database_url, poolclass=QueuePool, connect_args=connect_args, **pool_settings)

    # Add event listeners for monitoring
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record) -> None:
        """Log new connections."""
        connection_record.info["connect_time"] = time.time()
        logger.debug(f"New {mode} database connection established")

    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy) -> None:
        """Monitor connection checkouts."""
        # Log long-lived connections
        if "connect_time" in connection_record.info:
            age = time.time() - connection_record.info["connect_time"]
            if age > 3600:  # 1 hour
                logger.warning(f"Long-lived {mode} connection: {age:.0f} seconds")

    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record) -> None:
        """Reset connection state on checkin."""
        if mode == "readonly":
            # Ensure readonly transaction mode
            with dbapi_conn.cursor() as cursor:
                cursor.execute("SET default_transaction_read_only = on")

    return engine


# ========================= SINGLETON ENGINES =========================


class DatabaseEngines:
    """Singleton to manage database engines."""

    _instance = None
    _readonly_engine: Engine | None = None
    _write_engine: Engine | None = None
    _admin_engine: Engine | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def readonly(self) -> Engine:
        """Get or create readonly engine."""
        if self._readonly_engine is None:
            self._readonly_engine = create_secure_engine("readonly")
            logger.info("Created readonly database engine")
        return self._readonly_engine

    @property
    def write(self) -> Engine:
        """Get or create write engine."""
        if self._write_engine is None:
            self._write_engine = create_secure_engine("write")
            logger.info("Created write database engine")
        return self._write_engine

    @property
    def admin(self) -> Engine:
        """Get or create admin engine."""
        if self._admin_engine is None:
            self._admin_engine = create_secure_engine("admin")
            logger.info("Created admin database engine")
        return self._admin_engine

    def dispose_all(self) -> None:
        """Dispose all engines (cleanup)."""
        if self._readonly_engine:
            self._readonly_engine.dispose()
            self._readonly_engine = None

        if self._write_engine:
            self._write_engine.dispose()
            self._write_engine = None

        if self._admin_engine:
            self._admin_engine.dispose()
            self._admin_engine = None

        logger.info("All database engines disposed")


# Global instance
db_engines = DatabaseEngines()


# ========================= SESSION FACTORIES =========================

# Create session factories
ReadOnlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engines.readonly)

WriteSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=db_engines.write)

AdminSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=db_engines.admin)


# ========================= CONTEXT MANAGERS =========================


@contextmanager
def get_readonly_session() -> Generator[Session, None, None]:
    """Context manager for readonly database sessions
    Use for all SELECT queries.
    """
    session = ReadOnlySessionLocal()
    try:
        # Ensure readonly mode
        session.execute("SET default_transaction_read_only = on")
        yield session
    except Exception as e:
        logger.exception(f"Readonly session error: {e}")
        raise
    finally:
        session.close()


@contextmanager
def get_write_session() -> Generator[Session, None, None]:
    """Context manager for write database sessions
    Use for INSERT, UPDATE, DELETE operations.
    """
    session = WriteSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception(f"Write session error: {e}")
        raise
    finally:
        session.close()


@contextmanager
def get_admin_session() -> Generator[Session, None, None]:
    """Context manager for admin database sessions
    Use for DDL operations and migrations only.
    """
    session = AdminSessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception(f"Admin session error: {e}")
        raise
    finally:
        session.close()


# ========================= DEPENDENCY INJECTION FOR FASTAPI =========================


def get_db_readonly() -> Generator[Session, None, None]:
    """FastAPI dependency for readonly database sessions."""
    with get_readonly_session() as session:
        yield session


def get_db_write() -> Generator[Session, None, None]:
    """FastAPI dependency for write database sessions."""
    with get_write_session() as session:
        yield session


def get_db_admin() -> Generator[Session, None, None]:
    """FastAPI dependency for admin database sessions."""
    with get_admin_session() as session:
        yield session


# ========================= QUERY HELPERS =========================


class SecureQuery:
    """Helper class for secure database queries."""

    @staticmethod
    def fetch_one(query: str, params: dict = None) -> Any | None:
        """Execute a SELECT query and fetch one result."""
        with get_readonly_session() as session:
            result = session.execute(query, params or {})
            return result.first()

    @staticmethod
    def fetch_all(query: str, params: dict = None) -> list:
        """Execute a SELECT query and fetch all results."""
        with get_readonly_session() as session:
            result = session.execute(query, params or {})
            return result.fetchall()

    @staticmethod
    def execute_write(query: str, params: dict = None) -> int:
        """Execute a write query (INSERT, UPDATE, DELETE)."""
        with get_write_session() as session:
            result = session.execute(query, params or {})
            return result.rowcount

    @staticmethod
    def execute_admin(query: str, params: dict = None) -> Any:
        """Execute an admin query (DDL)."""
        with get_admin_session() as session:
            result = session.execute(query, params or {})
            return result


# ========================= MIGRATION HELPER =========================


def migrate_to_secure_database() -> None:
    """Migrate existing code to use secure database connections."""
    print("Migrating to secure database configuration...")

    # Test connections
    try:
        # Test readonly
        with get_readonly_session() as session:
            result = session.execute("SELECT 1")
            print("✅ Readonly connection successful")

        # Test write
        with get_write_session() as session:
            # Don't actually write, just test connection
            result = session.execute("SELECT current_user")
            print(f"✅ Write connection successful (user: {result.scalar()})")

        # Test admin (optional)
        try:
            with get_admin_session() as session:
                result = session.execute("SELECT current_user")
                print(f"✅ Admin connection successful (user: {result.scalar()})")
        except Exception as e:
            print(f"⚠️ Admin connection not configured: {e}")

        print("\n✅ Secure database configuration is ready!")
        print("\nUsage in your code:")
        print("  - For SELECT queries: use get_readonly_session()")
        print("  - For INSERT/UPDATE/DELETE: use get_write_session()")
        print("  - For migrations: use get_admin_session()")

    except Exception as e:
        print(f"❌ Error testing secure connections: {e}")
        print("\nPlease ensure you have set up the following environment variables:")
        print("  - DATABASE_URL_READONLY: postgresql://babyshield_readonly:PASSWORD@host/db")
        print("  - DATABASE_URL: postgresql://babyshield_app:PASSWORD@host/db")
        print("  - DATABASE_URL_ADMIN: postgresql://babyshield_admin:PASSWORD@host/db")


# ========================= USAGE EXAMPLES =========================

"""
# Example 1: FastAPI endpoint with readonly access
from fastapi import Depends
from sqlalchemy.orm import Session

# REMOVED FOR CROWN SAFE: Recall endpoints no longer applicable
# @app.get("/api/v1/recalls/{recall_id}")
# async def get_recall(recall_id: str, db: Session = Depends(get_db_readonly)):
#     # RecallDB removed - Crown Safe uses HairProductModel
#     pass


# Example 2: FastAPI endpoint with write access
@app.post("/api/v1/users")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db_write)  # Use write access
):
    new_user = User(**user_data.dict())
    db.add(new_user)
    db.commit()
    return new_user


# REMOVED FOR CROWN SAFE: Recall background tasks no longer applicable
# def analyze_recalls():
#     # RecallDB removed - Crown Safe uses HairProductModel
#     pass
#
# def update_risk_scores():
#     # RecallDB removed - Crown Safe uses hair product safety scoring
#     pass
        
        session.commit()
"""

if __name__ == "__main__":
    # Test the secure database configuration
    migrate_to_secure_database()
