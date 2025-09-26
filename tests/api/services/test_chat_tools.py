import pytest
from api.services.chat_tools import (
    run_tool_for_intent,
    tool_pregnancy,
    tool_allergy,
    tool_ingredients,
    tool_age,
    tool_alternatives,
    tool_recall_details
)

def test_tool_pregnancy_soft_cheese():
    """Test pregnancy tool detects soft cheese risks"""
    scan_data = {
        "product_name": "Brie",
        "category": "cheese",
        "flags": ["soft_cheese"],
        "ingredients": ["milk", "salt"]
    }
    
    result = tool_pregnancy(scan_data)
    
    assert "pregnancy" in result
    assert "soft_cheese_pasteurisation" in result["pregnancy"]["risks"]
    assert "pasteurisation" in result["pregnancy"]["notes"].lower()

def test_tool_pregnancy_raw_milk():
    """Test pregnancy tool detects raw milk risks"""
    scan_data = {
        "product_name": "Artisan Cheese",
        "ingredients": ["raw milk", "salt"]
    }
    
    result = tool_pregnancy(scan_data)
    
    assert "pregnancy" in result
    assert "unpasteurised_dairy" in result["pregnancy"]["risks"]

def test_tool_pregnancy_safe():
    """Test pregnancy tool with safe product"""
    scan_data = {
        "product_name": "Crackers",
        "category": "snack",
        "ingredients": ["wheat", "salt"]
    }
    
    result = tool_pregnancy(scan_data)
    
    assert "pregnancy" in result
    assert result["pregnancy"]["risks"] == []
    assert result["pregnancy"]["notes"] == ""

def test_tool_allergy_match():
    """Test allergy tool detects allergen matches"""
    scan_data = {
        "profile": {"allergies": ["peanut", "dairy"]},
        "ingredients": ["sugar", "peanuts", "cocoa"]
    }
    
    result = tool_allergy(scan_data)
    
    assert "allergy" in result
    assert "peanut" in result["allergy"]["hits"]
    assert set(result["allergy"]["allergies"]) == {"peanut", "dairy"}

def test_tool_allergy_no_profile():
    """Test allergy tool with no profile"""
    scan_data = {
        "ingredients": ["sugar", "peanuts"]
    }
    
    result = tool_allergy(scan_data)
    
    assert "allergy" in result
    assert result["allergy"]["hits"] == []
    assert result["allergy"]["allergies"] == []

def test_tool_allergy_no_match():
    """Test allergy tool with no allergen matches"""
    scan_data = {
        "profile": {"allergies": ["shellfish"]},
        "ingredients": ["sugar", "wheat", "salt"]
    }
    
    result = tool_allergy(scan_data)
    
    assert "allergy" in result
    assert result["allergy"]["hits"] == []
    assert "shellfish" in result["allergy"]["allergies"]

def test_tool_ingredients():
    """Test ingredients tool returns ingredient info"""
    scan_data = {
        "ingredients": ["milk", "sugar", "vanilla"],
        "ingredients_notes": "Contains natural flavoring"
    }
    
    result = tool_ingredients(scan_data)
    
    assert "ingredients_info" in result
    assert result["ingredients_info"]["ingredients"] == ["milk", "sugar", "vanilla"]
    assert result["ingredients_info"]["notes"] == "Contains natural flavoring"

def test_tool_ingredients_minimal():
    """Test ingredients tool with minimal data"""
    scan_data = {}
    
    result = tool_ingredients(scan_data)
    
    assert "ingredients_info" in result
    assert result["ingredients_info"]["ingredients"] == []
    assert result["ingredients_info"]["notes"] is None

def test_tool_age_newborn_safe():
    """Test age tool for newborn-safe product"""
    scan_data = {
        "age_min_months": 0
    }
    
    result = tool_age(scan_data)
    
    assert "age_fit" in result
    assert result["age_fit"]["age_ok"] is True
    assert result["age_fit"]["min_age_months"] == 0

def test_tool_age_not_newborn_safe():
    """Test age tool for product not safe for newborns"""
    scan_data = {
        "age_min_months": 6
    }
    
    result = tool_age(scan_data)
    
    assert "age_fit" in result
    assert result["age_fit"]["age_ok"] is False
    assert result["age_fit"]["min_age_months"] == 6

def test_tool_age_no_data():
    """Test age tool with no age data"""
    scan_data = {}
    
    result = tool_age(scan_data)
    
    assert "age_fit" in result
    assert result["age_fit"]["age_ok"] is False
    assert result["age_fit"]["min_age_months"] is None

def test_tool_alternatives():
    """Test alternatives tool (placeholder)"""
    scan_data = {"product_name": "Test Product"}
    
    result = tool_alternatives(scan_data)
    
    assert "alternatives" in result
    assert result["alternatives"] == []

def test_tool_recall_details_with_recalls():
    """Test recall details tool with recalls"""
    scan_data = {
        "recalls_found": 2,
        "recalls": [
            {"id": "123", "agency": "CPSC", "date": "2023-01-01"},
            {"id": "456", "agency": "FDA", "date": "2023-02-01"}
        ]
    }
    
    result = tool_recall_details(scan_data)
    
    assert "recalls" in result
    assert result["recalls_found"] == 2
    assert len(result["recalls"]) == 2
    assert "batch_check" in result
    assert "batch/lot" in result["batch_check"].lower()

def test_tool_recall_details_no_recalls():
    """Test recall details tool with no recalls"""
    scan_data = {"recalls_found": 0}
    
    result = tool_recall_details(scan_data)
    
    assert "recalls" in result
    assert result["recalls_found"] == 0
    assert result["recalls"] == []

def test_run_tool_for_intent_pregnancy():
    """Test tool dispatcher for pregnancy intent"""
    scan_data = {"category": "cheese", "flags": ["soft_cheese"]}
    
    result = run_tool_for_intent("pregnancy_risk", scan_data=scan_data)
    
    assert "pregnancy" in result
    assert "soft_cheese_pasteurisation" in result["pregnancy"]["risks"]

def test_run_tool_for_intent_allergy():
    """Test tool dispatcher for allergy intent"""
    scan_data = {
        "profile": {"allergies": ["peanut"]},
        "ingredients": ["peanuts", "sugar"]
    }
    
    result = run_tool_for_intent("allergy_question", scan_data=scan_data)
    
    assert "allergy" in result
    assert "peanut" in result["allergy"]["hits"]

def test_run_tool_for_intent_ingredients():
    """Test tool dispatcher for ingredients intent"""
    scan_data = {"ingredients": ["milk", "sugar"]}
    
    result = run_tool_for_intent("ingredient_info", scan_data=scan_data)
    
    assert "ingredients_info" in result

def test_run_tool_for_intent_age():
    """Test tool dispatcher for age intent"""
    scan_data = {"age_min_months": 0}
    
    result = run_tool_for_intent("age_appropriateness", scan_data=scan_data)
    
    assert "age_fit" in result

def test_run_tool_for_intent_alternatives():
    """Test tool dispatcher for alternatives intent"""
    scan_data = {"product_name": "Test"}
    
    result = run_tool_for_intent("alternative_products", scan_data=scan_data)
    
    assert "alternatives" in result

def test_run_tool_for_intent_recalls():
    """Test tool dispatcher for recall intent"""
    scan_data = {"recalls_found": 1, "recalls": [{"id": "123"}]}
    
    result = run_tool_for_intent("recall_details", scan_data=scan_data)
    
    assert "recalls" in result

def test_run_tool_for_intent_unclear():
    """Test tool dispatcher for unclear intent"""
    scan_data = {"product_name": "Test"}
    
    result = run_tool_for_intent("unclear_intent", scan_data=scan_data)
    
    assert result == {}

def test_run_tool_for_intent_with_db():
    """Test tool dispatcher accepts db parameter"""
    scan_data = {"category": "cheese"}
    
    # Should not raise an error even with db parameter
    result = run_tool_for_intent("pregnancy_risk", scan_data=scan_data, db=None)
    
    assert "pregnancy" in result
