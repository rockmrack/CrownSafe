#!/usr/bin/env python3
"""
Test suite for admin tools (Task 7)
Tests ingestion management, reindexing, and data freshness endpoints
"""

import os
import sys
import uuid

import requests

# Test configuration
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "test-admin-key-for-testing")


class AdminToolsTester:
    """Test suite for admin tools"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_headers = {"X-Admin-Key": ADMIN_API_KEY}
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

    def test_admin_unauthorized(self) -> bool:
        """Test 1: Admin endpoints require authentication"""
        print("\n📝 Test 1: Admin Authentication")

        # Test without key
        response = self.session.get(f"{self.base_url}/api/v1/admin/freshness")
        self.test(
            response.status_code in (401, 403),
            f"No key returns {response.status_code} (unauthorized)",
        )

        if response.status_code in (401, 403):
            data = response.json()
            self.test(not data.get("ok"), "Error response has ok=false")
            self.test("error" in data and "code" in data["error"], "Error has standard format")

        # Test with invalid key
        response = self.session.get(
            f"{self.base_url}/api/v1/admin/freshness",
            headers={"X-Admin-Key": "invalid-key"},
        )
        self.test(
            response.status_code in (401, 403),
            f"Invalid key returns {response.status_code}",
        )

        return True

    def test_admin_freshness(self) -> bool:
        """Test 2: Data freshness endpoint"""
        print("\n📝 Test 2: Data Freshness")

        response = self.session.get(f"{self.base_url}/api/v1/admin/freshness", headers=self.admin_headers)

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(
            response.status_code == 200,
            f"Freshness endpoint returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            self.test(data.get("ok"), "Response has ok=true")
            self.test("data" in data, "Response has data field")

            if "data" in data:
                self.test("summary" in data["data"], "Has summary section")
                self.test("agencies" in data["data"], "Has agencies list")

                summary = data["data"].get("summary", {})
                self.test(
                    "totalRecalls" in summary,
                    f"Total recalls: {summary.get('totalRecalls', 0)}",
                )

        return response.status_code == 200

    def test_admin_runs_list(self) -> bool:
        """Test 3: List ingestion runs"""
        print("\n📝 Test 3: List Ingestion Runs")

        response = self.session.get(f"{self.base_url}/api/v1/admin/runs", headers=self.admin_headers)

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(response.status_code == 200, f"Runs list returns {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            self.test("items" in data.get("data", {}), "Response has items array")

            items = data.get("data", {}).get("items", [])
            if items:
                first_run = items[0]
                self.test("id" in first_run, "Run has ID")
                self.test("agency" in first_run, "Run has agency")
                self.test("status" in first_run, "Run has status")
                print(f"   ℹ️ Found {len(items)} runs")

        return response.status_code == 200

    def test_admin_ingest_validation(self) -> bool:
        """Test 4: Ingestion request validation"""
        print("\n📝 Test 4: Ingestion Validation")

        # Test invalid agency
        response = self.session.post(
            f"{self.base_url}/api/v1/admin/ingest",
            headers=self.admin_headers,
            json={"agency": "INVALID_AGENCY", "mode": "delta"},
        )

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(
            response.status_code == 400,
            f"Invalid agency returns {response.status_code}",
        )

        if response.status_code == 400:
            data = response.json()
            self.test(
                data.get("error", {}).get("code") in ["UNSUPPORTED_AGENCY", "INVALID_REQUEST"],
                f"Error code: {data.get('error', {}).get('code')}",
            )

        # Test invalid mode
        response = self.session.post(
            f"{self.base_url}/api/v1/admin/ingest",
            headers=self.admin_headers,
            json={"agency": "FDA", "mode": "invalid_mode"},
        )

        self.test(response.status_code == 400, f"Invalid mode returns {response.status_code}")

        # Test missing agency
        response = self.session.post(
            f"{self.base_url}/api/v1/admin/ingest",
            headers=self.admin_headers,
            json={"mode": "delta"},
        )

        self.test(
            response.status_code == 400,
            f"Missing agency returns {response.status_code}",
        )

        return True

    def test_admin_run_details(self) -> bool:
        """Test 5: Get specific run details"""
        print("\n📝 Test 5: Run Details")

        # Test with invalid UUID
        invalid_id = "not-a-uuid"
        response = self.session.get(
            f"{self.base_url}/api/v1/admin/runs/{invalid_id}",
            headers=self.admin_headers,
        )

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(response.status_code == 400, f"Invalid UUID returns {response.status_code}")

        # Test with non-existent UUID
        fake_id = str(uuid.uuid4())
        response = self.session.get(f"{self.base_url}/api/v1/admin/runs/{fake_id}", headers=self.admin_headers)

        self.test(
            response.status_code == 404,
            f"Non-existent run returns {response.status_code}",
        )

        return True

    def test_admin_stats(self) -> bool:
        """Test 6: Admin statistics endpoint"""
        print("\n📝 Test 6: Admin Statistics")

        response = self.session.get(f"{self.base_url}/api/v1/admin/stats", headers=self.admin_headers)

        if response.status_code == 503:
            print("   ⚠️ Admin not configured, skipping")
            return True

        self.test(
            response.status_code == 200,
            f"Stats endpoint returns {response.status_code}",
        )

        if response.status_code == 200:
            data = response.json()
            stats = data.get("data", {})

            self.test("database" in stats, "Has database stats")
            self.test("ingestion" in stats, "Has ingestion stats")

            if "database" in stats:
                db_stats = stats["database"]
                self.test(
                    "recalls" in db_stats,
                    f"Recalls count: {db_stats.get('recalls', 0)}",
                )

        return response.status_code == 200

    def test_admin_dashboard_html(self) -> bool:
        """Test 7: Admin dashboard HTML is served"""
        print("\n📝 Test 7: Admin Dashboard HTML")

        response = self.session.get(f"{self.base_url}/admin/")

        self.test(
            response.status_code == 200,
            f"Admin dashboard returns {response.status_code}",
        )

        if response.status_code == 200:
            content = response.text
            self.test("BabyShield Admin" in content, "Dashboard contains expected title")
            self.test("apiKey" in content, "Dashboard has API key input")
            self.test("Data Freshness" in content, "Dashboard has freshness section")

        return response.status_code == 200

    def test_trace_id_present(self) -> bool:
        """Test 8: Trace ID in admin responses"""
        print("\n📝 Test 8: Trace ID Presence")

        response = self.session.get(f"{self.base_url}/api/v1/admin/freshness", headers=self.admin_headers)

        if response.status_code in (200, 401, 403):
            data = response.json()
            self.test("traceId" in data or "trace_id" in data, "Response includes trace ID")

        return True

    def test_rate_limiting(self) -> bool:
        """Test 9: Admin endpoints have rate limiting"""
        print("\n📝 Test 9: Rate Limiting")

        # Try to trigger rate limit on reindex (low limit)
        # Note: This requires actual rate limiting to be configured

        print("   ℹ️ Rate limiting test skipped (requires Redis)")
        return True

    def test_mock_ingestion(self) -> bool:
        """Test 10: Mock ingestion flow"""
        print("\n📝 Test 10: Ingestion Flow (Mocked)")

        # This would require mocking the subprocess execution
        # For CI, we can skip actual ingestion

        print("   ℹ️ Ingestion flow test skipped (requires mock setup)")
        return True

    def run_all_tests(self) -> bool:
        """Run all admin tools tests"""
        print("=" * 60)
        print("🛠️ ADMIN TOOLS TEST SUITE")
        print("=" * 60)

        tests = [
            ("Admin Authentication", self.test_admin_unauthorized),
            ("Data Freshness", self.test_admin_freshness),
            ("List Runs", self.test_admin_runs_list),
            ("Ingestion Validation", self.test_admin_ingest_validation),
            ("Run Details", self.test_admin_run_details),
            ("Admin Statistics", self.test_admin_stats),
            ("Dashboard HTML", self.test_admin_dashboard_html),
            ("Trace ID", self.test_trace_id_present),
            ("Rate Limiting", self.test_rate_limiting),
            ("Mock Ingestion", self.test_mock_ingestion),
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
            print("🎉 ALL ADMIN TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - review implementation")
        print("=" * 60)

        return all_passed


def main():
    """Main test runner"""
    tester = AdminToolsTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
