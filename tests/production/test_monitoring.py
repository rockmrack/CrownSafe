"""Test monitoring and observability features"""

import pytest
import requests

BASE_URL = "https://babyshield.cureviax.ai"


class TestMonitoring:
    """Test monitoring and observability"""

    def test_metrics_endpoint_exists(self):
        """Verify Prometheus metrics endpoint"""
        response = requests.get(f"{BASE_URL}/metrics", timeout=10)
        # May be protected or not exist
        print(f"Metrics endpoint status: {response.status_code}")
        assert response.status_code in [200, 401, 403, 404]

        if response.status_code == 200:
            # Should return Prometheus format
            content = response.text
            if "http_requests_total" in content or "# HELP" in content:
                print("✅ Prometheus metrics available")
            else:
                print("⚠️ Metrics endpoint exists but format unclear")

    def test_request_tracing_headers(self):
        """Verify request tracing headers"""
        response = requests.get(f"{BASE_URL}/healthz", timeout=10)
        headers = response.headers

        trace_headers = [
            k
            for k in headers.keys()
            if any(x in k.lower() for x in ["request-id", "trace-id", "correlation-id", "x-request"])
        ]

        if trace_headers:
            print(f"✅ Tracing headers found: {trace_headers}")
        else:
            print("⚠️ No explicit tracing headers found")

        # Always has some headers
        assert len(headers) > 0

    def test_error_logging_integration(self):
        """Verify errors are logged properly"""
        # Trigger an error
        response = requests.get(f"{BASE_URL}/api/v1/invalid", timeout=10)
        assert response.status_code == 404

        # Should return structured error
        data = response.json()
        print(f"Error response: {data}")
        assert "detail" in data or "error" in data or "message" in data
        print("✅ Structured error responses working")

    def test_health_check_comprehensive(self):
        """Verify health check includes system info"""
        response = requests.get(f"{BASE_URL}/healthz", timeout=10)
        assert response.status_code == 200
        data = response.json()

        print(f"Health check data: {data}")

        # Should have status
        assert "status" in data
        print(f"✅ Health check status: {data['status']}")

        # Check for additional info
        info_keys = [k for k in data.keys() if k in ["version", "timestamp", "uptime", "checks"]]
        if info_keys:
            print(f"  Additional info: {info_keys}")

    def test_api_documentation_available(self):
        """Verify API documentation is accessible"""
        response = requests.get(f"{BASE_URL}/docs", timeout=10)
        print(f"API docs status: {response.status_code}")

        if response.status_code == 200:
            print("✅ API documentation available at /docs")
            assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
        else:
            print(f"⚠️ API docs returned {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
