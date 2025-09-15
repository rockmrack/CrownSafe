import requests
import json

print("Testing if database is fixed...")

# Test search endpoint
response = requests.post(
    "https://babyshield.cureviax.ai/api/v1/search/advanced",
    json={"product": "baby", "limit": 5},
    headers={"Content-Type": "application/json"}
)

if response.status_code == 200:
    data = response.json()
    if data.get("ok"):
        results = data.get("data", {}).get("results", [])
        print(f"\n✅ SUCCESS! Search API is WORKING!")
        print(f"Found {len(results)} results")
        for i, r in enumerate(results[:3], 1):
            print(f"  {i}. {r.get('product_name', 'Unknown')[:50]}")
    else:
        print("✅ API responded but no results")
else:
    error = response.json().get("error", {}).get("message", "Unknown error")
    if "column" in error and "does not exist" in error:
        print(f"❌ Still broken: {error[:100]}")
        print("\n👉 Run the SQL in AWS RDS Query Editor!")
    else:
        print(f"❌ Error: {error[:100]}")
