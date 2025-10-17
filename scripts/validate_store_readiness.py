#!/usr/bin/env python3
"""
Validate store readiness against production API
Tests critical endpoints and features required for app store submission
"""

import os
import sys
import json
import requests
import time
from typing import Dict, List, Tuple

BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "https://babyshield.cureviax.ai")

CRITICAL_ENDPOINTS = [
    # Health and system
    ("GET", "/api/v1/healthz", None, "Health Check", True),
    ("GET", "/api/v1/version", None, "Version Info", False),
    # Core functionality
    (
        "POST",
        "/api/v1/search/advanced",
        {"product": "test", "limit": 1},
        "Search API",
        True,
    ),
    ("GET", "/api/v1/agencies", None, "Agencies List", False),
    # Privacy compliance
    ("GET", "/api/v1/user/privacy/summary", None, "Privacy Summary", True),
    # Documentation
    ("GET", "/docs", None, "API Documentation", True),
    # Legal pages
    ("GET", "/legal/privacy", None, "Privacy Policy", True),
    ("GET", "/legal/terms", None, "Terms of Service", True),
    ("GET", "/legal/data-deletion", None, "Data Deletion Policy", True),
]


def test_endpoint(
    method: str, path: str, data: dict, name: str
) -> Tuple[bool, str, int]:
    """Test a single endpoint and return status"""
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "BabyShield-Readiness-Check/1.0",
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            return False, f"Unsupported method: {method}", 0

        return response.status_code == 200, response.reason, response.status_code

    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection Error", 0
    except Exception as e:
        return False, str(e), 0


def check_headers(url: str) -> Dict[str, bool]:
    """Check security and operational headers"""
    try:
        response = requests.get(url, timeout=10)
        headers = response.headers

        checks = {
            "X-Content-Type-Options": "nosniff"
            in headers.get("X-Content-Type-Options", ""),
            "X-Frame-Options": headers.get("X-Frame-Options", "")
            in ["DENY", "SAMEORIGIN"],
            "Strict-Transport-Security": "max-age="
            in headers.get("Strict-Transport-Security", ""),
            "X-API-Version": bool(headers.get("X-API-Version")),
            "Server": bool(headers.get("Server")),
        }

        return checks
    except:
        return {}


def main():
    """Run store readiness validation"""
    print("🚀 BabyShield Store Readiness Validation")
    print(f"🌐 Testing: {BASE_URL}")
    print(f"📅 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    critical_failed = 0
    total_passed = 0
    total_failed = 0

    print("\n📡 Testing Endpoints...")
    for method, path, data, name, is_critical in CRITICAL_ENDPOINTS:
        success, reason, status = test_endpoint(method, path, data, name)

        if success:
            print(f"  ✅ {name}: OK ({status})")
            total_passed += 1
        else:
            icon = "❌" if is_critical else "⚠️"
            print(f"  {icon} {name}: FAILED ({reason})")
            total_failed += 1
            if is_critical:
                critical_failed += 1

    # Check security headers
    print("\n🔒 Checking Security Headers...")
    headers = check_headers(f"{BASE_URL}/api/v1/healthz")
    if headers:
        for header, present in headers.items():
            status = "✅" if present else "⚠️"
            print(f"  {status} {header}: {'Present' if present else 'Missing'}")
    else:
        print("  ❌ Could not check headers")

    # Check response format
    print("\n📋 Checking API Response Format...")
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/search/advanced",
            json={"product": "test", "limit": 1},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            has_ok = "ok" in data
            has_data = "data" in data
            has_trace = "traceId" in data or "trace_id" in data

            print(f"  {'✅' if has_ok else '❌'} 'ok' field present")
            print(f"  {'✅' if has_data else '❌'} 'data' field present")
            print(f"  {'✅' if has_trace else '⚠️'} Trace ID present")
    except:
        print("  ❌ Could not verify response format")

    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {total_passed}/{total_passed + total_failed}")
    print(f"❌ Failed: {total_failed}/{total_passed + total_failed}")
    print(f"🔴 Critical failures: {critical_failed}")

    # Readiness determination
    print("\n📱 STORE SUBMISSION READINESS:")
    if critical_failed == 0:
        print("✅ API is READY for app store submission")
        print("   All critical endpoints are working")
        return 0
    else:
        print("❌ API is NOT READY for app store submission")
        print(f"   {critical_failed} critical endpoint(s) are failing")
        print("\nRequired actions:")
        print("1. Deploy the latest code to production")
        print("2. Run database migrations")
        print("3. Ensure all environment variables are set")
        print("4. Restart the API service")
        return 1


if __name__ == "__main__":
    sys.exit(main())
