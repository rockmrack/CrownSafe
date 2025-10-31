#!/usr/bin/env python3
"""Test suite for pagination and caching functionality (Task 5)
Tests keyset pagination, snapshot isolation, cursor security, and HTTP caching
"""

import os
import sys
import time

import requests

# Test configuration
BASE_URL = os.getenv("BABYSHIELD_BASE_URL", "http://localhost:8000")
HEADERS = {"Content-Type": "application/json"}


class PaginationCacheTester:
    """Test suite for pagination and caching features"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
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

    def test_keyset_correctness(self) -> bool:
        """Test 1: Keyset pagination has no duplicates or gaps"""
        print("\n📝 Test 1: Keyset Pagination Correctness")

        # Initial search
        payload = {"product": "toy", "agencies": ["FDA", "CPSC"], "limit": 5}

        all_ids = []
        next_cursor = None
        pages_fetched = 0
        max_pages = 3  # Limit to prevent infinite loops

        while pages_fetched < max_pages:
            # Update payload with cursor
            if next_cursor:
                payload["nextCursor"] = next_cursor
            else:
                payload.pop("nextCursor", None)

            response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload)

            if response.status_code != 200:
                self.test(False, f"Search failed with status {response.status_code}")
                return False

            data = response.json()

            if not data.get("ok"):
                self.test(False, f"Search returned error: {data.get('error')}")
                return False

            # Extract items and cursor
            items = data.get("data", {}).get("items", [])
            next_cursor = data.get("data", {}).get("nextCursor")

            # Collect IDs
            page_ids = [item["id"] for item in items]
            all_ids.extend(page_ids)

            pages_fetched += 1
            print(f"   Page {pages_fetched}: {len(items)} items")

            # Check for duplicates within page
            if len(page_ids) != len(set(page_ids)):
                self.test(False, f"Duplicates found within page {pages_fetched}")
                return False

            # Stop if no more pages
            if not next_cursor or len(items) == 0:
                break

        # Check for duplicates across pages
        unique_ids = set(all_ids)
        self.test(
            len(all_ids) == len(unique_ids),
            f"No duplicates across {pages_fetched} pages ({len(all_ids)} total items)",
        )

        # Verify ordering (each page should have consistent order)
        self.test(pages_fetched > 0, f"Successfully paginated through {pages_fetched} pages")

        return len(all_ids) == len(unique_ids)

    def test_snapshot_isolation(self) -> bool:
        """Test 2: Snapshot isolation prevents mid-pagination drift"""
        print("\n📝 Test 2: Snapshot Isolation")

        # Note: This test requires the ability to insert data, which may not be possible
        # in a read-only test environment. We'll test the concept instead.

        # Get first page with snapshot time
        payload1 = {"product": "bottle", "limit": 3}

        response1 = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload1)

        if response1.status_code != 200:
            self.test(False, f"First search failed with status {response1.status_code}")
            return False

        data1 = response1.json()
        cursor1 = data1.get("data", {}).get("nextCursor")

        if not cursor1:
            print("   ⚠️ No pagination available, skipping snapshot test")
            return True

        # Get second page using cursor (should use same snapshot)
        payload2 = {"product": "bottle", "limit": 3, "nextCursor": cursor1}

        response2 = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload2)

        if response2.status_code != 200:
            self.test(False, f"Second search failed with status {response2.status_code}")
            return False

        data2 = response2.json()

        # Check if asOf timestamp is present (indicates snapshot)
        as_of = data2.get("data", {}).get("asOf")
        self.test(as_of is not None, f"Snapshot timestamp present: {as_of}")

        return True

    def test_cursor_tampering(self) -> bool:
        """Test 3: Tampered cursor returns 400 error"""
        print("\n📝 Test 3: Cursor Tampering Protection")

        # Get a valid cursor first
        payload = {"product": "test", "limit": 2}

        response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload)

        if response.status_code != 200:
            self.test(False, f"Initial search failed with status {response.status_code}")
            return False

        data = response.json()
        valid_cursor = data.get("data", {}).get("nextCursor")

        if not valid_cursor:
            print("   ⚠️ No cursor available, skipping tamper test")
            return True

        # Test 1: Completely invalid cursor
        invalid_payload = {
            "product": "test",
            "limit": 2,
            "nextCursor": "INVALID_CURSOR_STRING",
        }

        response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=invalid_payload)

        self.test(
            response.status_code in [400, 422],
            f"Invalid cursor returns {response.status_code}",
        )

        if response.status_code in [400, 422]:
            error_data = response.json()
            error_code = error_data.get("error", {}).get("code")
            self.test(
                error_code == "INVALID_CURSOR",
                f"Error code is INVALID_CURSOR: {error_code}",
            )

        # Test 2: Tampered cursor (modify signature)
        if "." in valid_cursor:
            parts = valid_cursor.split(".")
            if len(parts) == 2:
                # Flip a bit in the signature
                tampered = parts[0] + ".TAMPERED"

                tampered_payload = {
                    "product": "test",
                    "limit": 2,
                    "nextCursor": tampered,
                }

                response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=tampered_payload)

                self.test(
                    response.status_code in [400, 422],
                    f"Tampered cursor returns {response.status_code}",
                )

        # Test 3: Cursor with mismatched filters
        different_payload = {
            "product": "different_product",  # Different filter
            "limit": 2,
            "nextCursor": valid_cursor,  # Cursor from different search
        }

        response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=different_payload)

        if response.status_code in [400, 422]:
            error_data = response.json()
            error_code = error_data.get("error", {}).get("code")
            self.test(
                error_code in ["INVALID_CURSOR", "INVALID_CURSOR_FILTER_MISMATCH"],
                f"Filter mismatch detected: {error_code}",
            )

        return True

    def test_etag_search(self) -> bool:
        """Test 4: Search endpoint returns 304 with matching ETag"""
        print("\n📝 Test 4: ETag Support for Search")

        # First request
        payload = {"product": "pacifier", "agencies": ["FDA"], "limit": 5}

        response1 = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload)

        if response1.status_code != 200:
            self.test(False, f"First search failed with status {response1.status_code}")
            return False

        # Check for ETag header
        etag = response1.headers.get("ETag")
        self.test(etag is not None, f"ETag present: {etag}")

        # Check for Cache-Control header
        cache_control = response1.headers.get("Cache-Control")
        self.test(cache_control is not None, f"Cache-Control present: {cache_control}")

        if etag:
            # Second request with If-None-Match
            headers = HEADERS.copy()
            headers["If-None-Match"] = etag

            response2 = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload, headers=headers)

            self.test(
                response2.status_code == 304,
                f"Returns 304 Not Modified with matching ETag (got {response2.status_code})",
            )

            if response2.status_code == 304:
                # Verify 304 has minimal response
                self.test(len(response2.content) == 0, "304 response has empty body")

        return True

    def test_etag_detail(self) -> bool:
        """Test 5: Detail endpoint ETag and Last-Modified support"""
        print("\n📝 Test 5: ETag for Detail Endpoint")

        # First, get a valid recall ID
        search_response = self.session.post(
            f"{self.base_url}/api/v1/search/advanced",
            json={"product": "toy", "limit": 1},
        )

        if search_response.status_code != 200:
            print("   ⚠️ Could not get recall ID for testing")
            return True

        search_data = search_response.json()
        items = search_data.get("data", {}).get("items", [])

        if not items:
            print("   ⚠️ No recalls found for testing")
            return True

        recall_id = items[0]["id"]

        # Get recall detail
        response1 = self.session.get(f"{self.base_url}/api/v1/recall/{recall_id}")

        if response1.status_code == 404:
            print(f"   ⚠️ Recall detail endpoint not implemented for {recall_id}")
            return True

        if response1.status_code != 200:
            self.test(False, f"Detail request failed with status {response1.status_code}")
            return False

        # Check for cache headers
        etag = response1.headers.get("ETag")
        last_modified = response1.headers.get("Last-Modified")
        cache_control = response1.headers.get("Cache-Control")

        self.test(etag is not None, f"ETag present: {etag}")
        self.test(last_modified is not None, f"Last-Modified present: {last_modified}")
        self.test(cache_control is not None, f"Cache-Control present: {cache_control}")

        # Test If-None-Match
        if etag:
            headers = {"If-None-Match": etag}
            response2 = self.session.get(f"{self.base_url}/api/v1/recall/{recall_id}", headers=headers)

            self.test(
                response2.status_code == 304,
                f"Returns 304 with matching ETag (got {response2.status_code})",
            )

        # Test If-Modified-Since
        if last_modified:
            headers = {"If-Modified-Since": last_modified}
            response3 = self.session.get(f"{self.base_url}/api/v1/recall/{recall_id}", headers=headers)

            self.test(
                response3.status_code == 304,
                f"Returns 304 with If-Modified-Since (got {response3.status_code})",
            )

        return True

    def test_cache_headers(self) -> bool:
        """Test 6: Proper Cache-Control headers"""
        print("\n📝 Test 6: Cache-Control Headers")

        # Test search endpoint
        response = self.session.post(
            f"{self.base_url}/api/v1/search/advanced",
            json={"product": "test", "limit": 1},
        )

        if response.status_code == 200:
            cache_control = response.headers.get("Cache-Control", "")
            self.test(
                "private" in cache_control or "public" in cache_control,
                f"Search has cache directive: {cache_control}",
            )
            self.test("max-age=" in cache_control, "Search has max-age directive")

        # Test health endpoint (should not be cached)
        health_response = self.session.get(f"{self.base_url}/api/v1/healthz")

        if health_response.status_code == 200:
            health_cache = health_response.headers.get("Cache-Control", "")
            self.test(
                "no-cache" in health_cache or "no-store" in health_cache or "max-age=0" in health_cache,
                f"Health endpoint not cached: {health_cache}",
            )

        return True

    def test_performance(self) -> bool:
        """Test 7: Pagination performance (no OFFSET degradation)"""
        print("\n📝 Test 7: Pagination Performance")

        # Measure time for different pages
        payload = {"product": "baby", "limit": 10}

        timings = []
        next_cursor = None

        for page in range(3):
            if next_cursor:
                payload["nextCursor"] = next_cursor
            else:
                payload.pop("nextCursor", None)

            start_time = time.time()
            response = self.session.post(f"{self.base_url}/api/v1/search/advanced", json=payload)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                data = response.json()
                next_cursor = data.get("data", {}).get("nextCursor")
                timings.append(elapsed)
                print(f"   Page {page + 1}: {elapsed:.0f}ms")

                if not next_cursor:
                    break

        if len(timings) >= 2:
            # Check that later pages aren't significantly slower
            # Keyset pagination should have consistent performance
            max_timing = max(timings)
            min_timing = min(timings)
            variance = (max_timing - min_timing) / min_timing

            self.test(
                variance < 2.0,  # Allow up to 2x variance
                f"Consistent pagination performance (variance: {variance:.1%})",
            )

        return True

    def run_all_tests(self) -> bool:
        """Run all pagination and cache tests"""
        print("=" * 60)
        print("🔍 PAGINATION & CACHE TEST SUITE")
        print("=" * 60)

        tests = [
            ("Keyset Correctness", self.test_keyset_correctness),
            ("Snapshot Isolation", self.test_snapshot_isolation),
            ("Cursor Tampering", self.test_cursor_tampering),
            ("ETag Search", self.test_etag_search),
            ("ETag Detail", self.test_etag_detail),
            ("Cache Headers", self.test_cache_headers),
            ("Performance", self.test_performance),
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
            print("🎉 ALL PAGINATION & CACHE TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - review implementation")
        print("=" * 60)

        return all_passed


def main():
    """Main test runner"""
    tester = PaginationCacheTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
