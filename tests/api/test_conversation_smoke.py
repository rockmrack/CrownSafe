import os
import uuid

# Enable chat feature for tests - MUST be set before importing app
os.environ["BS_FEATURE_CHAT_ENABLED"] = "true"
os.environ["BS_FEATURE_CHAT_ROLLOUT_PCT"] = "1.0"  # 100% rollout for tests

from fastapi.testclient import TestClient
from api.main_crownsafe import app

# monkeypatch helpers from your code if needed:
from api.routers import chat as chat_router


class DummyLLM:
    def chat_json(self, **kwargs):
        # Minimal, schema-conformant response for tests
        return {
            "summary": "Quick summary for testing.",
            "reasons": ["Test reason"],
            "checks": ["Check label"],
            "flags": ["soft_cheese"] if "cheese" in str(kwargs.get("user", "")).lower() else [],
            "disclaimer": "Not medical advice.",
            "jurisdiction": {"code": "EU", "label": "EU Safety Gate"},
            "evidence": [],
        }


def _fake_scan(product="Brie", extra=None):
    base = {
        "product_name": product,
        "category": "cheese",
        "ingredients": ["milk"],
        "flags": ["soft_cheese"],
        "recalls_found": 0,
    }
    if extra:
        base.update(extra)
    return base


def test_conversation_pregnancy(monkeypatch):
    # Wire LLM + fetch_scan_data
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan("Brie Président"))
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "Is this safe in pregnancy?",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Check new response format: {"success": True, "data": {...}, "traceId": "..."}
    assert body.get("success") is True
    assert "data" in body
    assert "answer" in body["data"]
    assert "conversation_id" in body["data"]


def test_conversation_allergy(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(
        chat_router,
        "fetch_scan_data",
        lambda db, sid: _fake_scan(
            extra={
                "profile": {"allergies": ["peanut"]},
                "ingredients": ["sugar", "peanuts", "cocoa"],
            }
        ),
    )
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "My kid has a peanut allergy",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_recall_details(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(
        chat_router,
        "fetch_scan_data",
        lambda db, sid: _fake_scan(
            extra={
                "recalls_found": 1,
                "recalls": [{"id": "123", "agency": "CPSC", "date": "2023-01-01"}],
            }
        ),
    )
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "Tell me about the recall",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_age_appropriateness(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(
        chat_router,
        "fetch_scan_data",
        lambda db, sid: _fake_scan(extra={"age_min_months": 0, "category": "feeding"}),
    )
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "Is this suitable for newborns?",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_ingredient_info(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(
        chat_router,
        "fetch_scan_data",
        lambda db, sid: _fake_scan(
            extra={
                "ingredients": ["milk", "sugar", "vanilla"],
                "ingredients_notes": "Natural flavoring",
            }
        ),
    )
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "What ingredients does this contain?",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_alternatives(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "What are some safer alternatives?",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_unclear_intent(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={
            "scan_id": "abc",
            "message": "Random unclear question",
            "user_id": "test-user-123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    assert "data" in body


def test_conversation_diagnostic_headers(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": "abc", "message": "Is this safe?", "user_id": "test-user-123"},
    )
    assert r.status_code == 200, f"Expected 200 but got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("success") is True
    # Note: Diagnostic headers may not be present in current implementation
    assert "X-Trace-Id" in r.headers
