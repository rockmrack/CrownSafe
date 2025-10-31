#!/usr/bin/env python3
"""
Test script for critical backend features implementation
Tests all the newly added features to ensure they work correctly
"""

import os
import sys
import time
from typing import Any, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from api.main_crownsafe import app

client = TestClient(app)

# Test user credentials
TEST_EMAIL = f"test_critical_{int(time.time())}@example.com"
TEST_PASSWORD = "TestPass123!"


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {name}")
    if details:
        print(f"    {details}")


def register_user() -> Dict[str, Any]:
    """Register a test user"""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": "Test User"},
    )
    return response.json()


def login_user() -> str:
    """Login and get access token"""
    response = client.post("/api/v1/auth/token", data={"username": TEST_EMAIL, "password": TEST_PASSWORD})
    data = response.json()
    return data.get("access_token", "")


def get_headers(token: str) -> Dict[str, str]:
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}"}


def test_scan_history(token: str):
    """Test scan history endpoints"""
    print("\n=== Testing Scan History ===")
    headers = get_headers(token)

    # Test get scan history
    response = client.get("/api/v1/user/scan-history", headers=headers)
    print_test(
        "GET /scan-history",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Test scan statistics
    response = client.get("/api/v1/user/scan-statistics", headers=headers)
    print_test(
        "GET /scan-statistics",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )


def test_password_reset():
    """Test password reset flow"""
    print("\n=== Testing Password Reset ===")

    # Request password reset
    response = client.post("/api/v1/auth/password-reset/request", json={"email": TEST_EMAIL})
    print_test(
        "POST /password-reset/request",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Validate token (would need actual token from email)
    test_token = "test_token_123"
    response = client.post("/api/v1/auth/password-reset/validate", params={"token": test_token})
    # This will fail with invalid token, but endpoint should work
    print_test(
        "POST /password-reset/validate",
        response.status_code in [200, 400],
        f"Status: {response.status_code}",
    )


def test_notifications(token: str):
    """Test notification endpoints"""
    print("\n=== Testing Notifications ===")
    headers = get_headers(token)

    # Register device
    response = client.post(
        "/api/v1/notifications/device/register",
        headers=headers,
        json={
            "token": f"test_token_{int(time.time())}",
            "platform": "android",
            "device_name": "Test Device",
        },
    )
    print_test(
        "POST /notifications/device/register",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get notification history
    response = client.get("/api/v1/notifications/history", headers=headers)
    print_test(
        "GET /notifications/history",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Update preferences
    response = client.put(
        "/api/v1/notifications/preferences",
        headers=headers,
        json={
            "quiet_hours_enabled": True,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "notification_types": {"recalls": True, "safety_alerts": True},
        },
    )
    print_test(
        "PUT /notifications/preferences",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )


def test_monitoring(token: str):
    """Test product monitoring endpoints"""
    print("\n=== Testing Product Monitoring ===")
    headers = get_headers(token)

    # Add product to monitoring
    response = client.post(
        "/api/v1/monitoring/products/add",
        headers=headers,
        json={
            "product_name": "Test Baby Bottle",
            "brand_name": "TestBrand",
            "upc_code": "123456789012",
            "check_frequency_hours": 24,
        },
    )
    print_test(
        "POST /monitoring/products/add",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get monitored products
    response = client.get("/api/v1/monitoring/products", headers=headers)
    print_test(
        "GET /monitoring/products",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get monitoring status
    response = client.get("/api/v1/monitoring/status", headers=headers)
    print_test(
        "GET /monitoring/status",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )


def test_dashboard(token: str):
    """Test dashboard endpoints"""
    print("\n=== Testing Dashboard ===")
    headers = get_headers(token)

    # Get dashboard overview
    response = client.get("/api/v1/dashboard/overview", headers=headers)
    print_test(
        "GET /dashboard/overview",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get activity timeline
    response = client.get("/api/v1/dashboard/activity?days=7", headers=headers)
    print_test(
        "GET /dashboard/activity",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get product categories
    response = client.get("/api/v1/dashboard/product-categories", headers=headers)
    print_test(
        "GET /dashboard/product-categories",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get safety insights
    response = client.get("/api/v1/dashboard/safety-insights", headers=headers)
    print_test(
        "GET /dashboard/safety-insights",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    # Get achievements
    response = client.get("/api/v1/dashboard/achievements", headers=headers)
    print_test(
        "GET /dashboard/achievements",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )


def test_analytics():
    """Test analytics endpoint"""
    print("\n=== Testing Analytics ===")

    response = client.get("/api/v1/analytics/counts")
    print_test(
        "GET /analytics/counts",
        response.status_code == 200,
        f"Status: {response.status_code}",
    )

    if response.status_code == 200:
        data = response.json()
        print(f"    Total recalls: {data.get('total_recalls', 0)}")
        print(f"    Total agencies: {data.get('agencies_total', 0)}")


def main():
    """Run all tests"""
    print("=" * 50)
    print("CRITICAL FEATURES TEST SUITE")
    print("=" * 50)

    try:
        # Register and login
        print("\n=== Setup ===")
        reg_result = register_user()
        print_test("User Registration", "success" in reg_result or "id" in reg_result)

        token = login_user()
        print_test("User Login", bool(token))

        if not token:
            print("\n❌ Cannot proceed without authentication")
            return

        # Run all feature tests
        test_scan_history(token)
        test_password_reset()
        test_notifications(token)
        test_monitoring(token)
        test_dashboard(token)
        test_analytics()

        print("\n" + "=" * 50)
        print("✅ All critical features tested!")
        print("=" * 50)

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
