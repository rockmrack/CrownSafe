#!/usr/bin/env python3
"""
Test script to verify the fixes work
"""

import requests
import json

BASE_URL = "https://babyshield.cureviax.ai"

def test_endpoint(endpoint, method="GET", data=None, expected_status=200):
    """Test an endpoint and return the result"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data)
        
        print(f"✅ {method} {endpoint} - Status: {response.status_code}")
        if response.status_code == expected_status:
            try:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
        else:
            print(f"   Expected: {expected_status}, Got: {response.status_code}")
            print(f"   Error: {response.text[:200]}...")
        
        return response.status_code == expected_status
    except Exception as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False

def main():
    print("🧪 Testing BabyShield API Fixes")
    print("=" * 50)
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    test_endpoint("/healthz")
    
    # Test 2: Barcode Scan
    print("\n2. Testing Barcode Scan...")
    test_endpoint("/api/v1/barcode/scan", "POST", {"barcode": "012993441012"})
    
    # Test 3: Barcode Cache Status
    print("\n3. Testing Barcode Cache Status...")
    test_endpoint("/api/v1/barcode/cache/status")
    
    # Test 4: Barcode Cache Clear
    print("\n4. Testing Barcode Cache Clear...")
    test_endpoint("/api/v1/barcode/cache/clear", "POST")
    
    # Test 5: Recall Alerts Preferences (Dev)
    print("\n5. Testing Recall Alerts Preferences (Dev)...")
    test_endpoint("/api/v1/recall-alerts/preferences-dev")
    
    # Test 6: Recall Alerts Preferences (Production)
    print("\n6. Testing Recall Alerts Preferences (Production)...")
    test_endpoint("/api/v1/recall-alerts/preferences?user_id=1")
    
    # Test 7: Recall Alerts History
    print("\n7. Testing Recall Alerts History...")
    test_endpoint("/api/v1/recall-alerts/history/1")
    
    # Test 8: Recalls Search
    print("\n8. Testing Recalls Search...")
    test_endpoint("/api/v1/recalls?limit=5")
    
    # Test 9: Recall Detail
    print("\n9. Testing Recall Detail...")
    test_endpoint("/api/v1/recall/RECALL-002", expected_status=404)
    
    # Test 10: Safety Check
    print("\n10. Testing Safety Check...")
    test_endpoint("/api/v1/safety-check", "POST", {"user_id": 1, "barcode": "012993441012"})
    
    # Test 11: Mobile Instant Check
    print("\n11. Testing Mobile Instant Check...")
    test_endpoint("/api/v1/mobile/instant-check/012993441012?user_id=1")
    
    # Test 12: Mobile Quick Check
    print("\n12. Testing Mobile Quick Check...")
    test_endpoint("/api/v1/mobile/quick-check/012993441012?user_id=1")
    
    # Test 13: Advanced Guidelines (Valid Request)
    print("\n13. Testing Advanced Guidelines (Valid Request)...")
    test_endpoint("/api/v1/advanced/guidelines", "POST", {"user_id": 1, "child_age_months": 12, "product_name": "Baby Food"})
    
    # Test 14: Advanced Guidelines (Missing user_id)
    print("\n14. Testing Advanced Guidelines (Missing user_id)...")
    test_endpoint("/api/v1/advanced/guidelines", "POST", {"child_age_months": 12, "product_name": "Baby Food"}, expected_status=400)
    
    # Test 15: Supplemental Food Data
    print("\n15. Testing Supplemental Food Data...")
    test_endpoint("/api/v1/supplemental/food-data/apple")
    
    # Test 16: Supplemental Cosmetic Data
    print("\n16. Testing Supplemental Cosmetic Data...")
    test_endpoint("/api/v1/supplemental/cosmetic-data/glycerin")
    
    # Test 17: Supplemental Safety Report
    print("\n17. Testing Supplemental Safety Report...")
    test_endpoint("/api/v1/supplemental/safety-report", "POST", {"product_identifier": "012993441012", "product_name": "Test Product"})
    
    # Test 18: Test Barcodes Endpoint
    print("\n18. Testing Test Barcodes Endpoint...")
    test_endpoint("/api/v1/barcode/test/barcodes")
    
    # Test 19: WebDAV Method Blocking (PROPFIND)
    print("\n19. Testing WebDAV Method Blocking (PROPFIND)...")
    try:
        response = requests.request("PROPFIND", f"{BASE_URL}/")
        print(f"   Status: {response.status_code}")
        if response.status_code == 405:
            print("   ✅ WebDAV method properly blocked")
        else:
            print("   ❌ WebDAV method not blocked")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 20: Invalid Endpoint (404 Test)
    print("\n20. Testing Invalid Endpoint (404 Test)...")
    test_endpoint("/api/v1/nonexistent", expected_status=404)
    
    print("\n🎉 Testing completed!")

if __name__ == "__main__":
    main()
