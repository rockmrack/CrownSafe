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
    from api.main_babyshield import app

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
