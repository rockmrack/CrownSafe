#!/usr/bin/env python3
"""Verify BabyShield API deployment
Tests all critical endpoints after deployment.
"""

import json
import sys
from datetime import datetime

import requests

# Configuration
BASE_URL = "https://babyshield.cureviax.ai"
ENDPOINTS_TO_TEST = [
    ("GET", "/api/v1/healthz", None, "Health Check"),
    ("GET", "/api/v1/version", None, "Version Info"),
    (
        "POST",
        "/api/v1/search/advanced",
        {"product": "pacifier", "limit": 3},
        "Search Advanced",
    ),
    ("GET", "/api/v1/user/privacy/summary", None, "Privacy Summary"),
    ("GET", "/docs", None, "OpenAPI Documentation"),
]


def test_endpoint(method, path, data, name) -> str | None:
    """Test a single endpoint."""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        else:
            return f"❌ Unsupported method: {method}"

        if response.status_code == 200:
            # Try to parse JSON response
            try:
                json_data = response.json()
                if "ok" in json_data and json_data["ok"]:
                    return f"✅ {name}: Success"
                if "status" in json_data:  # for healthz
                    return f"✅ {name}: {json_data.get('status', 'ok')}"
                return f"✅ {name}: {response.status_code}"
            except (json.JSONDecodeError, ValueError):
                # Not JSON, but still successful
                if path == "/docs":
                    return f"✅ {name}: HTML documentation available"
                return f"✅ {name}: {response.status_code}"
        elif response.status_code == 404:
            return f"❌ {name}: NOT FOUND (404) - Endpoint not deployed!"
        elif response.status_code == 422:
            return f"⚠️  {name}: Validation error (422) - Check request format"
        elif response.status_code == 500:
            return f"❌ {name}: Server error (500) - Check logs"
        else:
            return f"⚠️  {name}: Status {response.status_code}"

    except requests.exceptions.Timeout:
        return f"❌ {name}: Timeout - Server not responding"
    except requests.exceptions.ConnectionError:
        return f"❌ {name}: Connection error - Server unreachable"
    except Exception as e:
        return f"❌ {name}: Error - {e!s}"


def main() -> int:
    print("=" * 60)
    print("🔍 BabyShield API Deployment Verification")
    print(f"🌐 Testing: {BASE_URL}")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    all_passed = True
    results = []

    for method, path, data, name in ENDPOINTS_TO_TEST:
        print(f"\nTesting: {name}")
        print(f"  {method} {path}")
        result = test_endpoint(method, path, data, name)
        print(f"  {result}")
        results.append(result)

        if "❌" in result:
            all_passed = False

    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if "✅" in r)
    failed = sum(1 for r in results if "❌" in r)
    warnings = sum(1 for r in results if "⚠️" in r)

    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")

    if all_passed:
        print("\n🎉 DEPLOYMENT SUCCESSFUL! All endpoints are working!")
    else:
        print("\n⚠️  DEPLOYMENT ISSUES DETECTED!")
        print("\nAction Required:")
        print("1. Check CloudWatch/container logs for errors")
        print("2. Verify database migrations were run")
        print("3. Ensure all environment variables are set")
        print("4. Check if ECS service has the latest image")

        # Provide specific troubleshooting for search endpoint
        if any("search/advanced" in r and "❌" in r for r in results):
            print("\n🔍 Search endpoint not working:")
            print("  - Run: alembic upgrade head")
            print("  - Check if pg_trgm extension is enabled")
            print("  - Verify services/search_service.py is deployed")

    print("\n" + "=" * 60)

    # Generate curl commands for manual testing
    print("\n📝 Manual Test Commands:")
    print("# Health check:")
    print(f"curl {BASE_URL}/api/v1/healthz")
    print("\n# Search test:")
    print(f"curl -X POST {BASE_URL}/api/v1/search/advanced \\")
    print("  -H 'Content-Type: application/json' \\")
    print('  -d \'{"product":"pacifier","limit":3}\'')

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
