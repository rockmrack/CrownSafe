"""
Test if Phase 2 middleware can be imported and executed
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("\n=== Testing Phase 2 Middleware Import ===\n")

# Test 1: Can we import it?
print("Test 1: Importing SecurityHeadersMiddleware...")
try:
    from utils.security.security_headers import SecurityHeadersMiddleware
    print("[OK] Import successful")
except Exception as e:
    print(f"[FAIL] Import FAILED: {e}")
    sys.exit(1)

# Test 2: Can we instantiate it?
print("\nTest 2: Instantiating middleware...")
try:
    from fastapi import FastAPI
    app = FastAPI()
    
    # Try to add middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=False,
        enable_csp=True,
        enable_frame_options=True,
        enable_xss_protection=True,
    )
    print("[OK] Middleware instantiation successful")
except Exception as e:
    print(f"[FAIL] Instantiation FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Can we make a test request?
print("\nTest 3: Testing middleware execution...")
try:
    from fastapi.testclient import TestClient
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {len(response.headers)} headers")
    
    # Check for security headers
    security_headers = [
        "x-frame-options",
        "x-content-type-options",
        "x-xss-protection",
        "content-security-policy",
    ]
    
    found = 0
    for header in security_headers:
        if header in response.headers:
            print(f"  [OK] {header}: {response.headers[header][:50]}...")
            found += 1
        else:
            print(f"  [FAIL] {header}: MISSING")
    
    if found > 0:
        print(f"\n[SUCCESS] Middleware is working! ({found}/{len(security_headers)} headers found)")
    else:
        print(f"\n[FAIL] No security headers in response!")
        print("\nAll headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
    
except Exception as e:
    print(f"[FAIL] Execution test FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n=== Test Complete ===\n")

