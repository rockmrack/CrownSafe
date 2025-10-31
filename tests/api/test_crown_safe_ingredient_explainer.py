"""Crown Safe - Ingredient Explainer Tests
Tests for GET /api/v1/ingredients/{name} and /api/v1/ingredients?query=... endpoints

Test Coverage:
- Ingredient lookup by exact name
- Ingredient lookup by INCI name
- Ingredient lookup by common name
- Case-insensitive search
- Porosity-specific guidance
- Best-for recommendations
- Avoid-if warnings
- Rinse-off vs leave-in guidance
- Ingredient search functionality
- Not found handling
"""

import pytest
from fastapi.testclient import TestClient

from api.main_crownsafe import app
from core_infra.crown_safe_models import IngredientModel
from core_infra.database import get_db


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Database session fixture"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_ingredients(db_session):
    """Create sample ingredients for testing"""
    ingredients = [
        IngredientModel(
            name="Shea Butter",
            inci_name="Butyrospermum Parkii (Shea) Butter",
            description=(
                "Rich, moisturizing butter from African shea tree nuts. "
                "Excellent for sealing moisture and adding shine."
            ),
            common_names=["shea", "karite butter"],
            category="Butter",
            effects=["Moisturizing", "Sealing", "Shine"],
            porosity_adjustments={
                "Low": "Use sparingly, may cause buildup",
                "Medium": "Perfect for moisture retention",
                "High": "Excellent for sealing moisture",
            },
            curl_pattern_adjustments={"4B": 8, "4C": 9, "4A": 7},
            rinse_off_product=False,
        ),
        IngredientModel(
            name="Sodium Lauryl Sulfate",
            inci_name="Sodium Lauryl Sulfate",
            description=(
                "Harsh sulfate cleanser that strips natural oils. Can cause dryness and irritation with frequent use."
            ),
            common_names=["SLS", "sodium lauryl sulfate"],
            category="Surfactant",
            effects=["Drying", "Stripping", "Cleansing"],
            porosity_adjustments={
                "Low": "May help remove buildup occasionally",
                "Medium": "Use only 1x per week",
                "High": "Avoid - too stripping for porous hair",
            },
            curl_pattern_adjustments={"3C": 3, "4A": 2, "4B": 1, "4C": 1},
            rinse_off_product=True,
        ),
        IngredientModel(
            name="Coconut Oil",
            inci_name="Cocos Nucifera (Coconut) Oil",
            description=(
                "Penetrating oil rich in fatty acids. Can be protein-like for some. Great for pre-poo treatments."
            ),
            common_names=["coconut oil", "cocos nucifera"],
            category="Oil",
            effects=["Penetrating", "Protein-like", "Strengthening"],
            porosity_adjustments={
                "Low": "Can penetrate shaft, use in pre-poo",
                "Medium": "Works well for most",
                "High": "May not provide enough moisture alone",
            },
            curl_pattern_adjustments={"3C": 7, "4A": 6, "4B": 5, "4C": 4},
            rinse_off_product=False,
        ),
    ]

    for ingredient in ingredients:
        db_session.add(ingredient)
    db_session.commit()

    return ingredients


# ============================================================================
# INGREDIENT LOOKUP TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_get_ingredient_by_name_success(client, sample_ingredients):
    """Test getting ingredient by exact name"""
    response = client.get("/api/v1/ingredients/Shea Butter")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Shea Butter"
    assert data["inci_name"] == "Butyrospermum Parkii (Shea) Butter"
    assert "Rich, moisturizing butter" in data["description"]
    assert "Moisturizing" in data["effects"]


@pytest.mark.api
@pytest.mark.unit
def test_get_ingredient_by_inci_name(client, sample_ingredients):
    """Test getting ingredient by INCI name"""
    response = client.get("/api/v1/ingredients/Sodium Lauryl Sulfate")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sodium Lauryl Sulfate"
    assert "sulfate cleanser" in data["description"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_get_ingredient_case_insensitive(client, sample_ingredients):
    """Test that ingredient lookup is case-insensitive"""
    response = client.get("/api/v1/ingredients/shea butter")  # lowercase

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Shea Butter"


@pytest.mark.api
@pytest.mark.unit
def test_get_ingredient_by_common_name(client, sample_ingredients):
    """Test getting ingredient by common name (JSON search)"""
    response = client.get("/api/v1/ingredients/SLS")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sodium Lauryl Sulfate"


@pytest.mark.api
@pytest.mark.unit
def test_get_ingredient_not_found(client):
    """Test getting non-existent ingredient"""
    response = client.get("/api/v1/ingredients/Nonexistent Ingredient XYZ")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# POROSITY GUIDANCE TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_includes_porosity_notes(client, sample_ingredients):
    """Test that ingredient response includes porosity-specific guidance"""
    response = client.get("/api/v1/ingredients/Shea Butter")

    assert response.status_code == 200
    data = response.json()
    assert "porosity_notes" in data

    porosity_notes = data["porosity_notes"]
    assert "Low" in porosity_notes
    assert "Medium" in porosity_notes
    assert "High" in porosity_notes
    assert "buildup" in porosity_notes["Low"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_porosity_warnings(client, sample_ingredients):
    """Test that harsh ingredients have proper porosity warnings"""
    response = client.get("/api/v1/ingredients/Sodium Lauryl Sulfate")

    assert response.status_code == 200
    data = response.json()

    porosity_notes = data["porosity_notes"]
    assert "avoid" in porosity_notes["High"].lower() or "stripping" in porosity_notes["High"].lower()


# ============================================================================
# BEST-FOR RECOMMENDATIONS TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_best_for_recommendations(client, sample_ingredients):
    """Test that ingredients include best-for curl pattern recommendations"""
    response = client.get("/api/v1/ingredients/Shea Butter")

    assert response.status_code == 200
    data = response.json()
    assert "best_for" in data

    best_for = data["best_for"]
    assert len(best_for) > 0
    # Shea Butter should be best for 4C (score 9) and 4B (score 8)
    assert "4C" in best_for or "4B" in best_for


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_best_for_filtering(client, sample_ingredients):
    """Test that best-for only includes patterns with score > 5"""
    response = client.get("/api/v1/ingredients/Coconut Oil")

    assert response.status_code == 200
    data = response.json()

    best_for = data["best_for"]
    # Coconut Oil: 3C=7, 4A=6, 4B=5, 4C=4
    # Should include 3C and 4A (score > 5), not 4B or 4C
    assert "3C" in best_for
    assert "4A" in best_for
    assert "4C" not in best_for


# ============================================================================
# AVOID-IF WARNINGS TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_avoid_if_warnings(client, sample_ingredients):
    """Test that ingredients include avoid-if warnings based on effects"""
    response = client.get("/api/v1/ingredients/Sodium Lauryl Sulfate")

    assert response.status_code == 200
    data = response.json()
    assert "avoid_if" in data

    avoid_if = data["avoid_if"]
    assert len(avoid_if) > 0
    # SLS has "Drying" and "Stripping" effects
    assert any("dry" in warning.lower() for warning in avoid_if)


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_protein_warning(client, sample_ingredients):
    """Test that protein-heavy ingredients have protein warning"""
    response = client.get("/api/v1/ingredients/Coconut Oil")

    assert response.status_code == 200
    data = response.json()

    avoid_if = data["avoid_if"]
    # Coconut Oil has "Protein-like" effect
    assert any("protein" in warning.lower() for warning in avoid_if)


# ============================================================================
# RINSE-OFF VS LEAVE-IN GUIDANCE TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_leave_in_guidance(client, sample_ingredients):
    """Test that leave-in ingredients have proper guidance"""
    response = client.get("/api/v1/ingredients/Shea Butter")

    assert response.status_code == 200
    data = response.json()
    assert "usage_notes" in data

    usage_notes = data["usage_notes"]
    assert "leave" in usage_notes.lower() or "stay" in usage_notes.lower()


@pytest.mark.api
@pytest.mark.unit
def test_ingredient_rinse_off_guidance(client, sample_ingredients):
    """Test that rinse-off ingredients have proper guidance"""
    response = client.get("/api/v1/ingredients/Sodium Lauryl Sulfate")

    assert response.status_code == 200
    data = response.json()

    usage_notes = data["usage_notes"]
    assert "rinse" in usage_notes.lower() or "wash" in usage_notes.lower()


# ============================================================================
# INGREDIENT SEARCH TESTS
# ============================================================================


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_success(client, sample_ingredients):
    """Test searching ingredients by query"""
    response = client.get("/api/v1/ingredients?query=butter")

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) > 0

    # Should find Shea Butter
    names = [r["name"] for r in data["results"]]
    assert "Shea Butter" in names


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_case_insensitive(client, sample_ingredients):
    """Test that search is case-insensitive"""
    response = client.get("/api/v1/ingredients?query=COCONUT")

    assert response.status_code == 200
    data = response.json()

    names = [r["name"] for r in data["results"]]
    assert "Coconut Oil" in names


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_partial_match(client, sample_ingredients):
    """Test that search supports partial matching"""
    response = client.get("/api/v1/ingredients?query=sul")

    assert response.status_code == 200
    data = response.json()

    # Should find Sodium Lauryl Sulfate
    names = [r["name"] for r in data["results"]]
    assert "Sodium Lauryl Sulfate" in names


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_empty_query(client):
    """Test searching with empty query"""
    response = client.get("/api/v1/ingredients?query=")

    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_no_results(client):
    """Test searching with query that matches nothing"""
    response = client.get("/api/v1/ingredients?query=xyznonexistent")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0


@pytest.mark.api
@pytest.mark.unit
def test_search_ingredients_limit(client, sample_ingredients):
    """Test that search respects 10-result limit"""
    # Create 15 ingredients with "test" in name
    db = next(get_db())
    for i in range(15):
        ingredient = IngredientModel(
            name=f"Test Ingredient {i}",
            inci_name=f"Test Ingredient {i} INCI",
            description=f"Test ingredient {i}",
            common_names=[],
            category="Test",
            effects=[],
            porosity_adjustments={},
            curl_pattern_adjustments={},
            rinse_off_product=False,
        )
        db.add(ingredient)
    db.commit()
    db.close()

    response = client.get("/api/v1/ingredients?query=test")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) <= 10  # Should respect limit


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.api
@pytest.mark.edge_cases
def test_get_ingredient_with_special_characters(client, db_session):
    """Test getting ingredient with special characters in name"""
    ingredient = IngredientModel(
        name="PEG-100 Stearate",
        inci_name="PEG-100 Stearate",
        description="Emulsifier and surfactant",
        common_names=["peg 100", "polyethylene glycol"],
        category="Emulsifier",
        effects=["Emulsifying"],
        porosity_adjustments={},
        curl_pattern_adjustments={},
        rinse_off_product=True,
    )
    db_session.add(ingredient)
    db_session.commit()

    response = client.get("/api/v1/ingredients/PEG-100 Stearate")
    assert response.status_code == 200


@pytest.mark.api
@pytest.mark.edge_cases
def test_get_ingredient_with_whitespace(client, sample_ingredients):
    """Test getting ingredient with extra whitespace"""
    response = client.get("/api/v1/ingredients/  Shea  Butter  ")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Shea Butter"


@pytest.mark.api
@pytest.mark.edge_cases
def test_search_ingredients_with_sql_injection_attempt(client):
    """Test that search is protected against SQL injection"""
    response = client.get("/api/v1/ingredients?query='; DROP TABLE ingredients; --")

    # Should not crash, should return 200 with empty results
    assert response.status_code in [200, 400]
