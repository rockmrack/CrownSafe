"""
Test middleware on a simple API endpoint
"""
import requests

print("\n" + "="*70)
print("Testing middleware on different endpoints")
print("="*70 + "\n")

endpoints = [
    "http://localhost:8001/healthz",
    "http://localhost:8001/api/v1/health",
    "http://localhost:8001/docs",
]

for url in endpoints:
    print(f"\nTesting: {url}")
    print("-" * 70)
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        
        security_headers = [
            "x-frame-options",
            "x-content-type-options",
            "content-security-policy"
        ]
        
        found = 0
        for header in security_headers:
            if header in response.headers:
                print(f"  [OK] {header}")
                found += 1
            else:
                print(f"  [FAIL] {header}")
        
        print(f"Result: {found}/{len(security_headers)} headers")
        
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "="*70 + "\n")

