import requests
import json

# Test search endpoint to see the exact error
url = "https://babyshield.cureviax.ai/api/v1/search/advanced"
headers = {"Content-Type": "application/json"}
data = {"product": "test", "limit": 1}

print("Testing search endpoint...")
response = requests.post(url, json=data, headers=headers)

print(f"\nStatus Code: {response.status_code}")
print(f"Headers: {dict(response.headers)}")

if response.text:
    try:
        result = response.json()
        print(f"\nResponse JSON:")
        print(json.dumps(result, indent=2))
    except:
        print(f"\nResponse Text: {response.text[:500]}")
