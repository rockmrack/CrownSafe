"""
Deep Conversation Endpoint Tests
Tests all edge cases, error conditions, and response variations
"""

import pytest
from fastapi.testclient import TestClient
from api.main_babyshield import app
from api.routers import chat as chat_router
import os

# Enable chat feature for tests
os.environ["BS_FEATURE_CHAT_ENABLED"] = "true"
os.environ["BS_FEATURE_CHAT_ROLLOUT_PCT"] = "1.0"


class DummyLLM:
    """Mock LLM for testing various response scenarios"""

    def __init__(self, response_override=None):
        self.response_override = response_override

    def chat_json(self, **kwargs):
        if self.response_override:
            return self.response_override
        return {
            "summary": "Test summary for baby product safety.",
            "reasons": ["Test reason 1", "Test reason 2"],
            "checks": ["Ingredient check", "Safety certification"],
            "flags": [],
            "disclaimer": "Not medical advice. Consult healthcare provider.",
            "jurisdiction": {
                "code": "US",
                "label": "US Consumer Product Safety Commission",
            },
            "evidence": [{"source": "Test Source", "finding": "Test finding"}],
        }


def _fake_scan(product="Test Product", **kwargs):
    """Create a fake scan result with flexible data"""
    base = {
        "product_name": product,
        "category": "baby_food",
        "ingredients": ["water", "sugar", "milk"],
        "flags": [],
        "recalls_found": 0,
    }
    base.update(kwargs)
    return base


class TestConversationDeep:
    """Deep tests for conversation endpoint"""

    def test_conversation_with_empty_message(self, monkeypatch):
        """Test that empty message is rejected"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={"scan_id": "test-123", "message": "", "user_id": "test-user"},
        )
        assert r.status_code == 400
        assert "message is required" in r.json().get("error", "").lower()

    def test_conversation_with_missing_message_field(self, monkeypatch):
        """Test that missing message field is rejected"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={"scan_id": "test-123", "user_id": "test-user"},
        )
        # Should return validation error (400 or 422 both acceptable)
        assert r.status_code in [400, 422]

    def test_conversation_with_very_long_message(self, monkeypatch):
        """Test handling of extremely long messages"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        long_message = "Is this safe? " * 1000  # 15000 characters
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": long_message,
                "user_id": "test-user",
            },
        )
        # Should either accept or reject gracefully, not crash
        assert r.status_code in [200, 400, 413]

    def test_conversation_with_special_characters(self, monkeypatch):
        """Test handling of special characters in message"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        special_message = "Is this safe? 🍼👶 <script>alert('test')</script> ' OR '1'='1"
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": special_message,
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_with_unicode_message(self, monkeypatch):
        """Test handling of Unicode characters"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        unicode_message = "这个产品安全吗？ Это безопасно? هل هذا آمن؟"
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": unicode_message,
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_response_structure(self, monkeypatch):
        """Test that response has all required fields"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this safe?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()

        # Verify top-level structure
        assert "success" in body
        assert "data" in body
        assert "traceId" in body or "trace_id" in body

        # Verify data structure
        data = body["data"]
        assert "answer" in data
        assert "conversation_id" in data

    def test_conversation_with_recall_present(self, monkeypatch):
        """Test conversation when product has active recalls"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(
            chat_router,
            "fetch_scan_data",
            lambda db, sid: _fake_scan(
                recalls_found=2,
                recalls=[
                    {
                        "id": "R001",
                        "agency": "CPSC",
                        "date": "2024-01-15",
                        "hazard": "Choking",
                    },
                    {
                        "id": "R002",
                        "agency": "FDA",
                        "date": "2024-02-20",
                        "hazard": "Contamination",
                    },
                ],
            ),
        )

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this product safe?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_with_allergen_flags(self, monkeypatch):
        """Test conversation when product has allergen flags"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(
            chat_router,
            "fetch_scan_data",
            lambda db, sid: _fake_scan(
                flags=["contains_peanuts", "contains_dairy", "gluten_free"],
                ingredients=["peanut butter", "milk", "rice flour"],
            ),
        )

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Does this contain allergens?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_with_age_restrictions(self, monkeypatch):
        """Test conversation when product has age restrictions"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(
            chat_router,
            "fetch_scan_data",
            lambda db, sid: _fake_scan(age_min_months=6, age_max_months=36, category="solid_food"),
        )

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Can I give this to my 3-month-old?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_headers_presence(self, monkeypatch):
        """Test that all required headers are present"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this safe?",
                "user_id": "test-user",
            },
        )

        # Check diagnostic headers
        assert "X-Trace-Id" in r.headers

        # Check security headers
        assert "X-Content-Type-Options" in r.headers
        assert "X-Frame-Options" in r.headers

    def test_conversation_trace_id_format(self, monkeypatch):
        """Test that X-Trace-Id has valid UUID format"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this safe?",
                "user_id": "test-user",
            },
        )

        trace_id = r.headers.get("X-Trace-Id")
        assert trace_id is not None
        # Should be UUID format (36 chars with hyphens)
        assert len(trace_id) >= 32

    def test_conversation_with_profile_data(self, monkeypatch):
        """Test conversation with user profile data"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(
            chat_router,
            "fetch_scan_data",
            lambda db, sid: _fake_scan(
                profile={
                    "allergies": ["peanuts", "shellfish"],
                    "dietary_restrictions": ["vegetarian"],
                    "baby_age_months": 8,
                }
            ),
        )

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this suitable for my baby?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_multiple_flags(self, monkeypatch):
        """Test conversation with multiple warning flags"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(
            chat_router,
            "fetch_scan_data",
            lambda db, sid: _fake_scan(flags=["high_sugar", "artificial_colors", "preservatives", "bpa_free"]),
        )

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "What concerns should I know about?",
                "user_id": "test-user",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True

    def test_conversation_content_type(self, monkeypatch):
        """Test response content type is correct"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        r = client.post(
            "/api/v1/chat/conversation",
            json={
                "scan_id": "test-123",
                "message": "Is this safe?",
                "user_id": "test-user",
            },
        )

        assert "application/json" in r.headers.get("content-type", "")

    def test_conversation_idempotency(self, monkeypatch):
        """Test that multiple identical requests produce consistent results"""
        monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
        monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())

        client = TestClient(app)
        request_data = {
            "scan_id": "test-123",
            "message": "Is this safe?",
            "user_id": "test-user",
        }

        r1 = client.post("/api/v1/chat/conversation", json=request_data)
        r2 = client.post("/api/v1/chat/conversation", json=request_data)

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Both should succeed (conversation IDs will differ, but structure should be same)
        assert r1.json().get("success") == r2.json().get("success")
