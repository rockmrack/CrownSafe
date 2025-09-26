from fastapi.testclient import TestClient
from api.main_babyshield import app
import uuid

# monkeypatch helpers from your code if needed:
from api.routers import chat as chat_router

class DummyLLM:
    def chat_json(self, **kwargs):
        # Minimal, schema-conformant response for tests
        return {
            "summary": "Quick summary for testing.",
            "reasons": ["Test reason"],
            "checks": ["Check label"],
            "flags": ["soft_cheese"] if "cheese" in str(kwargs.get("user","")).lower() else [],
            "disclaimer": "Not medical advice.",
            "jurisdiction": {"code":"EU","label":"EU Safety Gate"},
            "evidence": [],
        }

def _fake_scan(product="Brie", extra=None):
    base = {"product_name": product, "category": "cheese", "ingredients": ["milk"], "flags": ["soft_cheese"], "recalls_found": 0}
    if extra: base.update(extra)
    return base

def test_conversation_pregnancy(monkeypatch):
    # Wire LLM + fetch_scan_data
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan("Brie Président"))
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"Is this safe in pregnancy?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] in ("pregnancy_risk","ingredient_info")
    assert "message" in body and "summary" in body["message"]
    assert body["tool_calls"][0]["ok"] is True

def test_conversation_allergy(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan(extra={"profile":{"allergies":["peanut"]},"ingredients":["sugar","peanuts","cocoa"]}))
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"My kid has a peanut allergy"})
    assert r.status_code == 200
    assert "message" in r.json()

def test_conversation_recall_details(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan(extra={"recalls_found":1,"recalls":[{"id":"123","agency":"CPSC","date":"2023-01-01"}]}))
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"Tell me about the recall"})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert body["tool_calls"][0]["ok"] is True

def test_conversation_age_appropriateness(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan(extra={"age_min_months":0,"category":"feeding"}))
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"Is this suitable for newborns?"})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert body["tool_calls"][0]["ok"] is True

def test_conversation_ingredient_info(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan(extra={"ingredients":["milk","sugar","vanilla"],"ingredients_notes":"Natural flavoring"}))
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"What ingredients does this contain?"})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert body["tool_calls"][0]["ok"] is True

def test_conversation_alternatives(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"What are some safer alternatives?"})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    assert body["tool_calls"][0]["ok"] is True

def test_conversation_unclear_intent(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"Random unclear question"})
    assert r.status_code == 200
    body = r.json()
    assert "message" in body
    # unclear_intent should still work but with empty tool facts

def test_conversation_diagnostic_headers(monkeypatch):
    monkeypatch.setattr(chat_router, "get_llm_client", lambda: DummyLLM())
    monkeypatch.setattr(chat_router, "fetch_scan_data", lambda db, sid: _fake_scan())
    client = TestClient(app)
    r = client.post("/api/v1/chat/conversation", json={"scan_id":"abc","user_query":"Is this safe?"})
    assert r.status_code == 200
    
    # Check diagnostic headers
    assert "X-Chat-Latency-Ms" in r.headers
    assert "X-Chat-Remaining-Ms" in r.headers
    assert "X-Chat-Intent" in r.headers
    assert "X-Chat-Tool-Ok" in r.headers
    assert "X-Trace-Id" in r.headers
