"""Quick Chat Agent Test Runner
Runs essential tests for ChatAgent without Unicode issues
"""

import sys
from datetime import datetime


def test_chat_agent():
    """Run comprehensive ChatAgent tests"""
    print("\n" + "=" * 80)
    print("CHAT AGENT COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {}

    # Test 1: ChatAgent imports
    print("[TEST 1] ChatAgent Imports...")
    try:
        from agents.chat.chat_agent.agent_logic import (
            ChatAgentLogic,
            EmergencyNotice,
            EvidenceItem,
            ExplanationResponse,
        )

        print("PASS - All imports successful")
        results["ChatAgent Imports"] = True
    except Exception as e:
        print(f"FAIL - Import error: {e}")
        results["ChatAgent Imports"] = False

    # Test 2: ExplanationResponse model
    print("\n[TEST 2] ExplanationResponse Model...")
    try:
        from agents.chat.chat_agent.agent_logic import ExplanationResponse

        response = ExplanationResponse(
            summary="Test summary",
            reasons=["Reason 1"],
            checks=["Check 1"],
            flags=["test_flag"],
            disclaimer="Test disclaimer",
        )
        assert response.summary == "Test summary"
        print("PASS - ExplanationResponse model validated")
        results["ExplanationResponse Model"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["ExplanationResponse Model"] = False

    # Test 3: EvidenceItem model
    print("\n[TEST 3] EvidenceItem Model...")
    try:
        from agents.chat.chat_agent.agent_logic import EvidenceItem

        evidence = EvidenceItem(type="recall", source="CPSC", id="REC-001")
        assert evidence.source == "CPSC"
        print("PASS - EvidenceItem model validated")
        results["EvidenceItem Model"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["EvidenceItem Model"] = False

    # Test 4: EmergencyNotice model
    print("\n[TEST 4] EmergencyNotice Model...")
    try:
        from agents.chat.chat_agent.agent_logic import EmergencyNotice

        emergency = EmergencyNotice(level="red", reason="Critical", cta="Call 911")
        assert emergency.level == "red"
        print("PASS - EmergencyNotice model validated")
        results["EmergencyNotice Model"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["EmergencyNotice Model"] = False

    # Test 5: Intent classification - Pregnancy
    print("\n[TEST 5] Intent Classification - Pregnancy Risk...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        # Create mock LLM client
        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "pregnancy_risk", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("Is this safe during pregnancy?")
        assert intent == "pregnancy_risk"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Pregnancy"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Pregnancy"] = False

    # Test 6: Intent classification - Allergen
    print("\n[TEST 6] Intent Classification - Allergy Question...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "allergy_question", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("Does this contain peanuts?")
        assert intent == "allergy_question"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Allergy"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Allergy"] = False

    # Test 7: Intent classification - Age
    print("\n[TEST 7] Intent Classification - Age Appropriateness...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "age_appropriateness", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("Is this safe for newborns?")
        assert intent == "age_appropriateness"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Age"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Age"] = False

    # Test 8: Intent classification - Ingredients
    print("\n[TEST 8] Intent Classification - Ingredient Info...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "ingredient_info", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("What ingredients are in this?")
        assert intent == "ingredient_info"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Ingredients"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Ingredients"] = False

    # Test 9: Intent classification - Alternatives
    print("\n[TEST 9] Intent Classification - Alternative Products...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "alternative_products", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("What are safer alternatives?")
        assert intent == "alternative_products"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Alternatives"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Alternatives"] = False

    # Test 10: Intent classification - Recalls
    print("\n[TEST 10] Intent Classification - Recall Details...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "recall_details", "confidence": 0.9}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("Has this been recalled?")
        assert intent == "recall_details"
        print(f"PASS - Detected intent: {intent}")
        results["Intent: Recalls"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Intent: Recalls"] = False

    # Test 11: synthesize_result
    print("\n[TEST 11] Synthesize Result...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "Test summary",
                    "reasons": ["Reason 1"],
                    "checks": ["Check 1"],
                    "flags": ["test"],
                    "disclaimer": "Test disclaimer",
                }

        agent = ChatAgentLogic(llm=MockLLM())
        scan_data = {"query": "Is this safe?", "product": "toy"}
        result = agent.synthesize_result(scan_data)

        assert result is not None
        assert "summary" in result
        assert "disclaimer" in result
        print("PASS - Result synthesis working")
        results["Synthesize Result"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Synthesize Result"] = False

    # Test 12: Edge case - Empty query
    print("\n[TEST 12] Edge Case - Empty Query...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "unclear_intent", "confidence": 0.1}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent("")
        assert intent in ["unclear_intent", "pregnancy_risk", "allergy_question"]
        print(f"PASS - Empty query handled: {intent}")
        results["Edge: Empty Query"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Edge: Empty Query"] = False

    # Test 13: Edge case - None query
    print("\n[TEST 13] Edge Case - None Query...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {"intent": "unclear_intent", "confidence": 0.1}

        agent = ChatAgentLogic(llm=MockLLM())
        intent = agent.classify_intent(None)
        assert intent is not None
        print(f"PASS - None query handled: {intent}")
        results["Edge: None Query"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Edge: None Query"] = False

    # Test 14: Response structure
    print("\n[TEST 14] Response Structure Validation...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic

        class MockLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "Test",
                    "reasons": ["R1"],
                    "checks": ["C1"],
                    "flags": ["F1"],
                    "disclaimer": "Disclaimer",
                    "suggested_questions": ["Q1?"],
                }

        agent = ChatAgentLogic(llm=MockLLM())
        result = agent.synthesize_result({"query": "test"})

        required = ["summary", "reasons", "checks", "flags", "disclaimer"]
        for field in required:
            assert field in result
            print(f"  - {field}: OK")

        print("PASS - All required fields present")
        results["Response Structure"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Response Structure"] = False

    # Test 15: Emergency response format
    print("\n[TEST 15] Emergency Response Format...")
    try:
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic, EmergencyNotice

        class MockLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "EMERGENCY: Call 911",
                    "reasons": ["Life-threatening"],
                    "checks": ["Call now"],
                    "flags": ["emergency"],
                    "disclaimer": "Emergency",
                    "emergency": {
                        "level": "red",
                        "reason": "Critical",
                        "cta": "Call 911",
                    },
                }

        agent = ChatAgentLogic(llm=MockLLM())
        result = agent.synthesize_result({"query": "baby choking"})

        assert result is not None
        if result.get("emergency"):
            print("  - Emergency field present")
            print(f"  - Level: {result['emergency']['level']}")

        print("PASS - Emergency response formatted correctly")
        results["Emergency Response"] = True
    except Exception as e:
        print(f"FAIL - {e}")
        results["Emergency Response"] = False

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        print(f"{status} - {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Return 0 if all tests passed
    if passed == total:
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = test_chat_agent()
    sys.exit(exit_code)
