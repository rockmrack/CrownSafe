#!/usr/bin/env python3
"""
Test the EXACT query from the frontend developer
"""
import requests
import json

print("="*70)
print("TESTING FRONTEND DEVELOPER'S EXACT QUERY")
print("="*70)

url = "https://babyshield.cureviax.ai/api/v1/search/advanced"
headers = {"Content-Type": "application/json"}
data = {
    "product": "Triacting Night Time Cold",
    "agencies": ["FDA"],
    "date_from": "2014-01-01",
    "date_to": "2025-12-31",
    "limit": 5
}

print(f"\nURL: {url}")
print(f"Method: POST")
print(f"Body: {json.dumps(data, indent=2)}")
print("\n" + "="*70)

try:
    response = requests.post(url, json=data, headers=headers, timeout=20)
    
    if response.status_code == 200:
        print("✅ SUCCESS! The API is working perfectly!")
        print(f"Status Code: {response.status_code}")
        print("\nResponse Summary:")
        result = response.json()
        if result.get("ok"):
            data = result.get("data", {})
            print(f"- Total Results: {data.get('total', 0)}")
            print(f"- Results Returned: {len(data.get('items', []))}")
            if data.get('items'):
                print("\nFirst Result:")
                first = data['items'][0]
                print(f"  Product: {first.get('productName', 'N/A')[:60]}...")
                print(f"  Brand: {first.get('brand', 'N/A')}")
                print(f"  Agency: {first.get('agencyCode', 'N/A')}")
                print(f"  Date: {first.get('recallDate', 'N/A')}")
        print("\n✅ THE FRONTEND QUERY IS WORKING!")
    elif response.status_code == 404:
        print("❌ ERROR: Still returning 404 Not Found")
        print("The endpoint is not deployed")
    else:
        print(f"⚠️ Unexpected Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
except requests.exceptions.Timeout:
    print("❌ ERROR: Request timed out (>20 seconds)")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")

print("\n" + "="*70)
