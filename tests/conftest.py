import os
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Provide FastAPI test client"""
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TEST_MODE"] = "true"

    # Import after setting environment
    from core_infra.database import Base, SessionLocal, engine
    from api.models.user_report import UserReport

    # Ensure the user_reports table exists for sqlite-backed tests
    Base.metadata.create_all(bind=engine, tables=[UserReport.__table__])
    # Reset table contents so rate limiting tests start clean
    with SessionLocal() as session:
        session.query(UserReport).delete()
        session.commit()
    from api.main_crownsafe import app

    return TestClient(app)


@pytest.fixture
def db_session():
    """Provide database session for tests"""
    from core_infra.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user for authentication tests"""
    from core_infra.database import User
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Create test user
    test_user = User(
        id=999999,  # Use high ID to avoid conflicts
        email="test_security@example.com",
        hashed_password=pwd_context.hash("TestPass123!"),
        is_subscribed=True,
    )

    # Try to add user, but skip if it already exists
    try:
        existing = db_session.query(User).filter(User.id == 999999).first()
        if not existing:
            db_session.add(test_user)
            db_session.commit()
            db_session.refresh(test_user)
        else:
            test_user = existing
    except Exception:
        db_session.rollback()
        # User might already exist, try to fetch it
        test_user = db_session.query(User).filter(User.id == 999999).first()
        if not test_user:
            pytest.skip("Could not create test user")

    yield test_user

    # Cleanup (optional - can be skipped for test performance)
    try:
        db_session.delete(test_user)
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def auth_token(test_user):
    """Generate authentication token for test user"""
    try:
        from core_infra.auth import create_access_token

        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )
        return token
    except ImportError:
        # If auth module not available, return a mock token
        return "mock_token_for_testing"


@pytest.fixture
def valid_token():
    """Generate valid authentication token"""
    try:
        from core_infra.auth import create_access_token

        token = create_access_token(
            data={"sub": "999999", "email": "test_security@example.com"}
        )
        return token
    except Exception:
        # Return a mock token if anything fails
        return "mock_token_for_testing"


@pytest.fixture
def expired_token():
    """Generate an expired authentication token"""
    try:
        from core_infra.auth import create_access_token
        from datetime import timedelta

        # Create token that expired 1 hour ago
        token = create_access_token(
            data={"sub": "999", "email": "expired@example.com"},
            expires_delta=timedelta(hours=-1),
        )
        return token
    except Exception:
        return "expired_mock_token"


@pytest.fixture
def user1_token(test_user):
    """Generate token for user 1 (test_user)"""
    try:
        from core_infra.auth import create_access_token

        token = create_access_token(
            data={"sub": str(test_user.id), "email": test_user.email}
        )
        return token
    except Exception:
        return "user1_mock_token"


@pytest.fixture
def user2_id():
    """Return a different user ID for authorization tests"""
    return 9999  # Different from test_user.id (which is typically 1)


@pytest.fixture
def regular_user_token():
    """Generate token for a regular (non-admin) user"""
    try:
        from core_infra.auth import create_access_token

        token = create_access_token(
            data={"sub": "222222", "email": "regular@example.com", "is_admin": False}
        )
        return token
    except Exception:
        return "regular_user_mock_token"


def pytest_collection_modifyitems(config, items):
    """Skip tests that require unavailable dependencies"""
    skip_locust = pytest.mark.skip(reason="locust not installed")
    skip_mcp = pytest.mark.skip(reason="mcp_client_library not available")

    for item in items:
        # Skip performance tests if locust not available
        if "performance" in item.keywords:
            try:
                import locust
            except ImportError:
                item.add_marker(skip_locust)

        # Skip tests that need mcp_client_library
        if "mcp" in str(item.fspath).lower():
            try:
                from core_infra.mcp_client_library import client
            except ImportError:
                item.add_marker(skip_mcp)
