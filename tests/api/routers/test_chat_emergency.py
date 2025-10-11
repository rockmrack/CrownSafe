import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main_babyshield import app
from api.routers.chat import looks_emergency, build_suggested_questions, EMERGENCY_TERMS
from uuid import uuid4


class TestEmergencyDetection:
    """Tests for emergency keyword detection"""

    def test_emergency_terms_detection(self):
        # Test positive cases
        emergency_phrases = [
            "My baby is choking",
            "Child stopped breathing",
            "Baby not breathing",
            "Swallowed a battery",
            "Ingested poison",
            "Having a seizure",
            "Severe allergic reaction",
            "Baby is unconscious",
            "Difficulty breathing",
            "Can't breathe",
            "Turning blue",
            "Chemical burn on skin",
            "Possible overdose",
        ]

        for phrase in emergency_phrases:
            assert looks_emergency(phrase), f"Should detect emergency in: {phrase}"
            assert looks_emergency(phrase.upper()), f"Should detect emergency (uppercase) in: {phrase}"

    def test_non_emergency_phrases(self):
        # Test negative cases
        normal_phrases = [
            "Is this safe in pregnancy?",
            "What age is this for?",
            "Any allergen concerns?",
            "Check the ingredients",
            "Normal breathing pattern",
            "Healthy baby sleeping",
            "Regular feeding schedule",
        ]

        for phrase in normal_phrases:
            assert not looks_emergency(phrase), f"Should NOT detect emergency in: {phrase}"

    def test_emergency_terms_completeness(self):
        # Ensure we have comprehensive coverage
        expected_terms = {
            "choking",
            "stopped breathing",
            "not breathing",
            "battery",
            "ingested",
            "swallowed",
            "poison",
            "seizure",
            "anaphylaxis",
            "severe reaction",
            "unconscious",
            "allergic reaction",
            "difficulty breathing",
            "can't breathe",
            "turning blue",
            "chemical burn",
            "overdose",
        }

        # All expected terms should be in EMERGENCY_TERMS
        for term in expected_terms:
            assert any(term in emergency_term for emergency_term in EMERGENCY_TERMS), f"Missing emergency term: {term}"

    def test_empty_or_none_input(self):
        assert not looks_emergency("")
        assert not looks_emergency(None)
        assert not looks_emergency("   ")


class TestSuggestedQuestions:
    """Tests for suggested questions builder"""

    def test_cheese_category_suggestions(self):
        questions = build_suggested_questions("cheese", {})
        assert "Is this safe in pregnancy?" in questions
        assert "Check pasteurisation?" in questions
        assert len(questions) <= 4

    def test_toy_category_suggestions(self):
        questions = build_suggested_questions("toy", {})
        assert "What age is this for?" in questions
        assert "Any small parts?" in questions
        assert len(questions) <= 4

    def test_cosmetic_category_suggestions(self):
        questions = build_suggested_questions("cosmetic", {})
        assert "Safe during pregnancy?" in questions
        assert "Any harsh ingredients?" in questions
        assert len(questions) <= 4

    def test_food_category_suggestions(self):
        questions = build_suggested_questions("food", {})
        assert "Any allergen concerns?" in questions
        assert "Safe for kids?" in questions
        assert len(questions) <= 4

    def test_generic_category_suggestions(self):
        questions = build_suggested_questions("unknown", {})
        assert "Is this safe in pregnancy?" in questions
        assert "Any allergy concerns?" in questions
        assert "What age is this for?" in questions
        assert len(questions) <= 4

    def test_profile_based_suggestions(self):
        # Test pregnant user
        profile_pregnant = {"is_pregnant": True}
        questions = build_suggested_questions("general", profile_pregnant)
        assert "Safe in pregnancy?" == questions[0]  # Should be first

        # Test user with allergies
        profile_allergies = {"allergies": ["peanut", "dairy"]}
        questions = build_suggested_questions("general", profile_allergies)
        assert "Safe for my allergies?" == questions[0]  # Should be first

    def test_unique_questions_only(self):
        # Test that duplicate questions are removed
        questions = build_suggested_questions("cheese", {"is_pregnant": True})
        assert len(questions) == len(set(questions)), "Should not have duplicate questions"

    def test_max_four_questions(self):
        # Even with profile additions, should not exceed 4
        profile = {"is_pregnant": True, "allergies": ["peanut", "dairy", "soy"]}
        questions = build_suggested_questions("cheese", profile)
        assert len(questions) <= 4


class TestEmergencyEndToEnd:
    """End-to-end tests for emergency detection in conversation endpoint"""

    @patch("api.routers.chat.get_llm_client")
    @patch("api.routers.chat.fetch_scan_data")
    @patch("core.auth.current_user")
    def test_emergency_phrase_triggers_red_strip(self, mock_user, mock_fetch, mock_llm):
        # Setup mocks
        mock_user.id = uuid4()
        mock_fetch.return_value = {
            "product_name": "Test Product",
            "category": "general",
            "recalls_found": 0,
            "flags": [],
            "ingredients": [],
            "profile": {},
        }

        # Mock LLM to return minimal response
        mock_llm_client = MagicMock()
        mock_llm_client.chat_json.return_value = {
            "summary": "Emergency detected.",
            "reasons": ["Urgent situation reported"],
            "checks": [],
            "flags": [],
            "disclaimer": "Seek immediate medical attention.",
        }
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)

        # Test emergency phrase
        response = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test_scan_123",
                "user_query": "My baby swallowed a battery",
            },
        )

        assert response.status_code == 200
        body = response.json()

        # Should have emergency block
        assert "emergency" in body["message"]
        assert body["message"]["emergency"]["level"] == "red"
        assert body["message"]["emergency"]["reason"] == "Possible urgent situation reported."
        assert body["message"]["emergency"]["cta"] == "Open Emergency Guidance"

    @patch("api.routers.chat.get_llm_client")
    @patch("api.routers.chat.fetch_scan_data")
    @patch("core.auth.current_user")
    def test_unclear_intent_provides_suggestions(self, mock_user, mock_fetch, mock_llm):
        # Setup mocks
        mock_user.id = uuid4()
        mock_fetch.return_value = {
            "product_name": "Cheese",
            "category": "cheese",
            "recalls_found": 0,
            "flags": [],
            "ingredients": [],
            "profile": {},
        }

        # Mock LLM to return unclear intent
        mock_llm_client = MagicMock()
        mock_llm_client.classify_intent.return_value = "unclear_intent"
        mock_llm_client.chat_json.return_value = {
            "summary": "I'm not sure what you're asking about.",
            "reasons": [],
            "checks": ["Check the label"],
            "flags": [],
            "disclaimer": "Please ask a more specific question.",
        }
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)

        response = client.post(
            "/api/v1/chat/conversation",
            json={"scan_id": "test_scan_123", "user_query": "hmmm"},
        )

        assert response.status_code == 200
        body = response.json()

        # Should have suggested questions
        assert "suggested_questions" in body["message"]
        assert len(body["message"]["suggested_questions"]) > 0
        assert body["intent"] == "unclear_intent"

    @patch("api.routers.chat.get_llm_client")
    @patch("api.routers.chat.fetch_scan_data")
    @patch("core.auth.current_user")
    def test_empty_state_adds_helpful_checks(self, mock_user, mock_fetch, mock_llm):
        # Setup mocks for empty state (no recalls, minimal flags)
        mock_user.id = uuid4()
        mock_fetch.return_value = {
            "product_name": "Safe Product",
            "category": "cheese",
            "recalls_found": 0,  # No recalls
            "flags": [],  # No flags
            "ingredients": ["milk"],
            "profile": {},
        }

        # Mock LLM to return minimal response
        mock_llm_client = MagicMock()
        mock_llm_client.classify_intent.return_value = "ingredient_info"
        mock_llm_client.chat_json.return_value = {
            "summary": "This product appears safe.",
            "reasons": ["No recalls found"],
            "checks": [],  # Empty checks - should be augmented
            "flags": [],
            "disclaimer": "Always check labels.",
        }
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)

        response = client.post(
            "/api/v1/chat/conversation",
            json={"scan_id": "test_scan_123", "user_query": "Is this safe?"},
        )

        assert response.status_code == 200
        body = response.json()

        # Should have at least 2 checks added for empty state
        assert len(body["message"]["checks"]) >= 2
        # Should include batch/lot check for empty states
        checks_text = " ".join(body["message"]["checks"])
        assert "batch" in checks_text.lower() or "lot" in checks_text.lower()

    @patch("api.routers.chat.get_llm_client")
    @patch("api.routers.chat.fetch_scan_data")
    @patch("core.auth.current_user")
    def test_unclear_loop_prevention(self, mock_user, mock_fetch, mock_llm):
        # Setup mocks
        mock_user.id = uuid4()
        mock_fetch.return_value = {
            "product_name": "Test Product",
            "category": "general",
            "recalls_found": 0,
            "flags": [],
            "ingredients": [],
            "profile": {},
        }

        mock_llm_client = MagicMock()
        mock_llm_client.classify_intent.return_value = "unclear_intent"
        mock_llm_client.chat_json.return_value = {
            "summary": "Still unclear.",
            "reasons": [],
            "checks": [],
            "flags": [],
            "disclaimer": "Please be more specific.",
        }
        mock_llm.return_value = mock_llm_client

        client = TestClient(app)

        # Second unclear request with header
        response = client.post(
            "/api/v1/chat/conversation",
            json={"scan_id": "test_scan_123", "user_query": "what?"},
            headers={"X-Chat-Unclear-Count": "1"},
        )

        assert response.status_code == 200
        body = response.json()

        # Should provide suggested questions but limit to 3
        assert "suggested_questions" in body["message"]
        assert len(body["message"]["suggested_questions"]) <= 3


if __name__ == "__main__":
    pytest.main([__file__])
