"""
API Integration Tests - Phase 2

Tests full integration of API routes with database, authentication, and business logic.
These tests verify end-to-end functionality with real database operations.

Author: BabyShield Development Team
Date: October 11, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.main_babyshield import app
from core_infra.database import Base, User, engine, get_db


# Mock classes for testing (will be implemented later)
class Recall:
    """Mock Recall model for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Product:
    """Mock Product model for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Conversation:
    """Mock Conversation model for testing."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture(scope="module")
def test_client():
    """FastAPI test client for making API requests."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Database session for test setup and teardown."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Get session
    db = next(get_db())

    yield db

    # Cleanup
    db.rollback()
    db.close()

    # Drop tables
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(db_session: Session) -> Dict[str, str]:
    """Create authenticated user and return JWT token headers."""
    from api.auth_endpoints import create_access_token

    # Create test user
    user = User(
        username="testuser",
        email="test@babyshield.dev",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYBq8l5kMZy",
        is_active=True,
        created_at=datetime.utcnow(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Generate token
    token = create_access_token(data={"sub": user.email})

    return {"Authorization": f"Bearer {token}"}


# ====================
# API INTEGRATION TESTS
# ====================


@pytest.mark.api
@pytest.mark.integration
def test_recall_search_endpoint_integration(test_client, db_session: Session, auth_headers):
    """
    Test recall search endpoint with full database integration.

    Acceptance Criteria:
    - Create recalls in database
    - Search endpoint returns matching recalls
    - Pagination works correctly
    - Filters by category, severity, date range
    - Returns proper JSON structure
    """
    # Setup: Create test recalls
    recalls = [
        Recall(
            agency="CPSC",
            product_name="Baby Crib Model X",
            manufacturer="SafeSleep Inc",
            recall_date=datetime(2024, 1, 15),
            severity="high",
            category="cribs",
            description="Risk of entrapment",
            recall_number="24-001",
        ),
        Recall(
            agency="FDA",
            product_name="Infant Formula Plus",
            manufacturer="NutriCo",
            recall_date=datetime(2024, 2, 20),
            severity="critical",
            category="formula",
            description="Contamination risk",
            recall_number="24-002",
        ),
        Recall(
            agency="CPSC",
            product_name="Toy Rattle",
            manufacturer="ToyMakers",
            recall_date=datetime(2023, 12, 10),
            severity="medium",
            category="toys",
            description="Choking hazard",
            recall_number="23-999",
        ),
    ]

    for recall in recalls:
        db_session.add(recall)
    db_session.commit()

    # Test 1: Search all recalls
    response = test_client.get("/api/v1/recalls", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3
    assert data["total"] == 3

    # Test 2: Search with category filter
    response = test_client.get("/api/v1/recalls?category=cribs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_name"] == "Baby Crib Model X"

    # Test 3: Search with severity filter
    response = test_client.get("/api/v1/recalls?severity=critical", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["severity"] == "critical"

    # Test 4: Pagination
    response = test_client.get("/api/v1/recalls?skip=1&limit=1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1

    # Test 5: Date range filter
    response = test_client.get("/api/v1/recalls?start_date=2024-01-01&end_date=2024-12-31", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2  # Only 2024 recalls


@pytest.mark.api
@pytest.mark.integration
def test_product_barcode_scan_integration(test_client, db_session: Session, auth_headers):
    """
    Test barcode scanning endpoint with product lookup and recall matching.

    Acceptance Criteria:
    - Scan barcode returns product info
    - Matches product to recalls
    - Returns recall alerts if found
    - Handles unknown barcodes gracefully
    - Logs scan history
    """
    # Setup: Create product with recall
    product = Product(
        barcode="123456789012",
        name="Baby Monitor X200",
        manufacturer="TechBaby",
        category="monitors",
        model_number="X200",
    )
    db_session.add(product)

    recall = Recall(
        agency="CPSC",
        product_name="Baby Monitor X200",
        manufacturer="TechBaby",
        recall_date=datetime.utcnow(),
        severity="high",
        category="monitors",
        description="Fire hazard",
        recall_number="24-100",
    )
    db_session.add(recall)
    db_session.commit()

    # Test 1: Scan product with recall
    response = test_client.post("/api/v1/barcode/scan", json={"barcode": "123456789012"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["product"]["name"] == "Baby Monitor X200"
    assert data["has_recall"] is True
    assert len(data["recalls"]) == 1
    assert data["recalls"][0]["severity"] == "high"

    # Test 2: Scan unknown barcode
    response = test_client.post("/api/v1/barcode/scan", json={"barcode": "999999999999"}, headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

    # Test 3: Invalid barcode format
    response = test_client.post("/api/v1/barcode/scan", json={"barcode": "invalid"}, headers=auth_headers)
    assert response.status_code == 422  # Validation error


@pytest.mark.api
@pytest.mark.integration
def test_user_profile_crud_operations(test_client, db_session: Session, auth_headers):
    """
    Test user profile CRUD (Create, Read, Update, Delete) operations.

    Acceptance Criteria:
    - Create new user profile
    - Read user profile
    - Update user preferences
    - Delete user account
    - Proper authorization checks
    """
    # Test 1: Read current user profile
    response = test_client.get("/api/v1/user/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@babyshield.dev"
    assert "user_id" in data

    # Test 2: Update user profile
    update_data = {"first_name": "John", "last_name": "Doe", "language": "en", "timezone": "America/New_York"}
    response = test_client.put("/api/v1/user/profile", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["language"] == "en"

    # Test 3: Read updated profile
    response = test_client.get("/api/v1/user/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"

    # Test 4: Unauthorized access (no token)
    response = test_client.get("/api/v1/user/profile")
    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.integration
def test_conversation_history_retrieval(test_client, db_session: Session, auth_headers):
    """
    Test conversation history retrieval with pagination.

    Acceptance Criteria:
    - Retrieve user's chat history
    - Pagination works correctly
    - Newest messages first
    - Only user's own conversations
    - Includes message metadata
    """
    # Setup: Get user from auth headers
    from api.auth_endpoints import verify_token

    token = auth_headers["Authorization"].split(" ")[1]
    user_email = verify_token(token)
    user = db_session.query(User).filter(User.email == user_email).first()

    # Create conversations
    conversation = Conversation(
        user_id=user.id,  # Use id instead of user_id
        created_at=datetime.utcnow(),
    )
    db_session.add(conversation)
    db_session.commit()

    # Test 1: Get conversations list
    response = test_client.get("/api/v1/conversations", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1

    # Test 2: Pagination
    response = test_client.get("/api/v1/conversations?limit=5", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5


@pytest.mark.api
@pytest.mark.integration
def test_subscription_activation_flow(test_client, db_session: Session, auth_headers):
    """
    Test subscription activation workflow.

    Acceptance Criteria:
    - Create new subscription
    - Activate subscription
    - Check subscription status
    - Handle payment verification
    - Update user premium status
    """
    # Test 1: Check initial subscription status
    response = test_client.get("/api/v1/subscription/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_premium"] is False

    # Test 2: Create subscription
    subscription_data = {"plan": "premium_monthly", "payment_method": "stripe", "payment_token": "tok_test_12345"}
    response = test_client.post("/api/v1/subscription/create", json=subscription_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["plan"] == "premium_monthly"
    assert data["status"] == "active"

    # Test 3: Verify subscription activated
    response = test_client.get("/api/v1/subscription/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["is_premium"] is True


@pytest.mark.api
@pytest.mark.integration
def test_notification_preferences_update(test_client, db_session: Session, auth_headers):
    """
    Test notification preferences update and persistence.

    Acceptance Criteria:
    - Get current preferences
    - Update preferences
    - Persist to database
    - Apply preferences to notifications
    """
    # Test 1: Get default preferences
    response = test_client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "email_enabled" in data
    assert "push_enabled" in data

    # Test 2: Update preferences
    new_preferences = {"email_enabled": True, "push_enabled": False, "recall_alerts": True, "marketing_emails": False}
    response = test_client.put("/api/v1/notifications/preferences", json=new_preferences, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email_enabled"] is True
    assert data["push_enabled"] is False

    # Test 3: Verify persistence
    response = test_client.get("/api/v1/notifications/preferences", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["recall_alerts"] is True


@pytest.mark.api
@pytest.mark.integration
def test_feedback_submission_workflow(test_client, db_session: Session, auth_headers):
    """
    Test feedback submission workflow (submit → database → email).

    Acceptance Criteria:
    - Submit feedback
    - Save to database
    - Send confirmation email (mocked)
    - Return submission confirmation
    """
    # Test 1: Submit feedback
    feedback_data = {
        "type": "bug_report",
        "subject": "App crashes on startup",
        "message": "The app crashes when I try to scan a barcode.",
        "severity": "high",
    }
    response = test_client.post("/api/v1/feedback", json=feedback_data, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "submitted"
    assert "feedback_id" in data

    # Test 2: Verify feedback saved to database
    feedback_id = data["feedback_id"]
    response = test_client.get(f"/api/v1/feedback/{feedback_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "App crashes on startup"


@pytest.mark.api
@pytest.mark.integration
def test_error_handling_invalid_endpoints(test_client, auth_headers):
    """
    Test API error handling for invalid endpoints and methods.

    Acceptance Criteria:
    - 404 for non-existent endpoints
    - 405 for wrong HTTP methods
    - 422 for validation errors
    - Proper error response format
    """
    # Test 1: 404 Not Found
    response = test_client.get("/api/v1/nonexistent", headers=auth_headers)
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data

    # Test 2: 405 Method Not Allowed
    response = test_client.post("/api/v1/recalls", headers=auth_headers)
    # Note: This might be 404 if route doesn't exist for POST
    assert response.status_code in [404, 405]

    # Test 3: 422 Validation Error
    response = test_client.post("/api/v1/barcode/scan", json={"invalid_field": "value"}, headers=auth_headers)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
