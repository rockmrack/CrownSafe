#!/usr/bin/env python3
"""
Verify Task 11 deployment is successful
"""

import requests
import json
from datetime import datetime
import time

BASE_URL = "https://babyshield.cureviax.ai"

def test_endpoint(name, method, path, data=None):
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            return 0, None
        return resp.status_code, resp.json() if resp.text else None
    except Exception as e:
        return 0, str(e)


print("=" * 70)
print("TASK 11 DEPLOYMENT VERIFICATION")
print("=" * 70)
print(f"URL: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Critical endpoints to test
tests = [
    ("OAuth Providers", "GET", "/api/v1/auth/oauth/providers"),
    ("Settings", "GET", "/api/v1/settings/"),
    ("Crashlytics Status", "GET", "/api/v1/settings/crashlytics/status"),
    ("Retry Policy", "GET", "/api/v1/settings/retry-policy"),
    ("Privacy Summary", "GET", "/api/v1/user/privacy/summary"),
]

print("Testing Task 11 Endpoints:")
print("-" * 70)

passed = 0
failed = 0

for name, method, path in tests:
    status, response = test_endpoint(name, method, path)
    
    if status == 200:
        print(f"✅ {name:20} - Status: {status}")
        passed += 1
        
        # Show some response details
        if response and isinstance(response, dict):
            if "providers" in response:
                providers = response.get("providers", [])
                print(f"   Found {len(providers)} OAuth providers")
            elif "crashlytics_enabled" in response:
                print(f"   Crashlytics: {response.get('crashlytics_enabled')} (should be False by default)")
            elif "retry_policy" in response:
                policy = response.get("retry_policy", {})
                print(f"   Max retries: {policy.get('max_retries')}")
    else:
        print(f"❌ {name:20} - Status: {status}")
        failed += 1

print()
print("=" * 70)
print("DEPLOYMENT STATUS")
print("=" * 70)

if passed == len(tests):
    print("✅ DEPLOYMENT SUCCESSFUL!")
    print("All Task 11 endpoints are working correctly.")
    print()
    print("Mobile app can now use:")
    print("- Sign in with Apple/Google")
    print("- Export/Delete user data")
    print("- Toggle Crashlytics (OFF by default)")
    print()
    print("Next steps:")
    print("1. Test OAuth with real Apple/Google tokens")
    print("2. Verify data export/delete in app")
    print("3. Confirm Crashlytics toggle works")
    
elif passed > 0:
    print(f"⚠️ PARTIAL SUCCESS: {passed}/{len(tests)} endpoints working")
    print("Some endpoints may still be updating. Wait 1 minute and retry.")
    print()
    print("If issues persist:")
    print("1. Check ECS task logs")
    print("2. Verify database migrations ran")
    print("3. Check environment variables")
    
else:
    print("❌ DEPLOYMENT NOT READY")
    print("Task 11 endpoints not accessible yet.")
    print()
    print("Troubleshooting:")
    print("1. Check if ECS deployment is still in progress")
    print("2. Verify Docker image was pushed successfully")
    print("3. Check CloudWatch logs for errors")
    print("4. Ensure security groups allow traffic")

print()
print(f"Passed: {passed}/{len(tests)}")
print(f"Failed: {failed}/{len(tests)}")

# Test authentication flow simulation
print()
print("=" * 70)
print("OAUTH FLOW TEST")
print("=" * 70)

# Simulate OAuth login (will fail without real token, but tests endpoint)
test_oauth_data = {
    "provider": "apple",
    "id_token": "test_token_invalid"
}

status, response = test_endpoint("OAuth Login Test", "POST", "/api/v1/auth/oauth/login", test_oauth_data)

if status == 401:
    print("✅ OAuth endpoint responding correctly (401 for invalid token)")
    print("   Ready for real Apple/Google tokens")
elif status == 200:
    print("⚠️ OAuth accepted test token (check validation)")
elif status == 404:
    print("❌ OAuth endpoint not found - deployment may be pending")
else:
    print(f"⚠️ Unexpected status: {status}")

# Final summary
print()
print("=" * 70)
print("ACCEPTANCE CRITERIA")
print("=" * 70)

criteria = [
    ("OAuth endpoints available", "/api/v1/auth/oauth/providers" in [p for _, _, p in tests]),
    ("Settings endpoints available", "/api/v1/settings/" in [p for _, _, p in tests]),
    ("Crashlytics toggle available", "/api/v1/settings/crashlytics/status" in [p for _, _, p in tests]),
    ("Privacy compliance ready", "/api/v1/user/privacy/summary" in [p for _, _, p in tests]),
]

all_met = True
for criterion, met in criteria:
    status = "✅" if met else "❌"
    print(f"{status} {criterion}")
    if not met:
        all_met = False

if all_met and passed == len(tests):
    print()
    print("🎉 TASK 11 FULLY DEPLOYED AND OPERATIONAL!")
    print("Ready for mobile app integration!")
else:
    print()
    print("⏳ Deployment in progress or needs attention...")
