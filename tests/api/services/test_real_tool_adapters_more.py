import pytest
from unittest.mock import MagicMock, patch
from api.services import chat_tools_real as real
from api.schemas.tools import (
    RecallDetailsIn, RecallDetailsOut, RecallRecord,
    IngredientInfoIn, IngredientInfoOut,
    AgeCheckIn, AgeCheckOut
)


class TestRecallDetailsAdapter:
    """Tests for recall_details_adapter"""

    @patch('api.services.chat_tools_real.get_db_session')
    def test_recall_details_adapter_with_results(self, mock_get_db_session):
        # Mock database session and query
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock RecallDB query results
        mock_recall = MagicMock()
        mock_recall.recall_id = "CPSC-2023-001"
        mock_recall.id = 123
        mock_recall.source_agency = "CPSC"
        mock_recall.recall_date.isoformat.return_value = "2023-01-15"
        mock_recall.url = "https://cpsc.gov/recall/123"
        mock_recall.product_name = "Baby Teether"
        mock_recall.hazard = "Choking hazard"
        mock_recall.recall_reason = None
        
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_recall]
        
        scan_data = {
            "product_name": "Baby Teether",
            "brand": "SafeToys",
            "model_number": "ST-001",
            "barcode": "1234567890123"
        }
        
        result = real.recall_details_adapter(scan_data)
        
        # Verify structure
        assert "recalls" in result
        assert "recalls_found" in result
        assert "batch_check" in result
        assert "evidence" in result
        
        # Verify content
        assert result["recalls_found"] == 1
        assert len(result["recalls"]) == 1
        assert result["recalls"][0]["id"] == "CPSC-2023-001"
        assert result["recalls"][0]["agency"] == "CPSC"
        assert result["recalls"][0]["date"] == "2023-01-15"
        assert result["recalls"][0]["url"] == "https://cpsc.gov/recall/123"
        assert result["recalls"][0]["title"] == "Baby Teether"
        assert result["recalls"][0]["hazard"] == "Choking hazard"
        
        # Verify evidence
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["type"] == "recall"
        assert result["evidence"][0]["source"] == "CPSC"
        assert result["evidence"][0]["id"] == "CPSC-2023-001"
        assert result["evidence"][0]["url"] == "https://cpsc.gov/recall/123"

    @patch('api.services.chat_tools_real.get_db_session')
    def test_recall_details_adapter_no_results(self, mock_get_db_session):
        # Mock database session with no results
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        
        scan_data = {
            "product_name": "Unknown Product"
        }
        
        result = real.recall_details_adapter(scan_data)
        
        assert result["recalls_found"] == 0
        assert result["recalls"] == []
        assert result["batch_check"] is None
        assert result["evidence"] == []

    @patch('api.services.chat_tools_real.get_db_session')
    def test_recall_details_adapter_multiple_identifiers(self, mock_get_db_session):
        # Mock database session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock two recall results
        mock_recall1 = MagicMock()
        mock_recall1.recall_id = "FDA-2023-001"
        mock_recall1.id = 456
        mock_recall1.source_agency = "FDA"
        mock_recall1.recall_date.isoformat.return_value = "2023-02-10"
        mock_recall1.url = "https://fda.gov/recall/456"
        mock_recall1.product_name = "Baby Formula"
        mock_recall1.hazard = "Contamination"
        mock_recall1.recall_reason = "Salmonella contamination"
        
        mock_recall2 = MagicMock()
        mock_recall2.recall_id = "EU-2023-002"
        mock_recall2.id = 789
        mock_recall2.source_agency = "EU Safety Gate"
        mock_recall2.recall_date.isoformat.return_value = "2023-03-05"
        mock_recall2.url = None
        mock_recall2.product_name = "Baby Formula"
        mock_recall2.hazard = None
        mock_recall2.recall_reason = "Chemical contamination"
        
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_recall1, mock_recall2]
        
        scan_data = {
            "product_name": "Baby Formula",
            "brand": "NutriCorp",
            "gtin": "1234567890123"
        }
        
        result = real.recall_details_adapter(scan_data)
        
        assert result["recalls_found"] == 2
        assert len(result["recalls"]) == 2
        assert len(result["evidence"]) == 2
        
        # Check first recall
        assert result["recalls"][0]["agency"] == "FDA"
        assert result["recalls"][0]["hazard"] == "Contamination"
        
        # Check second recall
        assert result["recalls"][1]["agency"] == "EU Safety Gate"
        assert result["recalls"][1]["hazard"] == "Chemical contamination"


class TestIngredientInfoAdapter:
    """Tests for ingredient_info_adapter"""

    def test_ingredient_info_adapter_with_concerns(self):
        scan_data = {
            "ingredients": ["Water", "Retinol", "Fragrance", "Methylisothiazolinone"],
            "product_name": "Face Cream",
            "category": "cosmetic"
        }
        
        result = real.ingredient_info_adapter(scan_data)
        
        assert "ingredients" in result
        assert "highlighted" in result
        assert "notes" in result
        assert "evidence" in result
        
        # Check ingredients are preserved
        assert result["ingredients"] == ["Water", "Retinol", "Fragrance", "Methylisothiazolinone"]
        
        # Check highlighting
        assert "Retinol" in result["highlighted"]
        assert "Fragrance" in result["highlighted"]
        assert "Methylisothiazolinone" in result["highlighted"]
        
        # Check notes
        assert "Retinol: Check with healthcare provider during pregnancy" in result["notes"]
        assert "Methylisothiazolinone: Potential skin sensitizer" in result["notes"]
        
        # Check evidence (should have label verification)
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["type"] == "label"
        assert result["evidence"][0]["source"] == "Product label"

    def test_ingredient_info_adapter_no_concerns(self):
        scan_data = {
            "ingredients": ["Water", "Glycerin", "Aloe Vera"],
            "product_name": "Moisturizer",
            "category": "general"
        }
        
        result = real.ingredient_info_adapter(scan_data)
        
        assert result["ingredients"] == ["Water", "Glycerin", "Aloe Vera"]
        assert result["highlighted"] == []
        assert result["notes"] is None
        assert "evidence" not in result or result["evidence"] == []

    def test_ingredient_info_adapter_food_category(self):
        scan_data = {
            "ingredients": ["Flour", "Sugar", "Salt"],
            "product_name": "Crackers",
            "category": "food"
        }
        
        result = real.ingredient_info_adapter(scan_data)
        
        # Should recommend label check for food products
        assert len(result["evidence"]) == 1
        assert result["evidence"][0]["type"] == "label"

    def test_ingredient_info_adapter_empty_ingredients(self):
        scan_data = {
            "ingredients": [],
            "product_name": "Mystery Product"
        }
        
        result = real.ingredient_info_adapter(scan_data)
        
        assert result["ingredients"] == []
        assert result["highlighted"] == []
        assert result["notes"] is None


class TestAgeCheckAdapter:
    """Tests for age_check_adapter"""

    def test_age_check_adapter_with_category_rule(self):
        scan_data = {
            "category": "teether",
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert "age_ok" in result
        assert "min_age_months" in result
        assert "reasons" in result
        
        assert result["min_age_months"] == 3  # From AGE_RULES
        assert result["age_ok"] is False  # 3 months > 0
        assert result["reasons"] == []

    def test_age_check_adapter_with_small_parts_flag(self):
        scan_data = {
            "category": "toy",
            "flags": ["small_parts"]
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 36  # Max of toy rule (36) and small_parts (36)
        assert result["age_ok"] is False
        assert "Contains small parts; not suitable for under 36 months." in result["reasons"]

    def test_age_check_adapter_multiple_flags(self):
        scan_data = {
            "category": "toy",
            "flags": ["small_parts", "choking_hazard", "sharp_edges"]
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 36
        assert result["age_ok"] is False
        assert len(result["reasons"]) == 3
        assert "Contains small parts; not suitable for under 36 months." in result["reasons"]
        assert "Choking hazard; requires adult supervision." in result["reasons"]
        assert "Sharp edges present; not suitable for young children." in result["reasons"]

    def test_age_check_adapter_newborn_safe(self):
        scan_data = {
            "category": "bottle",
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 0  # From AGE_RULES
        assert result["age_ok"] is True  # 0 months <= 0
        assert result["reasons"] == []

    def test_age_check_adapter_explicit_age(self):
        scan_data = {
            "category": "toy",
            "age_min_months": 6,
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 6  # Explicit age takes precedence
        assert result["age_ok"] is False
        assert result["reasons"] == []

    def test_age_check_adapter_unknown_category(self):
        scan_data = {
            "category": "unknown_category",
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] is None
        assert result["age_ok"] is None  # None is not None and None <= 0 is False
        assert result["reasons"] == []

    def test_age_check_adapter_toy_with_no_age(self):
        scan_data = {
            "category": "toy",
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 36  # Default for toys
        assert result["age_ok"] is False
        assert result["reasons"] == []

    def test_age_check_adapter_game_category(self):
        scan_data = {
            "category": "game",
            "flags": []
        }
        
        result = real.age_check_adapter(scan_data)
        
        assert result["min_age_months"] == 36  # Default for games
        assert result["age_ok"] is False
        assert "Age recommendation based on product category." in result["reasons"]


class TestEvidenceIntegration:
    """Tests for evidence integration across adapters"""

    @patch('api.services.chat_tools_real.get_db_session')
    def test_recalls_to_evidence_integration(self, mock_get_db_session):
        # Mock database session
        mock_session = MagicMock()
        mock_get_db_session.return_value.__enter__.return_value = mock_session
        
        # Mock recall with full data
        mock_recall = MagicMock()
        mock_recall.recall_id = "TEST-001"
        mock_recall.id = 999
        mock_recall.source_agency = "Test Agency"
        mock_recall.recall_date.isoformat.return_value = "2023-12-01"
        mock_recall.url = "https://test.gov/recall/999"
        mock_recall.product_name = "Test Product"
        mock_recall.hazard = "Test hazard"
        mock_recall.recall_reason = None
        
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_recall]
        
        scan_data = {"product_name": "Test Product"}
        result = real.recall_details_adapter(scan_data)
        
        # Verify evidence structure matches EvidenceItem
        evidence = result["evidence"][0]
        assert evidence["type"] == "recall"
        assert evidence["source"] == "Test Agency"
        assert evidence["id"] == "TEST-001"
        assert evidence["url"] == "https://test.gov/recall/999"

    def test_label_to_evidence_integration(self):
        scan_data = {
            "ingredients": ["Water", "Fragrance"],
            "category": "cosmetic"
        }
        
        result = real.ingredient_info_adapter(scan_data)
        
        # Verify evidence structure
        evidence = result["evidence"][0]
        assert evidence["type"] == "label"
        assert evidence["source"] == "Product label"
        assert evidence["id"] == "ingredient verification"
        assert evidence["url"] is None


if __name__ == "__main__":
    pytest.main([__file__])
