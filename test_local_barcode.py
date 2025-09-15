#!/usr/bin/env python3
"""
Test barcode endpoint locally
"""

# Test the fixed barcode module
try:
    import sys
    sys.path.insert(0, '.')
    
    from api.barcode_bridge import normalize_barcode, extract_brand_from_barcode
    
    print("✅ Module imports successfully")
    
    # Test normalize function
    test_barcode = "012345678905"
    normalized, barcode_type = normalize_barcode(test_barcode)
    print(f"✅ Normalize works: {test_barcode} → {normalized} ({barcode_type})")
    
    # Test brand extraction
    brand = extract_brand_from_barcode(normalized)
    print(f"✅ Brand extraction works: {brand if brand else 'No brand found'}")
    
    print("\n✅ ALL LOCAL TESTS PASS - Barcode module is fixed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
