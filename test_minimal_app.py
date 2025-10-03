"""
Minimal FastAPI app to test if SecurityHeadersMiddleware works at all
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from utils.security.security_headers import SecurityHeadersMiddleware

print("\n" + "="*70)
print("MINIMAL APP TEST - Does middleware work in isolation?")
print("="*70 + "\n")

# Create minimal app
app = FastAPI()

# Add middleware
print("Adding SecurityHeadersMiddleware...")
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=False,
    enable_csp=True,
    enable_frame_options=True,
    enable_xss_protection=True,
)
print("Middleware added.\n")

# Add test endpoint
@app.get("/test")
def test_endpoint():
    return {"status": "ok"}

# Test it
print("Making test request...\n")
client = TestClient(app)
response = client.get("/test")

print(f"Status Code: {response.status_code}\n")
print("Response Headers:")
print("-" * 70)

security_headers = {
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "x-xss-protection": "1; mode=block",
    "content-security-policy": "default-src 'self'",
    "referrer-policy": "strict-origin-when-cross-origin",
    "permissions-policy": "geolocation=()"
}

found = 0
for header, expected_start in security_headers.items():
    if header in response.headers:
        value = response.headers[header]
        if value.startswith(expected_start):
            print(f"[OK] {header}: {value[:60]}")
            found += 1
        else:
            print(f"[WARN] {header}: {value[:60]} (unexpected value)")
            found += 1
    else:
        print(f"[FAIL] {header}: MISSING")

print(f"\n{'='*70}")
if found == len(security_headers):
    print(f"✅ SUCCESS! {found}/{len(security_headers)} headers present")
    print("The middleware works in isolation!")
else:
    print(f"❌ FAILED! Only {found}/{len(security_headers)} headers present")
    print("The middleware has a bug!")
print(f"{'='*70}\n")

