# core_infra/database.py
# Version 5.2 – Single subscription model with family profiles and allergies

import os
from contextlib import contextmanager
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,  # Added for relationships
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    declarative_base,
    relationship,
    sessionmaker,
)  # Added relationship

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
load_dotenv()
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
DEFAULT_DATABASE_URL = "sqlite:///:memory:"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

if TEST_MODE and DATABASE_URL == DEFAULT_DATABASE_URL:
    DATABASE_URL = "sqlite:///test_db.sqlite"
    print(f"TEST_MODE active: using {DATABASE_URL}")

# -------------------------------------------------------------------
# Engine & Session setup
# -------------------------------------------------------------------
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,
        future=True,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", 10)),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 20)),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", 30)),
        future=True,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
    future=True,
)

# ============================================================================
# STANDALONE TEST UTILITY BASE (INTENTIONALLY SEPARATE)
# ============================================================================
# This file is a standalone test/debug utility that can be run directly.
# It has its own Base = declarative_base() by design for complete isolation.
# This is NOT a mistake - do not import production Base here.
# Production Base is in core_infra/database.py - this is separate by design.
# ============================================================================
Base = declarative_base()


# -------------------------------------------------------------------
# ORM Models
# -------------------------------------------------------------------
class RecallDB(Base):
    __tablename__ = "recalls"

    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(String, unique=True, index=True, nullable=False)
    product_name = Column(String, index=True, nullable=False)
    model_number = Column(String, index=True, nullable=True)  # NEW: Model number for precise matching
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
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            result[c.name] = v.isoformat() if isinstance(v, date) else v
        return result

    def __repr__(self):
        return f"<RecallDB(id={self.id}, recall_id={self.recall_id!r})>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False, default="", server_default="")
    is_subscribed = Column(Boolean, default=False, nullable=False)  # Single subscription status
    is_pregnant = Column(Boolean, default=False, nullable=False)

    # Relationship to family members
    family_members = relationship("FamilyMember", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return (
            f"<User(id={self.id}, email={self.email!r}, "
            f"is_subscribed={self.is_subscribed}, is_pregnant={self.is_pregnant})>"
        )


class FamilyMember(Base):
    __tablename__ = "family_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))  # Link to the main user account

    # Relationships
    user = relationship("User", back_populates="family_members")
    allergies = relationship("Allergy", back_populates="family_member", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "allergies": [allergy.allergen for allergy in self.allergies],
        }

    def __repr__(self):
        return f"<FamilyMember(id={self.id}, name={self.name!r}, user_id={self.user_id})>"


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True, index=True)
    allergen = Column(String, nullable=False)
    member_id = Column(Integer, ForeignKey("family_members.id"))

    # Relationships
    family_member = relationship("FamilyMember", back_populates="allergies")

    def to_dict(self) -> dict:
        return {"id": self.id, "allergen": self.allergen, "member_id": self.member_id}

    def __repr__(self):
        return f"<Allergy(id={self.id}, allergen={self.allergen!r}, member_id={self.member_id})>"


# -------------------------------------------------------------------
# Migration: add missing columns and handle existing ones
# -------------------------------------------------------------------
def ensure_user_columns():
    """Add missing columns and handle deprecated columns from users table."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return

    existing = {col["name"] for col in insp.get_columns("users")}
    migrations = []

    # Add new columns only if they don't exist
    if "hashed_password" not in existing:
        migrations.append("ALTER TABLE users ADD COLUMN hashed_password TEXT NOT NULL DEFAULT ''")
    if "is_pregnant" not in existing:
        migrations.append("ALTER TABLE users ADD COLUMN is_pregnant BOOLEAN DEFAULT FALSE")

    # Handle is_subscribed column
    if "is_subscribed" not in existing:
        if "is_premium" in existing:
            # Migrate from is_premium to is_subscribed
            migrations.append("ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT FALSE")
            migrations.append("UPDATE users SET is_subscribed = is_premium")
        else:
            # Just add is_subscribed
            migrations.append("ALTER TABLE users ADD COLUMN is_subscribed BOOLEAN DEFAULT FALSE")

    # Apply migrations
    if migrations:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for ddl in migrations:
                try:
                    print(f"Applying migration: {ddl}")
                    conn.execute(text(ddl))
                except Exception as e:
                    print(f"Migration already applied or error: {e}")
        print("User table migrations completed.")

    # Handle column cleanup separately
    cleanup_deprecated_columns()


def cleanup_deprecated_columns():
    """Remove deprecated columns if they exist."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return

    existing = {col["name"] for col in insp.get_columns("users")}

    # Only try to drop is_premium if it exists and we're on PostgreSQL
    if "is_premium" in existing and DATABASE_URL.startswith("postgresql"):
        try:
            with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text("ALTER TABLE users DROP COLUMN is_premium"))
                print("Removed deprecated is_premium column")
        except Exception as e:
            print(f"Note: Could not remove is_premium column: {e}")


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
Base.metadata.create_all(bind=engine)
ensure_user_columns()


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
    except Exception:
        db.rollback()
        raise
    finally:
        if close_on_exit:
            db.close()


def get_test_session():
    return SessionLocal()


def create_tables():
    Base.metadata.create_all(bind=engine)
    ensure_user_columns()


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
    else:
        ensure_user_columns()


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
                INSERT INTO users (id, email, stripe_customer_id, hashed_password, is_subscribed, is_pregnant)
                VALUES 
                    (1, 'subscribed@test.com', NULL, 'testhash', true, true),
                    (2, 'unsubscribed@test.com', NULL, 'testhash', false, false)
                ON CONFLICT (id) 
                DO UPDATE SET
                    email = EXCLUDED.email,
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    hashed_password = EXCLUDED.hashed_password,
                    is_subscribed = EXCLUDED.is_subscribed,
                    is_pregnant = EXCLUDED.is_pregnant
            """
            )
        else:
            stmt = text(
                """
                INSERT OR REPLACE INTO users (id, email, stripe_customer_id, hashed_password, is_subscribed, is_pregnant)  # noqa: E501
                VALUES 
                    (1, 'subscribed@test.com', NULL, 'testhash', 1, 1),
                    (2, 'unsubscribed@test.com', NULL, 'testhash', 0, 0)
            """
            )

        try:
            conn.execute(stmt)
            print("Test users created successfully")
        except IntegrityError as e:
            print(f"Error creating test users: {e}")


def create_or_update_test_user(user_id: int, email: str, is_subscribed: bool = False, is_pregnant: bool = False):
    """Helper to create or update a single test user."""
    with get_db_session() as db:
        try:
            user = db.query(User).filter_by(id=user_id).first()
            if user:
                # Update existing user
                user.email = email
                user.hashed_password = "testhash"
                user.is_subscribed = is_subscribed
                user.is_pregnant = is_pregnant
                db.commit()
                print(f"Updated existing user {user_id}")
            else:
                # Create new user
                user = User(
                    id=user_id,
                    email=email,
                    hashed_password="testhash",
                    is_subscribed=is_subscribed,
                    is_pregnant=is_pregnant,
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
# Helper functions for family and allergy management
# -------------------------------------------------------------------
def add_family_member(user_id: int, name: str, allergies: list = None):
    """Add a family member with optional allergies."""
    with get_db_session() as db:
        member = FamilyMember(name=name, user_id=user_id)
        db.add(member)
        db.flush()  # Get the member ID

        if allergies:
            for allergen in allergies:
                allergy = Allergy(allergen=allergen, member_id=member.id)
                db.add(allergy)

        db.commit()
        return member.id


def get_family_allergies(user_id: int):
    """Get all family members and their allergies for a user."""
    with get_db_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return []

        result = []
        for member in user.family_members:
            result.append(
                {
                    "member_id": member.id,
                    "name": member.name,
                    "allergies": [allergy.allergen for allergy in member.allergies],
                }
            )
        return result


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

        # Test adding family members with allergies
        print("\nTesting family members and allergies...")
        member_id = add_family_member(1, "Child 1", ["peanuts", "milk"])
        print(f"Added family member with ID: {member_id}")

        allergies = get_family_allergies(1)
        print(f"Family allergies for user 1: {allergies}")

    print("=== Done ===")
