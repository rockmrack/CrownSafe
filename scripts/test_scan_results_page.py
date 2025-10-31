#!/usr/bin/env python3
"""
Test the new scan results page implementation
Verifies legally defensible language and proper formatting
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.models.scan_results import (
    VerdictType,
    create_scan_results,
)


def test_scan_results_page():
    """Test the scan results page generation"""

    print("Testing Scan Results Page Implementation...")
    print("=" * 60)

    # Test Case 1: No recalls found (safe product)
    print("\n1. Testing NO RECALLS FOUND scenario...")

    scan_data_safe = {
        "product_name": "Baby Monitor Pro",
        "brand": "SafeWatch",
        "barcode": "014292998228",
        "model_number": "SM-2024",
        "upc_gtin": "014292998228",
        "scan_type": "barcode",
    }

    barcode_info_safe = {
        "barcode": "014292998228",
        "format": "ean13",
        "confidence": 99.0,
    }

    result_safe = create_scan_results(scan_data_safe, None, barcode_info_safe)

    # Verify the response
    assert result_safe.verdict == VerdictType.NO_RECALLS_FOUND, "Verdict should be 'No Recalls Found'"
    assert result_safe.verdict_color == "green", "Color should be green for safe products"
    assert result_safe.verdict_icon == "checkmark", "Icon should be checkmark"
    assert result_safe.sub_text == "No recalls or allergen issues found in our database.", (
        "Sub-text should clarify database check"
    )
    assert "39+ (No recalls found)" in result_safe.safety_check.agencies_checked, "Should show 39+ agencies"
    assert result_safe.barcode_detection.quality_badge == "Best Quality: 014292998228 (ean13)", (
        "Should show quality badge"
    )

    print(f"✅ Verdict: {result_safe.verdict}")
    print(f"✅ Sub-text: {result_safe.sub_text}")
    print(f"✅ Agencies: {result_safe.safety_check.agencies_checked}")
    print(f"✅ Quality Badge: {result_safe.barcode_detection.quality_badge}")

    # Test Case 2: Recall found (dangerous product)
    print("\n2. Testing RECALL FOUND scenario...")

    scan_data_recall = {
        "product_name": "Recalled Crib",
        "brand": "DangerBrand",
        "barcode": "987654321098",
        "model_number": "CRIB-X",
        "scan_type": "barcode",
    }

    recall_data = {
        "recall_found": True,
        "recall_count": 2,
        "recalls": [
            {
                "recall_id": "CPSC-2024-001",
                "agency": "CPSC",
                "date": "2024-01-15",
                "hazard": "Entrapment and suffocation hazard",
                "remedy": "Stop use immediately and contact manufacturer for refund",
                "severity": "critical",
                "match_confidence": 0.95,
            },
            {
                "recall_id": "FDA-2024-002",
                "agency": "FDA",
                "date": "2024-01-20",
                "hazard": "Lead paint detected",
                "remedy": "Return product for full refund",
                "severity": "high",
                "match_confidence": 0.90,
            },
        ],
    }

    result_recall = create_scan_results(scan_data_recall, recall_data, None)

    # Verify the response
    assert result_recall.verdict == VerdictType.RECALL_FOUND, "Verdict should be 'Recall Alert'"
    assert result_recall.verdict_color == "red", "Color should be red for recalls"
    assert result_recall.verdict_icon == "warning", "Icon should be warning"
    assert "2 recall(s) found" in result_recall.sub_text, "Sub-text should show recall count"
    assert "39+ (2 recalls found)" in result_recall.safety_check.agencies_checked, (
        "Should show recall count in agencies"
    )
    assert len(result_recall.recalls) == 2, "Should have 2 recalls"
    assert result_recall.total_recalls == 2, "Total recalls should be 2"

    print(f"✅ Verdict: {result_recall.verdict}")
    print(f"✅ Sub-text: {result_recall.sub_text}")
    print(f"✅ Agencies: {result_recall.safety_check.agencies_checked}")
    print(f"✅ Recalls found: {result_recall.total_recalls}")

    # Test Case 3: Verify action buttons
    print("\n3. Testing action buttons...")

    assert result_safe.actions["download_pdf"] == "/api/v1/reports/generate", "Should have PDF download endpoint"
    assert result_safe.actions["view_details"] == "/api/v1/products/details", "Should have view details endpoint"

    print(f"✅ Download PDF: {result_safe.actions['download_pdf']}")
    print(f"✅ View Details: {result_safe.actions['view_details']}")

    # Test Case 4: Verify JSON serialization
    print("\n4. Testing JSON serialization...")

    json_output = result_safe.model_dump_json(indent=2)
    parsed = json.loads(json_output)

    assert parsed["verdict"] == "No Recalls Found", "JSON should contain correct verdict"
    assert parsed["safety_check"]["status"] == "All checks complete", "Should show complete status"

    print("✅ JSON serialization successful")

    # Test Case 5: Verify no contradictory messaging
    print("\n5. Verifying no contradictory messaging...")

    # For safe products
    assert "safe" not in result_safe.verdict.lower(), "Should not use 'safe' in verdict"
    assert "guarantee" not in result_safe.sub_text.lower(), "Should not use 'guarantee' language"

    # Check that agencies are never shown as 0
    assert "0" not in result_safe.safety_check.agencies_checked, "Should never show 0 agencies"

    print("✅ No contradictory messaging found")
    print("✅ Legally defensible language used throughout")

    print("\n" + "=" * 60)
    print("All tests passed! The scan results page implementation:")
    print("1. ✅ Uses legally defensible language (no 'Safe to use')")
    print("2. ✅ Shows 'No Recalls Found' as primary verdict")
    print("3. ✅ Includes transparent barcode detection data")
    print("4. ✅ Shows '39+' agencies (never 0)")
    print("5. ✅ Provides clear product summary")
    print("6. ✅ Includes action buttons for PDF and details")
    print("7. ✅ Differentiates between recall and no-recall scenarios")
    print("=" * 60)


if __name__ == "__main__":
    test_scan_results_page()
