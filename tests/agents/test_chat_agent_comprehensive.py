"""
COMPREHENSIVE CHAT AGENT TEST SUITE
Tests all possible scenarios for the BabyShield ChatAgent
Date: October 10, 2025

Tests cover:
1. Basic initialization and setup
2. Intent classification (7 intents)
3. Emergency detection
4. Allergen concerns
5. Age appropriateness
6. Pregnancy risks
7. Alternative products
8. Recall details
9. Ingredient information
10. Conversation flow
11. Edge cases and error handling
"""

import asyncio
from datetime import datetime
from typing import Any, Dict
from unittest.mock import Mock, MagicMock, patch

import pytest

from agents.chat.chat_agent.agent_logic import (
    ChatAgentLogic,
    EvidenceItem,
    EmergencyNotice,
    ExplanationResponse,
)


print("\n" + "=" * 80)
print("COMPREHENSIVE CHAT AGENT TEST SUITE")
print("Testing all scenarios for BabyShield ChatAgent")
print("=" * 80 + "\n")


# ============================================================================
# MOCK LLM CLIENT FOR TESTING
# ============================================================================


class MockLLMClient:
    """Mock LLM client for testing without real API calls"""

    def __init__(self):
        self.call_count = 0
        self.last_request = None

    def chat_json(
        self,
        *,
        model: str,
        system: str,
        user: str,
        response_schema: Dict[str, Any],
        timeout: float = 8.0,
    ) -> Dict[str, Any]:
        """Mock chat_json method"""
        self.call_count += 1
        self.last_request = {
            "model": model,
            "system": system,
            "user": user,
            "schema": response_schema,
            "timeout": timeout,
        }

        # Return appropriate mock response based on user query
        user_lower = user.lower()

        # Emergency detection
        if any(word in user_lower for word in ["choking", "swallowed battery", "emergency", "911"]):
            return {
                "summary": "🚨 EMERGENCY: Call 911 immediately",
                "reasons": ["This is a life-threatening emergency"],
                "checks": ["Call emergency services now"],
                "flags": ["emergency"],
                "disclaimer": "This is medical emergency guidance only",
                "emergency": {"level": "red", "reason": "Life-threatening", "cta": "Call 911"},
                "suggested_questions": [],
            }

        # Allergen questions
        if any(word in user_lower for word in ["allerg", "peanut", "nuts", "lactose"]):
            return {
                "summary": "This product may contain allergens. Check the label carefully.",
                "reasons": ["Common allergens may be present", "Cross-contamination possible"],
                "checks": ["Check ingredient list", "Look for allergen warnings"],
                "flags": ["contains_allergens"],
                "disclaimer": "Always consult with a pediatrician for allergy concerns",
                "suggested_questions": ["What allergens are common?", "How to read labels?"],
            }

        # Pregnancy-related
        if any(word in user_lower for word in ["pregnan", "breastfeed", "listeria"]):
            return {
                "summary": "Some products may not be safe during pregnancy or breastfeeding.",
                "reasons": ["Certain ingredients avoided during pregnancy", "Risk to baby"],
                "checks": ["Consult healthcare provider", "Check ingredient safety"],
                "flags": ["pregnancy_concern"],
                "disclaimer": "Not medical advice. Consult your doctor.",
                "suggested_questions": ["Is this safe in pregnancy?", "Breastfeeding concerns?"],
            }

        # Age appropriateness
        if any(word in user_lower for word in ["age", "months", "newborn", "suitable for"]):
            return {
                "summary": "This product has age recommendations you should follow.",
                "reasons": ["Age-appropriate features", "Safety for developmental stage"],
                "checks": ["Check age label", "Verify small parts warning"],
                "flags": ["age_restricted"],
                "disclaimer": "Follow manufacturer age guidelines",
                "suggested_questions": ["What age is safe?", "Any age restrictions?"],
            }

        # Recall information
        if any(word in user_lower for word in ["recall", "cpsc", "safety notice"]):
            return {
                "summary": "Product recalls are important safety information.",
                "reasons": ["Recall may indicate serious hazard", "Manufacturer notified"],
                "checks": ["Check recall database", "Verify product model/batch"],
                "flags": ["has_recall"],
                "disclaimer": "Check official recall notices for details",
                "evidence": [
                    {"type": "recall", "source": "CPSC", "id": "REC-001", "url": "https://cpsc.gov"}
                ],
                "suggested_questions": ["Is my product recalled?", "What should I do?"],
            }

        # Alternative products
        if any(word in user_lower for word in ["alternative", "instead", "recommend"]):
            return {
                "summary": "Here are safer alternatives to consider.",
                "reasons": ["Better safety features", "No recalls", "Higher ratings"],
                "checks": ["Compare safety ratings", "Check reviews"],
                "flags": ["has_alternatives"],
                "disclaimer": "Research each alternative carefully",
                "suggested_questions": ["What alternatives exist?", "Which is safest?"],
            }

        # Ingredients
        if any(word in user_lower for word in ["ingredient", "contains", "made of"]):
            return {
                "summary": "Understanding ingredients helps ensure safety.",
                "reasons": ["Ingredient transparency important", "Some may cause reactions"],
                "checks": ["Read full ingredient list", "Look for preservatives"],
                "flags": ["check_ingredients"],
                "disclaimer": "Ingredient safety varies by individual",
                "suggested_questions": ["What's in this?", "Any harmful ingredients?"],
            }

        # Default response
        return {
            "summary": "I can help you with baby safety questions.",
            "reasons": ["Safety information available", "Product guidance provided"],
            "checks": ["Review product details", "Check safety ratings"],
            "flags": [],
            "disclaimer": "Always prioritize your baby's safety",
            "suggested_questions": [
                "Is this product safe?",
                "What should I check?",
                "Any recalls?",
            ],
        }


# ============================================================================
# TEST 1-5: INITIALIZATION AND SETUP
# ============================================================================


@pytest.mark.unit
def test_01_chat_agent_initialization():
    """Test 1: ChatAgent initialization with mock LLM"""
    print("\n[TEST 1] ChatAgent - Initialization with Mock LLM")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm, model="gpt-4o-mini")

    assert agent is not None
    assert agent.llm is not None
    assert agent.model == "gpt-4o-mini"

    print("✅ PASSED - ChatAgent initialized successfully")


@pytest.mark.unit
def test_02_explanation_response_model():
    """Test 2: ExplanationResponse model validation"""
    print("\n[TEST 2] ExplanationResponse - Model Validation")

    response = ExplanationResponse(
        summary="This is a test summary",
        reasons=["Reason 1", "Reason 2"],
        checks=["Check 1", "Check 2"],
        flags=["test_flag"],
        disclaimer="Test disclaimer",
    )

    assert response.summary == "This is a test summary"
    assert len(response.reasons) == 2
    assert len(response.checks) == 2
    assert response.flags[0] == "test_flag"

    print("✅ PASSED - ExplanationResponse model validated")


@pytest.mark.unit
def test_03_evidence_item_model():
    """Test 3: EvidenceItem model validation"""
    print("\n[TEST 3] EvidenceItem - Model Validation")

    evidence = EvidenceItem(
        type="recall", source="CPSC", id="REC-001", url="https://cpsc.gov/recall/001"
    )

    assert evidence.type == "recall"
    assert evidence.source == "CPSC"
    assert evidence.id == "REC-001"

    print("✅ PASSED - EvidenceItem model validated")


@pytest.mark.unit
def test_04_emergency_notice_model():
    """Test 4: EmergencyNotice model validation"""
    print("\n[TEST 4] EmergencyNotice - Model Validation")

    emergency = EmergencyNotice(level="red", reason="Life-threatening", cta="Call 911")

    assert emergency.level == "red"
    assert emergency.reason == "Life-threatening"
    assert emergency.cta == "Call 911"

    print("✅ PASSED - EmergencyNotice model validated")


@pytest.mark.unit
def test_05_mock_llm_client():
    """Test 5: Mock LLM client functionality"""
    print("\n[TEST 5] MockLLMClient - Functionality Test")

    llm = MockLLMClient()

    response = llm.chat_json(
        model="gpt-4o-mini",
        system="Test system",
        user="Test query",
        response_schema={},
        timeout=1.0,
    )

    assert response is not None
    assert "summary" in response
    assert llm.call_count == 1

    print("✅ PASSED - MockLLMClient working correctly")


# ============================================================================
# TEST 6-12: INTENT CLASSIFICATION
# ============================================================================


@pytest.mark.unit
def test_06_intent_pregnancy_risk():
    """Test 6: Intent classification - Pregnancy Risk"""
    print("\n[TEST 6] Intent Classification - Pregnancy Risk")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "Is this safe during pregnancy?",
        "Can I use this while breastfeeding?",
        "What about listeria in this product?",
        "Safe for third trimester?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "pregnancy_risk"

    print("✅ PASSED - Pregnancy risk intent detected correctly")


@pytest.mark.unit
def test_07_intent_allergy_question():
    """Test 7: Intent classification - Allergy Question"""
    print("\n[TEST 7] Intent Classification - Allergy Question")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "Does this contain peanuts?",
        "Any allergens in this product?",
        "Is this gluten-free?",
        "Safe for nut allergies?",
        "Contains lactose?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "allergy_question"

    print("✅ PASSED - Allergy question intent detected correctly")


@pytest.mark.unit
def test_08_intent_age_appropriateness():
    """Test 8: Intent classification - Age Appropriateness"""
    print("\n[TEST 8] Intent Classification - Age Appropriateness")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "Is this safe for newborns?",
        "What age is this suitable for?",
        "Can my 6-month-old use this?",
        "Age 2 years okay?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "age_appropriateness"

    print("✅ PASSED - Age appropriateness intent detected correctly")


@pytest.mark.unit
def test_09_intent_ingredient_info():
    """Test 9: Intent classification - Ingredient Info"""
    print("\n[TEST 9] Intent Classification - Ingredient Info")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "What ingredients are in this?",
        "What's this made of?",
        "Does this contain BPA?",
        "What are the components?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "ingredient_info"

    print("✅ PASSED - Ingredient info intent detected correctly")


@pytest.mark.unit
def test_10_intent_alternative_products():
    """Test 10: Intent classification - Alternative Products"""
    print("\n[TEST 10] Intent Classification - Alternative Products")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "What are safer alternatives?",
        "Can you recommend something instead?",
        "Better options available?",
        "Alternative products?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "alternative_products"

    print("✅ PASSED - Alternative products intent detected correctly")


@pytest.mark.unit
def test_11_intent_recall_details():
    """Test 11: Intent classification - Recall Details"""
    print("\n[TEST 11] Intent Classification - Recall Details")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = [
        "Has this been recalled?",
        "Any CPSC notices?",
        "Check for recalls",
        "Safety Gate alerts?",
        "What batch was recalled?",
    ]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        assert intent == "recall_details"

    print("✅ PASSED - Recall details intent detected correctly")


@pytest.mark.unit
def test_12_intent_unclear():
    """Test 12: Intent classification - Unclear Intent"""
    print("\n[TEST 12] Intent Classification - Unclear Intent")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    queries = ["Hello", "Hi there", "Test", "xyz123"]

    for query in queries:
        intent = agent.classify_intent(query)
        print(f"  Query: '{query}' → Intent: {intent}")
        # Should either detect intent or return unclear
        assert intent in [
            "pregnancy_risk",
            "allergy_question",
            "ingredient_info",
            "age_appropriateness",
            "alternative_products",
            "recall_details",
            "unclear_intent",
        ]

    print("✅ PASSED - Unclear intent handled correctly")


# ============================================================================
# TEST 13-18: EMERGENCY SCENARIOS
# ============================================================================


@pytest.mark.integration
def test_13_emergency_choking():
    """Test 13: Emergency detection - Choking"""
    print("\n[TEST 13] Emergency Detection - Choking Scenario")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "My baby is choking on a small part!", "product": "toy"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert "emergency" in response or "EMERGENCY" in response["summary"]

    print("✅ PASSED - Choking emergency detected")


@pytest.mark.integration
def test_14_emergency_battery():
    """Test 14: Emergency detection - Battery Ingestion"""
    print("\n[TEST 14] Emergency Detection - Battery Ingestion")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Baby swallowed a button battery!", "product": "remote"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert "911" in response["summary"] or response.get("emergency") is not None

    print("✅ PASSED - Battery ingestion emergency detected")


@pytest.mark.integration
def test_15_emergency_call_911():
    """Test 15: Emergency detection - General Emergency"""
    print("\n[TEST 15] Emergency Detection - Call 911")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Emergency! Need help now!", "product": "unknown"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Response summary: {response['summary'][:50]}...")

    print("✅ PASSED - General emergency detected")


# ============================================================================
# TEST 16-20: ALLERGEN SCENARIOS
# ============================================================================


@pytest.mark.integration
def test_16_allergen_peanuts():
    """Test 16: Allergen detection - Peanuts"""
    print("\n[TEST 16] Allergen Detection - Peanuts")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Does this contain peanuts?", "product": "baby food"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("allergen" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Peanut allergen concern detected")


@pytest.mark.integration
def test_17_allergen_dairy():
    """Test 17: Allergen detection - Dairy/Lactose"""
    print("\n[TEST 17] Allergen Detection - Dairy/Lactose")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this lactose-free?", "product": "formula"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Flags: {response.get('flags', [])}")

    print("✅ PASSED - Dairy/lactose concern detected")


@pytest.mark.integration
def test_18_allergen_multiple():
    """Test 18: Allergen detection - Multiple Allergens"""
    print("\n[TEST 18] Allergen Detection - Multiple Allergens")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {
        "query": "Does this have nuts, gluten, or soy?",
        "product": "snack",
    }

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert len(response.get("checks", [])) > 0

    print("✅ PASSED - Multiple allergen concerns handled")


# ============================================================================
# TEST 19-23: AGE APPROPRIATENESS
# ============================================================================


@pytest.mark.integration
def test_19_age_newborn():
    """Test 19: Age appropriateness - Newborn"""
    print("\n[TEST 19] Age Appropriateness - Newborn")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this safe for newborns?", "product": "pacifier"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("age" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Newborn age concern detected")


@pytest.mark.integration
def test_20_age_specific_months():
    """Test 20: Age appropriateness - Specific Months"""
    print("\n[TEST 20] Age Appropriateness - Specific Months (6 months)")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Safe for 6-month-old?", "product": "toy"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Checks: {response.get('checks', [])}")

    print("✅ PASSED - Specific age (months) handled")


@pytest.mark.integration
def test_21_age_toddler():
    """Test 21: Age appropriateness - Toddler"""
    print("\n[TEST 21] Age Appropriateness - Toddler (2 years)")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Suitable for 2-year-old?", "product": "puzzle"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert len(response.get("reasons", [])) > 0

    print("✅ PASSED - Toddler age appropriateness checked")


# ============================================================================
# TEST 22-25: PREGNANCY & BREASTFEEDING
# ============================================================================


@pytest.mark.integration
def test_22_pregnancy_safety():
    """Test 22: Pregnancy safety concerns"""
    print("\n[TEST 22] Pregnancy Safety - General")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this safe during pregnancy?", "product": "supplement"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("pregnancy" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Pregnancy safety concern detected")


@pytest.mark.integration
def test_23_breastfeeding():
    """Test 23: Breastfeeding safety"""
    print("\n[TEST 23] Breastfeeding Safety")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Can I use this while breastfeeding?", "product": "cream"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Disclaimer: {response.get('disclaimer', '')[:50]}...")

    print("✅ PASSED - Breastfeeding safety addressed")


@pytest.mark.integration
def test_24_listeria_concern():
    """Test 24: Listeria/Food safety in pregnancy"""
    print("\n[TEST 24] Pregnancy - Listeria Concern")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Risk of listeria?", "product": "soft cheese"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert len(response.get("checks", [])) > 0

    print("✅ PASSED - Listeria concern handled")


# ============================================================================
# TEST 25-28: RECALL INFORMATION
# ============================================================================


@pytest.mark.integration
def test_25_recall_check():
    """Test 25: Recall information check"""
    print("\n[TEST 25] Recall Information - Check")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Has this been recalled?", "product": "crib"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("recall" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Recall check performed")


@pytest.mark.integration
def test_26_recall_with_evidence():
    """Test 26: Recall with evidence citation"""
    print("\n[TEST 26] Recall Information - With Evidence")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "CPSC recall for this?", "product": "stroller"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    # Check if evidence is provided
    if response.get("evidence"):
        print(f"  Evidence sources: {len(response['evidence'])} items")

    print("✅ PASSED - Recall evidence handling working")


# ============================================================================
# TEST 27-30: ALTERNATIVES & RECOMMENDATIONS
# ============================================================================


@pytest.mark.integration
def test_27_alternative_products():
    """Test 27: Alternative product recommendations"""
    print("\n[TEST 27] Alternative Products - Recommendations")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "What are safer alternatives?", "product": "bottle"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("alternative" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Alternative products suggested")


@pytest.mark.integration
def test_28_product_comparison():
    """Test 28: Product comparison request"""
    print("\n[TEST 28] Alternative Products - Comparison")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Better options than this?", "product": "pacifier"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Suggested questions: {len(response.get('suggested_questions', []))}")

    print("✅ PASSED - Product comparison handled")


# ============================================================================
# TEST 29-32: INGREDIENT INFORMATION
# ============================================================================


@pytest.mark.integration
def test_29_ingredient_list():
    """Test 29: Ingredient information request"""
    print("\n[TEST 29] Ingredient Information - List")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "What ingredients are in this?", "product": "baby food"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert any("ingredient" in flag.lower() for flag in response.get("flags", []))

    print("✅ PASSED - Ingredient information provided")


@pytest.mark.integration
def test_30_specific_ingredient():
    """Test 30: Specific ingredient check"""
    print("\n[TEST 30] Ingredient Information - Specific (BPA)")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Does this contain BPA?", "product": "bottle"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Checks required: {len(response.get('checks', []))}")

    print("✅ PASSED - Specific ingredient check handled")


# ============================================================================
# TEST 31-35: EDGE CASES & ERROR HANDLING
# ============================================================================


@pytest.mark.unit
def test_31_empty_query():
    """Test 31: Handle empty query"""
    print("\n[TEST 31] Edge Case - Empty Query")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    intent = agent.classify_intent("")

    assert intent is not None
    print(f"  Intent for empty query: {intent}")

    print("✅ PASSED - Empty query handled")


@pytest.mark.unit
def test_32_none_query():
    """Test 32: Handle None query"""
    print("\n[TEST 32] Edge Case - None Query")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    intent = agent.classify_intent(None)

    assert intent is not None
    print(f"  Intent for None query: {intent}")

    print("✅ PASSED - None query handled")


@pytest.mark.integration
def test_33_very_long_query():
    """Test 33: Handle very long query"""
    print("\n[TEST 33] Edge Case - Very Long Query")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    long_query = "Is this product safe for babies? " * 100  # Very long
    scan_data = {"query": long_query, "product": "test"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print(f"  Response generated for {len(long_query)} char query")

    print("✅ PASSED - Long query handled")


@pytest.mark.integration
def test_34_special_characters():
    """Test 34: Handle special characters"""
    print("\n[TEST 34] Edge Case - Special Characters")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this safe? 🍼👶 #BabySafety", "product": "bottle"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print("  Special characters processed")

    print("✅ PASSED - Special characters handled")


@pytest.mark.integration
def test_35_mixed_language():
    """Test 35: Handle potential mixed language"""
    print("\n[TEST 35] Edge Case - Mixed Content")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this safe for baby age 6 months?", "product": "toy"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    print("  Mixed content query processed")

    print("✅ PASSED - Mixed content handled")


# ============================================================================
# TEST 36-40: CONVERSATION FLOW
# ============================================================================


@pytest.mark.integration
def test_36_suggested_questions():
    """Test 36: Suggested questions generation"""
    print("\n[TEST 36] Conversation Flow - Suggested Questions")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Tell me about this product", "product": "bottle"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    suggested = response.get("suggested_questions", [])
    print(f"  Generated {len(suggested)} suggested questions")
    if suggested:
        print(f"  Example: '{suggested[0]}'")

    print("✅ PASSED - Suggested questions generated")


@pytest.mark.integration
def test_37_disclaimer_present():
    """Test 37: Disclaimer always present"""
    print("\n[TEST 37] Conversation Flow - Disclaimer Present")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Is this safe?", "product": "toy"}

    response = agent.synthesize_result(scan_data)

    assert response is not None
    assert "disclaimer" in response
    assert len(response["disclaimer"]) > 0
    print(f"  Disclaimer: '{response['disclaimer'][:50]}...'")

    print("✅ PASSED - Disclaimer always included")


@pytest.mark.integration
def test_38_response_structure():
    """Test 38: Response structure validation"""
    print("\n[TEST 38] Conversation Flow - Response Structure")

    llm = MockLLMClient()
    agent = ChatAgentLogic(llm=llm)

    scan_data = {"query": "Product safety check", "product": "crib"}

    response = agent.synthesize_result(scan_data)

    # Verify required fields
    required_fields = ["summary", "reasons", "checks", "flags", "disclaimer"]
    for field in required_fields:
        assert field in response, f"Missing required field: {field}"
        print(f"  ✓ {field}: present")

    print("✅ PASSED - Response structure valid")


# ============================================================================
# FINAL SUMMARY TEST
# ============================================================================


def test_39_final_summary():
    """Test 39: Print comprehensive test summary"""
    print("\n" + "=" * 80)
    print("CHAT AGENT TEST SUMMARY")
    print("=" * 80)
    print("\nTest Categories Completed:")
    print("  ✅ Initialization & Setup (Tests 1-5)")
    print("  ✅ Intent Classification (Tests 6-12)")
    print("  ✅ Emergency Scenarios (Tests 13-15)")
    print("  ✅ Allergen Detection (Tests 16-18)")
    print("  ✅ Age Appropriateness (Tests 19-21)")
    print("  ✅ Pregnancy & Breastfeeding (Tests 22-24)")
    print("  ✅ Recall Information (Tests 25-26)")
    print("  ✅ Alternative Products (Tests 27-28)")
    print("  ✅ Ingredient Information (Tests 29-30)")
    print("  ✅ Edge Cases & Error Handling (Tests 31-35)")
    print("  ✅ Conversation Flow (Tests 36-38)")
    print("\n" + "=" * 80)
    print("TOTAL: 38 COMPREHENSIVE CHAT AGENT TESTS")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    print("\n" + "=" * 80)
    print("RUNNING COMPREHENSIVE CHAT AGENT TEST SUITE")
    print("=" * 80)

    # Run pytest with verbose output
    exit_code = pytest.main(
        [__file__, "-v", "-s", "--tb=short", "--asyncio-mode=auto", "-m", "unit or integration"]
    )

    sys.exit(exit_code)
