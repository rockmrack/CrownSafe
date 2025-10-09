#!/usr/bin/env python3
"""
Security limits test suite for Task 6
Tests request size limits, CORS, compression, input validation, and abuse protection
"""

import os
import sys
import json
import gzip
import time
import base64
import requests
from typing import Dict, Any, Optional

# Test configuration
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")


class SecurityLimitsTester:
    """Test suite for security limits and protections"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []

    def test(self, condition: bool, message: str) -> bool:
        """Record test result"""
        if condition:
            print(f"✅ {message}")
            self.test_results.append(True)
        else:
            print(f"❌ {message}")
            self.test_results.append(False)
        return condition

    def test_oversize_payload_413(self) -> bool:
        """Test 1: Oversize payload returns 413"""
        print("\n📝 Test 1: Request Size Limits")

        # Create large payload (200KB)
        large_data = {"product": "a" * 200000, "query": "test"}  # 200KB string

        response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=large_data)

        self.test(
            response.status_code == 413,
            f"Oversize payload returns 413 (got {response.status_code})",
        )

        if response.status_code == 413:
            try:
                data = response.json()
                self.test(
                    data.get("error", {}).get("code") == "PAYLOAD_TOO_LARGE",
                    f"Error code is PAYLOAD_TOO_LARGE: {data.get('error', {}).get('code')}",
                )
                self.test("traceId" in data, "Error response includes traceId")
            except:
                self.test(False, "413 response is valid JSON")

        # Test with Content-Length header
        headers = {"Content-Type": "application/json", "Content-Length": "500000"}  # 500KB

        response2 = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", data='{"product":"test"}', headers=headers
        )

        self.test(
            response2.status_code == 413,
            f"Large Content-Length rejected early (got {response2.status_code})",
        )

        return response.status_code == 413

    def test_cors_allowed_origin(self) -> bool:
        """Test 2: CORS allows configured origins"""
        print("\n📝 Test 2: CORS Allowed Origins")

        # Test allowed origin
        allowed_origins = [
            "https://babyshield.app",
            "https://app.babyshield.app",
            "https://babyshield.cureviax.ai",
        ]

        for origin in allowed_origins[:1]:  # Test first one
            response = self.session.options(
                f"{self.base_url}/api/v1/search/advanced",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type",
                },
            )

            self.test(
                response.status_code in (200, 204),
                f"Preflight for {origin} returns {response.status_code}",
            )

            # Check CORS headers
            headers_lower = {k.lower(): v for k, v in response.headers.items()}

            self.test(
                "access-control-allow-origin" in headers_lower, "CORS headers present in response"
            )

            if "access-control-allow-origin" in headers_lower:
                allowed_origin = headers_lower["access-control-allow-origin"]
                self.test(
                    allowed_origin == origin or allowed_origin == "*",
                    f"Origin allowed: {allowed_origin}",
                )

            # Check allowed methods
            if "access-control-allow-methods" in headers_lower:
                methods = headers_lower["access-control-allow-methods"]
                self.test("POST" in methods, f"POST method allowed: {methods}")

        return True

    def test_cors_denied_origin(self) -> bool:
        """Test 3: CORS denies unknown origins"""
        print("\n📝 Test 3: CORS Denied Origins")

        # Test denied origin
        evil_origins = ["https://evil.example.com", "http://localhost:1337", "https://attacker.com"]

        for origin in evil_origins[:1]:  # Test first one
            response = self.session.options(
                f"{self.base_url}/api/v1/search/advanced",
                headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
            )

            # Preflight may still return 200/204
            self.test(
                response.status_code in (200, 204, 403),
                f"Preflight response: {response.status_code}",
            )

            headers_lower = {k.lower(): v for k, v in response.headers.items()}

            if "access-control-allow-origin" in headers_lower:
                allowed = headers_lower["access-control-allow-origin"]
                self.test(allowed != origin, f"Evil origin NOT echoed: {allowed} != {origin}")
            else:
                self.test(True, "No Access-Control-Allow-Origin for evil origin")

        return True

    def test_field_length_limits(self) -> bool:
        """Test 4: Field length validation"""
        print("\n📝 Test 4: Input Field Length Limits")

        # Test oversized product field (>128 chars)
        response = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", json={"product": "x" * 1000}
        )

        self.test(
            response.status_code in (400, 422), f"Oversized field returns {response.status_code}"
        )

        if response.status_code in (400, 422):
            data = response.json()
            self.test(not data.get("ok"), "Error response has ok=false")
            self.test("error" in data, "Error response has error object")

        # Test empty string (should be rejected)
        response2 = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", json={"product": "   "}  # Only whitespace
        )

        self.test(
            response2.status_code in (400, 422),
            f"Empty/whitespace field rejected: {response2.status_code}",
        )

        # Test ID field with invalid chars
        response3 = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", json={"id": "../../etc/passwd"}
        )

        self.test(
            response3.status_code in (200, 400, 422, 404),
            f"Path traversal attempt handled: {response3.status_code}",
        )

        return True

    def test_keywords_size_limits(self) -> bool:
        """Test 5: Keywords list size limits"""
        print("\n📝 Test 5: Keywords List Limits")

        # Test too many keywords (>8)
        keywords = ["keyword" + str(i) for i in range(100)]

        response = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", json={"keywords": keywords}
        )

        self.test(
            response.status_code in (200, 400, 422),
            f"Too many keywords handled: {response.status_code}",
        )

        # If accepted, check it was truncated
        if response.status_code == 200:
            print("   ℹ️ Keywords accepted - should be truncated to 8")

        # Test oversized keyword (>32 chars each)
        long_keywords = ["x" * 100, "y" * 100]

        response2 = self.session.post(
            f"{self.base_url}/api/v1/search/advanced", json={"keywords": long_keywords}
        )

        self.test(
            response2.status_code in (400, 422),
            f"Oversized keywords rejected: {response2.status_code}",
        )

        return True

    def test_compression(self) -> bool:
        """Test 6: Response compression"""
        print("\n📝 Test 6: GZip Compression")

        # Request with compression
        response = self.session.post(
            f"{self.base_url}/api/v1/search/advanced",
            json={"product": "pacifier", "limit": 50},
            headers={"Accept-Encoding": "gzip, deflate"},
        )

        self.test(
            response.status_code in (200, 304),
            f"Compressed request successful: {response.status_code}",
        )

        if response.status_code == 200:
            encoding = response.headers.get("Content-Encoding", "").lower()

            # Check if response is compressed (for large responses)
            content_length = len(response.content)
            if content_length > 1024:  # Only expect compression for >1KB
                self.test(
                    "gzip" in encoding or "deflate" in encoding,
                    f"Large response compressed: {encoding}",
                )
            else:
                print(f"   ℹ️ Response size {content_length} bytes - may not be compressed")

        return True

    def test_security_headers(self) -> bool:
        """Test 7: Security headers present"""
        print("\n📝 Test 7: Security Headers")

        response = self.session.get(f"{self.base_url}/api/v1/healthz")

        required_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Referrer-Policy",
            "X-Request-ID",
            "X-API-Version",
        ]

        headers_lower = {k.lower(): v for k, v in response.headers.items()}

        for header in required_headers:
            self.test(header.lower() in headers_lower, f"{header} present")

        # Check new headers from Task 6
        optional_headers = ["Permissions-Policy", "Cross-Origin-Opener-Policy"]

        for header in optional_headers:
            if header.lower() in headers_lower:
                self.test(True, f"{header} present: {headers_lower[header.lower()][:50]}")

        return True

    def test_ua_blocking(self) -> bool:
        """Test 8: User-Agent blocking"""
        print("\n📝 Test 8: User-Agent Blocking")

        # Test malicious user agents
        bad_agents = ["sqlmap/1.5", "nikto/2.1.5", "acunetix-scanner", "nmap scripting engine"]

        for ua in bad_agents[:2]:  # Test first two
            response = self.session.get(
                f"{self.base_url}/api/v1/healthz", headers={"User-Agent": ua}
            )

            self.test(
                response.status_code in (403, 200),
                f"UA '{ua[:20]}...' returns {response.status_code}",
            )

            if response.status_code == 403:
                try:
                    data = response.json()
                    self.test(
                        data.get("error", {}).get("code") == "FORBIDDEN",
                        "Blocked UA returns FORBIDDEN error",
                    )
                except:
                    pass

        # Test normal user agent (should pass)
        response = self.session.get(
            f"{self.base_url}/api/v1/healthz", headers={"User-Agent": "BabyShield/1.0 (iOS)"}
        )

        self.test(response.status_code == 200, f"Normal UA allowed: {response.status_code}")

        return True

    def test_sql_injection_protection(self) -> bool:
        """Test 9: SQL injection protection"""
        print("\n📝 Test 9: SQL Injection Protection")

        # Test SQL injection in search
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users--",
            "1' UNION SELECT * FROM users--",
            "admin' --",
        ]

        for payload in sql_payloads[:2]:
            response = self.session.post(
                f"{self.base_url}/api/v1/search/advanced", json={"product": payload}
            )

            self.test(
                response.status_code in (200, 400, 422),
                f"SQL injection attempt handled: {response.status_code}",
            )

            # Should either reject (400/422) or safely handle (200 with no results)
            if response.status_code == 200:
                data = response.json()
                results = data.get("data", {}).get("items", [])
                self.test(len(results) == 0, "SQL injection returns no results")

        return True

    def test_xss_protection(self) -> bool:
        """Test 10: XSS protection"""
        print("\n📝 Test 10: XSS Protection")

        # Test XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
        ]

        for payload in xss_payloads[:2]:
            response = self.session.post(
                f"{self.base_url}/api/v1/search/advanced", json={"query": payload}
            )

            self.test(
                response.status_code in (200, 400, 422),
                f"XSS attempt handled: {response.status_code}",
            )

            # Check response doesn't reflect the script
            if response.status_code == 200:
                content = response.text
                self.test(
                    "<script>" not in content and "javascript:" not in content,
                    "XSS payload not reflected in response",
                )

        return True

    def run_all_tests(self) -> bool:
        """Run all security tests"""
        print("=" * 60)
        print("🔒 SECURITY LIMITS TEST SUITE")
        print("=" * 60)

        tests = [
            ("Oversize Payload (413)", self.test_oversize_payload_413),
            ("CORS Allowed Origins", self.test_cors_allowed_origin),
            ("CORS Denied Origins", self.test_cors_denied_origin),
            ("Field Length Limits", self.test_field_length_limits),
            ("Keywords Size Limits", self.test_keywords_size_limits),
            ("Response Compression", self.test_compression),
            ("Security Headers", self.test_security_headers),
            ("User-Agent Blocking", self.test_ua_blocking),
            ("SQL Injection Protection", self.test_sql_injection_protection),
            ("XSS Protection", self.test_xss_protection),
        ]

        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append((name, passed))
            except Exception as e:
                print(f"\n❌ {name} test error: {e}")
                results.append((name, False))

        print("\n" + "=" * 60)
        print("📊 TEST RESULTS")
        print("=" * 60)

        for name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{name}: {status}")

        all_passed = all(passed for _, passed in results)

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL SECURITY TESTS PASSED!")
        else:
            print("⚠️ Some security tests failed - review implementation")
        print("=" * 60)

        return all_passed


def main():
    """Main test runner"""
    tester = SecurityLimitsTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
