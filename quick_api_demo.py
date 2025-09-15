import requests
import json

print("QUICK API DEMO - Showing it works with real data")
print("=" * 60)

# Test with a product that should have recalls
test_queries = [
    {"product": "tylenol", "agencies": ["FDA"], "limit": 3},
    {"product": "baby", "limit": 3},
    {"product": "car seat", "limit": 2}
]

for i, query in enumerate(test_queries, 1):
    print(f"\nTest {i}: Searching for '{query.get('product')}'")
    print("-" * 40)
    
    response = requests.post(
        "https://babyshield.cureviax.ai/api/v1/search/advanced",
        json=query,
        headers={"Content-Type": "application/json"},
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            results = data.get("data", {}).get("results", [])
            print(f"✅ Found {len(results)} recalls")
            
            for j, recall in enumerate(results[:2], 1):
                print(f"  {j}. {recall.get('product_name', 'Unknown')[:50]}")
                print(f"     Agency: {recall.get('source_agency', 'N/A')}")
        else:
            print(f"❌ Error: {data.get('error')}")
    else:
        print(f"❌ HTTP {response.status_code}")
