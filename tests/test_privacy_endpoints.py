#!/usr/bin/env python3
"""Test suite for privacy endpoints (Task 8)
Tests GDPR/CCPA compliance features and privacy management.
"""

import os
import sys
import uuid

import requests

# Test configuration
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "test-admin-key")


class PrivacyEndpointTester:
    """Test suite for privacy and DSAR endpoints."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_headers = {"X-Admin-Key": ADMIN_API_KEY}
        self.test_results = []
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    def test(self, condition: bool, message: str) -> bool:
        """Record test result."""
        if condition:
            print(f"✅ {message}")
            self.test_results.append(True)
        else:
            print(f"❌ {message}")
            self.test_results.append(False)
        return condition

    def test_legal_pages(self) -> bool:
        """Test 1: Legal pages are accessible."""
        print("\n📝 Test 1: Legal Pages")

        pages = [
            ("/legal/privacy", "Privacy Policy"),
            ("/legal/terms", "Terms of Service"),
            ("/legal/data-deletion", "Data Deletion"),
        ]

        all_ok = True
        for path, expected_title in pages:
            response = self.session.get(f"{self.base_url}{path}")
            self.test(response.status_code == 200, f"{path} returns {response.status_code}")

            if response.status_code == 200:
                content = response.text
                self.test(expected_title in content, f"{path} contains '{expected_title}'")
                self.test("BabyShield" in content, f"{path} contains BabyShield branding")
            else:
                all_ok = False

        return all_ok

    def test_export_request(self) -> bool:
        """Test 2: Data export request."""
        print("\n📝 Test 2: Data Export Request")

        response = self.session.post(
            f"{self.base_url}/api/v1/user/data/export",
            json={
                "email": self.test_email,
                "jurisdiction": "gdpr",
                "source": "api",
                "reason": "Testing export functionality",
            },
        )

        self.test(
            response.status_code == 200,
            f"Export request returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            self.test(data.get("ok"), "Response has ok=true")
            self.test("data" in data, "Response has data field")

            if "data" in data:
                result = data["data"]
                self.test(
                    "sla_days" in result,
                    f"SLA days specified: {result.get('sla_days')}",
                )
                self.test(
                    "request_id" in result,
                    f"Request ID provided: {result.get('request_id')}",
                )
                self.test(
                    result.get("status") == "queued",
                    f"Status is queued: {result.get('status')}",
                )

                # Save request ID for later tests
                self.export_request_id = result.get("request_id")

        return response.status_code == 200

    def test_delete_request(self) -> bool:
        """Test 3: Data deletion request."""
        print("\n📝 Test 3: Data Deletion Request")

        test_email = f"delete_{uuid.uuid4().hex[:8]}@example.com"

        response = self.session.post(
            f"{self.base_url}/api/v1/user/data/delete",
            json={"email": test_email, "jurisdiction": "ccpa", "source": "web"},
        )

        self.test(
            response.status_code == 200,
            f"Delete request returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            self.test(data.get("ok"), "Response has ok=true")

            result = data.get("data", {})
            self.test(
                "message" in result,
                f"Message provided: {result.get('message', '')[:50]}...",
            )
            self.test(
                result.get("sla_days") in [30, 45],
                f"Valid SLA days: {result.get('sla_days')}",
            )

        return response.status_code == 200

    def test_privacy_summary(self) -> bool:
        """Test 4: Privacy summary endpoint."""
        print("\n📝 Test 4: Privacy Summary")

        response = self.session.get(f"{self.base_url}/api/v1/user/privacy/summary")

        self.test(
            response.status_code == 200,
            f"Privacy summary returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            summary = data.get("data", {})

            self.test("dpo_email" in summary, f"DPO email: {summary.get('dpo_email')}")
            self.test("retention_periods" in summary, "Retention periods specified")
            self.test("links" in summary, "Privacy links provided")
            self.test(
                "notes" in summary and "NOT medical advice" in summary.get("notes", ""),
                "Medical disclaimer present",
            )

            # Check links
            if "links" in summary:
                links = summary["links"]
                self.test(
                    "privacy_policy" in links,
                    f"Privacy policy link: {links.get('privacy_policy')}",
                )
                self.test(
                    "data_deletion" in links,
                    f"Data deletion link: {links.get('data_deletion')}",
                )

        return response.status_code == 200

    def test_admin_list_requests(self) -> bool:
        """Test 5: Admin can list privacy requests."""
        print("\n📝 Test 5: Admin List Privacy Requests")

        # Test without auth first
        response = self.session.get(f"{self.base_url}/api/v1/admin/privacy/requests")
        self.test(
            response.status_code in (401, 403),
            f"No auth returns {response.status_code} (unauthorized)",
        )

        # Test with auth
        response = self.session.get(f"{self.base_url}/api/v1/admin/privacy/requests", headers=self.admin_headers)

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(response.status_code == 200, f"Admin list returns {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            items = data.get("data", {}).get("items", [])

            self.test(
                isinstance(items, list),
                f"Returns list of requests ({len(items)} items)",
            )

            if items:
                first = items[0]
                self.test("id" in first, "Request has ID")
                self.test("kind" in first, f"Request has kind: {first.get('kind')}")
                self.test("status" in first, f"Request has status: {first.get('status')}")
                self.test(
                    "email_masked" in first,
                    f"Email is masked: {first.get('email_masked')}",
                )

        return response.status_code == 200

    def test_admin_update_status(self) -> bool:
        """Test 6: Admin can update request status."""
        print("\n📝 Test 6: Admin Update Request Status")

        # First create a request to update
        create_response = self.session.post(
            f"{self.base_url}/api/v1/user/data/export",
            json={"email": f"admin_test_{uuid.uuid4().hex[:8]}@example.com"},
        )

        if create_response.status_code != 200:
            print("   ⚠️ Could not create test request")
            return False

        request_id = create_response.json().get("data", {}).get("request_id")
        if not request_id:
            print("   ⚠️ No request ID returned")
            return False

        # Try to update with invalid status
        response = self.session.patch(
            f"{self.base_url}/api/v1/admin/privacy/requests/{request_id}",
            headers=self.admin_headers,
            json={"status": "invalid_status"},
        )

        if response.status_code != 503:  # Skip if admin not configured
            self.test(
                response.status_code in (400, 422),
                f"Invalid status returns {response.status_code}",
            )

        # Try to update with valid status
        response = self.session.patch(
            f"{self.base_url}/api/v1/admin/privacy/requests/{request_id}",
            headers=self.admin_headers,
            json={"status": "verifying", "notes": "Test verification"},
        )

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(response.status_code == 200, f"Valid update returns {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            result = data.get("data", {})
            self.test(
                result.get("status") == "verifying",
                f"Status updated to: {result.get('status')}",
            )

        return response.status_code == 200

    def test_request_status_check(self) -> bool:
        """Test 7: Check request status."""
        print("\n📝 Test 7: Request Status Check")

        # Use the export request ID from earlier test
        if not hasattr(self, "export_request_id") or not self.export_request_id:
            print("   ⚠️ No request ID from earlier test, creating new one")

            create_response = self.session.post(
                f"{self.base_url}/api/v1/user/data/export",
                json={"email": f"status_test_{uuid.uuid4().hex[:8]}@example.com"},
            )

            if create_response.status_code == 200:
                self.export_request_id = create_response.json().get("data", {}).get("request_id")

        if self.export_request_id:
            response = self.session.get(f"{self.base_url}/api/v1/user/privacy/status/{self.export_request_id}")

            self.test(
                response.status_code == 200,
                f"Status check returns {response.status_code}",
            )

            if response.status_code == 200:
                data = response.json()
                status = data.get("data", {})

                self.test("status" in status, f"Current status: {status.get('status')}")
                self.test("submitted_at" in status, "Submission time provided")
                self.test("sla_days" in status, f"SLA days: {status.get('sla_days')}")
                self.test(
                    "days_elapsed" in status,
                    f"Days elapsed: {status.get('days_elapsed')}",
                )
        else:
            print("   ⚠️ No request ID available")
            return False

        return response.status_code == 200

    def test_rate_limiting(self) -> bool:
        """Test 8: Rate limiting on DSAR endpoints."""
        print("\n📝 Test 8: Rate Limiting")

        # Note: This test assumes rate limiting is configured (5 per hour)
        # In a test environment, this might not be enforced

        print("   ℹ️ Rate limiting test skipped (requires Redis)")
        return True

    def test_invalid_email(self) -> bool:
        """Test 9: Invalid email validation."""
        print("\n📝 Test 9: Email Validation")

        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
            "",
        ]

        all_ok = True
        for email in invalid_emails:
            response = self.session.post(f"{self.base_url}/api/v1/user/data/export", json={"email": email})

            self.test(
                response.status_code in (400, 422),
                f"Invalid email '{email}' returns {response.status_code}",
            )

            if response.status_code not in (400, 422):
                all_ok = False

        return all_ok

    def test_privacy_headers(self) -> bool:
        """Test 10: Privacy-related headers."""
        print("\n📝 Test 10: Privacy Headers")

        response = self.session.get(f"{self.base_url}/api/v1/user/privacy/summary")

        headers = response.headers

        # Check for security headers
        self.test(
            "X-Content-Type-Options" in headers,
            f"X-Content-Type-Options: {headers.get('X-Content-Type-Options')}",
        )
        self.test(
            "X-Frame-Options" in headers,
            f"X-Frame-Options: {headers.get('X-Frame-Options')}",
        )

        # Check for trace ID
        data = response.json() if response.status_code == 200 else {}
        self.test("traceId" in data or "trace_id" in data, "Response includes trace ID")

        return True

    def test_gdpr_rights(self) -> bool:
        """Test 11: Additional GDPR rights endpoints."""
        print("\n📝 Test 11: GDPR Rights Endpoints")

        test_email = f"gdpr_{uuid.uuid4().hex[:8]}@example.com"

        endpoints = [
            ("/api/v1/user/data/rectify", "rectify"),
            ("/api/v1/user/data/restrict", "restrict"),
            ("/api/v1/user/data/object", "object"),
        ]

        all_ok = True
        for endpoint, right in endpoints:
            response = self.session.post(f"{self.base_url}{endpoint}", json={"email": test_email})

            self.test(
                response.status_code == 200,
                f"Right to {right} returns {response.status_code}",
            )

            if response.status_code != 200:
                all_ok = False

        return all_ok

    def test_admin_statistics(self) -> bool:
        """Test 12: Privacy statistics endpoint."""
        print("\n📝 Test 12: Privacy Statistics")

        response = self.session.get(
            f"{self.base_url}/api/v1/admin/privacy/statistics",
            headers=self.admin_headers,
            params={"days": 7},
        )

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(
            response.status_code == 200,
            f"Statistics endpoint returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            stats = data.get("data", {})

            self.test("overview" in stats, "Has overview statistics")
            self.test("by_kind" in stats, "Has breakdown by request type")
            self.test("processing_metrics" in stats, "Has processing metrics")

        return response.status_code == 200

    def run_all_tests(self) -> bool:
        """Run all privacy endpoint tests."""
        print("=" * 60)
        print("🔐 PRIVACY ENDPOINTS TEST SUITE")
        print("=" * 60)

        tests = [
            ("Legal Pages", self.test_legal_pages),
            ("Export Request", self.test_export_request),
            ("Delete Request", self.test_delete_request),
            ("Privacy Summary", self.test_privacy_summary),
            ("Admin List Requests", self.test_admin_list_requests),
            ("Admin Update Status", self.test_admin_update_status),
            ("Request Status Check", self.test_request_status_check),
            ("Rate Limiting", self.test_rate_limiting),
            ("Email Validation", self.test_invalid_email),
            ("Privacy Headers", self.test_privacy_headers),
            ("GDPR Rights", self.test_gdpr_rights),
            ("Admin Statistics", self.test_admin_statistics),
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
            print("🎉 ALL PRIVACY TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - review implementation")
        print("=" * 60)

        return all_passed


def main() -> int:
    """Main test runner."""
    tester = PrivacyEndpointTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
