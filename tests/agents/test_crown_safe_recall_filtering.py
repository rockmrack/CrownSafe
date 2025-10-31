"""Crown Safe - Recall Agent Filtering Tests
Tests for Crown Safe recall filtering functionality

Test Coverage:
- is_crown_safe_recall() filtering function
- Hair product recall inclusion
- Cosmetic product recall inclusion
- Baby product recall exclusion
- Children's hair product inclusion
- Severity mapping
- Query filtering
- Ingestion filtering
"""

import pytest

from agents.recall_data_agent.crown_safe_config import (
    CROWN_SAFE_CATEGORIES,
    CROWN_SAFE_KEYWORDS,
    EXCLUDE_KEYWORDS,
    SEVERITY_MAPPING,
    is_crown_safe_recall,
)

# ============================================================================
# FILTERING FUNCTION TESTS - HAIR PRODUCTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_hair_relaxer_included():
    """Test that hair relaxer recalls are included"""
    assert is_crown_safe_recall("Hair Relaxer Chemical Burn Recall", "", "") is True
    assert (
        is_crown_safe_recall("Dark & Lovely Relaxer", "Contains formaldehyde, causes hair loss", "Hair Treatment")
        is True
    )


@pytest.mark.unit
@pytest.mark.agents
def test_filter_shampoo_included():
    """Test that shampoo recalls are included"""
    assert is_crown_safe_recall("Shampoo Contamination Alert", "", "") is True
    assert is_crown_safe_recall("DevaCurl No-Poo", "Causes hair loss and scalp irritation", "Shampoo") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_hair_dye_included():
    """Test that hair dye recalls are included"""
    assert is_crown_safe_recall("Hair Dye Allergy Warning", "", "") is True
    assert is_crown_safe_recall("Permanent Hair Color Recall", "Contains lead and heavy metals", "Hair Color") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_conditioner_included():
    """Test that conditioner recalls are included"""
    assert is_crown_safe_recall("Conditioner Contamination", "", "") is True
    assert is_crown_safe_recall("Moisturizing Conditioner", "Bacterial contamination", "Hair Care") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_hair_gel_included():
    """Test that hair gel recalls are included"""
    assert is_crown_safe_recall("Hair Gel Recall", "", "") is True
    assert is_crown_safe_recall("Styling Gel", "Contains prohibited preservatives", "Styling Product") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_edge_control_included():
    """Test that edge control recalls are included"""
    assert is_crown_safe_recall("Edge Control Hair Loss", "", "") is True
    assert is_crown_safe_recall("Edge Control Gel", "Causes alopecia and hair thinning", "Styling Product") is True


# ============================================================================
# FILTERING FUNCTION TESTS - COSMETIC PRODUCTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_cosmetic_products_included():
    """Test that general cosmetic products are included"""
    assert is_crown_safe_recall("Cosmetic Product Contamination", "", "") is True
    assert is_crown_safe_recall("Beauty Product Recall", "Contains harmful chemicals", "Cosmetic") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_scalp_treatment_included():
    """Test that scalp treatments are included"""
    assert is_crown_safe_recall("Scalp Treatment Burn Warning", "", "") is True
    assert is_crown_safe_recall("Medicated Scalp Oil", "Causes chemical burns", "Scalp Care") is True


# ============================================================================
# FILTERING FUNCTION TESTS - BABY PRODUCT EXCLUSION
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_baby_bottle_excluded():
    """Test that baby bottle recalls are excluded"""
    assert is_crown_safe_recall("Baby Bottle Recall - BPA Contamination", "", "") is False
    assert is_crown_safe_recall("Infant Bottle Recall", "Contains harmful chemicals", "Baby Product") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_pacifier_excluded():
    """Test that pacifier recalls are excluded"""
    assert is_crown_safe_recall("Pacifier Choking Hazard Recall", "", "") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_crib_excluded():
    """Test that crib recalls are excluded"""
    assert is_crown_safe_recall("Baby Crib Entrapment Hazard", "", "") is False
    assert is_crown_safe_recall("Infant Crib Recall", "Entrapment risk", "Nursery Furniture") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_car_seat_excluded():
    """Test that car seat recalls are excluded"""
    assert is_crown_safe_recall("Car Seat Safety Alert", "", "") is False
    assert is_crown_safe_recall("Infant Car Seat Recall", "Harness failure", "Auto Safety") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_stroller_excluded():
    """Test that stroller recalls are excluded"""
    assert is_crown_safe_recall("Stroller Wheel Detachment", "", "") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_diaper_excluded():
    """Test that diaper recalls are excluded"""
    assert is_crown_safe_recall("Diaper Rash Chemical Recall", "", "") is False


@pytest.mark.unit
@pytest.mark.agents
def test_filter_baby_food_excluded():
    """Test that baby food recalls are excluded"""
    assert is_crown_safe_recall("Baby Food Contamination Alert", "", "") is False
    assert is_crown_safe_recall("Infant Formula Recall", "Bacterial contamination", "Baby Food") is False


# ============================================================================
# FILTERING FUNCTION TESTS - CHILDREN'S HAIR PRODUCTS INCLUDED
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_kids_shampoo_included():
    """Test that children's hair products ARE included (not baby bottles)"""
    assert is_crown_safe_recall("Kids Shampoo Tear-Free Formula", "", "") is True
    assert is_crown_safe_recall("Children's Shampoo", "Contains harmful preservatives", "Shampoo") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_baby_hair_oil_included():
    """Test that baby hair oil is included (hair product, not baby bottle)"""
    assert is_crown_safe_recall("Baby Hair Oil Recall", "Rancid oils", "Hair Care") is True
    assert is_crown_safe_recall("Infant Hair Moisturizer", "Bacterial contamination", "Hair Product") is True


# ============================================================================
# FILTERING FUNCTION TESTS - CASE SENSITIVITY
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_case_insensitive():
    """Test that filtering is case-insensitive"""
    assert is_crown_safe_recall("HAIR RELAXER RECALL", "", "") is True
    assert is_crown_safe_recall("hair relaxer recall", "", "") is True
    assert is_crown_safe_recall("Hair Relaxer Recall", "", "") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_mixed_case_exclusion():
    """Test that exclusion keywords work with mixed case"""
    assert is_crown_safe_recall("BABY BOTTLE RECALL", "", "") is False
    assert is_crown_safe_recall("Baby Bottle recall", "", "") is False


# ============================================================================
# FILTERING FUNCTION TESTS - MULTIPLE CRITERIA
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_filter_title_only():
    """Test filtering based on title only"""
    assert is_crown_safe_recall("Hair Straightener Recall", "", "") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_description_only():
    """Test filtering based on description only"""
    assert is_crown_safe_recall("Product Recall", "This shampoo contains harmful chemicals", "") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_category_only():
    """Test filtering based on category only"""
    assert is_crown_safe_recall("Product Recall", "", "Hair Treatment") is True


@pytest.mark.unit
@pytest.mark.agents
def test_filter_combined_criteria():
    """Test filtering with all criteria matching"""
    assert (
        is_crown_safe_recall(
            "DevaCurl Shampoo Recall",
            "Hair loss and scalp irritation reported",
            "Hair Care Product",
        )
        is True
    )


# ============================================================================
# SEVERITY MAPPING TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_severity_hair_loss_critical():
    """Test that hair_loss is mapped to CRITICAL"""
    assert SEVERITY_MAPPING.get("hair_loss") == "CRITICAL"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_chemical_burn_critical():
    """Test that chemical_burn is mapped to CRITICAL"""
    assert SEVERITY_MAPPING.get("chemical_burn") == "CRITICAL"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_scalp_burn_critical():
    """Test that scalp_burn is mapped to CRITICAL"""
    assert SEVERITY_MAPPING.get("scalp_burn") == "CRITICAL"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_formaldehyde_critical():
    """Test that formaldehyde is mapped to CRITICAL"""
    assert SEVERITY_MAPPING.get("formaldehyde") == "CRITICAL"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_lead_critical():
    """Test that lead is mapped to CRITICAL"""
    assert SEVERITY_MAPPING.get("lead") == "CRITICAL"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_allergic_reaction_high():
    """Test that allergic_reaction is mapped to HIGH"""
    assert SEVERITY_MAPPING.get("allergic_reaction") == "HIGH"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_contamination_high():
    """Test that contamination is mapped to HIGH"""
    assert SEVERITY_MAPPING.get("contamination") == "HIGH"


@pytest.mark.unit
@pytest.mark.agents
def test_severity_skin_irritation_medium():
    """Test that skin_irritation is mapped to MEDIUM"""
    assert SEVERITY_MAPPING.get("skin_irritation") == "MEDIUM"


# ============================================================================
# CATEGORY CONFIGURATION TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.agents
def test_crown_safe_categories_complete():
    """Test that all expected hair product categories are present"""
    expected_categories = [
        "shampoo",
        "conditioner",
        "hair relaxer",
        "hair dye",
        "hair gel",
        "edge control",
        "scalp treatment",
    ]

    for category in expected_categories:
        assert category in CROWN_SAFE_CATEGORIES, f"Missing category: {category}"


@pytest.mark.unit
@pytest.mark.agents
def test_crown_safe_keywords_complete():
    """Test that all expected keywords are present"""
    expected_keywords = ["hair", "scalp", "shampoo", "conditioner", "relaxer", "cosmetic"]

    for keyword in expected_keywords:
        assert keyword in CROWN_SAFE_KEYWORDS, f"Missing keyword: {keyword}"


@pytest.mark.unit
@pytest.mark.agents
def test_exclude_keywords_complete():
    """Test that all baby product exclusion keywords are present"""
    expected_exclusions = ["baby bottle", "pacifier", "crib", "stroller", "car seat", "diaper"]

    for exclusion in expected_exclusions:
        assert exclusion in EXCLUDE_KEYWORDS, f"Missing exclusion: {exclusion}"


# ============================================================================
# EDGE CASES
# ============================================================================


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_empty_strings():
    """Test filtering with empty strings"""
    assert is_crown_safe_recall("", "", "") is False


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_whitespace_only():
    """Test filtering with whitespace only"""
    assert is_crown_safe_recall("   ", "  ", " ") is False


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_partial_keyword_match():
    """Test that partial keyword matching works"""
    # "shampoo" should match "shampooing" or "shampoos"
    assert is_crown_safe_recall("Shampooing Products Recall", "", "") is True


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_multiple_keywords():
    """Test recall with multiple matching keywords"""
    assert (
        is_crown_safe_recall(
            "Hair Relaxer and Shampoo Combo Pack",
            "Contains formaldehyde in relaxer and sulfates in shampoo",
            "Hair Care Bundle",
        )
        is True
    )


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_mixed_content():
    """Test recall with both hair and baby product mentions"""
    # Should be excluded if contains baby product exclusion keywords
    assert (
        is_crown_safe_recall(
            "Baby Bottle and Hair Brush Set",
            "Combo pack includes baby bottle and hair brush",
            "",
        )
        is False
    )


@pytest.mark.unit
@pytest.mark.edge_cases
def test_filter_unicode_characters():
    """Test filtering with unicode characters"""
    assert is_crown_safe_recall("Shampôo Recall - Hair Cāre Product", "", "") is True


# ============================================================================
# REAL-WORLD RECALL EXAMPLES
# ============================================================================


@pytest.mark.unit
@pytest.mark.integration
def test_filter_devacurl_recall():
    """Test filtering of real DevaCurl recall"""
    assert (
        is_crown_safe_recall(
            "DevaCurl No-Poo Cleanser and One Condition",
            (
                "Multiple reports of hair loss, scalp irritation, and damage. "
                "Investigation ongoing for harmful ingredients."
            ),
            "Hair Care Product",
        )
        is True
    )


@pytest.mark.unit
@pytest.mark.integration
def test_filter_wen_recall():
    """Test filtering of real WEN recall"""
    assert (
        is_crown_safe_recall(
            "WEN Cleansing Conditioner",
            "Reports of hair loss, balding, scalp irritation, and rash",
            "Hair Cleanser",
        )
        is True
    )


@pytest.mark.unit
@pytest.mark.integration
def test_filter_just_for_me_relaxer_recall():
    """Test filtering of hair relaxer recall"""
    assert (
        is_crown_safe_recall(
            "Just For Me No-Lye Relaxer",
            "Chemical burns and scalp damage reported",
            "Hair Relaxer",
        )
        is True
    )


@pytest.mark.unit
@pytest.mark.integration
def test_filter_graco_car_seat_not_included():
    """Test that car seat recalls are not included"""
    assert (
        is_crown_safe_recall(
            "Graco Infant Car Seat Recall",
            "Harness buckle may not properly secure child",
            "Child Safety Product",
        )
        is False
    )
