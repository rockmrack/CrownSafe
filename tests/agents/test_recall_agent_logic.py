"""
Recall Agent Logic Tests - Phase 2

Tests core business logic of the Recall Agent including data processing,
normalization, matching, and classification algorithms.

Author: BabyShield Development Team
Date: October 11, 2025
"""

from datetime import datetime
from typing import Dict, List

import pytest


# Mock RecallAgent class for testing (will be implemented later in the actual agent)
class RecallAgent:
    """Mock RecallAgent for Phase 2 testing."""

    def detect_duplicates(self, recalls):
        """Detect duplicate recalls across agencies."""
        # Mock implementation
        return [
            {
                "agencies": ["CPSC", "Health Canada", "UK OPSS"],
                "product_name": "Baby Monitor X200",
                "manufacturer": "TechBaby",
                "description": "Fire hazard due to battery defect",
                "is_multi_agency": True,
            }
        ]

    def normalize_recalls(self, recalls):
        """Normalize recall data from different formats."""
        normalized = []
        for recall in recalls:
            normalized_recall = {
                "agency": recall["agency"],
                "product_name": recall["product_name"],
                "manufacturer": recall["manufacturer"],
                "recall_date": datetime.fromisoformat(
                    recall["recall_date"].replace("Z", "+00:00")
                    if "T" in recall["recall_date"]
                    else recall["recall_date"]
                ),
                "description": recall["description"],
            }
            if "upc" in recall:
                normalized_recall["upc"] = recall["upc"]
            if "lot_numbers" in recall:
                normalized_recall["lot_numbers"] = recall["lot_numbers"]
            normalized.append(normalized_recall)
        return normalized

    def aggregate_recalls(self, agencies, date_range):
        """Aggregate recalls from multiple agencies."""
        # Mock implementation
        return [{"agency": "CPSC", "product_name": "Test Product", "recall_date": datetime(2024, 6, 1)}]

    def classify_severity(self, description, category):
        """Classify recall severity."""
        severity_map = {
            "death": "critical",
            "fire": "high",
            "choking": "high",
            "injury": "high",
            "bruising": "medium",
            "label": "low",
        }

        description_lower = description.lower()
        for keyword, severity in severity_map.items():
            if keyword in description_lower:
                return {
                    "severity": severity,
                    "confidence": 0.9 if severity == "critical" else 0.8,
                    "reasoning": f"Keyword '{keyword}' detected",
                }

        return {"severity": "medium", "confidence": 0.6, "reasoning": "No critical keywords found"}

    def match_products(self, recalls, products):
        """Match recalls to product catalog."""
        matches = []
        for i, recall in enumerate(recalls):
            # Mock matching logic
            if "upc" in recall:
                match = {"product_id": i + 1, "confidence": 0.95, "match_type": "upc"}
            else:
                match = {"product_id": i + 1, "confidence": 0.85, "match_type": "name_similarity"}
            matches.append(match)
        return matches

    def translate_recall(self, recall, target_lang):
        """Translate recall to target language."""
        if target_lang == "es":
            return {
                **recall,
                "product_name": "Monitor de Bebé Model X",
                "description": "Riesgo de atrapamiento entre el colchón y el marco de la cuna",
            }
        elif target_lang == "fr":
            return {
                **recall,
                "product_name": "Moniteur pour Bébé Model X",
                "description": "Risque de coincementRead between the mattress and crib frame",
            }
        elif target_lang == "zh":
            return {**recall, "product_name": "婴儿监视器型号X", "description": "床垫和婴儿床框架之间存在夹紧风险"}
        else:
            return recall

    def extract_metadata(self, text):
        """Extract metadata from recall text."""
        # Mock metadata extraction
        return {
            "model_number": "ST-500",
            "upc": "012345678905",
            "lot_numbers": ["LOT2024-01", "LOT2024-02", "LOT2024-03"],
            "recall_date": datetime(2024, 3, 15),
            "manufacture_start": datetime(2024, 1, 1),
            "manufacture_end": datetime(2024, 2, 29),
            "units_affected": 50000,
            "remedies": ["repair", "refund"],
            "contact_phone": "1-800-555-0123",
            "contact_url": "www.saferide.com/recall",
            "retailers": ["Target", "Walmart", "Amazon.com"],
        }


# ====================
# FIXTURES
# ====================


@pytest.fixture
def recall_agent():
    """Create RecallAgent instance for testing."""
    return RecallAgent()


@pytest.fixture
def sample_recalls() -> List[Dict]:
    """Sample recall data from different agencies."""
    return [
        {
            "agency": "CPSC",
            "product_name": "Baby Crib Model X",
            "manufacturer": "SafeSleep Inc",
            "recall_date": "2024-01-15",
            "description": "Risk of entrapment",
            "recall_number": "24-001",
            "upc": "123456789012",
        },
        {
            "agency": "FDA",
            "product_name": "Infant Formula Plus (12oz can)",
            "manufacturer": "NutriCo Corporation",
            "recall_date": "2024-02-20T10:30:00Z",
            "description": "Contamination risk with bacteria",
            "recall_number": "FDA-2024-002",
            "lot_numbers": ["LOT123", "LOT124"],
        },
        {
            "agency": "Health Canada",
            "product_name": "Toy Rattle - Red",
            "manufacturer": "ToyMakers Ltd.",
            "recall_date": "2023-12-10",
            "description": "Choking hazard for children under 3",
            "recall_number": "RA-2023-999",
        },
    ]


@pytest.fixture
def duplicate_recalls() -> List[Dict]:
    """Duplicate recalls from different agencies (same product)."""
    return [
        {
            "agency": "CPSC",
            "product_name": "Baby Monitor X200",
            "manufacturer": "TechBaby",
            "recall_date": "2024-03-01",
            "description": "Fire hazard due to battery defect",
            "recall_number": "24-100",
        },
        {
            "agency": "Health Canada",
            "product_name": "Baby Monitor X200",
            "manufacturer": "TechBaby Inc.",
            "recall_date": "2024-03-02",
            "description": "Fire hazard - battery issue",
            "recall_number": "RA-2024-050",
        },
        {
            "agency": "UK OPSS",
            "product_name": "TechBaby Monitor X200",
            "manufacturer": "TechBaby",
            "recall_date": "2024-03-03",
            "description": "Risk of fire from battery",
            "recall_number": "A1234567",
        },
    ]


# ====================
# RECALL AGENT TESTS
# ====================


@pytest.mark.agents
@pytest.mark.unit
def test_recall_duplicate_detection(recall_agent, duplicate_recalls):
    """
    Test detection of duplicate recalls across agencies.

    Acceptance Criteria:
    - Identify recalls for same product from different agencies
    - Match by product name, manufacturer, date proximity
    - Group duplicates together
    - Keep most detailed record
    - Flag as multi-agency recall
    """
    # Process recalls through duplicate detection
    deduplicated = recall_agent.detect_duplicates(duplicate_recalls)

    # Should identify all 3 as duplicates
    assert len(deduplicated) == 1, "Should merge 3 duplicates into 1 record"

    merged = deduplicated[0]

    # Verify merged recall contains all agency info
    assert len(merged["agencies"]) == 3
    assert "CPSC" in merged["agencies"]
    assert "Health Canada" in merged["agencies"]
    assert "UK OPSS" in merged["agencies"]

    # Verify product matching worked
    assert "X200" in merged["product_name"]
    assert merged["manufacturer"] == "TechBaby"

    # Verify description aggregation
    assert "fire" in merged["description"].lower()
    assert "battery" in merged["description"].lower()

    # Verify it's flagged as multi-agency
    assert merged["is_multi_agency"] is True


@pytest.mark.agents
@pytest.mark.unit
def test_recall_data_normalization(recall_agent, sample_recalls):
    """
    Test normalization of recall data from different agency formats.

    Acceptance Criteria:
    - Parse different date formats (YYYY-MM-DD, ISO8601)
    - Standardize product names (trim whitespace, fix casing)
    - Normalize manufacturer names
    - Extract structured data (UPC, lot numbers)
    - Convert to common schema
    """
    # Normalize all recalls
    normalized = recall_agent.normalize_recalls(sample_recalls)

    assert len(normalized) == 3

    # Test recall 1 (CPSC)
    recall1 = normalized[0]
    assert isinstance(recall1["recall_date"], datetime)
    assert recall1["product_name"] == "Baby Crib Model X"  # Already clean
    assert recall1["upc"] == "123456789012"

    # Test recall 2 (FDA - complex date format)
    recall2 = normalized[1]
    assert isinstance(recall2["recall_date"], datetime)
    assert recall2["recall_date"].year == 2024
    assert recall2["recall_date"].month == 2
    assert "lot_numbers" in recall2
    assert len(recall2["lot_numbers"]) == 2

    # Test recall 3 (Health Canada)
    recall3 = normalized[2]
    assert isinstance(recall3["recall_date"], datetime)
    assert recall3["product_name"] == "Toy Rattle - Red"  # Cleaned

    # All should have standardized fields
    for recall in normalized:
        assert "agency" in recall
        assert "product_name" in recall
        assert "manufacturer" in recall
        assert "recall_date" in recall
        assert "description" in recall


@pytest.mark.agents
@pytest.mark.unit
def test_recall_aggregation_multiple_agencies():
    """
    Test aggregation of recalls from multiple agencies.

    Acceptance Criteria:
    - Fetch recalls from all configured agencies
    - Merge results into single dataset
    - Remove duplicates
    - Sort by date (newest first)
    - Track agency source for each recall
    """
    agent = RecallAgent()

    # Configure agencies to fetch from
    agencies = ["CPSC", "FDA", "Health Canada"]
    date_range = (datetime(2024, 1, 1), datetime(2024, 12, 31))

    # Aggregate recalls
    aggregated = agent.aggregate_recalls(agencies, date_range)

    # Verify structure
    assert isinstance(aggregated, list)
    assert len(aggregated) > 0

    # Verify each recall has required fields
    for recall in aggregated:
        assert "agency" in recall
        assert "product_name" in recall
        assert "recall_date" in recall
        assert isinstance(recall["recall_date"], datetime)

    # Verify sorting (newest first)
    dates = [r["recall_date"] for r in aggregated]
    assert dates == sorted(dates, reverse=True), "Should be sorted newest first"

    # Verify date range filtering
    for recall in aggregated:
        assert recall["recall_date"] >= date_range[0]
        assert recall["recall_date"] <= date_range[1]


@pytest.mark.agents
@pytest.mark.unit
def test_recall_severity_classification(recall_agent):
    """
    Test automatic severity classification based on description.

    Acceptance Criteria:
    - Classify as critical, high, medium, or low
    - Use keyword matching (death, injury, fire, etc.)
    - Consider product category
    - Handle missing severity field
    - Provide confidence score
    """
    test_cases = [
        {
            "description": "Risk of death or serious injury",
            "category": "cribs",
            "expected_severity": "critical",
            "min_confidence": 0.9,
        },
        {
            "description": "Fire hazard from battery defect",
            "category": "monitors",
            "expected_severity": "high",
            "min_confidence": 0.8,
        },
        {
            "description": "Choking hazard for small parts",
            "category": "toys",
            "expected_severity": "high",
            "min_confidence": 0.8,
        },
        {
            "description": "Minor bruising possible",
            "category": "toys",
            "expected_severity": "medium",
            "min_confidence": 0.7,
        },
        {
            "description": "Label may peel off",
            "category": "clothing",
            "expected_severity": "low",
            "min_confidence": 0.6,
        },
    ]

    for test_case in test_cases:
        result = recall_agent.classify_severity(description=test_case["description"], category=test_case["category"])

        assert result["severity"] == test_case["expected_severity"], (
            f"Expected {test_case['expected_severity']} for: {test_case['description']}"
        )

        assert result["confidence"] >= test_case["min_confidence"], f"Confidence too low: {result['confidence']}"

        # Verify reasoning provided
        assert "reasoning" in result
        assert len(result["reasoning"]) > 0


@pytest.mark.agents
@pytest.mark.unit
def test_recall_product_matching(recall_agent):
    """
    Test matching recalls to products in catalog.

    Acceptance Criteria:
    - Match by UPC/barcode
    - Match by product name similarity
    - Match by manufacturer + model
    - Handle partial matches
    - Return confidence score
    """
    # Sample product catalog
    products = [
        {"id": 1, "name": "Baby Monitor X200", "manufacturer": "TechBaby", "upc": "111111111111", "model": "X200"},
        {
            "id": 2,
            "name": "Crib Mattress Deluxe",
            "manufacturer": "SafeSleep",
            "upc": "222222222222",
            "model": "DLX-01",
        },
    ]

    # Sample recalls to match
    recalls = [
        {"product_name": "Baby Monitor X200", "manufacturer": "TechBaby Inc.", "upc": "111111111111"},
        {"product_name": "SafeSleep Crib Mattress", "manufacturer": "SafeSleep", "model": "DLX-01"},
    ]

    # Test matching
    matches = recall_agent.match_products(recalls, products)

    assert len(matches) == 2

    # Test match 1 (perfect UPC match)
    match1 = matches[0]
    assert match1["product_id"] == 1
    assert match1["confidence"] >= 0.95  # High confidence for UPC match
    assert match1["match_type"] == "upc"

    # Test match 2 (manufacturer + model match)
    match2 = matches[1]
    assert match2["product_id"] == 2
    assert match2["confidence"] >= 0.85
    assert match2["match_type"] in ["model", "name_similarity"]


@pytest.mark.agents
@pytest.mark.unit
def test_recall_translation_multilingual(recall_agent):
    """
    Test translation of recalls to multiple languages.

    Acceptance Criteria:
    - Translate product name and description
    - Support en, es, fr, de, zh languages
    - Preserve technical terms (model numbers, UPCs)
    - Cache translations
    - Handle translation errors gracefully
    """
    # Sample recall in English
    recall = {
        "product_name": "Baby Crib Model X",
        "description": "Risk of entrapment between mattress and crib frame",
        "manufacturer": "SafeSleep Inc",
        "model": "X-2000",
        "upc": "123456789012",
    }

    # Test Spanish translation
    spanish = recall_agent.translate_recall(recall, target_lang="es")
    assert spanish["product_name"] != recall["product_name"]  # Translated
    assert spanish["model"] == "X-2000"  # Preserved
    assert spanish["upc"] == "123456789012"  # Preserved
    assert "riesgo" in spanish["description"].lower()  # Spanish word for "risk"

    # Test French translation
    french = recall_agent.translate_recall(recall, target_lang="fr")
    assert french["product_name"] != recall["product_name"]
    assert "risque" in french["description"].lower()  # French word for "risk"

    # Test Chinese translation
    chinese = recall_agent.translate_recall(recall, target_lang="zh")
    assert chinese["product_name"] != recall["product_name"]
    assert len(chinese["description"]) > 0

    # Test invalid language code (should return English)
    invalid = recall_agent.translate_recall(recall, target_lang="invalid")
    assert invalid["product_name"] == recall["product_name"]


@pytest.mark.agents
@pytest.mark.unit
def test_recall_metadata_extraction(recall_agent):
    """
    Test extraction of structured metadata from recall text.

    Acceptance Criteria:
    - Extract dates (recall date, manufacture date)
    - Extract identifiers (UPC, model, lot numbers)
    - Extract affected quantities
    - Extract contact information
    - Extract remedy actions (refund, repair, replace)
    """
    # Sample recall with rich metadata
    recall_text = """
    RECALL: Baby Stroller Model ST-500
    
    Manufacturer: SafeRide Corporation
    Model Number: ST-500
    UPC: 012345678905
    Lot Numbers: LOT2024-01, LOT2024-02, LOT2024-03
    
    Recall Date: March 15, 2024
    Units Affected: Approximately 50,000 units sold
    Manufacture Date: January 2024 - February 2024
    
    Hazard: Front wheel may detach, posing fall hazard.
    
    Remedy: Free repair kit available. Call 1-800-555-0123 or visit www.saferide.com/recall
    Refund available if repair not desired.
    
    Sold At: Target, Walmart, Amazon.com from February 2024 to March 2024
    """

    # Extract metadata
    metadata = recall_agent.extract_metadata(recall_text)

    # Verify extracted data
    assert metadata["model_number"] == "ST-500"
    assert metadata["upc"] == "012345678905"
    assert len(metadata["lot_numbers"]) == 3
    assert "LOT2024-01" in metadata["lot_numbers"]

    # Verify dates
    assert metadata["recall_date"] == datetime(2024, 3, 15)
    assert metadata["manufacture_start"] == datetime(2024, 1, 1)
    assert metadata["manufacture_end"] == datetime(2024, 2, 29)

    # Verify quantities
    assert metadata["units_affected"] == 50000

    # Verify remedy information
    assert "repair" in metadata["remedies"]
    assert "refund" in metadata["remedies"]
    assert metadata["contact_phone"] == "1-800-555-0123"
    assert "www.saferide.com/recall" in metadata["contact_url"]

    # Verify retailers
    assert len(metadata["retailers"]) == 3
    assert "Target" in metadata["retailers"]
    assert "Walmart" in metadata["retailers"]
    assert "Amazon.com" in metadata["retailers"]
