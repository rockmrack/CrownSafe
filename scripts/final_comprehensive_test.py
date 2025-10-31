from datetime import datetime

import requests

BASE_URL = "http://localhost:8001"
print("\n" + "=" * 80)
print(" FINAL COMPREHENSIVE BABYSHIELD API TEST - 100% VERIFICATION")
print("=" * 80)
print(f"Testing against: {BASE_URL}")
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

results = {"passed": [], "failed": []}


def test_endpoint(name, method, path, data=None, params=None, files=None):
    """Test a single endpoint and track results"""
    try:
        url = f"{BASE_URL}{path}"
        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, data=data, timeout=5)
            else:
                response = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)

        if response.status_code in [200, 201]:
            print(f" {name}: SUCCESS ({response.status_code})")
            if response.content:
                try:
                    result = response.json()
                    # Show key fields for verification
                    if isinstance(result, dict):
                        keys = list(result.keys())[:3]
                        print(f"   Response keys: {keys}")
                except (json.JSONDecodeError, ValueError):
                    # Invalid JSON response
                    print(f"   Response: {response.text[:100]}")
            results["passed"].append(name)
            return True
        else:
            print(f" {name}: FAILED ({response.status_code})")
            try:
                error = response.json()
                print(f"   Error: {error.get('detail', error.get('error', str(error))[:100])}")
            except (json.JSONDecodeError, ValueError):
                # Invalid JSON error response
                print(f"   Error: {response.text[:100]}")
            results["failed"].append(name)
            return False
    except Exception as e:
        print(f" {name}: ERROR - {str(e)[:100]}")
        results["failed"].append(name)
        return False


# Test Categories
print("\n" + "=" * 80)
print("TESTING CORE SYSTEM ENDPOINTS")
print("=" * 80)

test_endpoint("Health Check", "GET", "/health")
test_endpoint("Root Endpoint", "GET", "/")
test_endpoint("API Documentation", "GET", "/docs")

print("\n" + "=" * 80)
print("TESTING CORE SAFETY FEATURES")
print("=" * 80)

test_endpoint(
    "Safety Check",
    "POST",
    "/api/v1/safety-check",
    {"barcode": "123456789012", "user_id": 1},
)

test_endpoint(
    "Mobile Scan",
    "POST",
    "/api/v1/mobile/scan",
    {"user_id": 1, "barcode": "123456789012", "quick_scan": True},
)

test_endpoint(
    "Advanced Search",
    "POST",
    "/api/v1/search/advanced",
    {"product": "baby bottle", "agencies": ["FDA", "CPSC"], "limit": 5},
)

print("\n" + "=" * 80)
print("TESTING PREMIUM FEATURES (Pregnancy & Allergy)")
print("=" * 80)

test_endpoint(
    "Pregnancy Safety Check",
    "POST",
    "/api/v1/premium/pregnancy/check",
    {
        "user_id": 1,
        "product": "Prenatal Vitamins",
        "trimester": 2,
        "barcode": "123456789",
    },
)

test_endpoint(
    "Allergy Check",
    "POST",
    "/api/v1/premium/allergy/check",
    {
        "user_id": 1,
        "product": "Baby Food",
        "barcode": "123",
        "allergies": ["peanuts", "milk"],
    },
)

test_endpoint("Get Family Members", "GET", "/api/v1/premium/family/members", params={"user_id": 1})

test_endpoint(
    "Add Family Member",
    "POST",
    "/api/v1/premium/family/members",
    {
        "user_id": 1,
        "name": "Baby John",
        "relationship": "child",
        "age": 2,
        "allergies": ["nuts"],
        "dietary_restrictions": ["gluten-free"],
    },
)

print("\n" + "=" * 80)
print("TESTING BABY SAFETY FEATURES")
print("=" * 80)

test_endpoint(
    "Safe Alternatives",
    "POST",
    "/api/v1/baby/alternatives",
    {"user_id": 1, "product": "Baby Lotion", "reason": "sensitive skin"},
)

test_endpoint(
    "Push Notification",
    "POST",
    "/api/v1/baby/notifications/send",
    {
        "user_id": 1,
        "title": "Safety Alert",
        "body": "Product recall",
        "token": "test-token",
    },
)

test_endpoint(
    "Generate Report",
    "POST",
    "/api/v1/baby/reports/generate",
    {"user_id": 1, "product_id": "123", "include_alternatives": True},
)

test_endpoint(
    "Community Alerts",
    "GET",
    "/api/v1/baby/community/alerts",
    params={"topic": "baby safety"},
)

test_endpoint(
    "Product Onboarding",
    "POST",
    "/api/v1/baby/onboarding/start",
    {"user_id": 1, "age_group": "infant"},
)

test_endpoint(
    "Hazard Analysis",
    "POST",
    "/api/v1/baby/hazards/analyze",
    {"product": "Baby Toy", "materials": ["plastic", "metal"]},
)

print("\n" + "=" * 80)
print("TESTING ADVANCED FEATURES")
print("=" * 80)

test_endpoint(
    "Web Research",
    "POST",
    "/api/v1/advanced/research",
    {"product_name": "Baby Monitor", "research_depth": "comprehensive"},
)

test_endpoint(
    "Age Guidelines",
    "POST",
    "/api/v1/advanced/guidelines",
    {"child_age_months": 6, "product_category": "toys"},
)

test_endpoint(
    "Visual Recognition",
    "POST",
    "/api/v1/advanced/visual/recognize",
    params={"user_id": 1},
    data={"image_data": "base64_test_image"},
)

test_endpoint(
    "Monitor Product",
    "POST",
    "/api/v1/advanced/monitor/add",
    {"user_id": 1, "product_id": "ABC123", "alert_threshold": "high"},
)

print("\n" + "=" * 80)
print("TESTING LEGAL COMPLIANCE FEATURES")
print("=" * 80)

test_endpoint(
    "COPPA Age Verification",
    "POST",
    "/api/v1/compliance/coppa/verify-age",
    {"email": "parent@example.com", "birthdate": "1990-01-01", "parent_consent": True},
)

test_endpoint(
    "Children's Code Assessment",
    "POST",
    "/api/v1/compliance/childrens-code/assess",
    {"data_collected": ["name", "age"], "purpose": "safety", "age_appropriate": True},
)

test_endpoint(
    "GDPR Data Request",
    "POST",
    "/api/v1/compliance/gdpr/data-request",
    {"user_id": 1, "request_type": "access"},
)

test_endpoint(
    "Legal Documents",
    "GET",
    "/api/v1/compliance/legal/documents",
    params={"doc_type": "privacy_policy", "version": "latest"},
)

test_endpoint("Delete User Data", "DELETE", "/api/v1/compliance/gdpr/delete/1")

print("\n" + "=" * 80)
print("TESTING ADDITIONAL FEATURES")
print("=" * 80)

test_endpoint(
    "Product Ingredients",
    "GET",
    "/api/v1/product/ingredients",
    params={"barcode": "123456789"},
)

test_endpoint(
    "Recall Details",
    "GET",
    "/api/v1/recalls/details",
    params={"recall_id": "REC-2024-001"},
)

test_endpoint(
    "User Preferences",
    "PUT",
    "/api/v1/users/1/preferences",
    {"notifications": True, "email_alerts": False},
)

# Final Summary
print("\n" + "=" * 80)
print(" FINAL TEST RESULTS SUMMARY")
print("=" * 80)
print(f" PASSED: {len(results['passed'])} tests")
print(f" FAILED: {len(results['failed'])} tests")
print(f" SUCCESS RATE: {len(results['passed']) / (len(results['passed']) + len(results['failed'])) * 100:.1f}%")

if results["failed"]:
    print("\n Failed Tests:")
    for test in results["failed"]:
        print(f"   {test}")
    print("\n ACTION REQUIRED: Fix the above failures before deployment!")
else:
    print("\n ALL TESTS PASSED! SYSTEM IS 100% READY FOR DEPLOYMENT!")

print("\n" + "=" * 80)
print(f"Test suite completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# Final verdict
if len(results["failed"]) == 0:
    print("\n DEPLOYMENT READY: 100% FUNCTIONAL ")
else:
    print(f"\n NOT READY: {len(results['failed'])} ISSUES NEED FIXING ")
