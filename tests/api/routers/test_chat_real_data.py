import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from api.main_babyshield import app
from db.models.scan_history import ScanHistory
from agents.chat.chat_agent.agent_logic import ChatAgentLogic


class TestChatWithRealData:
    """Test chat endpoints using real database data without monkeypatching fetch_scan_data"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def _create_test_scan(self, db: Session, scan_id: str = None) -> ScanHistory:
        """Helper to create a test scan record in the database"""
        if scan_id is None:
            scan_id = f"test_scan_{uuid4().hex[:8]}"
        
        scan = ScanHistory(
            user_id=1,  # Assuming user ID 1 exists
            scan_id=scan_id,
            scan_timestamp=datetime.utcnow(),
            product_name="Test Baby Formula",
            brand="TestBrand",
            barcode="123456789012",
            model_number="TF-001",
            upc_gtin="123456789012",
            category="baby_food",
            scan_type="barcode",
            confidence_score=0.95,
            barcode_format="ean13",
            verdict="No Recalls Found",
            risk_level="low",
            recalls_found=0,
            recall_ids=[],
            agencies_checked="39+ (No recalls found)",
            allergen_alerts=["milk", "soy"],
            pregnancy_warnings=[],
            age_warnings=["0-12 months"]
        )
        
        db.add(scan)
        db.commit()
        db.refresh(scan)
        return scan
    
    @patch("api.routers.chat.get_db")
    @patch("api.routers.chat.ChatAgentLogic")
    def test_explain_result_with_real_scan_data(self, mock_chat_agent_class, mock_get_db):
        """Test /explain-result endpoint with real scan data from database"""
        # Setup mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Create test scan data
        test_scan = ScanHistory(
            scan_id="real_test_scan_123",
            user_id=1,
            scan_timestamp=datetime.utcnow(),
            product_name="Gerber Baby Formula",
            brand="Gerber",
            barcode="012000123456",
            model_number="GBF-001",
            upc_gtin="012000123456",
            category="baby_food",
            scan_type="barcode",
            confidence_score=0.98,
            barcode_format="ean13",
            verdict="No Recalls Found",
            risk_level="low",
            recalls_found=0,
            recall_ids=[],
            agencies_checked="39+ (No recalls found)",
            allergen_alerts=["milk"],
            pregnancy_warnings=[],
            age_warnings=[]
        )
        
        # Mock the database query to return our test scan
        mock_db.query.return_value.filter.return_value.first.return_value = test_scan
        
        # Setup mock chat agent
        mock_agent = MagicMock()
        mock_agent.synthesize_result.return_value = {
            "summary": "This baby formula appears safe with no recalls found.",
            "reasons": [
                "No active recalls found in FDA database",
                "Product from established manufacturer"
            ],
            "checks": [
                "Verify expiration date on package",
                "Check for any visible damage to container"
            ],
            "flags": ["allergen_milk"],
            "disclaimer": "Not medical advice. Consult pediatrician for feeding guidance.",
            "jurisdiction": {"code": "US", "label": "US FDA"},
            "evidence": []
        }
        mock_chat_agent_class.return_value = mock_agent
        
        # Make request
        response = self.client.post(
            "/api/v1/chat/explain-result",
            json={"scan_id": "real_test_scan_123"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify structured response
        assert "summary" in data
        assert "reasons" in data
        assert "checks" in data
        assert "flags" in data
        assert "disclaimer" in data
        
        # Verify the synthesize_result was called with properly normalized scan data
        mock_agent.synthesize_result.assert_called_once()
        call_args = mock_agent.synthesize_result.call_args[0][0]
        
        # Verify key fields are present and normalized
        assert call_args["product_name"] == "Gerber Baby Formula"
        assert call_args["brand"] == "Gerber"
        assert call_args["category"] == "baby_food"
        assert call_args["recalls_found"] == 0
        assert call_args["flags"] == ["allergen_milk"]  # Normalized from allergen_alerts
        assert call_args["allergens"] == ["milk"]
        assert isinstance(call_args["ingredients"], list)  # Should be empty list, not None
        assert isinstance(call_args["recalls"], list)  # Should be empty list, not None
        
    @patch("api.routers.chat.get_db")
    @patch("api.routers.chat.ChatAgentLogic")
    @patch("api.routers.chat.get_or_create_conversation")
    @patch("api.routers.chat.get_profile")
    @patch("api.routers.chat.log_message")
    @patch("api.routers.chat.run_tool_for_intent")
    def test_conversation_with_real_scan_data(
        self, mock_tool, mock_log, mock_profile, mock_conv, mock_chat_agent_class, mock_get_db
    ):
        """Test /conversation endpoint with real scan data from database"""
        # Setup mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Create test scan with recall
        test_scan = ScanHistory(
            scan_id="real_conv_test_456",
            user_id=1,
            scan_timestamp=datetime.utcnow(),
            product_name="Fisher-Price Rock 'n Play",
            brand="Fisher-Price",
            barcode="027084567890",
            model_number="FPR-123",
            upc_gtin="027084567890",
            category="baby_gear",
            scan_type="barcode",
            confidence_score=0.99,
            barcode_format="ean13",
            verdict="Recall Alert",
            risk_level="critical",
            recalls_found=1,
            recall_ids=["CPSC-2019-001"],
            agencies_checked="39+ (1 recall found)",
            allergen_alerts=[],
            pregnancy_warnings=[],
            age_warnings=["0-6 months"]
        )
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = test_scan
        
        # Setup other mocks
        mock_conv.return_value = MagicMock(id="conv-456")
        mock_profile.return_value = {"allergies": [], "consent_personalization": True}
        mock_tool.return_value = {"recall_details": {"recalls_found": 1, "batch_check": "Verify model number"}}
        
        # Setup mock chat agent
        mock_agent = MagicMock()
        mock_agent.classify_intent.return_value = "recall_details"
        mock_chat_agent_class.return_value = mock_agent
        
        # Enable feature flag for this test
        with patch("core.feature_flags.chat_enabled_for", return_value=True):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "real_conv_test_456",
                    "user_query": "Is this product safe? I heard there might be recalls."
                }
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify conversation response structure
        assert "intent" in data
        assert "message" in data
        assert "trace_id" in data
        assert "tool_calls" in data
        
        # Verify intent classification was called
        mock_agent.classify_intent.assert_called_once_with("Is this product safe? I heard there might be recalls.")
        
        # Verify tool was called with normalized scan data
        mock_tool.assert_called_once()
        call_kwargs = mock_tool.call_args.kwargs
        scan_data = call_kwargs["scan_data"]
        
        # Verify scan data normalization
        assert scan_data["product_name"] == "Fisher-Price Rock 'n Play"
        assert scan_data["recalls_found"] == 1
        assert scan_data["risk_level"] == "critical"
        assert scan_data["flags"] == ["recall_found", "age_0-6 months"]  # Built from recalls + age warnings
        assert isinstance(scan_data["ingredients"], list)
        assert isinstance(scan_data["allergens"], list)
    
    @patch("api.routers.chat.get_db")
    def test_explain_result_scan_not_found(self, mock_get_db):
        """Test /explain-result returns 404 for non-existent scan_id"""
        # Setup mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock query to return None (scan not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        response = self.client.post(
            "/api/v1/chat/explain-result",
            json={"scan_id": "nonexistent_scan_999"}
        )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "scan_id not found"
    
    @patch("api.routers.chat.get_db")
    def test_conversation_scan_not_found(self, mock_get_db):
        """Test /conversation returns 404 for non-existent scan_id"""
        # Setup mock database session
        mock_db = MagicMock(spec=Session)
        mock_get_db.return_value = mock_db
        
        # Mock query to return None (scan not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Enable feature flag for this test
        with patch("core.feature_flags.chat_enabled_for", return_value=True):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "nonexistent_scan_888",
                    "user_query": "Tell me about this product"
                }
            )
        
        assert response.status_code == 404
        assert response.json()["detail"] == "scan_id not found"
    
    def test_defensive_defaults_with_minimal_scan_data(self):
        """Test that fetch_scan_data handles minimal scan data gracefully"""
        from api.routers.chat import fetch_scan_data
        
        # Create minimal scan record
        minimal_scan = ScanHistory(
            scan_id="minimal_test",
            user_id=1
            # Most fields left as None/default
        )
        
        # Mock database session
        mock_db = MagicMock(spec=Session)
        mock_db.query.return_value.filter.return_value.first.return_value = minimal_scan
        
        result = fetch_scan_data(mock_db, "minimal_test")
        
        # Verify defensive defaults are applied
        assert result is not None
        assert result["product_name"] == "Unknown Product"
        assert result["brand"] == "Unknown Brand"
        assert result["category"] == "general"
        assert result["scan_type"] == "barcode"
        assert result["recalls_found"] == 0
        assert result["risk_level"] == "low"
        assert isinstance(result["flags"], list)
        assert isinstance(result["ingredients"], list)
        assert isinstance(result["allergens"], list)
        assert result["jurisdiction"]["code"] == "US"
