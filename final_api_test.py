#!/usr/bin/env python3
"""
Final API verification - tests all critical endpoints
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://babyshield.cureviax.ai"

def test_endpoint(name, method, path, data=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        status = response.status_code
        if status == 200:
            print(f"✅ {name:30} - SUCCESS")
            return True
        else:
            print(f"❌ {name:30} - {status} {response.reason}")
            if status == 500 and response.json().get('error'):
                error = response.json()['error']['message']
                if 'column' in error and 'does not exist' in error:
                    print(f"   → Database schema issue: {error[:100]}...")
            return False
    except Exception as e:
        print(f"❌ {name:30} - ERROR: {e}")
        return False

print("=" * 70)
print("BABYSHIELD API - FINAL VERIFICATION")
print("=" * 70)
print(f"URL: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test all endpoints
tests = [
    ("Health Check", "GET", "/api/v1/healthz"),
    ("Version", "GET", "/api/v1/version"),
    ("Agencies List", "GET", "/api/v1/agencies"),
    ("Search API", "POST", "/api/v1/search/advanced", {"product": "baby formula", "limit": 5}),
    ("Privacy Summary", "GET", "/api/v1/user/privacy/summary"),
    ("API Documentation", "GET", "/docs"),
    ("OpenAPI Spec", "GET", "/openapi.json"),
]

passed = 0
failed = 0

print("[ENDPOINT TESTS]")
print("-" * 70)

for test in tests:
    name, method, path = test[0:3]
    data = test[3] if len(test) > 3 else None
    
    if test_endpoint(name, method, path, data):
        passed += 1
    else:
        failed += 1

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"✅ Passed: {passed}/{passed + failed}")
print(f"❌ Failed: {failed}/{passed + failed}")

if passed == len(tests):
    print("\n🎉 PERFECT! All endpoints working!")
    print("Your API is fully operational!")
elif failed <= 2:
    print("\n✅ GOOD! Most endpoints working!")
    print("Minor issues remaining - likely database schema.")
else:
    print("\n⚠️ Issues detected. Check deployment.")

# Test a real product search
print("\n[BONUS TEST - Real Product Search]")
print("-" * 70)

search_data = {
    "product": "Gerber",
    "agencies": ["FDA", "CPSC"],
    "limit": 3
}

response = requests.post(f"{BASE_URL}/api/v1/search/advanced", json=search_data, timeout=10)
if response.status_code == 200:
    data = response.json()
    if data.get('ok') and data.get('data'):
        results = data['data'].get('results', [])
        print(f"✅ Search returned {len(results)} results")
        for i, result in enumerate(results[:2], 1):
            print(f"   {i}. {result.get('product_name', 'Unknown')} - {result.get('agency', 'N/A')}")
    else:
        print("✅ Search worked but no results found")
else:
    print(f"❌ Search failed with status {response.status_code}")

print("\n✨ Test complete!")
