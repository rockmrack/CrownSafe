"""
Quick test to make a single request and see all headers
"""
import requests

print("\n" + "="*70)
print("TESTING: http://localhost:8001/docs")
print("="*70 + "\n")

try:
    response = requests.get("http://localhost:8001/docs", timeout=5)
    
    print(f"Status Code: {response.status_code}\n")
    print(f"Total Headers: {len(response.headers)}\n")
    print("ALL RESPONSE HEADERS:")
    print("-" * 70)
    
    for header, value in sorted(response.headers.items()):
        print(f"{header}: {value}")
    
    print("\n" + "="*70)
    print("SECURITY HEADERS CHECK:")
    print("="*70 + "\n")
    
    security_headers = [
        "x-frame-options",
        "x-content-type-options",
        "x-xss-protection",
        "referrer-policy",
        "content-security-policy",
        "permissions-policy",
        "x-permitted-cross-domain-policies"
    ]
    
    found = 0
    for header in security_headers:
        if header in response.headers:
            print(f"[OK] {header}: {response.headers[header][:80]}")
            found += 1
        else:
            print(f"[FAIL] {header}: MISSING")
    
    print(f"\n{'='*70}")
    print(f"RESULT: {found}/{len(security_headers)} security headers present")
    print(f"{'='*70}\n")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

