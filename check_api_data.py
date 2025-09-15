import requests
import json

print("CHECKING API DATA STATUS")
print("=" * 60)

# 1. Check if API is running
health = requests.get("https://babyshield.cureviax.ai/api/v1/healthz")
print(f"Health Check: {'✅ OK' if health.status_code == 200 else '❌ Failed'}")

# 2. Check version
version = requests.get("https://babyshield.cureviax.ai/api/v1/version")
if version.status_code == 200:
    v_data = version.json()
    print(f"API Version: {v_data.get('api_version', 'Unknown')}")

# 3. Try different search patterns
print("\nTesting various search patterns:")
print("-" * 40)

searches = [
    {"product": "a"},  # Single letter - should match many things
    {"limit": 10},     # No filter - get any 10 recalls
    {"agencies": ["FDA"]},  # Just FDA recalls
    {"date_from": "2020-01-01", "date_to": "2025-12-31"}  # Date range only
]

for search in searches:
    response = requests.post(
        "https://babyshield.cureviax.ai/api/v1/search/advanced",
        json=search,
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("data", {}).get("results", []) if data.get("ok") else []
        print(f"Query {search}: Found {len(results)} results")
        if results:
            print(f"  First result: {results[0].get('product_name', 'Unknown')[:50]}")
    elif response.status_code == 400:
        error = response.json().get("error", {}).get("message", "")
        print(f"Query {search}: {error[:50]}")
    else:
        print(f"Query {search}: HTTP {response.status_code}")

# 4. Check database stats (if endpoint exists)
print("\n" + "=" * 60)
print("SUMMARY:")

conclusion = """
If all searches return 0 results, it means:
- ✅ API is working correctly
- ✅ Search endpoint is functional  
- ⚠️ Database may be empty or needs data population

To populate the database:
1. Run ingestion scripts from agents/recall_data_agent/
2. Or manually insert test data
3. Or restore from a database backup
"""

print(conclusion)
