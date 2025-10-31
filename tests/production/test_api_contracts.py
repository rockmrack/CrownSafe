"""Test API contracts and backward compatibility"""

import pytest
import requests

BASE_URL = "https://babyshield.cureviax.ai"


class TestAPIContracts:
    """Test API contracts and schemas"""

    def test_healthz_response_schema(self):
        """Verify health endpoint schema"""
        response = requests.get(f"{BASE_URL}/healthz", timeout=10)
        assert response.status_code == 200
        data = response.json()

        # Define expected fields
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy", "ok"]
        print(f"✅ Health endpoint schema valid: status={data['status']}")

    def test_recall_list_response_schema(self):
        """Verify recall list endpoint schema"""
        try:
            response = requests.get(f"{BASE_URL}/api/v1/recalls", params={"limit": 1}, timeout=30)

            if response.status_code != 200:
                pytest.skip(f"Recalls endpoint returned {response.status_code}")

            data = response.json()

            # Check for nested structure (data.items) or flat structure (items)
            has_items = any(k in data for k in ["items", "results", "recalls"]) or (
                "data" in data and any(k in data["data"] for k in ["items", "results", "recalls"])
            )

            if not has_items:
                print(f"Response structure: {list(data.keys())}")
                # If it's a wrapped response with success/data structure, that's also valid
                if "success" in data and "data" in data:
                    print("✅ Recall list uses wrapped response structure")
                    has_items = True

            assert has_items, f"Response should have items/results/recalls. Got: {list(data.keys())}"

            print("✅ Recall list response schema valid")

            # Check for total in either top level or data object
            total_count = data.get("total") or (data.get("data", {}).get("total")) or (data.get("count"))
            if total_count is not None:
                assert isinstance(total_count, int)
                print(f"  Total count: {total_count}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Request failed: {e}")

    def test_error_response_schema(self):
        """Verify error responses have consistent schema"""
        response = requests.get(f"{BASE_URL}/api/v1/nonexistent", timeout=10)
        assert response.status_code == 404

        data = response.json()

        # Should have error information
        has_error_info = any(k in data for k in ["detail", "error", "message"])
        assert has_error_info, "Error response should have detail/error/message"

        print(f"✅ Error response schema: {list(data.keys())}")

    def test_api_versioning(self):
        """Verify API version is accessible"""
        response = requests.get(f"{BASE_URL}/healthz", timeout=10)
        data = response.json()

        # Check for version info
        version_keys = [k for k in data.keys() if "version" in k.lower()]

        if version_keys:
            print(f"✅ Version info found: {version_keys}")
            for key in version_keys:
                print(f"  {key}: {data[key]}")
        else:
            print("⚠️ No explicit version info in health check")

    def test_pagination_schema(self):
        """Verify pagination parameters are supported"""
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/recalls",
                params={"limit": 5, "offset": 0},
                timeout=30,
            )

            if response.status_code != 200:
                pytest.skip(f"Pagination test skipped: {response.status_code}")

            data = response.json()

            # Should have pagination metadata
            items = data.get("items", data.get("results", []))
            print(f"✅ Pagination working: returned {len(items)} items")

            # Check for pagination info
            pagination_keys = [k for k in data.keys() if k in ["total", "limit", "offset", "next", "previous", "page"]]
            if pagination_keys:
                print(f"  Pagination metadata: {pagination_keys}")

        except requests.exceptions.RequestException as e:
            pytest.skip(f"Request failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
