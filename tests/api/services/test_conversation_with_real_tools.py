import pytest
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main_babyshield import app


class TestConversationWithRealTools:
    """End-to-end tests for conversation endpoint with real tools enabled"""
    
    def setup_method(self):
        self.client = TestClient(app)
        # Enable real tools for these tests
        self.original_env = os.environ.get("BS_USE_REAL_TOOLS")
        os.environ["BS_USE_REAL_TOOLS"] = "true"
    
    def teardown_method(self):
        # Restore original environment
        if self.original_env is not None:
            os.environ["BS_USE_REAL_TOOLS"] = self.original_env
        elif "BS_USE_REAL_TOOLS" in os.environ:
            del os.environ["BS_USE_REAL_TOOLS"]
    
    def test_conversation_with_real_tools_pregnancy(self):
        """Test conversation endpoint with real pregnancy tool enabled"""
        # We need to reload the module to pick up the environment change
        import importlib
        import api.services.chat_tools
        importlib.reload(api.services.chat_tools)
        
        from api.routers import chat as chat_router
        
        class DummyLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "This soft cheese may pose pregnancy risks unless pasteurised.",
                    "reasons": ["Soft cheeses can contain listeria bacteria", "Pasteurisation kills harmful bacteria"],
                    "checks": ["Check label for 'pasteurised' marking", "Consult healthcare provider"],
                    "flags": ["soft_cheese_pasteurisation"],
                    "disclaimer": "Not medical advice. Consult healthcare provider for pregnancy-specific dietary advice.",
                    "jurisdiction": {"code": "US", "label": "FDA"},
                    "evidence": []
                }
        
        def mock_fetch_scan_data(db, scan_id):
            return {
                "scan_id": scan_id,
                "product_name": "Brie Cheese",
                "category": "cheese",
                "flags": ["soft_cheese"],
                "ingredients": ["milk", "cultures", "salt"],
                "recalls_found": 0,
                "profile": None
            }
        
        # Mock the real agents used by adapters
        import api.services.chat_tools_real as real
        
        class FakePregnancyAgent:
            def __init__(self):
                self.logic = MagicMock()
        
        class FakeAllergyAgent:
            def __init__(self):
                self.logic = MagicMock()
        
        with patch.object(chat_router, "get_llm_client", return_value=DummyLLM()), \
             patch.object(chat_router, "fetch_scan_data", side_effect=mock_fetch_scan_data), \
             patch.object(chat_router, "get_or_create_conversation", return_value=MagicMock(id="conv-123")), \
             patch.object(chat_router, "get_profile", return_value=None), \
             patch.object(chat_router, "log_message"), \
             patch.object(real, "PregnancyProductSafetyAgent", FakePregnancyAgent), \
             patch.object(real, "AllergySensitivityAgent", FakeAllergyAgent), \
             patch("core.feature_flags.chat_enabled_for", return_value=True):
            
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test_brie_123",
                    "user_query": "Is this cheese safe during pregnancy?"
                }
            )
        
        # Verify response
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        
        # Verify conversation response structure
        assert "intent" in data
        assert "message" in data
        assert "trace_id" in data
        assert "tool_calls" in data
        assert "conversation_id" in data
        
        # Verify intent classification
        assert data["intent"] == "pregnancy_risk"
        
        # Verify tool calls were made
        tool_calls = data["tool_calls"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["ok"] is True
        assert tool_calls[0]["name"] == "tool::pregnancy_risk"
        
        # Verify message structure
        message = data["message"]
        assert "summary" in message
        assert "reasons" in message
        assert "checks" in message
        assert "flags" in message
        assert "disclaimer" in message
        
        # Should contain pregnancy-specific guidance
        assert "pregnancy" in message["summary"].lower() or "pasteur" in message["summary"].lower()
    
    def test_conversation_with_real_tools_allergy(self):
        """Test conversation endpoint with real allergy tool enabled"""
        # Reload modules to pick up environment changes
        import importlib
        import api.services.chat_tools
        importlib.reload(api.services.chat_tools)
        
        from api.routers import chat as chat_router
        
        class DummyLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "This product contains peanuts which match your allergy profile.",
                    "reasons": ["Peanuts detected in ingredient list", "Direct allergen match found"],
                    "checks": ["Verify all ingredients on label", "Check for cross-contamination warnings"],
                    "flags": ["contains_peanuts", "allergen_match"],
                    "disclaimer": "Not medical advice. Always read labels carefully.",
                    "jurisdiction": {"code": "US", "label": "FDA"},
                    "evidence": []
                }
        
        def mock_fetch_scan_data(db, scan_id):
            return {
                "scan_id": scan_id,
                "product_name": "Peanut Butter Cookies",
                "category": "snack",
                "flags": ["contains_peanuts"],
                "ingredients": ["flour", "peanuts", "sugar", "butter"],
                "recalls_found": 0,
                "profile": {"allergies": ["peanut", "tree_nut"], "consent_personalization": True}
            }
        
        # Mock the real agents
        import api.services.chat_tools_real as real
        
        class FakePregnancyAgent:
            def __init__(self):
                self.logic = MagicMock()
        
        class FakeAllergyAgent:
            def __init__(self):
                self.logic = MagicMock()
        
        with patch.object(chat_router, "get_llm_client", return_value=DummyLLM()), \
             patch.object(chat_router, "fetch_scan_data", side_effect=mock_fetch_scan_data), \
             patch.object(chat_router, "get_or_create_conversation", return_value=MagicMock(id="conv-456")), \
             patch.object(chat_router, "get_profile", return_value={"allergies": ["peanut"], "consent_personalization": True}), \
             patch.object(chat_router, "log_message"), \
             patch.object(real, "PregnancyProductSafetyAgent", FakePregnancyAgent), \
             patch.object(real, "AllergySensitivityAgent", FakeAllergyAgent), \
             patch("core.feature_flags.chat_enabled_for", return_value=True):
            
            response = self.client.post(
                "/api/v1/chat/conversation", 
                json={
                    "scan_id": "test_peanut_cookies_456",
                    "user_query": "My child has a peanut allergy - is this safe?"
                }
            )
        
        # Verify response
        assert response.status_code == 200, f"Response: {response.text}"
        data = response.json()
        
        # Verify intent classification
        assert data["intent"] == "allergy_question"
        
        # Verify tool calls
        tool_calls = data["tool_calls"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["ok"] is True
        assert tool_calls[0]["name"] == "tool::allergy_question"
        
        # Should contain allergy-specific guidance
        message = data["message"]
        assert "allergy" in message["summary"].lower() or "peanut" in message["summary"].lower()
    
    def test_conversation_with_real_tools_ingredient_info(self):
        """Test conversation endpoint with ingredient info intent (still uses stub)"""
        # Reload modules
        import importlib
        import api.services.chat_tools
        importlib.reload(api.services.chat_tools)
        
        from api.routers import chat as chat_router
        
        class DummyLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "This product contains basic ingredients with no major concerns.",
                    "reasons": ["Simple ingredient list", "No known harmful additives"],
                    "checks": ["Check expiration date", "Store properly"],
                    "flags": [],
                    "disclaimer": "Always read labels for the most current information.",
                    "jurisdiction": {"code": "US", "label": "FDA"},
                    "evidence": []
                }
        
        def mock_fetch_scan_data(db, scan_id):
            return {
                "scan_id": scan_id,
                "product_name": "Apple Juice",
                "category": "beverage",
                "flags": [],
                "ingredients": ["apple juice", "vitamin c", "natural flavors"],
                "recalls_found": 0,
                "profile": None
            }
        
        with patch.object(chat_router, "get_llm_client", return_value=DummyLLM()), \
             patch.object(chat_router, "fetch_scan_data", side_effect=mock_fetch_scan_data), \
             patch.object(chat_router, "get_or_create_conversation", return_value=MagicMock(id="conv-789")), \
             patch.object(chat_router, "get_profile", return_value=None), \
             patch.object(chat_router, "log_message"), \
             patch("core.feature_flags.chat_enabled_for", return_value=True):
            
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test_apple_juice_789",
                    "user_query": "What are the ingredients in this product?"
                }
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Should classify as ingredient_info (which still uses stub)
        assert data["intent"] == "ingredient_info"
        
        # Tool should still work (using stub implementation)
        tool_calls = data["tool_calls"]
        assert len(tool_calls) > 0
        assert tool_calls[0]["ok"] is True
    
    def test_real_tools_flag_disabled_falls_back_to_stubs(self):
        """Test that when real tools flag is disabled, it falls back to stubs"""
        # Temporarily disable real tools
        os.environ["BS_USE_REAL_TOOLS"] = "false"
        
        # Reload modules to pick up the change
        import importlib
        import api.services.chat_tools
        importlib.reload(api.services.chat_tools)
        
        from api.routers import chat as chat_router
        
        class DummyLLM:
            def chat_json(self, **kwargs):
                return {
                    "summary": "Basic safety check completed.",
                    "reasons": ["No major concerns identified"],
                    "checks": ["Read label carefully"],
                    "flags": [],
                    "disclaimer": "Not medical advice.",
                    "jurisdiction": {"code": "US", "label": "FDA"},
                    "evidence": []
                }
        
        def mock_fetch_scan_data(db, scan_id):
            return {
                "scan_id": scan_id,
                "product_name": "Test Product",
                "category": "food",
                "flags": [],
                "ingredients": ["water", "salt"],
                "recalls_found": 0,
                "profile": {"allergies": ["peanut"]}
            }
        
        with patch.object(chat_router, "get_llm_client", return_value=DummyLLM()), \
             patch.object(chat_router, "fetch_scan_data", side_effect=mock_fetch_scan_data), \
             patch.object(chat_router, "get_or_create_conversation", return_value=MagicMock(id="conv-stub")), \
             patch.object(chat_router, "get_profile", return_value={"allergies": ["peanut"]}), \
             patch.object(chat_router, "log_message"), \
             patch("core.feature_flags.chat_enabled_for", return_value=True):
            
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test_stub_product",
                    "user_query": "Is this safe for someone with peanut allergies?"
                }
            )
        
        # Should still work using stub implementations
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "allergy_question"
        assert len(data["tool_calls"]) > 0
        assert data["tool_calls"][0]["ok"] is True
        
        # Reset environment for other tests
        os.environ["BS_USE_REAL_TOOLS"] = "true"


def test_conversation_with_real_recall_tool(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools for this test
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")
    
    # Mock RecallDB query
    from core_infra.database import RecallDB
    mock_recall = MagicMock()
    mock_recall.recall_id = "CPSC-2023-TEETHER"
    mock_recall.id = 12345
    mock_recall.source_agency = "CPSC"
    mock_recall.recall_date.isoformat.return_value = "2023-06-15"
    mock_recall.url = "https://cpsc.gov/recall/teether-123"
    mock_recall.product_name = "Baby Teether"
    mock_recall.hazard = "Choking hazard - small parts can detach"
    mock_recall.recall_reason = None
    
    # Mock the database query to return our mock recall
    def mock_db_query(*args, **kwargs):
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [mock_recall]
        return mock_query
    
    monkeypatch.setattr("api.services.chat_tools_real.get_db_session", 
                       lambda: MagicMock(__enter__=lambda x: MagicMock(query=mock_db_query), __exit__=lambda *args: None))

    user_id = uuid.uuid4()
    scan_id = "scan_recall_456"
    create_test_scan(db_session, scan_id, user_id, product_name="Baby Teether", category="toy")

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "Are there any recalls for this product?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "recall_details"
    assert body["message"]["summary"] == "Test summary from LLM."
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["name"] == "tool::recall_details"
    assert body["tool_calls"][0]["ok"] is True
    
    # Check recall data structure
    output = body["tool_calls"][0]["output"]
    assert output["recalls_found"] == 1
    assert len(output["recalls"]) == 1
    assert output["recalls"][0]["id"] == "CPSC-2023-TEETHER"
    assert output["recalls"][0]["agency"] == "CPSC"
    assert output["recalls"][0]["hazard"] == "Choking hazard - small parts can detach"
    
    # Check evidence
    assert len(output["evidence"]) == 1
    assert output["evidence"][0]["type"] == "recall"
    assert output["evidence"][0]["source"] == "CPSC"
    assert output["evidence"][0]["id"] == "CPSC-2023-TEETHER"
    assert output["evidence"][0]["url"] == "https://cpsc.gov/recall/teether-123"


def test_conversation_with_real_ingredient_tool(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools for this test
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")

    user_id = uuid.uuid4()
    scan_id = "scan_ingredient_789"
    
    # Create scan with ingredients that will trigger highlighting
    scan = create_test_scan(db_session, scan_id, user_id, product_name="Face Cream", category="cosmetic")
    
    # Mock scan data to include ingredients (this would normally come from fetch_scan_data)
    def mock_fetch_scan_data(db, sid):
        base_data = {
            "product_name": "Face Cream",
            "brand": "BeautyBrand", 
            "barcode": "9876543210987",
            "category": "cosmetic",
            "scan_type": "barcode",
            "scan_id": sid,
            "confidence_score": 0.95,
            "barcode_format": "EAN13",
            "verdict": "No Recalls Found",
            "risk_level": "low",
            "recalls_found": 0,
            "recalls": [],
            "agencies_checked": "FDA",
            "flags": [],
            "key_flags": [],
            "ingredients": ["Water", "Retinol", "Fragrance", "Glycerin"],  # Ingredients that trigger highlighting
            "allergens": [],
            "pregnancy_warnings": [],
            "age_warnings": [],
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
        }
        return base_data

    monkeypatch.setattr("api.routers.chat.fetch_scan_data", mock_fetch_scan_data)

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "What ingredients should I be concerned about?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "ingredient_info"
    assert body["message"]["summary"] == "Test summary from LLM."
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["name"] == "tool::ingredient_info"
    assert body["tool_calls"][0]["ok"] is True
    
    # Check ingredient analysis
    output = body["tool_calls"][0]["output"]
    assert output["ingredients"] == ["Water", "Retinol", "Fragrance", "Glycerin"]
    assert "Retinol" in output["highlighted"]
    assert "Fragrance" in output["highlighted"]
    assert "Retinol: Check with healthcare provider during pregnancy" in output["notes"]
    
    # Check evidence for label verification
    assert len(output["evidence"]) == 1
    assert output["evidence"][0]["type"] == "label"
    assert output["evidence"][0]["source"] == "Product label"


def test_conversation_with_real_age_tool(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools for this test
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")

    user_id = uuid.uuid4()
    scan_id = "scan_age_101"
    create_test_scan(db_session, scan_id, user_id, product_name="Toy Car", category="toy")

    # Mock scan data with small_parts flag
    def mock_fetch_scan_data(db, sid):
        return {
            "product_name": "Toy Car",
            "brand": "ToyMaker", 
            "barcode": "1111222233334",
            "category": "toy",
            "scan_type": "barcode",
            "scan_id": sid,
            "confidence_score": 0.90,
            "barcode_format": "EAN13",
            "verdict": "No Recalls Found",
            "risk_level": "low",
            "recalls_found": 0,
            "recalls": [],
            "agencies_checked": "CPSC",
            "flags": ["small_parts"],  # This will trigger age restrictions
            "key_flags": ["small_parts"],
            "ingredients": [],
            "allergens": [],
            "pregnancy_warnings": [],
            "age_warnings": [],
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
        }

    monkeypatch.setattr("api.routers.chat.fetch_scan_data", mock_fetch_scan_data)

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "Is this appropriate for my 2-year-old?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "age_appropriateness"
    assert body["message"]["summary"] == "Test summary from LLM."
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["name"] == "tool::age_appropriateness"
    assert body["tool_calls"][0]["ok"] is True
    
    # Check age appropriateness analysis
    output = body["tool_calls"][0]["output"]
    assert output["min_age_months"] == 36  # 36 months due to small_parts flag
    assert output["age_ok"] is False  # Not suitable for under 36 months
    assert "Contains small parts; not suitable for under 36 months." in output["reasons"]


def test_conversation_with_real_alternatives_tool(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools for this test
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")

    user_id = uuid.uuid4()
    scan_id = "scan_alternatives_202"
    create_test_scan(db_session, scan_id, user_id, product_name="Soft Brie Cheese", category="cheese")

    # Mock scan data with soft cheese flags
    def mock_fetch_scan_data(db, sid):
        return {
            "product_name": "Soft Brie Cheese",
            "brand": "FrenchCheese Co", 
            "barcode": "5555666677778",
            "category": "cheese",
            "scan_type": "barcode",
            "scan_id": sid,
            "confidence_score": 0.88,
            "barcode_format": "EAN13",
            "verdict": "No Recalls Found",
            "risk_level": "medium",  # Medium risk to trigger alternatives
            "recalls_found": 0,
            "recalls": [],
            "agencies_checked": "FDA",
            "flags": ["soft_cheese"],  # This will trigger cheese alternatives
            "key_flags": ["soft_cheese"],
            "ingredients": ["milk", "cultures", "salt"],
            "allergens": [],
            "pregnancy_warnings": ["listeria_risk"],
            "age_warnings": [],
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
            "profile": {}  # No specific user allergies for this test
        }

    monkeypatch.setattr("api.routers.chat.fetch_scan_data", mock_fetch_scan_data)

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "What are some safer alternatives to this cheese?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "alternative_products"
    assert body["message"]["summary"] == "Test summary from LLM."
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["name"] == "tool::alternative_products"
    assert body["tool_calls"][0]["ok"] is True
    
    # Check alternatives data structure
    output = body["tool_calls"][0]["output"]
    assert "alternatives" in output
    assert output["alternatives"]["schema"] == "AlternativesOut@v1"
    assert len(output["alternatives"]["items"]) >= 1
    
    # Check specific alternatives for cheese
    items = output["alternatives"]["items"]
    alt_names = [item["name"] for item in items]
    assert any("Pasteurised Brie" in name for name in alt_names)
    
    # Check structure of first alternative
    first_alt = items[0]
    assert "id" in first_alt
    assert "name" in first_alt
    assert "reason" in first_alt
    assert "tags" in first_alt
    assert isinstance(first_alt["tags"], list)
    
    # Check evidence if present
    if "evidence" in first_alt and first_alt["evidence"]:
        evidence = first_alt["evidence"][0]
        assert "type" in evidence
        assert "source" in evidence


def test_conversation_with_alternatives_peanut_allergy(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools for this test
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")

    user_id = uuid.uuid4()
    scan_id = "scan_peanut_alt_303"
    create_test_scan(db_session, scan_id, user_id, product_name="Peanut Butter", category="spread")

    # Mock scan data with peanut ingredients and user profile
    def mock_fetch_scan_data(db, sid):
        return {
            "product_name": "Peanut Butter",
            "brand": "NutCorp", 
            "barcode": "7777888899990",
            "category": "spread",
            "scan_type": "barcode",
            "scan_id": sid,
            "confidence_score": 0.95,
            "barcode_format": "UPC",
            "verdict": "No Recalls Found",
            "risk_level": "high",  # High risk due to allergy
            "recalls_found": 0,
            "recalls": [],
            "agencies_checked": "FDA",
            "flags": [],
            "key_flags": [],
            "ingredients": ["peanuts", "salt", "palm oil"],  # Contains peanuts
            "allergens": ["peanut"],
            "pregnancy_warnings": [],
            "age_warnings": [],
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
            "profile": {"allergies": ["peanut"]}  # User has peanut allergy
        }

    monkeypatch.setattr("api.routers.chat.fetch_scan_data", mock_fetch_scan_data)

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "I have a peanut allergy. What alternatives do you recommend?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "alternative_products"
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["ok"] is True
    
    # Check alternatives for peanut allergy
    output = body["tool_calls"][0]["output"]
    items = output["alternatives"]["items"]
    assert len(items) >= 1
    
    # Should have peanut-free alternatives
    peanut_free_items = [item for item in items if "peanut" in item.get("allergy_safe_for", [])]
    assert len(peanut_free_items) >= 1
    
    # Check SunButter alternative specifically
    sunbutter_alt = next((item for item in items if "SunButter" in item["name"]), None)
    if sunbutter_alt:
        assert "peanut" in sunbutter_alt["allergy_safe_for"]
        assert "spread" in sunbutter_alt["tags"]


def test_conversation_alternatives_disabled_flag(client: TestClient, db_session: Session, monkeypatch):
    # Enable real tools but disable alternatives
    monkeypatch.setitem(os.environ, "BS_USE_REAL_TOOLS", "true")
    monkeypatch.setitem(os.environ, "BS_ALTERNATIVES_ENABLED", "false")

    user_id = uuid.uuid4()
    scan_id = "scan_no_alt_404"
    create_test_scan(db_session, scan_id, user_id, product_name="Soft Cheese", category="cheese")

    def mock_fetch_scan_data(db, sid):
        return {
            "product_name": "Soft Cheese",
            "brand": "TestBrand", 
            "barcode": "1111222233334",
            "category": "cheese",
            "scan_type": "barcode",
            "scan_id": sid,
            "confidence_score": 0.90,
            "barcode_format": "EAN13",
            "verdict": "No Recalls Found",
            "risk_level": "medium",
            "recalls_found": 0,
            "recalls": [],
            "agencies_checked": "FDA",
            "flags": ["soft_cheese"],
            "key_flags": ["soft_cheese"],
            "ingredients": ["milk"],
            "allergens": [],
            "pregnancy_warnings": [],
            "age_warnings": [],
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
            "profile": {}
        }

    monkeypatch.setattr("api.routers.chat.fetch_scan_data", mock_fetch_scan_data)

    mock_user = MagicMock()
    mock_user.id = user_id
    monkeypatch.setattr("core.auth.current_user", mock_user)

    response = client.post(
        "/api/v1/chat/conversation",
        json={"scan_id": scan_id, "user_query": "What alternatives do you suggest?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["intent"] == "alternative_products"
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["ok"] is True
    
    # Should have no alternatives when disabled
    output = body["tool_calls"][0]["output"]
    assert output["alternatives"]["items"] == []


def test_analytics_alt_click_endpoint(client: TestClient, db_session: Session):
    """Test the alternative click analytics endpoint"""
    response = client.post(
        "/api/v1/analytics/alt-click",
        json={
            "scan_id": "test_scan_123",
            "alt_id": "alt_pasteurised_brie"
        }
    )
    
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True


def test_analytics_alt_click_validation(client: TestClient, db_session: Session):
    """Test validation on alt-click endpoint"""
    # Test missing fields
    response = client.post(
        "/api/v1/analytics/alt-click",
        json={"scan_id": "test_scan_123"}  # Missing alt_id
    )
    assert response.status_code == 422
    
    # Test empty fields
    response = client.post(
        "/api/v1/analytics/alt-click",
        json={
            "scan_id": "",  # Empty scan_id
            "alt_id": "alt_test"
        }
    )
    assert response.status_code == 422
    
    # Test field length limits
    response = client.post(
        "/api/v1/analytics/alt-click",
        json={
            "scan_id": "a" * 65,  # Too long
            "alt_id": "alt_test"
        }
    )
    assert response.status_code == 422
