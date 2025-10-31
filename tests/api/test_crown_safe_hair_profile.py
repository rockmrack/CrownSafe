"""
Crown Safe - Hair Profile Endpoints Tests
Tests for POST/GET/PUT/DELETE /api/v1/profiles endpoints

Test Coverage:
- Profile creation with valid data
- Profile creation with invalid data
- Profile retrieval (own profile)
- Profile retrieval (unauthorized access)
- Profile update (partial updates)
- Profile deletion (GDPR compliance)
- Duplicate profile prevention
- User ownership verification
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.auth_endpoints import create_access_token
from api.main_crownsafe import app
from core_infra.crown_safe_models import HairProfileModel
from core_infra.database import User, get_db


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def test_user(db_session: Session):
    """Create test user for authentication"""
    user = User(
        email="test_profile@crownsafe.com",
        username="test_profile",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def db_session():
    """Database session fixture"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# PROFILE CREATION TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_create_hair_profile_success(client, auth_headers, test_user, db_session):
    """Test creating hair profile with valid data"""
    profile_data = {
        "hair_type": "4C",
        "porosity": "Low",
        "hair_state": "Natural",
        "hair_goals": ["Length Retention", "Moisture", "Definition"],
        "sensitivities": ["Protein", "Fragrance"],
        "climate": "Humid",
    }

    response = client.post("/api/v1/profiles", json=profile_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["hair_type"] == "4C"
    assert data["porosity"] == "Low"
    assert data["user_id"] == test_user.id
    assert "id" in data
    assert "created_at" in data

    # Verify in database
    profile = db_session.query(HairProfileModel).filter_by(user_id=test_user.id).first()
    assert profile is not None
    assert profile.hair_type == "4C"


@pytest.mark.api
@pytest.mark.unit
def test_create_duplicate_profile_fails(client, auth_headers, test_user, db_session):
    """Test that creating duplicate profile fails"""
    profile_data = {
        "hair_type": "4B",
        "porosity": "Medium",
        "hair_state": "Natural",
        "hair_goals": ["Moisture"],
        "sensitivities": [],
        "climate": "Dry",
    }

    # Create first profile
    response1 = client.post("/api/v1/profiles", json=profile_data, headers=auth_headers)
    assert response1.status_code == 201

    # Try to create second profile (should fail)
    response2 = client.post("/api/v1/profiles", json=profile_data, headers=auth_headers)
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_create_profile_invalid_hair_type(client, auth_headers):
    """Test creating profile with invalid hair type"""
    profile_data = {
        "hair_type": "5Z",  # Invalid
        "porosity": "Low",
        "hair_state": "Natural",
        "hair_goals": ["Moisture"],
        "sensitivities": [],
        "climate": "Humid",
    }

    response = client.post("/api/v1/profiles", json=profile_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error


@pytest.mark.api
@pytest.mark.unit
def test_create_profile_unauthenticated(client):
    """Test creating profile without authentication"""
    profile_data = {
        "hair_type": "4C",
        "porosity": "Low",
        "hair_state": "Natural",
        "hair_goals": ["Moisture"],
        "sensitivities": [],
        "climate": "Humid",
    }

    response = client.post("/api/v1/profiles", json=profile_data)
    assert response.status_code == 401


# ============================================================================
# PROFILE RETRIEVAL TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_get_hair_profile_success(client, auth_headers, test_user, db_session):
    """Test retrieving own hair profile"""
    # Create profile first
    profile = HairProfileModel(
        user_id=test_user.id,
        hair_type="4A",
        porosity="High",
        hair_state="Chemically Treated",
        hair_goals=["Strength", "Growth"],
        sensitivities=["Sulfates"],
        climate="Temperate",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    response = client.get(f"/api/v1/profiles/{profile.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == profile.id
    assert data["hair_type"] == "4A"
    assert data["porosity"] == "High"
    assert data["user_id"] == test_user.id


@pytest.mark.api
@pytest.mark.unit
def test_get_profile_not_found(client, auth_headers):
    """Test retrieving non-existent profile"""
    response = client.get("/api/v1/profiles/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.security
def test_get_profile_unauthorized_access(client, auth_headers, test_user, db_session):
    """Test that users cannot access other users' profiles"""
    # Create another user's profile
    other_user = User(
        email="other@crownsafe.com",
        username="other_user",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    other_profile = HairProfileModel(
        user_id=other_user.id,
        hair_type="3C",
        porosity="Medium",
        hair_state="Natural",
        hair_goals=["Volume"],
        sensitivities=[],
        climate="Cold",
    )
    db_session.add(other_profile)
    db_session.commit()
    db_session.refresh(other_profile)

    # Try to access other user's profile
    response = client.get(f"/api/v1/profiles/{other_profile.id}", headers=auth_headers)
    assert response.status_code == 403


# ============================================================================
# PROFILE UPDATE TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_update_hair_profile_success(client, auth_headers, test_user, db_session):
    """Test updating hair profile with partial data"""
    # Create profile
    profile = HairProfileModel(
        user_id=test_user.id,
        hair_type="4B",
        porosity="Low",
        hair_state="Natural",
        hair_goals=["Moisture"],
        sensitivities=["Protein"],
        climate="Humid",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # Update only hair_goals and porosity
    update_data = {"hair_goals": ["Moisture", "Shine", "Definition"], "porosity": "Medium"}

    response = client.put(f"/api/v1/profiles/{profile.id}", json=update_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["porosity"] == "Medium"
    assert set(data["hair_goals"]) == {"Moisture", "Shine", "Definition"}
    assert data["hair_type"] == "4B"  # Unchanged
    assert "updated_at" in data


@pytest.mark.api
@pytest.mark.unit
def test_update_profile_not_found(client, auth_headers):
    """Test updating non-existent profile"""
    update_data = {"porosity": "High"}
    response = client.put("/api/v1/profiles/99999", json=update_data, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.security
def test_update_profile_unauthorized(client, auth_headers, test_user, db_session):
    """Test that users cannot update other users' profiles"""
    # Create another user's profile
    other_user = User(
        email="other2@crownsafe.com",
        username="other_user2",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    other_profile = HairProfileModel(
        user_id=other_user.id,
        hair_type="4A",
        porosity="Low",
        hair_state="Natural",
        hair_goals=["Growth"],
        sensitivities=[],
        climate="Dry",
    )
    db_session.add(other_profile)
    db_session.commit()
    db_session.refresh(other_profile)

    # Try to update other user's profile
    update_data = {"hair_type": "4C"}
    response = client.put(f"/api/v1/profiles/{other_profile.id}", json=update_data, headers=auth_headers)
    assert response.status_code == 403


# ============================================================================
# PROFILE DELETION TESTS (GDPR Compliance)
# ============================================================================


@pytest.mark.api
@pytest.mark.privacy
def test_delete_hair_profile_success(client, auth_headers, test_user, db_session):
    """Test deleting hair profile (GDPR compliance)"""
    # Create profile
    profile = HairProfileModel(
        user_id=test_user.id,
        hair_type="4C",
        porosity="High",
        hair_state="Natural",
        hair_goals=["Length Retention"],
        sensitivities=["Fragrance"],
        climate="Humid",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    profile_id = profile.id

    # Delete profile
    response = client.delete(f"/api/v1/profiles/{profile_id}", headers=auth_headers)
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"].lower()

    # Verify deletion
    deleted_profile = db_session.query(HairProfileModel).filter_by(id=profile_id).first()
    assert deleted_profile is None


@pytest.mark.api
@pytest.mark.unit
def test_delete_profile_not_found(client, auth_headers):
    """Test deleting non-existent profile"""
    response = client.delete("/api/v1/profiles/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.security
def test_delete_profile_unauthorized(client, auth_headers, test_user, db_session):
    """Test that users cannot delete other users' profiles"""
    # Create another user's profile
    other_user = User(
        email="other3@crownsafe.com",
        username="other_user3",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db_session.add(other_user)
    db_session.commit()

    other_profile = HairProfileModel(
        user_id=other_user.id,
        hair_type="3C",
        porosity="Medium",
        hair_state="Natural",
        hair_goals=["Volume"],
        sensitivities=[],
        climate="Cold",
    )
    db_session.add(other_profile)
    db_session.commit()
    db_session.refresh(other_profile)

    # Try to delete other user's profile
    response = client.delete(f"/api/v1/profiles/{other_profile.id}", headers=auth_headers)
    assert response.status_code == 403


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.api
@pytest.mark.edge_cases
def test_create_profile_with_empty_arrays(client, auth_headers):
    """Test creating profile with empty arrays (valid)"""
    profile_data = {
        "hair_type": "4B",
        "porosity": "Medium",
        "hair_state": "Natural",
        "hair_goals": [],  # Empty
        "sensitivities": [],  # Empty
        "climate": "Humid",
    }

    response = client.post("/api/v1/profiles", json=profile_data, headers=auth_headers)
    assert response.status_code == 201


@pytest.mark.api
@pytest.mark.edge_cases
def test_update_profile_with_no_changes(client, auth_headers, test_user, db_session):
    """Test updating profile with no actual changes"""
    # Create profile
    profile = HairProfileModel(
        user_id=test_user.id,
        hair_type="4A",
        porosity="Low",
        hair_state="Natural",
        hair_goals=["Moisture"],
        sensitivities=[],
        climate="Dry",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # Update with empty data
    response = client.put(f"/api/v1/profiles/{profile.id}", json={}, headers=auth_headers)
    assert response.status_code == 200
