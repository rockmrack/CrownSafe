import pytest
from unittest.mock import MagicMock, patch
from api.services import chat_tools_real as real


class FakePregnancyAgent:
    """Mock PregnancyProductSafetyAgent for testing"""
    def __init__(self):
        self.logic = MagicMock()


class FakeAllergyAgent:
    """Mock AllergySensitivityAgent for testing"""
    def __init__(self):
        self.logic = MagicMock()


class TestPregnancyAdapter:
    def test_pregnancy_adapter_with_soft_cheese(self, monkeypatch):
        """Test pregnancy adapter identifies soft cheese risks"""
        monkeypatch.setattr(real, "PregnancyProductSafetyAgent", lambda: FakePregnancyAgent())
        
        scan_data = {
            "product_name": "Brie Cheese",
            "category": "cheese",
            "ingredients": ["milk", "cultures"],
            "flags": ["soft_cheese"],
            "jurisdiction": {"code": "US", "label": "FDA"}
        }
        
        result = real.pregnancy_adapter(scan_data)
        
        # Verify structure
        assert "pregnancy" in result
        pregnancy_data = result["pregnancy"]
        assert "schema" in pregnancy_data
        assert pregnancy_data["schema"] == "PregnancyCheckOut@v1"
        assert "risks" in pregnancy_data
        assert "notes" in pregnancy_data
        
        # Should detect soft cheese risk
        risks = pregnancy_data["risks"]
        assert len(risks) > 0
        soft_cheese_risk = next((r for r in risks if "soft_cheese" in r["code"]), None)
        assert soft_cheese_risk is not None
        assert soft_cheese_risk["severity"] == "moderate"
        assert "pasteurised" in soft_cheese_risk["reason"].lower()
    
    def test_pregnancy_adapter_with_unsafe_ingredients(self, monkeypatch):
        """Test pregnancy adapter identifies unsafe ingredients"""
        monkeypatch.setattr(real, "PregnancyProductSafetyAgent", lambda: FakePregnancyAgent())
        
        scan_data = {
            "product_name": "Wine",
            "category": "beverage",
            "ingredients": ["alcohol", "grapes", "sulfites"],
            "flags": [],
        }
        
        result = real.pregnancy_adapter(scan_data)
        
        pregnancy_data = result["pregnancy"]
        risks = pregnancy_data["risks"]
        
        # Should detect alcohol risk
        alcohol_risk = next((r for r in risks if "alcohol" in r["code"]), None)
        assert alcohol_risk is not None
        assert alcohol_risk["severity"] == "high"
        assert "birth defects" in alcohol_risk["reason"]
    
    def test_pregnancy_adapter_safe_product(self, monkeypatch):
        """Test pregnancy adapter with safe product"""
        monkeypatch.setattr(real, "PregnancyProductSafetyAgent", lambda: FakePregnancyAgent())
        
        scan_data = {
            "product_name": "Apple Juice",
            "category": "beverage", 
            "ingredients": ["apple juice", "vitamin c"],
            "flags": [],
        }
        
        result = real.pregnancy_adapter(scan_data)
        
        pregnancy_data = result["pregnancy"]
        assert len(pregnancy_data["risks"]) == 0
        assert pregnancy_data["notes"] is not None


class TestAllergyAdapter:
    def test_allergy_adapter_with_matches(self, monkeypatch):
        """Test allergy adapter identifies allergen matches"""
        monkeypatch.setattr(real, "AllergySensitivityAgent", lambda: FakeAllergyAgent())
        
        scan_data = {
            "product_name": "Peanut Butter",
            "ingredients": ["peanuts", "oil", "salt"],
            "profile": {"allergies": ["peanut", "tree_nut"]}
        }
        
        result = real.allergy_adapter(scan_data)
        
        # Verify structure
        assert "allergy" in result
        allergy_data = result["allergy"]
        assert "schema" in allergy_data
        assert allergy_data["schema"] == "AllergyCheckOut@v1"
        assert "hits" in allergy_data
        assert "summary" in allergy_data
        
        # Should detect peanut match
        hits = allergy_data["hits"]
        assert len(hits) > 0
        peanut_hit = next((h for h in hits if h["allergen"] == "peanut"), None)
        assert peanut_hit is not None
        assert peanut_hit["present"] is True
        assert peanut_hit["evidence"] is not None
    
    def test_allergy_adapter_with_aliases(self, monkeypatch):
        """Test allergy adapter recognizes allergen aliases"""
        monkeypatch.setattr(real, "AllergySensitivityAgent", lambda: FakeAllergyAgent())
        
        scan_data = {
            "product_name": "Milk Chocolate",
            "ingredients": ["cocoa", "milk", "sugar"],
            "profile": {"allergies": ["dairy"]}
        }
        
        result = real.allergy_adapter(scan_data)
        
        allergy_data = result["allergy"]
        hits = allergy_data["hits"]
        
        # Should detect dairy through milk alias
        dairy_hit = next((h for h in hits if h["allergen"] == "dairy"), None)
        assert dairy_hit is not None
        assert dairy_hit["present"] is True
    
    def test_allergy_adapter_no_matches(self, monkeypatch):
        """Test allergy adapter with no allergen matches"""
        monkeypatch.setattr(real, "AllergySensitivityAgent", lambda: FakeAllergyAgent())
        
        scan_data = {
            "product_name": "Rice Cakes", 
            "ingredients": ["rice", "salt"],
            "profile": {"allergies": ["peanut", "dairy"]}
        }
        
        result = real.allergy_adapter(scan_data)
        
        allergy_data = result["allergy"]
        assert len(allergy_data["hits"]) == 0
        assert allergy_data["summary"] is None
    
    def test_allergy_adapter_no_profile(self, monkeypatch):
        """Test allergy adapter with no user profile"""
        monkeypatch.setattr(real, "AllergySensitivityAgent", lambda: FakeAllergyAgent())
        
        scan_data = {
            "product_name": "Peanut Butter",
            "ingredients": ["peanuts", "oil"],
            "profile": None
        }
        
        result = real.allergy_adapter(scan_data)
        
        allergy_data = result["allergy"]
        assert len(allergy_data["hits"]) == 0


class TestInputValidation:
    def test_pregnancy_checkin_schema_validation(self):
        """Test PregnancyCheckIn schema validation"""
        from api.schemas.tools import PregnancyCheckIn
        
        # Valid input
        valid_input = PregnancyCheckIn(
            product_name="Test Product",
            category="food",
            ingredients=["water", "salt"],
            flags=["organic"]
        )
        assert valid_input.schema == "PregnancyCheck@v1"
        assert valid_input.product_name == "Test Product"
        
        # Default values
        minimal_input = PregnancyCheckIn()
        assert minimal_input.ingredients == []
        assert minimal_input.flags == []
    
    def test_allergy_checkin_schema_validation(self):
        """Test AllergyCheckIn schema validation"""
        from api.schemas.tools import AllergyCheckIn
        
        # Valid input
        valid_input = AllergyCheckIn(
            ingredients=["milk", "eggs"],
            profile_allergies=["dairy", "egg"],
            product_name="Test Product"
        )
        assert valid_input.schema == "AllergyCheck@v1"
        assert len(valid_input.ingredients) == 2
        assert len(valid_input.profile_allergies) == 2
    
    def test_risk_item_validation(self):
        """Test RiskItem schema validation"""
        from api.schemas.tools import RiskItem
        
        risk = RiskItem(
            code="soft_cheese_pasteurisation",
            reason="Soft cheese may contain listeria",
            severity="moderate"
        )
        assert risk.code == "soft_cheese_pasteurisation"
        assert risk.severity == "moderate"
    
    def test_allergy_hit_validation(self):
        """Test AllergyHit schema validation"""
        from api.schemas.tools import AllergyHit
        
        hit = AllergyHit(
            allergen="peanut",
            present=True,
            evidence="ingredient_list"
        )
        assert hit.allergen == "peanut"
        assert hit.present is True
        assert hit.evidence == "ingredient_list"


class TestErrorHandling:
    def test_pregnancy_adapter_handles_exceptions(self, monkeypatch):
        """Test pregnancy adapter handles agent exceptions gracefully"""
        def failing_agent():
            raise Exception("Agent initialization failed")
        
        monkeypatch.setattr(real, "PregnancyProductSafetyAgent", failing_agent)
        
        scan_data = {"product_name": "Test Product"}
        
        # Should not raise exception
        result = real.pregnancy_adapter(scan_data)
        
        # Should return valid structure even on error
        assert "pregnancy" in result
        pregnancy_data = result["pregnancy"]
        assert "risks" in pregnancy_data
        assert isinstance(pregnancy_data["risks"], list)
    
    def test_allergy_adapter_handles_exceptions(self, monkeypatch):
        """Test allergy adapter handles agent exceptions gracefully"""
        def failing_agent():
            raise Exception("Agent initialization failed")
        
        monkeypatch.setattr(real, "AllergySensitivityAgent", failing_agent)
        
        scan_data = {"ingredients": ["test"], "profile": {"allergies": ["peanut"]}}
        
        # Should not raise exception
        result = real.allergy_adapter(scan_data)
        
        # Should return valid structure even on error
        assert "allergy" in result
        allergy_data = result["allergy"]
        assert "hits" in allergy_data
        assert isinstance(allergy_data["hits"], list)
