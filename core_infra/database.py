# core_infra/database.py
# Version 5.2 – Single subscription model with family profiles and allergies

import logging
import os
from contextlib import contextmanager
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker

# Initialize logger
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
# Test mode and explicit test DB URL support
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
DEFAULT_DATABASE_URL = os.getenv("DEFAULT_DATABASE_URL", "")

# Prefer an explicitly configured DATABASE_URL for production.
# For local tests, TEST_DATABASE_URL or TEST_MODE may enable SQLite.
DATABASE_URL = os.getenv("DATABASE_URL") or ""
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if TEST_MODE:
    # Allow explicit test database URL, fallback to in-memory SQLite
    if TEST_DATABASE_URL:
        DATABASE_URL = TEST_DATABASE_URL
    elif not DATABASE_URL:
        DATABASE_URL = "sqlite:///:memory:"
    print(f"TEST_MODE active: using {DATABASE_URL}")

if not DATABASE_URL:
    # In production/staging we require DATABASE_URL to be set to a PostgreSQL DSN
    logger.warning("DATABASE_URL not set. Application may fail to connect to a production database.")

# -------------------------------------------------------------------
# Engine & Session setup
# -------------------------------------------------------------------
connect_args = {}

# Determine the actual database URL to use (with fallback)
actual_db_url = DATABASE_URL or "sqlite:///:memory:"

# If using SQLite (only expected for TEST_MODE), we need check_same_thread
if actual_db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create engine. For production, DATABASE_URL should be a postgres+psycopg URL.
# Build engine kwargs conditionally based on database type
engine_kwargs = {
    "connect_args": connect_args,
    "echo": False,
    "pool_pre_ping": True,
    "future": True,
}

# Only add pool settings for non-SQLite databases (PostgreSQL supports pooling)
# Check the ACTUAL URL being used, not just DATABASE_URL which might be empty
if not actual_db_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 20)),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),
        }
    )

engine = create_engine(actual_db_url, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)

# Create Base BEFORE importing any models that use it
Base = declarative_base()

# -------------------------------------------------------------------
# ORM Models
# -------------------------------------------------------------------
# CROWN SAFE: Import hair product safety models (used by helper functions below)
from core_infra.crown_safe_models import HairProfileModel  # noqa: E402

# -------------------------------------------------------------------


class User(Base):
    """Crown Safe user model - authentication and subscription management"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False, default="", server_default="")
    is_subscribed = Column(Boolean, default=False, nullable=False)  # Single subscription status
    is_active = Column(Boolean, default=True, nullable=False)  # Account status

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email!r}, is_subscribed={self.is_subscribed})>"


class FamilyMember(Base):
    """Family member profile for multi-user household management"""

    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, nullable=False)  # Link to the main user account

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
        }

    def __repr__(self):
        return f"<FamilyMember(id={self.id}, name={self.name!r}, user_id={self.user_id})>"


class Allergy(Base):
    """Allergy tracking for family members"""

    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, index=True)
    allergen = Column(String, nullable=False)
    member_id = Column(Integer, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "allergen": self.allergen, "member_id": self.member_id}

    def __repr__(self):
        return f"<Allergy(id={self.id}, allergen={self.allergen!r}, member_id={self.member_id})>"


# -------------------------------------------------------------------
# COPILOT AUDIT FIX: Removed runtime schema modification functions
# These have been replaced with proper Alembic migrations:
# - alembic/versions/202410_04_add_user_columns.py
#
# If you need to modify the database schema:
# 1. Create a new Alembic migration: `alembic revision -m "description"`
# 2. Edit the generated file in alembic/versions/
# 3. Run the migration: `alembic upgrade head`
#
# DO NOT add runtime schema modifications here!
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def drop_all_tables_forcefully():
    """Drop ALL tables in the database, handling foreign key constraints."""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()

        if DATABASE_URL.startswith("postgresql"):
            for table in all_tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        else:
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table in all_tables:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
            conn.execute(text("PRAGMA foreign_keys = ON"))

        print(f"Dropped {len(all_tables)} tables")


# -------------------------------------------------------------------
# Create tables + run migrations
# -------------------------------------------------------------------
# Only create tables if explicitly requested (not on import)
# This prevents import errors when database is not available
if os.getenv("CREATE_TABLES_ON_IMPORT", "false").lower() == "true":
    Base.metadata.create_all(bind=engine)
    # COPILOT AUDIT FIX: Removed ensure_user_columns() call
    # Database schema changes now handled by Alembic migrations


# -------------------------------------------------------------------
# Session context manager
# -------------------------------------------------------------------
@contextmanager
def get_db_session(commit_on_exit=True, close_on_exit=True):
    db = SessionLocal()
    try:
        yield db
        if commit_on_exit:
            db.commit()
    except IntegrityError as e:
        db.rollback()
        # Handle duplicate key errors gracefully in test mode
        if TEST_MODE and "duplicate key" in str(e):
            print(f"Duplicate key in test mode: {e}")
        else:
            raise
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}", exc_info=True)
        raise
    finally:
        if close_on_exit:
            db.close()


# FastAPI Dependency for Database Sessions
def get_db():
    """
    FastAPI dependency for database sessions.
    Use this with Depends() in FastAPI endpoints.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_test_session():
    return SessionLocal()


def create_tables():
    """Create all database tables from all Base classes"""
    # Import all models to ensure they're registered with Base
    try:
        # Import models that use the main Base
        from api.models.chat_memory import (
            Conversation,  # noqa: F401
            ConversationMessage,  # noqa: F401
            UserProfile,  # noqa: F401
        )
        from api.models.user_report import UserReport
        from api.monitoring_scheduler import MonitoredProduct, MonitoringRun  # noqa: F401, F401
        from db.models.ingestion_run import IngestionRun  # noqa: F401
        from db.models.privacy_request import PrivacyRequest  # noqa: F401
        from db.models.scan_history import ScanHistory  # noqa: F401

        # Import risk assessment models to register them with Base.metadata
        try:
            import core_infra.risk_assessment_models  # noqa: F401
        except ImportError:
            pass  # Risk assessment models not available

        # Explicit attribute access ensures the class is registered without lint errors
        _ = UserReport.__tablename__

        # Create tables again to include any newly imported models
        Base.metadata.create_all(bind=engine)

    except ImportError as e:
        logger.warning(f"Some models could not be imported: {e}")

    logger.info("Database tables created successfully")

    # COPILOT AUDIT FIX: Removed ensure_user_columns() call
    # Database schema changes now handled by Alembic migrations


def drop_tables():
    """Drop all tables handling foreign key constraints."""
    drop_all_tables_forcefully()


def init_test_db():
    """Initialize test database - drops ALL tables and recreates."""
    if not TEST_MODE:
        raise RuntimeError("init_test_db only allowed in TEST_MODE")
    print("Initializing test database...")
    drop_all_tables_forcefully()
    create_tables()
    print("Test database initialized.")


def reset_database():
    """Reset database for tests."""
    if TEST_MODE:
        drop_all_tables_forcefully()
        create_tables()
    # COPILOT AUDIT FIX: ensure_user_columns() function removed as schema modifications
    # should be handled via Alembic migrations, not runtime code


# -------------------------------------------------------------------
# Test user creation/update
# -------------------------------------------------------------------
def ensure_test_users():
    """Create or update test users for testing."""
    if TEST_MODE:
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                # Clean up existing test users
                conn.execute(text("DELETE FROM users WHERE id IN (1, 2)"))
                print("Cleaned up existing test users")
        except Exception as e:
            print(f"Note: Could not clean up test users: {e}")

    # Create test users with different subscription states
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        if DATABASE_URL.startswith("postgresql"):
            stmt = text(
                """
                INSERT INTO users (id, email, stripe_customer_id, hashed_password, is_subscribed)
                VALUES 
                    (1, 'subscribed@test.com', NULL, 'testhash', true),
                    (2, 'unsubscribed@test.com', NULL, 'testhash', false)
                ON CONFLICT (id) 
                DO UPDATE SET
                    email = EXCLUDED.email,
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    hashed_password = EXCLUDED.hashed_password,
                    is_subscribed = EXCLUDED.is_subscribed
            """
            )
        else:
            stmt = text(
                """
                INSERT OR REPLACE INTO users 
                (id, email, stripe_customer_id, hashed_password, is_subscribed)
                VALUES 
                    (1, 'subscribed@test.com', NULL, 'testhash', 1),
                    (2, 'unsubscribed@test.com', NULL, 'testhash', 0)
            """
            )

        try:
            conn.execute(stmt)
            print("Test users created successfully")
        except IntegrityError as e:
            print(f"Error creating test users: {e}")


def create_or_update_test_user(user_id: int, email: str, is_subscribed: bool = False):
    """Helper to create or update a single test user."""
    with get_db_session() as db:
        try:
            user = db.query(User).filter_by(id=user_id).first()
            if user:
                # Update existing user
                user.email = email
                user.hashed_password = "testhash"
                user.is_subscribed = is_subscribed
                db.commit()
                print(f"Updated existing user {user_id}")
            else:
                # Create new user
                user = User(
                    id=user_id,
                    email=email,
                    hashed_password="testhash",
                    is_subscribed=is_subscribed,
                )
                db.add(user)
                db.commit()
                print(f"Created new user {user_id}")
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating/updating user {user_id}: {e}")


def setup_test_environment():
    """Set up test environment with sample users."""
    if not TEST_MODE:
        print("Not in TEST_MODE, skipping test setup")
        return

    print("Setting up test environment...")

    try:
        ensure_test_users()
    except Exception as e:
        print(f"Error in test setup: {e}")
        # Try full reset
        try:
            init_test_db()
            ensure_test_users()
        except Exception as e2:
            print(f"Could not reset database: {e2}")


# -------------------------------------------------------------------
# -------------------------------------------------------------------
# Crown Safe - Hair Profile Helper Functions
# -------------------------------------------------------------------
def create_hair_profile(
    user_id: int,
    hair_type: str,
    porosity: str,
    hair_state: dict | None = None,
    hair_goals: dict | None = None,
    sensitivities: dict | None = None,
):
    """Create a hair profile for a user."""
    with get_db_session() as db:
        profile = HairProfileModel(
            user_id=user_id,
            hair_type=hair_type,
            porosity=porosity,
            hair_state=hair_state or {},
            hair_goals=hair_goals or {},
            sensitivities=sensitivities or {},
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile


def get_user_hair_profile(user_id: int):
    """Get the hair profile for a user."""
    with get_db_session() as db:
        profile = db.query(HairProfileModel).filter_by(user_id=user_id).first()
        return profile


# -------------------------------------------------------------------
# Safety Hub - Safety Articles Model
# -------------------------------------------------------------------
class SafetyArticle(Base):
    """Stores educational safety articles and campaigns from trusted agencies"""

    __tablename__ = "safety_articles"

    id = Column(Integer, primary_key=True, index=True)
    # A unique ID we create or get from the source
    article_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    source_agency = Column(String, index=True, nullable=False)  # e.g., "CPSC", "AAP"
    publication_date = Column(Date, nullable=False)
    image_url = Column(String, nullable=True)  # URL for the article's main image
    article_url = Column(String, nullable=False)  # The direct URL to the original article
    # A flag to feature an article on the home screen
    is_featured = Column(Boolean, default=False, index=True)


# -------------------------------------------------------------------
# Recalls Model - for recalls table
# -------------------------------------------------------------------
class RecallDB(Base):
    """Model for recalls table - used for recall data storage and queries"""

    __tablename__ = "recalls"

    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(String, unique=True, index=True, nullable=False)
    product_name = Column(String, index=True, nullable=False)
    model_number = Column(String, index=True, nullable=True)
    brand = Column(String, nullable=True)
    country = Column(String, nullable=True)
    recall_date = Column(Date, index=True, nullable=False)
    hazard_description = Column(Text, nullable=True)
    manufacturer_contact = Column(String, nullable=True)
    upc = Column(String, index=True, nullable=True)
    source_agency = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    hazard = Column(Text, nullable=True)
    remedy = Column(Text, nullable=True)
    url = Column(String, nullable=True)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            result[c.name] = v.isoformat() if isinstance(v, date) else v
        return result

    def __repr__(self):
        return f"<RecallDB(id={self.id}, recall_id={self.recall_id!r})>"


# Alias for backwards compatibility with tests
LegacyRecallDB = RecallDB


# -------------------------------------------------------------------
# Test scaffolding
# -------------------------------------------------------------------
class DatabaseTestCase:
    @classmethod
    def setup_class(cls):
        os.environ["TEST_MODE"] = "true"
        cls.session = get_test_session()

    @classmethod
    def teardown_class(cls):
        if hasattr(cls, "session"):
            cls.session.close()

    def setup_method(self, method):
        if hasattr(self, "session"):
            self.session.rollback()

    def teardown_method(self, method):
        if hasattr(self, "session"):
            self.session.rollback()


# -------------------------------------------------------------------
# Standalone test runner
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("=== DB CONFIG ===")
    print("URL:", DATABASE_URL)
    print("Creating tables + migrations…")
    create_tables()
    print("Setting up test environment…")

    setup_test_environment()

    # Verify
    with get_db_session(commit_on_exit=False) as db:
        all_users = db.query(User).all()
        print(f"\nFound {len(all_users)} users in database:")
        for u in all_users:
            print(f"  {u}")

        # LEGACY BABY CODE: Family/allergy tests commented out
        # Test adding family members with allergies
        # print("\nTesting family members and allergies...")
        # member_id = add_family_member(1, "Child 1", ["peanuts", "milk"])
        # print(f"Added family member with ID: {member_id}")
        #
        # allergies = get_family_allergies(1)
        # print(f"Family allergies for user 1: {allergies}")

        # CROWN SAFE: Test hair profile creation
        print("\nTesting Crown Safe hair profile creation...")
        test_profile = create_hair_profile(
            user_id=1,
            hair_type="4C",
            porosity="High",
            hair_state={"dryness": True, "breakage": False},
            hair_goals={"moisture_retention": True, "length_retention": True},
        )
        print(f"Created hair profile: ID={test_profile.id}, Type={test_profile.hair_type}")

        # Retrieve profile
        profile = get_user_hair_profile(1)
        if profile:
            print(f"Retrieved hair profile: {profile.hair_type}, {profile.porosity} porosity")
        else:
            print("No hair profile found for user 1")

    print("=== Done ===")
