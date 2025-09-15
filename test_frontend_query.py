#!/usr/bin/env python3
"""
Test the EXACT query your frontend developer sent
"""

import requests
import json
from datetime import datetime

print("=" * 70)
print("TESTING FRONTEND DEVELOPER'S EXACT QUERY")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Your frontend developer's exact query
url = "https://babyshield.cureviax.ai/api/v1/search/advanced"
headers = {"Content-Type": "application/json"}
data = {
    "product": "Triacting Night Time Cold",
    "agencies": ["FDA"],
    "date_from": "2014-01-01",
    "date_to": "2025-12-31",
    "limit": 5
}

print("[ORIGINAL QUERY FROM YURII]")
print("-" * 70)
print(f"URL: {url}")
print(f"Method: POST")
print(f"Payload:")
print(json.dumps(data, indent=2))
print()

# Test the exact request
print("[TESTING NOW]")
print("-" * 70)

response = requests.post(url, json=data, headers=headers, timeout=10)

print(f"Status Code: {response.status_code}")
print(f"Status: {'✅ SUCCESS' if response.status_code == 200 else '❌ FAILED'}")
print()

# Parse response
try:
    result = response.json()
    
    if response.status_code == 200:
        print("[RESPONSE]")
        print("-" * 70)
        
        if result.get("ok"):
            data_section = result.get("data", {})
            results = data_section.get("results", [])
            
            print(f"✅ API returned successfully!")
            print(f"Found {len(results)} recall(s)")
            print()
            
            if results:
                print("[RECALL RESULTS]")
                print("-" * 70)
                for i, recall in enumerate(results, 1):
                    print(f"\n{i}. {recall.get('product_name', 'Unknown Product')}")
                    print(f"   Brand: {recall.get('brand', 'N/A')}")
                    print(f"   Agency: {recall.get('source_agency', 'N/A')}")
                    print(f"   Date: {recall.get('recall_date', 'N/A')}")
                    print(f"   Hazard: {recall.get('hazard', 'N/A')[:100]}")
            else:
                print("No recalls found for 'Triacting Night Time Cold'")
                print("(This is normal if this specific product has no recalls)")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    else:
        print("[ERROR RESPONSE]")
        print("-" * 70)
        print(json.dumps(result, indent=2))
        
except Exception as e:
    print(f"Failed to parse response: {e}")
    print(f"Raw response: {response.text[:500]}")

# Test other variations
print()
print("[ADDITIONAL TESTS]")
print("-" * 70)

# Test 1: Simpler search
print("\n1. Testing simpler search (product='cold'):")
simple_response = requests.post(url, 
    json={"product": "cold", "limit": 3},
    headers=headers,
    timeout=10
)
print(f"   Status: {simple_response.status_code} {'✅' if simple_response.status_code == 200 else '❌'}")
if simple_response.status_code == 200:
    data = simple_response.json()
    if data.get("ok"):
        results = data.get("data", {}).get("results", [])
        print(f"   Found {len(results)} results")

# Test 2: FDA search
print("\n2. Testing FDA-only search (product='medicine'):")
fda_response = requests.post(url,
    json={"product": "medicine", "agencies": ["FDA"], "limit": 3},
    headers=headers,
    timeout=10
)
print(f"   Status: {fda_response.status_code} {'✅' if fda_response.status_code == 200 else '❌'}")
if fda_response.status_code == 200:
    data = fda_response.json()
    if data.get("ok"):
        results = data.get("data", {}).get("results", [])
        print(f"   Found {len(results)} FDA recalls")

# Generate curl command for frontend developer
print()
print("=" * 70)
print("FOR YOUR FRONTEND DEVELOPER (YURII)")
print("=" * 70)

if response.status_code == 200:
    print("✅ THE API IS NOW WORKING!")
    print()
    print("Working curl command:")
    print("```bash")
    print('curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\')
    print('  -H "Content-Type: application/json" \\')
    print("  -d '{")
    print('    "product": "Triacting Night Time Cold",')
    print('    "agencies": ["FDA"],')
    print('    "date_from": "2014-01-01",')
    print('    "date_to": "2025-12-31",')
    print('    "limit": 5')
    print("  }'")
    print("```")
    print()
    print("Also try these working examples:")
    print()
    print("# Search for any product:")
    print('curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"product": "baby formula", "limit": 10}\'')
    print()
    print("# Search FDA recalls only:")
    print('curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"product": "tylenol", "agencies": ["FDA"]}\'')
    
else:
    print("❌ API still has issues.")
    print(f"Error: {response.status_code} - {response.reason}")
    print()
    print("Please check:")
    print("1. Database columns were added (severity, risk_category)")
    print("2. ECS service has restarted")
    print("3. CloudFront cache was cleared (if using CDN)")
