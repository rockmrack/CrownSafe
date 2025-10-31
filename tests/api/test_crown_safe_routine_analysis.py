"""Crown Safe - Routine Analysis Tests
Tests for POST /api/v1/cabinet-audit and /api/v1/routine-check endpoints

Test Coverage:
- Cabinet audit with protein overload detection
- Cabinet audit with buildup detection
- Cabinet audit with stripping detection
- Cabinet audit with moisture imbalance detection
- Routine check for silicone buildup
- Routine check for protein + sulfate stripping
- Routine check for oil + water incompatibility
- Crown Score calculation
- Rotation plan generation
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
    """Create test user with hair profile"""
    user = User(
        email="test_routine@crownsafe.com",
        username="test_routine",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create hair profile for user
    profile = HairProfileModel(
        user_id=user.id,
        hair_type="4C",
        porosity="High",
        hair_state="Natural",
        hair_goals=["Moisture", "Length Retention"],
        sensitivities=["Protein"],
        climate="Humid",
    )
    db_session.add(profile)
    db_session.commit()

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
# CABINET AUDIT TESTS - PROTEIN OVERLOAD DETECTION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_protein_overload_detected(client, auth_headers):
    """Test that cabinet audit detects protein overload (3+ products)"""
    audit_data = {
        "products": [
            {
                "name": "Protein Treatment",
                "type": "Deep Conditioner",
                "ingredients": ["Water", "Hydrolyzed Keratin", "Behentrimonium Methosulfate"],
            },
            {
                "name": "Protein Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Hydrolyzed Collagen", "Cocamidopropyl Betaine"],
            },
            {
                "name": "Protein Leave-In",
                "type": "Leave-In",
                "ingredients": ["Water", "Silk Amino Acids", "Glycerin"],
            },
            {
                "name": "Regular Conditioner",
                "type": "Conditioner",
                "ingredients": ["Water", "Cetearyl Alcohol", "Shea Butter"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "issues" in data
    issues = data["issues"]

    # Should detect protein overload
    protein_issues = [i for i in issues if "protein" in i["issue"].lower()]
    assert len(protein_issues) > 0

    protein_issue = protein_issues[0]
    assert protein_issue["severity"] in ["HIGH", "CRITICAL"]
    assert "3" in protein_issue["issue"] or "overload" in protein_issue["issue"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_no_protein_overload(client, auth_headers):
    """Test that cabinet audit does NOT flag protein when only 1-2 products have it"""
    audit_data = {
        "products": [
            {
                "name": "Protein Treatment",
                "type": "Deep Conditioner",
                "ingredients": ["Water", "Hydrolyzed Keratin"],
            },
            {
                "name": "Regular Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Cocamidopropyl Betaine"],
            },
            {
                "name": "Regular Leave-In",
                "type": "Leave-In",
                "ingredients": ["Water", "Glycerin", "Shea Butter"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    protein_issues = [i for i in data["issues"] if "protein overload" in i["issue"].lower()]
    assert len(protein_issues) == 0  # Should not flag protein overload


# ============================================================================
# CABINET AUDIT TESTS - BUILDUP DETECTION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_buildup_detected(client, auth_headers):
    """Test that cabinet audit detects buildup risk (silicones without clarifying)"""
    audit_data = {
        "products": [
            {
                "name": "Silicone Leave-In",
                "type": "Leave-In",
                "ingredients": ["Water", "Dimethicone", "Glycerin"],
            },
            {
                "name": "Silicone Gel",
                "type": "Gel",
                "ingredients": ["Water", "Amodimethicone", "Carbomer"],
            },
            {
                "name": "Sulfate-Free Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Cocamidopropyl Betaine", "Glycerin"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    buildup_issues = [i for i in data["issues"] if "buildup" in i["issue"].lower()]
    assert len(buildup_issues) > 0

    buildup_issue = buildup_issues[0]
    assert buildup_issue["severity"] == "MEDIUM"
    assert "clarifying" in buildup_issue["recommendation"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_no_buildup_with_clarifying(client, auth_headers):
    """Test that cabinet audit does NOT flag buildup when clarifying shampoo present"""
    audit_data = {
        "products": [
            {
                "name": "Silicone Leave-In",
                "type": "Leave-In",
                "ingredients": ["Water", "Dimethicone", "Glycerin"],
            },
            {
                "name": "Clarifying Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Sodium Lauryl Sulfate", "Citric Acid"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    buildup_issues = [i for i in data["issues"] if "buildup" in i["issue"].lower()]
    assert len(buildup_issues) == 0  # Should not flag buildup


# ============================================================================
# CABINET AUDIT TESTS - STRIPPING DETECTION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_stripping_detected(client, auth_headers):
    """Test that cabinet audit detects stripping (harsh sulfates daily)"""
    audit_data = {
        "products": [
            {
                "name": "Harsh Sulfate Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Sodium Lauryl Sulfate", "Cocamide DEA"],
            },
            {
                "name": "Another Sulfate Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Sodium Laureth Sulfate", "Fragrance"],
            },
            {
                "name": "Conditioner",
                "type": "Conditioner",
                "ingredients": ["Water", "Cetearyl Alcohol"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    stripping_issues = [i for i in data["issues"] if "stripping" in i["issue"].lower() or "dry" in i["issue"].lower()]
    assert len(stripping_issues) > 0

    stripping_issue = stripping_issues[0]
    assert stripping_issue["severity"] == "MEDIUM"
    assert "sulfate-free" in stripping_issue["recommendation"].lower()


# ============================================================================
# CABINET AUDIT TESTS - MOISTURE IMBALANCE DETECTION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_moisture_imbalance_detected(client, auth_headers):
    """Test that cabinet audit detects moisture imbalance (missing key steps)"""
    audit_data = {
        "products": [
            {
                "name": "Basic Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Cocamidopropyl Betaine"],
            },
            # Missing: deep conditioner, leave-in, moisturizing ingredients
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    moisture_issues = [i for i in data["issues"] if "moisture" in i["issue"].lower()]
    assert len(moisture_issues) > 0

    moisture_issue = moisture_issues[0]
    assert moisture_issue["severity"] == "HIGH"


# ============================================================================
# CABINET AUDIT TESTS - CROWN SCORE CALCULATION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_calculates_crown_score(client, auth_headers):
    """Test that cabinet audit calculates Crown Score for each product"""
    audit_data = {
        "products": [
            {
                "name": "Good Product",
                "type": "Conditioner",
                "ingredients": ["Water", "Glycerin", "Shea Butter", "Aloe Vera"],
            },
            {
                "name": "Bad Product",
                "type": "Shampoo",
                "ingredients": ["Water", "Sodium Lauryl Sulfate", "Fragrance", "Parabens"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "scored_products" in data
    scored_products = data["scored_products"]
    assert len(scored_products) == 2

    for product in scored_products:
        assert "name" in product
        assert "crown_score" in product
        assert 0 <= product["crown_score"] <= 100


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_calculates_average_score(client, auth_headers):
    """Test that cabinet audit calculates average Crown Score"""
    audit_data = {
        "products": [
            {
                "name": "Product 1",
                "type": "Conditioner",
                "ingredients": ["Water", "Glycerin", "Shea Butter"],
            },
            {
                "name": "Product 2",
                "type": "Shampoo",
                "ingredients": ["Water", "Cocamidopropyl Betaine"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "average_score" in data
    assert 0 <= data["average_score"] <= 100


# ============================================================================
# CABINET AUDIT TESTS - ROTATION PLAN GENERATION
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_generates_rotation_plan(client, auth_headers):
    """Test that cabinet audit generates rotation plan"""
    audit_data = {
        "products": [
            {
                "name": "Shampoo",
                "type": "Shampoo",
                "ingredients": ["Water", "Cocamidopropyl Betaine"],
            },
            {
                "name": "Conditioner",
                "type": "Conditioner",
                "ingredients": ["Water", "Cetearyl Alcohol"],
            },
            {
                "name": "Leave-In",
                "type": "Leave-In",
                "ingredients": ["Water", "Glycerin"],
            },
        ],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "rotation_plan" in data
    rotation_plan = data["rotation_plan"]

    assert "daily" in rotation_plan
    assert "weekly" in rotation_plan
    assert "monthly" in rotation_plan


# ============================================================================
# ROUTINE CHECK TESTS - INTERACTION WARNINGS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_routine_check_silicone_buildup_warning(client, auth_headers):
    """Test routine check detects silicone buildup (silicone + no sulfates)"""
    check_data = {
        "product_a": {
            "name": "Silicone Leave-In",
            "type": "Leave-In",
            "ingredients": ["Water", "Dimethicone", "Glycerin"],
        },
        "product_b": {
            "name": "Sulfate-Free Shampoo",
            "type": "Shampoo",
            "ingredients": ["Water", "Cocamidopropyl Betaine"],
        },
    }

    response = client.post("/api/v1/routine-check", json=check_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert "warnings" in data
    warnings = data["warnings"]

    silicone_warnings = [w for w in warnings if "silicone" in w["issue"].lower()]
    assert len(silicone_warnings) > 0

    warning = silicone_warnings[0]
    assert warning["severity"] in ["MEDIUM", "HIGH"]
    assert "clarifying" in warning["recommendation"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_routine_check_protein_sulfate_stripping(client, auth_headers):
    """Test routine check detects protein + sulfate stripping"""
    check_data = {
        "product_a": {
            "name": "Protein Treatment",
            "type": "Deep Conditioner",
            "ingredients": ["Water", "Hydrolyzed Keratin", "Cetearyl Alcohol"],
        },
        "product_b": {
            "name": "Harsh Sulfate Shampoo",
            "type": "Shampoo",
            "ingredients": ["Water", "Sodium Lauryl Sulfate", "Cocamide DEA"],
        },
    }

    response = client.post("/api/v1/routine-check", json=check_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    warnings = data["warnings"]

    protein_warnings = [w for w in warnings if "protein" in w["issue"].lower() and "sulfate" in w["issue"].lower()]
    assert len(protein_warnings) > 0

    warning = protein_warnings[0]
    assert warning["severity"] in ["MEDIUM", "HIGH"]


@pytest.mark.api
@pytest.mark.unit
def test_routine_check_oil_water_incompatibility(client, auth_headers):
    """Test routine check detects oil + water gel incompatibility"""
    check_data = {
        "product_a": {
            "name": "Heavy Oil",
            "type": "Oil",
            "ingredients": ["Castor Oil", "Olive Oil", "Jojoba Oil"],
        },
        "product_b": {
            "name": "Water-Based Gel",
            "type": "Gel",
            "ingredients": ["Water", "Carbomer", "Aloe Vera Juice"],
        },
    }

    response = client.post("/api/v1/routine-check", json=check_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    warnings = data["warnings"]

    oil_warnings = [w for w in warnings if "oil" in w["issue"].lower() and "water" in w["issue"].lower()]
    assert len(oil_warnings) > 0

    warning = oil_warnings[0]
    assert warning["severity"] == "LOW"


@pytest.mark.api
@pytest.mark.unit
def test_routine_check_no_warnings(client, auth_headers):
    """Test routine check with compatible products (no warnings)"""
    check_data = {
        "product_a": {
            "name": "Gentle Shampoo",
            "type": "Shampoo",
            "ingredients": ["Water", "Cocamidopropyl Betaine", "Glycerin"],
        },
        "product_b": {
            "name": "Moisturizing Conditioner",
            "type": "Conditioner",
            "ingredients": ["Water", "Cetearyl Alcohol", "Shea Butter"],
        },
    }

    response = client.post("/api/v1/routine-check", json=check_data, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data["warnings"]) == 0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_empty_products(client, auth_headers):
    """Test cabinet audit with empty products array"""
    audit_data = {"products": []}

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=auth_headers)

    assert response.status_code == 400
    assert "at least one product" in response.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_unauthenticated(client):
    """Test cabinet audit without authentication"""
    audit_data = {
        "products": [{"name": "Shampoo", "type": "Shampoo", "ingredients": ["Water", "Cocamidopropyl Betaine"]}],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data)

    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.unit
def test_routine_check_unauthenticated(client):
    """Test routine check without authentication"""
    check_data = {
        "product_a": {"name": "Product A", "type": "Shampoo", "ingredients": ["Water"]},
        "product_b": {"name": "Product B", "type": "Conditioner", "ingredients": ["Water"]},
    }

    response = client.post("/api/v1/routine-check", json=check_data)

    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.unit
def test_cabinet_audit_no_profile(client):
    """Test cabinet audit for user without hair profile"""
    # Create user without profile
    db = next(get_db())
    user = User(
        email="noprofile@crownsafe.com",
        username="noprofile",
        hashed_password="$2b$12$test_hashed_password",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    audit_data = {
        "products": [{"name": "Shampoo", "type": "Shampoo", "ingredients": ["Water", "Cocamidopropyl Betaine"]}],
    }

    response = client.post("/api/v1/cabinet-audit", json=audit_data, headers=headers)

    assert response.status_code == 404
    assert "profile not found" in response.json()["detail"].lower()

    db.close()
