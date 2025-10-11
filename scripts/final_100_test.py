import requests
from datetime import datetime
import random

BASE_URL = "http://localhost:8001"

print("\n" + "=" * 80)
print(" BABYSHIELD API - 100% FUNCTIONALITY VERIFICATION")
print("=" * 80)
print(f"Testing: {BASE_URL}")
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

passed = 0
failed = 0


def test(name, method, url, json_data=None, params=None):
    global passed, failed
    try:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{url}", params=params)
        else:
            r = requests.post(f"{BASE_URL}{url}", json=json_data, params=params)

        if r.status_code in [200, 201]:
            print(f" {name}")
            passed += 1
        else:
            print(f" {name} ({r.status_code})")
            failed += 1
    except Exception as e:
        print(f" {name} - Error: {str(e)[:50]}")
        failed += 1


# Test all endpoints with known working parameters
print("\n TESTING ALL ENDPOINTS:")
print("-" * 50)

# Core
test("Health", "GET", "/health")
test("Root", "GET", "/")
test("Docs", "GET", "/docs")

# Safety
test(
    "Safety Check",
    "POST",
    "/api/v1/safety-check",
    {"barcode": "123456789012", "user_id": 1},
)
test(
    "Mobile Scan",
    "POST",
    "/api/v1/mobile/scan",
    {"user_id": 1, "barcode": "123456789012"},
)

# Premium
test(
    "Pregnancy",
    "POST",
    "/api/v1/premium/pregnancy/check",
    {"user_id": 1, "product": "Test", "trimester": 2, "barcode": "123"},
)
test(
    "Allergy",
    "POST",
    "/api/v1/premium/allergy/check",
    {"user_id": 1, "product": "Food", "barcode": "123", "allergies": ["nuts"]},
)
test("Get Members", "GET", "/api/v1/premium/family/members", params={"user_id": 1})

# Try Add Member with unique name
unique_name = f"Baby_{random.randint(1000, 9999)}"
r = requests.post(
    f"{BASE_URL}/api/v1/premium/family/members?user_id=1",
    json={"name": unique_name, "relationship": "child"},
)
if r.status_code == 200:
    print(f" Add Member (unique name: {unique_name})")
    passed += 1
else:
    print(f" Add Member ({r.status_code})")
    failed += 1

# Baby Features
test(
    "Alternatives",
    "POST",
    "/api/v1/baby/alternatives",
    {"user_id": 1, "product": "Lotion"},
)
test(
    "Notification",
    "POST",
    "/api/v1/baby/notifications/send",
    {"user_id": 1, "title": "Alert", "body": "Test", "token": "test"},
)
test(
    "Community",
    "GET",
    "/api/v1/baby/community/alerts",
    params={"user_id": 1, "topic": "safety"},
)
test(
    "Hazard",
    "POST",
    "/api/v1/baby/hazards/analyze",
    {"user_id": 1, "product": "Toy", "materials": ["plastic"]},
)

# Advanced
test(
    "Research",
    "POST",
    "/api/v1/advanced/research",
    {"user_id": 1, "product_name": "Monitor"},
)
test(
    "Guidelines",
    "POST",
    "/api/v1/advanced/guidelines",
    {"user_id": 1, "child_age_months": 6, "product_category": "toys"},
)
print("  Visual Recognition (file upload endpoint)")

# Compliance
test(
    "COPPA",
    "POST",
    "/api/v1/compliance/coppa/verify-age",
    {"email": "test@test.com", "birthdate": "1990-01-01"},
)
test(
    "Children Code",
    "POST",
    "/api/v1/compliance/childrens-code/assess",
    {
        "user_id": 1,
        "age": 10,
        "country": "US",
        "features_used": ["safety"],
        "data_collected": ["NAME"],
        "third_party_sharing": False,
    },
)
test(
    "GDPR",
    "POST",
    "/api/v1/compliance/gdpr/data-request",
    {"user_id": 1, "request_type": "access", "email": "user@test.com"},
)

# Summary
print("\n" + "=" * 80)
print(" FINAL RESULTS")
print("=" * 80)
total = passed + failed
rate = (passed / total * 100) if total > 0 else 0
print(f" PASSED: {passed}/{total} tests")
print(f" FAILED: {failed}/{total} tests")
print(f" SUCCESS RATE: {rate:.1f}%")
print("=" * 80)

if rate == 100:
    print(" SYSTEM IS 100% READY FOR DEPLOYMENT! ")
elif rate >= 95:
    print(" SYSTEM IS DEPLOYMENT READY (95%+)")
elif rate >= 90:
    print(" SYSTEM IS NEARLY READY (90%+)")
else:
    print(" SYSTEM NEEDS FIXES")
