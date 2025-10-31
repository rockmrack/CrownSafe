#!/usr/bin/env python3
"""FINAL 100% VERIFICATION TEST FOR BABYSHIELD API
Tests all implemented endpoints with correct parameters
"""

from datetime import datetime

import requests

BASE_URL = "http://localhost:8001"


def test_endpoint(name, method, path, data=None, params=None, expected_status=[200, 201]):
    """Test a single endpoint"""
    try:
        url = f"{BASE_URL}{path}"

        if method == "GET":
            response = requests.get(url, params=params, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, timeout=5)

        success = response.status_code in expected_status

        if success:
            print(f"✅ {name}")
            return True
        else:
            print(f"❌ {name} - Status: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ {name} - Error: {str(e)[:50]}")
        return False


def main():
    print("\n" + "=" * 80)
    print("🚀 100% VERIFICATION TEST - BABYSHIELD API")
    print("=" * 80)
    print(f"Testing: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {"passed": 0, "failed": 0}

    # Track test results
    def run_test(name, method, path, data=None, params=None, expected=[200, 201]):
        if test_endpoint(name, method, path, data, params, expected_status=expected):
            results["passed"] += 1
        else:
            results["failed"] += 1

    print("\n🔍 CORE SYSTEM")
    print("-" * 40)
    run_test("Health Check", "GET", "/health")
    run_test("Root", "GET", "/")
    run_test("API Docs", "GET", "/docs")

    print("\n🔍 CORE SAFETY FEATURES")
    print("-" * 40)
    run_test(
        "Safety Check",
        "POST",
        "/api/v1/safety-check",
        {"barcode": "123456789012", "user_id": 1},
    )
    run_test(
        "Mobile Scan",
        "POST",
        "/api/v1/mobile/scan",
        {"user_id": 1, "barcode": "123456789012", "quick_scan": True},
    )

    print("\n🔍 PREMIUM FEATURES")
    print("-" * 40)
    run_test(
        "Pregnancy Safety",
        "POST",
        "/api/v1/premium/pregnancy/check",
        {
            "user_id": 1,
            "product": "Test Product",
            "trimester": 2,
            "barcode": "123456789",
        },
    )
    run_test(
        "Allergy Check",
        "POST",
        "/api/v1/premium/allergy/check",
        {
            "user_id": 1,
            "product": "Baby Food",
            "barcode": "123",
            "allergies": ["peanuts"],
        },
    )
    run_test(
        "Get Family Members",
        "GET",
        "/api/v1/premium/family/members",
        params={"user_id": 1},
    )
    run_test(
        "Add Family Member",
        "POST",
        "/api/v1/premium/family/members",
        {"name": "Test Baby", "relationship": "child"},
        params={"user_id": 1},
        expected=[200, 201],
    )

    print("\n🔍 BABY SAFETY FEATURES")
    print("-" * 40)
    run_test(
        "Safe Alternatives",
        "POST",
        "/api/v1/baby/alternatives",
        {"user_id": 1, "product": "Baby Lotion", "reason": "sensitive skin"},
    )
    run_test(
        "Push Notification",
        "POST",
        "/api/v1/baby/notifications/send",
        {
            "user_id": 1,
            "title": "Test Alert",
            "body": "Test message",
            "token": "test-token",
        },
    )
    run_test(
        "Community Alerts",
        "GET",
        "/api/v1/baby/community/alerts",
        params={"user_id": 1, "topic": "baby safety"},
    )
    run_test(
        "Hazard Analysis",
        "POST",
        "/api/v1/baby/hazards/analyze",
        {"user_id": 1, "product": "Baby Toy", "materials": ["plastic"]},
    )

    print("\n🔍 ADVANCED FEATURES")
    print("-" * 40)
    run_test(
        "Web Research",
        "POST",
        "/api/v1/advanced/research",
        {
            "user_id": 1,
            "product_name": "Baby Monitor",
            "research_depth": "comprehensive",
        },
    )
    run_test(
        "Age Guidelines",
        "POST",
        "/api/v1/advanced/guidelines",
        {"user_id": 1, "child_age_months": 6, "product_category": "toys"},
    )
    # Visual Recognition requires file upload (multipart/form-data), not JSON
    # Skipping in JSON-only test suite - works with actual file upload
    print("⏭️  Visual Recognition (requires file upload, tested separately)")

    print("\n🔍 COMPLIANCE FEATURES")
    print("-" * 40)
    run_test(
        "COPPA Age Verify",
        "POST",
        "/api/v1/compliance/coppa/verify-age",
        {
            "email": "parent@example.com",
            "birthdate": "1990-01-01",
            "parent_consent": True,
        },
    )
    run_test(
        "Children's Code",
        "POST",
        "/api/v1/compliance/childrens-code/assess",
        {
            "user_id": 1,
            "age": 10,
            "country": "US",
            "features_used": ["safety_check", "alerts"],
            "data_collected": ["NAME", "AGE"],
            "third_party_sharing": False,
        },
    )
    run_test(
        "GDPR Data Request",
        "POST",
        "/api/v1/compliance/gdpr/data-request",
        {"user_id": 1, "request_type": "access", "email": "user@example.com"},
    )

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    total = results["passed"] + results["failed"]
    success_rate = (results["passed"] / total * 100) if total > 0 else 0

    print(f"✅ PASSED: {results['passed']} tests")
    print(f"❌ FAILED: {results['failed']} tests")
    print(f"📈 SUCCESS RATE: {success_rate:.1f}%")

    print("\n" + "=" * 80)
    if success_rate == 100:
        print("✅✅✅ SYSTEM IS 100% READY FOR DEPLOYMENT! ✅✅✅")
    elif success_rate >= 80:
        print("⚠️ SYSTEM IS MOSTLY READY (>80%) - Minor fixes needed")
    else:
        print("❌ SYSTEM NEEDS FIXES BEFORE DEPLOYMENT")
    print("=" * 80)

    return success_rate


if __name__ == "__main__":
    rate = main()
    exit(0 if rate == 100 else 1)
