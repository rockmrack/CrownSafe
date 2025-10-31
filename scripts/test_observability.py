#!/usr/bin/env python3
"""
Test script for Task 4 - Observability features
Validates correlation IDs, rate limits, metrics, and error handling
"""

import json
import os
import sys
import time

import requests

# Configuration
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")
HEADERS = {"Content-Type": "application/json"}


class ObservabilityTester:
    """Test suite for observability features"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.results = []

    def test(self, condition: bool, message: str):
        """Record test result"""
        if condition:
            print(f"✅ {message}")
            self.results.append(True)
        else:
            print(f"❌ {message}")
            self.results.append(False)
        return condition

    def test_correlation_ids(self) -> bool:
        """Test that correlation IDs are present in all responses"""
        print("\n📝 Testing Correlation IDs...")

        # Test various endpoints
        endpoints = [
            ("/api/v1/healthz", "GET", None),
            ("/api/v1/search/advanced", "POST", {"product": "test", "limit": 1}),
            ("/api/v1/recall/TEST-ID", "GET", None),  # Should 404 but have headers
        ]

        for path, method, data in endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{path}")
                else:
                    response = self.session.post(f"{self.base_url}{path}", json=data)

                # Check for correlation headers
                has_request_id = "X-Request-ID" in response.headers
                has_correlation_id = "X-Correlation-ID" in response.headers
                has_api_version = "X-API-Version" in response.headers

                self.test(
                    has_request_id or has_correlation_id,
                    f"{method} {path} has correlation ID header",
                )

                self.test(has_api_version, f"{method} {path} has X-API-Version header")

                # Check for traceId in JSON response
                if response.headers.get("content-type", "").startswith("application/json"):
                    try:
                        data = response.json()
                        has_trace = "traceId" in data or "trace_id" in data
                        self.test(has_trace, f"{method} {path} has traceId in JSON response")
                    except (json.JSONDecodeError, ValueError):
                        pass  # Response is not valid JSON

            except Exception as e:
                print(f"   ⚠️ Error testing {path}: {e}")

        return all(self.results[-6:]) if len(self.results) >= 6 else False

    def test_security_headers(self) -> bool:
        """Test that security headers are present"""
        print("\n🔒 Testing Security Headers...")

        response = self.session.get(f"{self.base_url}/api/v1/healthz")

        security_headers = {
            "Strict-Transport-Security": "HSTS",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "X-Frame-Options",
            "Referrer-Policy": "Referrer-Policy",
        }

        for header, name in security_headers.items():
            self.test(header in response.headers, f"{name} header present")

        return all(self.results[-4:]) if len(self.results) >= 4 else False

    def test_error_format(self) -> bool:
        """Test unified error response format"""
        print("\n❌ Testing Error Format...")

        # Test 404
        response = self.session.get(f"{self.base_url}/api/v1/recall/NONEXISTENT")
        if response.status_code == 404:
            try:
                data = response.json()
                self.test(not data.get("ok"), "404 error has ok=false")
                self.test("error" in data, "404 error has error object")
                self.test("code" in data.get("error", {}), "404 error has error code")
                self.test("message" in data.get("error", {}), "404 error has error message")
                self.test("traceId" in data, "404 error has traceId")
            except (json.JSONDecodeError, ValueError):
                self.test(False, "404 response is valid JSON")

        # Test validation error (422)
        response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json={"invalid_field": "test"})
        if response.status_code in [400, 422]:
            try:
                data = response.json()
                self.test(not data.get("ok"), "Validation error has ok=false")
                self.test(
                    data.get("error", {}).get("code") in ["VALIDATION_ERROR", "INVALID_PARAMETERS", "BAD_REQUEST"],
                    "Validation error has appropriate error code",
                )
            except (json.JSONDecodeError, ValueError):
                self.test(False, "Validation error response is valid JSON")

        return all(self.results[-7:]) if len(self.results) >= 7 else False

    def test_health_readiness(self) -> bool:
        """Test health and readiness endpoints"""
        print("\n💚 Testing Health & Readiness...")

        # Test health endpoint
        response = self.session.get(f"{self.base_url}/api/v1/healthz")
        self.test(response.status_code == 200, "Health endpoint returns 200")
        if response.status_code == 200:
            data = response.json()
            self.test(data.get("ok"), "Health endpoint has ok=true")
            self.test(data.get("status") == "healthy", "Health endpoint shows healthy")

        # Test readiness endpoint
        response = self.session.get(f"{self.base_url}/api/v1/readyz")
        self.test(
            response.status_code in [200, 503],
            f"Readiness endpoint returns {response.status_code}",
        )
        if response.status_code in [200, 503]:
            data = response.json()
            self.test("dependencies" in data, "Readiness has dependencies")
            deps = data.get("dependencies", {})
            self.test("db" in deps, "Readiness checks database")
            self.test("redis" in deps, "Readiness checks Redis")

            if response.status_code == 200:
                print(f"   ℹ️ Dependencies: DB={deps.get('db')}, Redis={deps.get('redis')}")

        return all(self.results[-7:]) if len(self.results) >= 7 else False

    def test_metrics(self) -> bool:
        """Test Prometheus metrics endpoint"""
        print("\n📊 Testing Metrics...")

        response = self.session.get(f"{self.base_url}/metrics")
        self.test(
            response.status_code == 200,
            f"Metrics endpoint returns {response.status_code}",
        )

        if response.status_code == 200:
            content = response.text
            self.test(
                "http_requests_total" in content or "http_request_duration" in content,
                "Metrics contain HTTP request metrics",
            )
            self.test(
                "# TYPE" in content and "# HELP" in content,
                "Metrics are in Prometheus format",
            )

        return all(self.results[-3:]) if len(self.results) >= 3 else False

    def test_rate_limiting(self) -> bool:
        """Test rate limiting (simplified test)"""
        print("\n⏱️ Testing Rate Limiting...")
        print("   Note: Full rate limit test requires Redis and multiple requests")

        # Make a few rapid requests
        hit_limit = False
        for i in range(10):
            response = self.session.post(
                f"{self.base_url}/api/v1/search/advanced",
                json={"product": "test", "limit": 1},
            )

            if response.status_code == 429:
                hit_limit = True
                data = response.json()
                self.test(
                    data.get("error", {}).get("code") == "RATE_LIMITED",
                    "Rate limit error has correct code",
                )
                self.test(
                    "Retry-After" in response.headers,
                    "Rate limit response has Retry-After header",
                )
                break

        if not hit_limit:
            print("   ℹ️ Rate limit not hit in 10 requests (may be disabled or high limit)")
            return True  # Not a failure if rate limiting is disabled

        return all(self.results[-2:]) if len(self.results) >= 2 else True

    def test_server_timing(self) -> bool:
        """Test Server-Timing header"""
        print("\n⏱️ Testing Server Timing...")

        response = self.session.get(f"{self.base_url}/api/v1/healthz")
        self.test(
            "Server-Timing" in response.headers or "X-Response-Time" in response.headers,
            "Response includes timing information",
        )

        return self.results[-1] if self.results else False

    def run_all_tests(self) -> bool:
        """Run all observability tests"""
        print("=" * 60)
        print("🔍 OBSERVABILITY TEST SUITE")
        print("=" * 60)

        tests = [
            ("Correlation IDs", self.test_correlation_ids),
            ("Security Headers", self.test_security_headers),
            ("Error Format", self.test_error_format),
            ("Health & Readiness", self.test_health_readiness),
            ("Metrics", self.test_metrics),
            ("Rate Limiting", self.test_rate_limiting),
            ("Server Timing", self.test_server_timing),
        ]

        test_results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                test_results.append((name, passed))
            except Exception as e:
                print(f"\n❌ {name} test failed with error: {e}")
                test_results.append((name, False))

        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)

        for name, passed in test_results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{name}: {status}")

        all_passed = all(passed for _, passed in test_results)

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL OBSERVABILITY TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - review output above")
        print("=" * 60)

        return all_passed


def test_rate_limit_stress(base_url: str = BASE_URL):
    """
    Stress test for rate limiting
    Makes many requests to verify rate limiting works
    """
    print("\n🔥 Rate Limit Stress Test")
    print("-" * 40)

    session = requests.Session()
    session.headers.update(HEADERS)

    # Make 65 requests (should hit 60 req/min limit)
    statuses = []
    for i in range(65):
        response = session.post(f"{base_url}/api/v1/search/advanced", json={"product": "test", "limit": 1})
        statuses.append(response.status_code)

        if response.status_code == 429:
            print(f"   ✅ Rate limit hit at request {i + 1}")
            data = response.json()
            print(f"   Error: {data.get('error', {}).get('message')}")
            print(f"   Retry-After: {response.headers.get('Retry-After')} seconds")
            return True

        # Small delay to not overwhelm
        time.sleep(0.05)

    print("   ⚠️ Made 65 requests without hitting rate limit")
    print(f"   Status codes: {set(statuses)}")
    return False


def main():
    """Main test runner"""
    # Run observability tests
    tester = ObservabilityTester()
    observability_passed = tester.run_all_tests()

    # Optionally run stress test
    if "--stress" in sys.argv:
        rate_limit_passed = test_rate_limit_stress()
        return 0 if (observability_passed and rate_limit_passed) else 1

    return 0 if observability_passed else 1


if __name__ == "__main__":
    sys.exit(main())
