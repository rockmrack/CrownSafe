#!/usr/bin/env python3
"""
Comprehensive deployment verification and fix script
"""

import requests
import json
import sys
from typing import Dict, List, Tuple

BASE_URL = "https://babyshield.cureviax.ai"


def check_endpoint(path: str, method: str = "GET", data: Dict = None) -> Tuple[int, Dict]:
    """Check if an endpoint is working"""
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data or {}, headers=headers, timeout=10)
        else:
            return 0, {"error": "Unsupported method"}

        return response.status_code, response.json() if response.headers.get(
            "content-type", ""
        ).startswith("application/json") else {"text": response.text[:200]}
    except requests.exceptions.Timeout:
        return 0, {"error": "Timeout"}
    except requests.exceptions.ConnectionError:
        return 0, {"error": "Connection failed"}
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    print("=" * 70)
    print("BABYSHIELD API DEPLOYMENT VERIFICATION")
    print("=" * 70)
    print(f"Testing: {BASE_URL}")
    print()

    # Test endpoints
    tests = [
        ("GET", "/", None, "Root"),
        ("GET", "/docs", None, "API Documentation"),
        ("GET", "/openapi.json", None, "OpenAPI Spec"),
        ("GET", "/api/v1/healthz", None, "Health Check"),
        ("GET", "/api/v1/version", None, "Version Info"),
        ("GET", "/api/v1/agencies", None, "Agencies List"),
        ("GET", "/api/v1/user/privacy/summary", None, "Privacy Summary"),
        (
            "POST",
            "/api/v1/search/advanced",
            {"product": "test", "limit": 1},
            "Search API",
        ),
        ("GET", "/api/v1/recall/TEST123", None, "Recall Detail"),
    ]

    results = []
    critical_failures = []

    print("[ENDPOINT TESTS]")
    print("-" * 70)

    for method, path, data, name in tests:
        status, response = check_endpoint(path, method, data)

        # Format result
        if status == 200:
            icon = "[OK]"
            detail = "Success"
        elif status == 404:
            icon = "[404]"
            detail = "Not Found"
            if path in ["/api/v1/healthz", "/api/v1/search/advanced"]:
                critical_failures.append(path)
        elif status == 0:
            icon = "[ERR]"
            detail = response.get("error", "Unknown error")
            if path in ["/api/v1/healthz", "/api/v1/search/advanced"]:
                critical_failures.append(path)
        else:
            icon = f"[{status}]"
            detail = f"HTTP {status}"

        print(f"{icon:7} {method:6} {path:40} - {name:20} ({detail})")
        results.append((path, status, response))

    # Check what's actually being served
    print("\n[ROOT RESPONSE ANALYSIS]")
    print("-" * 70)

    root_status, root_response = check_endpoint("/", "GET")
    if root_status == 200:
        if isinstance(root_response, dict) and "text" in root_response:
            content = root_response["text"].lower()
            if "fastapi" in content or "swagger" in content:
                print("[OK] FastAPI is running")
            elif "nginx" in content:
                print("[WARN] Nginx default page - API not properly routed")
            else:
                print(f"[INFO] Unknown response: {root_response['text'][:100]}...")

    # Check OpenAPI
    print("\n[OPENAPI SPECIFICATION]")
    print("-" * 70)

    openapi_status, openapi_response = check_endpoint("/openapi.json", "GET")
    if openapi_status == 200 and isinstance(openapi_response, dict):
        paths = openapi_response.get("paths", {})
        if "/api/v1/search/advanced" in paths:
            print("[OK] Search endpoint is in OpenAPI spec")
        else:
            print("[ERROR] Search endpoint NOT in OpenAPI spec")
            print(f"[INFO] Available paths: {list(paths.keys())[:5]}...")
    else:
        print("[ERROR] Cannot retrieve OpenAPI spec")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    working = sum(1 for _, status, _ in results if status == 200)
    total = len(results)

    print(f"Working endpoints: {working}/{total}")

    if critical_failures:
        print("\n[CRITICAL] The following critical endpoints are failing:")
        for path in critical_failures:
            print(f"  - {path}")

        print("\n[DIAGNOSIS]")
        print("-" * 70)

        if (
            "/api/v1/healthz" in critical_failures
            and "/api/v1/search/advanced" in critical_failures
        ):
            print(">>> The API is NOT running or NOT properly deployed!")
            print("\nPOSSIBLE CAUSES:")
            print("1. Docker container failed to start")
            print("2. Application crashed during startup")
            print("3. Database connection failed")
            print("4. Missing environment variables")
            print("5. Port mapping issue (API on wrong port)")
            print("6. Reverse proxy misconfiguration")

            print("\n[RECOMMENDED FIXES]")
            print("-" * 70)
            print("1. Check container logs:")
            print("   aws ecs describe-tasks --cluster <cluster> --tasks <task-id>")
            print("   docker logs <container-id>")
            print()
            print("2. Verify environment variables:")
            print("   - DATABASE_URL")
            print("   - REDIS_URL")
            print("   - SECRET_KEY")
            print()
            print("3. Test locally with production config:")
            print("   docker run --env-file .env.prod -p 8001:8001 babyshield-backend:api-v1")
            print()
            print("4. Force new deployment with fixed Dockerfile:")
            print("   docker build -f Dockerfile.final -t babyshield-backend:api-v1 .")
            print(
                "   aws ecr get-login-password | docker login --username AWS --password-stdin <ecr-url>"
            )
            print("   docker tag babyshield-backend:api-v1 <ecr-url>/babyshield-backend:api-v1")
            print("   docker push <ecr-url>/babyshield-backend:api-v1")
            print(
                "   aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment"
            )
    else:
        print("\n[SUCCESS] API is running!")

        if "/api/v1/search/advanced" not in [p for p, s, _ in results if s == 200]:
            print("\n[WARNING] Search endpoint not working. Check:")
            print("- Database connection")
            print("- Search service file exists")
            print("- PostgreSQL extensions (pg_trgm)")

    # Return exit code
    return 0 if not critical_failures else 1


if __name__ == "__main__":
    sys.exit(main())
