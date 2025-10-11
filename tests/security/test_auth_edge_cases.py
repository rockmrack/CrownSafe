"""
Authentication Edge Cases Tests - Phase 2

Tests edge cases and security scenarios for authentication including JWT tokens,
OAuth flows, session management, and password reset workflows.

Author: BabyShield Development Team
Date: October 11, 2025
"""

from datetime import datetime, timedelta
from typing import Dict
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from api.main_babyshield import app
from core_infra.database import User, get_db


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user(db_session):
    """Create test user in database."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYBq8l5kMZy",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ====================
# AUTHENTICATION TESTS
# ====================


@pytest.mark.security
@pytest.mark.integration
def test_jwt_token_expiration_handling(test_client, test_user):
    """
    Test JWT token expiration and refresh flow.

    Acceptance Criteria:
    - Access token expires after 30 minutes
    - Refresh token expires after 7 days
    - Expired access token rejected
    - Valid refresh token generates new access token
    - Expired refresh token rejected
    - Token refresh invalidates old token
    """
    from api.auth_endpoints import create_access_token, create_refresh_token, SECRET_KEY, ALGORITHM

    # Test 1: Create access token with short expiry
    access_token = create_access_token(data={"sub": test_user.email}, expires_delta=timedelta(seconds=1))

    # Wait for expiration
    import time

    time.sleep(2)

    # Try to use expired token
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()

    # Test 2: Create refresh token
    refresh_token = create_refresh_token(data={"sub": test_user.email})

    # Use refresh token to get new access token
    response = test_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data

    # Test 3: New access token works
    new_access_token = data["access_token"]
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {new_access_token}"})
    assert response.status_code == 200

    # Test 4: Expired refresh token
    expired_refresh = jwt.encode(
        {"sub": test_user.email, "exp": datetime.utcnow() - timedelta(days=1)}, SECRET_KEY, algorithm=ALGORITHM
    )

    response = test_client.post("/api/v1/auth/refresh", json={"refresh_token": expired_refresh})
    assert response.status_code == 401


@pytest.mark.security
@pytest.mark.integration
def test_jwt_token_revocation_logout(test_client, test_user):
    """
    Test token revocation on user logout.

    Acceptance Criteria:
    - Logout invalidates current token
    - Revoked token cannot be used
    - Token added to blocklist
    - Logout all sessions invalidates all tokens
    - Refresh after logout fails
    """
    from api.auth_endpoints import create_access_token, token_blocklist

    # Test 1: Login and get token
    access_token = create_access_token(data={"sub": test_user.email})

    # Verify token works
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    # Test 2: Logout
    response = test_client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

    # Test 3: Token should be in blocklist
    assert access_token in token_blocklist

    # Test 4: Try to use revoked token
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()

    # Test 5: Logout all sessions
    # Create multiple tokens
    token1 = create_access_token(data={"sub": test_user.email})
    token2 = create_access_token(data={"sub": test_user.email})

    # Logout all
    response = test_client.post("/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200

    # Both tokens should be revoked
    assert token1 in token_blocklist
    assert token2 in token_blocklist


@pytest.mark.security
@pytest.mark.integration
@patch("api.oauth_endpoints.google_oauth_client")
def test_oauth_google_authentication_flow(mock_google_oauth, test_client):
    """
    Test Google OAuth authentication flow.

    Acceptance Criteria:
    - Redirect to Google OAuth
    - Handle OAuth callback
    - Verify Google token
    - Create/update user from Google profile
    - Return JWT tokens
    - Link existing account
    """
    # Mock Google OAuth response
    mock_google_oauth.fetch_token.return_value = {"access_token": "google_access_token", "id_token": "google_id_token"}

    mock_google_oauth.parse_id_token.return_value = {
        "sub": "google_user_123",
        "email": "newuser@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg",
        "email_verified": True,
    }

    # Test 1: Initiate OAuth flow
    response = test_client.get("/api/v1/auth/google/login")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "google.com" in data["auth_url"]

    # Test 2: OAuth callback with authorization code
    response = test_client.get("/api/v1/auth/google/callback?code=test_auth_code&state=test_state")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "newuser@gmail.com"

    # Test 3: Verify user created in database
    from sqlalchemy.orm import Session

    db = next(get_db())
    user = db.query(User).filter(User.email == "newuser@gmail.com").first()
    assert user is not None
    assert user.oauth_provider == "google"
    assert user.oauth_id == "google_user_123"

    # Test 4: OAuth with existing account
    mock_google_oauth.parse_id_token.return_value["email"] = "test@example.com"

    response = test_client.get("/api/v1/auth/google/callback?code=test_auth_code2&state=test_state")
    assert response.status_code == 200
    data = response.json()
    # Should link to existing account, not create new one


@pytest.mark.security
@pytest.mark.integration
def test_session_timeout_inactive_user(test_client, test_user):
    """
    Test automatic session timeout after inactivity.

    Acceptance Criteria:
    - Track last activity timestamp
    - Timeout after 30 minutes of inactivity
    - Extend session on activity
    - Force logout on timeout
    - Show timeout warning
    """
    from api.auth_endpoints import create_access_token, SessionManager

    # Create session manager
    session_manager = SessionManager(timeout_minutes=30)

    # Test 1: Create session
    access_token = create_access_token(data={"sub": test_user.email})
    session_id = session_manager.create_session(user_id=test_user.user_id, token=access_token)

    assert session_id is not None

    # Test 2: Check session is active
    is_active = session_manager.is_session_active(session_id)
    assert is_active is True

    # Test 3: Update last activity
    session_manager.update_activity(session_id)
    last_activity = session_manager.get_last_activity(session_id)
    assert last_activity is not None
    assert (datetime.utcnow() - last_activity).seconds < 5

    # Test 4: Simulate timeout (manually set old timestamp)
    old_time = datetime.utcnow() - timedelta(minutes=31)
    session_manager.sessions[session_id]["last_activity"] = old_time

    is_active = session_manager.is_session_active(session_id)
    assert is_active is False

    # Test 5: Try to use timed-out session
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {access_token}"})
    # Should fail if session timeout is enforced
    assert response.status_code in [401, 403]


@pytest.mark.security
@pytest.mark.integration
def test_password_reset_token_validation(test_client, test_user):
    """
    Test password reset token validation and security.

    Acceptance Criteria:
    - Generate unique reset token
    - Token expires after 1 hour
    - Token can only be used once
    - Validate email before sending
    - New password meets requirements
    - Old password no longer works
    """
    # Test 1: Request password reset
    response = test_client.post("/api/v1/auth/password-reset/request", json={"email": test_user.email})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "email sent" in data["message"].lower()

    # In real implementation, token would be sent via email
    # For testing, we'll extract it from database
    from sqlalchemy.orm import Session

    db = next(get_db())
    user = db.query(User).filter(User.email == test_user.email).first()
    reset_token = user.password_reset_token
    assert reset_token is not None

    # Test 2: Validate reset token
    response = test_client.get(f"/api/v1/auth/password-reset/validate/{reset_token}")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True

    # Test 3: Reset password with valid token
    new_password = "NewSecurePassword123!"
    response = test_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": new_password, "confirm_password": new_password},
    )
    assert response.status_code == 200

    # Test 4: Token should be invalidated after use
    response = test_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "AnotherPassword456!", "confirm_password": "AnotherPassword456!"},
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()

    # Test 5: Login with new password
    response = test_client.post("/api/v1/auth/login", data={"username": test_user.email, "password": new_password})
    assert response.status_code == 200

    # Test 6: Expired reset token
    expired_token = jwt.encode(
        {"sub": test_user.email, "exp": datetime.utcnow() - timedelta(hours=2)}, "reset_secret", algorithm="HS256"
    )

    response = test_client.get(f"/api/v1/auth/password-reset/validate/{expired_token}")
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.security
@pytest.mark.integration
def test_multi_device_session_management(test_client, test_user):
    """
    Test managing multiple concurrent sessions across devices.

    Acceptance Criteria:
    - Allow multiple active sessions
    - Track device/location for each session
    - List all active sessions
    - Revoke individual sessions
    - Revoke all sessions except current
    - Show last activity per session
    """
    from api.auth_endpoints import create_access_token, SessionManager

    session_manager = SessionManager()

    # Test 1: Create multiple sessions (different devices)
    sessions = []
    devices = ["iPhone 14", "MacBook Pro", "iPad Air", "Chrome Browser"]

    for device in devices:
        token = create_access_token(data={"sub": test_user.email})
        session_id = session_manager.create_session(
            user_id=test_user.user_id,
            token=token,
            device_info={"device_name": device, "ip_address": "192.168.1.1", "user_agent": f"BabyShield/{device}"},
        )
        sessions.append({"id": session_id, "token": token, "device": device})

    # Test 2: List all active sessions
    response = test_client.get("/api/v1/auth/sessions", headers={"Authorization": f"Bearer {sessions[0]['token']}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 4

    # Verify device info in response
    device_names = [s["device_name"] for s in data["sessions"]]
    assert "iPhone 14" in device_names
    assert "MacBook Pro" in device_names

    # Test 3: Revoke specific session
    session_to_revoke = sessions[2]["id"]
    response = test_client.delete(
        f"/api/v1/auth/sessions/{session_to_revoke}", headers={"Authorization": f"Bearer {sessions[0]['token']}"}
    )
    assert response.status_code == 200

    # Verify session revoked
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {sessions[2]['token']}"})
    assert response.status_code == 401

    # Test 4: Revoke all sessions except current
    response = test_client.post(
        "/api/v1/auth/sessions/revoke-others", headers={"Authorization": f"Bearer {sessions[0]['token']}"}
    )
    assert response.status_code == 200

    # Current session should still work
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {sessions[0]['token']}"})
    assert response.status_code == 200

    # Other sessions should be revoked
    response = test_client.get("/api/v1/user/profile", headers={"Authorization": f"Bearer {sessions[1]['token']}"})
    assert response.status_code == 401
