"""Comprehensive Pytest Configuration
Provides fixtures and test utilities for all test suites.
"""

import os
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"


@pytest.fixture(scope="session")
def test_database_engine():
    """Create a test database engine.

    Uses SQLite in-memory database for fast testing
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    from core_infra.database import Base

    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_database_engine) -> Generator[Session, None, None]:
    """Create a new database session for each test.

    Automatically rolls back after each test to ensure isolation
    """
    connection = test_database_engine.connect()
    transaction = connection.begin()

    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="module")
def test_app():
    """Create FastAPI test application.

    Returns a TestClient for making API requests
    """
    from api.app_factory import create_app

    app = create_app(environment="testing", enable_docs=True)

    # Override database dependency

    def override_get_db() -> None:
        # Use test database
        pass

    # Don't override for now - use actual implementation
    # app.dependency_overrides[get_db] = override_get_db

    return TestClient(app)


@pytest.fixture
def test_user(db_session) -> dict:
    """Create a test user.

    Returns user data dictionary
    """
    from core_infra.auth import pwd_context
    from core_infra.database import User

    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("TestPassword123!"),
        created_at=datetime.now(UTC),
        is_subscribed=False,
        email_verified=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "password": "TestPassword123!",
        "user_obj": user,
    }


@pytest.fixture
def test_subscriber(db_session) -> dict:
    """Create a test user with active subscription."""
    from core_infra.auth import pwd_context
    from core_infra.database import User

    user = User(
        email="subscriber@example.com",
        hashed_password=pwd_context.hash("TestPassword123!"),
        created_at=datetime.now(UTC),
        is_subscribed=True,
        subscription_tier="premium",
        subscription_start=datetime.now(UTC),
        subscription_end=datetime.now(UTC) + timedelta(days=30),
        email_verified=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "password": "TestPassword123!",
        "user_obj": user,
    }


@pytest.fixture
def test_admin(db_session) -> dict:
    """Create a test admin user."""
    from core_infra.auth import pwd_context
    from core_infra.database import User

    user = User(
        email="admin@example.com",
        hashed_password=pwd_context.hash("AdminPassword123!"),
        created_at=datetime.now(UTC),
        is_subscribed=True,
        is_admin=True,
        email_verified=True,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "password": "AdminPassword123!",
        "user_obj": user,
    }


@pytest.fixture
def auth_token(test_user) -> str:
    """Generate authentication token for test user."""
    from core_infra.auth import create_access_token

    return create_access_token(data={"sub": str(test_user["id"]), "email": test_user["email"]})


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Get authentication headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_recall(db_session) -> dict:
    """Create a test recall record."""
    from core_infra.database import RecallDB

    recall = RecallDB(
        recall_id="TEST-001",
        product_name="Test Baby Product",
        brand="Test Brand",
        hazard="Choking hazard",
        description="Test recall for automated testing",
        recall_date=datetime.now(UTC).date(),
        source_agency="CPSC",
        country="USA",
        url="https://example.com/recall/001",
    )

    db_session.add(recall)
    db_session.commit()
    db_session.refresh(recall)

    return {
        "recall_id": recall.recall_id,
        "product_name": recall.product_name,
        "recall_obj": recall,
    }


@pytest.fixture
def test_barcode_data() -> dict:
    """Generate test barcode data."""
    return {
        "valid_upc": "012345678905",
        "valid_ean": "4006381333931",
        "invalid_barcode": "INVALID123",
        "malicious_input": "'; DROP TABLE users; --",
    }


@pytest.fixture
def mock_external_api(monkeypatch) -> None:
    """Mock external API calls for testing."""

    class MockResponse:
        def __init__(self, json_data, status_code=200) -> None:
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    def mock_get(*args, **kwargs):
        return MockResponse({"data": "mocked"}, 200)

    def mock_post(*args, **kwargs):
        return MockResponse({"success": True}, 200)

    import httpx

    monkeypatch.setattr(httpx, "get", mock_get)
    monkeypatch.setattr(httpx, "post", mock_post)


@pytest.fixture
def temp_file():
    """Create a temporary file for upload testing."""
    with tempfile.NamedTemporaryFile(mode="w+b", delete=False, suffix=".jpg") as f:
        # Write some dummy image data
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # JPEG header
        f.write(b"\x00" * 1000)  # Dummy data
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


# Pytest configuration


def pytest_configure(config) -> None:
    """Configure pytest."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks tests as API tests")
    config.addinivalue_line("markers", "security: marks tests as security tests")


# Test utilities


class TestHelper:
    """Helper methods for testing."""

    @staticmethod
    def assert_success_response(response):
        """Assert that response is a successful API response."""
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        return data

    @staticmethod
    def assert_error_response(response, expected_status: int = 400):
        """Assert that response is an error response."""
        assert response.status_code == expected_status
        data = response.json()
        assert data.get("success") is False
        assert "error" in data
        return data

    @staticmethod
    def assert_unauthorized(response) -> None:
        """Assert that response is 401 Unauthorized."""
        assert response.status_code == 401

    @staticmethod
    def assert_forbidden(response) -> None:
        """Assert that response is 403 Forbidden."""
        assert response.status_code == 403

    @staticmethod
    def assert_not_found(response) -> None:
        """Assert that response is 404 Not Found."""
        assert response.status_code == 404

    @staticmethod
    def assert_validation_error(response) -> None:
        """Assert that response is 422 Validation Error."""
        assert response.status_code == 422


@pytest.fixture
def test_helper():
    """Provide TestHelper instance."""
    return TestHelper()


# Performance testing utilities


@pytest.fixture
def performance_tracker():
    """Track test performance metrics."""
    import time

    class PerformanceTracker:
        def __init__(self) -> None:
            self.start_time = None
            self.end_time = None

        def start(self) -> None:
            self.start_time = time.time()

        def stop(self) -> None:
            self.end_time = time.time()

        def duration(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0

        def assert_faster_than(self, threshold: float) -> None:
            duration = self.duration()
            assert duration < threshold, f"Test took {duration}s (max {threshold}s)"

    return PerformanceTracker()
