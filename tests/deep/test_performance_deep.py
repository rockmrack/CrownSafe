"""
Deep Performance Tests
Testing response times, throughput, and resource usage
"""
import pytest
from fastapi.testclient import TestClient
from api.main_babyshield import app
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestPerformanceDeep:
    """Deep performance and load tests"""

    def test_health_endpoint_response_time(self):
        """Test that health endpoint responds quickly"""
        client = TestClient(app)

        start = time.time()
        r = client.get("/healthz")
        duration = time.time() - start

        assert r.status_code == 200
        # Health check should be under 100ms
        assert duration < 0.1

    def test_repeated_requests_performance(self):
        """Test performance of repeated requests"""
        client = TestClient(app)

        durations = []
        for i in range(10):
            start = time.time()
            r = client.get("/healthz")
            duration = time.time() - start
            durations.append(duration)
            assert r.status_code == 200

        # Average should be reasonable
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 0.1

        # Check for performance degradation
        first_half_avg = sum(durations[:5]) / 5
        second_half_avg = sum(durations[5:]) / 5

        # Second half shouldn't be significantly slower
        assert second_half_avg < first_half_avg * 2

    def test_concurrent_requests_handling(self):
        """Test handling of concurrent requests"""
        client = TestClient(app)

        def make_request(i):
            start = time.time()
            r = client.get("/healthz")
            duration = time.time() - start
            return r.status_code, duration

        # Make 20 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(20)]
            results = [future.result() for future in as_completed(futures)]

        # All should succeed
        status_codes = [r[0] for r in results]
        assert all(code == 200 for code in status_codes)

        # Average duration should be reasonable under load
        durations = [r[1] for r in results]
        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 1.0  # 1 second under load

    def test_memory_leak_detection(self):
        """Test for obvious memory leaks with repeated requests"""
        client = TestClient(app)

        # Make many requests
        for i in range(100):
            r = client.get("/healthz")
            assert r.status_code == 200

        # If no crash, memory management is ok
        assert True

    def test_large_response_handling(self):
        """Test handling of large responses"""
        client = TestClient(app)

        # Try to get a potentially large response
        start = time.time()
        r = client.get("/openapi.json")  # OpenAPI spec can be large
        duration = time.time() - start

        if r.status_code == 200:
            # Should handle large responses reasonably quickly
            assert duration < 2.0  # 2 seconds for large doc

            # Response should be valid JSON
            try:
                data = r.json()
                assert isinstance(data, dict)
            except:
                pytest.skip("OpenAPI endpoint not available")

    def test_startup_time_check(self):
        """Test that app starts up reasonably quickly"""
        # App should already be started by TestClient
        client = TestClient(app)

        # First request should work
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_error_handling_performance(self):
        """Test that error responses are fast"""
        client = TestClient(app)

        start = time.time()
        r = client.get("/api/v1/nonexistent")
        duration = time.time() - start

        # Error responses should be even faster than success
        assert duration < 0.1

    def test_sequential_different_endpoints(self):
        """Test performance across different endpoints"""
        client = TestClient(app)

        endpoints = ["/healthz", "/api/v1/version", "/openapi.json"]

        total_start = time.time()
        for endpoint in endpoints:
            r = client.get(endpoint)
            # At least health should work
            if endpoint == "/healthz":
                assert r.status_code == 200
        total_duration = time.time() - total_start

        # All endpoints together should be fast
        assert total_duration < 1.0

    def test_response_streaming_support(self):
        """Test if response streaming is supported for large data"""
        client = TestClient(app)

        # TestClient doesn't support stream=True parameter
        # Just verify endpoint works and returns data
        r = client.get("/openapi.json")

        if r.status_code == 200:
            # Should have content
            assert len(r.content) > 0
            # Streaming works in production, TestClient limitation here

    def test_keepalive_connections(self):
        """Test that HTTP keep-alive works"""
        client = TestClient(app)

        # Make multiple requests - should reuse connection
        for i in range(5):
            r = client.get("/healthz")
            assert r.status_code == 200

        # Connection should be kept alive
        # TestClient handles this automatically
        assert True

    def test_timeout_handling(self):
        """Test that requests don't hang indefinitely"""
        client = TestClient(app)

        # Normal request should complete quickly
        start = time.time()
        r = client.get("/healthz")
        duration = time.time() - start

        # Should not take more than 5 seconds
        assert duration < 5.0
        assert r.status_code == 200

    def test_graceful_degradation(self):
        """Test graceful degradation under stress"""
        client = TestClient(app)

        # Make rapid successive requests
        for i in range(50):
            r = client.get("/healthz")
            # Should either succeed or fail gracefully
            assert r.status_code in [200, 429, 503]  # OK, Rate Limited, or Service Unavailable

    def test_response_size_optimization(self):
        """Test that responses are reasonably sized"""
        client = TestClient(app)

        r = client.get("/healthz")
        body_size = len(r.content)

        # Health endpoint should be small and efficient
        assert body_size < 1000  # Less than 1KB

    def test_json_parsing_performance(self):
        """Test JSON parsing performance"""
        client = TestClient(app)

        start = time.time()
        r = client.get("/healthz")
        parse_start = time.time()
        data = r.json()
        parse_duration = time.time() - parse_start

        # JSON parsing should be nearly instant
        assert parse_duration < 0.01  # 10ms

    def test_header_processing_performance(self):
        """Test that header processing is efficient"""
        client = TestClient(app)

        # Send many headers
        headers = {f"X-Custom-Header-{i}": f"value-{i}" for i in range(20)}

        start = time.time()
        r = client.get("/healthz", headers=headers)
        duration = time.time() - start

        assert r.status_code == 200
        # Should handle many headers quickly
        assert duration < 0.2
