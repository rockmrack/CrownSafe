import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

# We need to mock the dependencies before importing the router
with patch('api.routers.chat.get_llm_client') as mock_llm_client, \
     patch('api.routers.chat.get_db') as mock_get_db, \
     patch('api.routers.chat.fetch_scan_data') as mock_fetch_scan_data:
    
    # Mock the LLM client
    mock_llm = Mock()
    mock_llm.chat_json.return_value = {
        "summary": "Test summary from mock LLM",
        "reasons": ["Test reason 1", "Test reason 2"],
        "checks": ["Test check 1"],
        "flags": ["test_flag"],
        "disclaimer": "Test disclaimer"
    }
    mock_llm_client.return_value = mock_llm
    
    # Mock the database
    mock_get_db.return_value = Mock()
    
    # Mock the scan data fetcher
    def mock_scan_fetcher(db, scan_id):
        if scan_id == "valid_scan_123":
            return {
                "product_name": "Test Product",
                "barcode": "1234567890",
                "recalls_found": 0,
                "key_flags": ["contains_milk"],
                "scan_status": "completed"
            }
        return None
    
    mock_fetch_scan_data.side_effect = mock_scan_fetcher
    
    # Now import the router
    from api.routers.chat import router

# Create a test app
app = FastAPI()
app.include_router(router, prefix="/api/v1/chat")
client = TestClient(app)

def test_conversation_endpoint_success():
    """Test successful conversation endpoint call"""
    payload = {
        "scan_id": "valid_scan_123",
        "user_query": "Is this safe for pregnant women?",
        "conversation_id": "test_conv_123"
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "conversation_id" in data
    assert "intent" in data
    assert "message" in data
    assert "trace_id" in data
    assert "tool_calls" in data
    
    # Check specific values
    assert data["conversation_id"] == "test_conv_123"
    assert data["intent"] == "pregnancy_risk"
    assert data["message"]["summary"] is not None
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["name"] == "tool::pregnancy_risk"
    assert data["tool_calls"][0]["ok"] == False  # NotImplementedError expected
    assert "Wire PregnancyProductSafetyAgent" in data["tool_calls"][0]["error"]

def test_conversation_endpoint_scan_not_found():
    """Test conversation endpoint with invalid scan_id"""
    payload = {
        "scan_id": "invalid_scan_456",
        "user_query": "Is this safe?",
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 404
    assert "scan_id not found" in response.json()["detail"]

def test_conversation_endpoint_unclear_intent():
    """Test conversation endpoint with unclear intent"""
    payload = {
        "scan_id": "valid_scan_123",
        "user_query": "Random unclear question about stuff",
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["intent"] == "unclear_intent"
    # Should have no tool calls for unclear intent
    assert len(data["tool_calls"]) == 0

def test_conversation_endpoint_auto_conversation_id():
    """Test that conversation_id is auto-generated when not provided"""
    payload = {
        "scan_id": "valid_scan_123",
        "user_query": "Is this safe?",
        # No conversation_id provided
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have auto-generated conversation_id
    assert "conversation_id" in data
    assert len(data["conversation_id"]) > 0
    assert data["conversation_id"] != "test_conv_123"  # Should be different from manual ID

def test_conversation_request_validation():
    """Test request validation"""
    # Missing required fields
    response = client.post("/api/v1/chat/conversation", json={})
    assert response.status_code == 422  # Validation error
    
    # Invalid payload - empty scan_id should still be accepted by pydantic
    # but will fail at the scan_data lookup stage
    response = client.post("/api/v1/chat/conversation", json={
        "scan_id": "empty_scan",
        "user_query": "test query",
    })
    assert response.status_code == 404  # scan_id not found

def test_allergy_intent():
    """Test allergy question intent classification"""
    payload = {
        "scan_id": "valid_scan_123",
        "user_query": "Does this contain peanuts? My child has allergies.",
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "allergy_question"
    assert data["tool_calls"][0]["name"] == "tool::allergy_question"
    assert "Wire AllergySensitivityAgent" in data["tool_calls"][0]["error"]

def test_ingredient_intent():
    """Test ingredient info intent classification"""
    payload = {
        "scan_id": "valid_scan_123",
        "user_query": "What ingredients does this product contain?",
    }
    
    response = client.post("/api/v1/chat/conversation", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "ingredient_info"
    assert data["tool_calls"][0]["name"] == "tool::ingredient_info"
    assert "Provide ingredient breakdown facts" in data["tool_calls"][0]["error"]