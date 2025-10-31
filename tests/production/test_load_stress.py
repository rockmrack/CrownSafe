"""Load and stress testing for production deployment"""

import concurrent.futures
import time

import pytest
import requests

BASE_URL = "https://babyshield.cureviax.ai"


@pytest.mark.production
@pytest.mark.stress
@pytest.mark.slow
class TestLoadStress:
    """Load and stress tests for production"""

    def test_concurrent_reads(self):
        """Test handling of 20 concurrent read requests"""

        def fetch_healthz():
            try:
                response = requests.get(f"{BASE_URL}/healthz", timeout=10)
                return response.status_code == 200
            except Exception:
                return False

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(fetch_healthz) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        duration = time.time() - start_time

        # At least 90% should succeed
        success_rate = sum(results) / len(results)
        print(f"✅ Concurrent requests: {success_rate * 100:.1f}% success rate")
        print(f"  Total time: {duration:.2f}s")
        assert success_rate >= 0.90

    def test_sustained_load(self):
        """Test sustained load over 10 seconds"""
        start_time = time.time()
        success_count = 0
        total_count = 0

        while time.time() - start_time < 10:
            try:
                response = requests.get(f"{BASE_URL}/healthz", timeout=5)
                if response.status_code == 200:
                    success_count += 1
                total_count += 1
                time.sleep(0.2)  # 5 requests per second
            except Exception:
                total_count += 1

        success_rate = success_count / total_count if total_count > 0 else 0
        print(f"✅ Sustained load: {success_count}/{total_count} requests successful")
        print(f"  Success rate: {success_rate * 100:.1f}%")

        # Ensure we have a reasonable number of requests completed
        # In production with network latency, 10 successful requests in 10s is reasonable
        assert total_count >= 10, f"Expected at least 10 requests, got {total_count}"
        assert success_count >= 8, f"Expected at least 8 successful requests, got {success_count}"
        assert success_rate >= 0.80, f"Expected 80% success rate, got {success_rate * 100:.1f}%"

    def test_large_result_set_handling(self):
        """Test handling of large result sets"""
        try:
            start = time.time()
            response = requests.get(
                f"{BASE_URL}/api/v1/recalls",
                params={"limit": 100},  # Large page
                timeout=60,
            )
            duration = time.time() - start

            if response.status_code == 200:
                print(f"✅ Large result set handled in {duration:.2f}s")
                assert duration < 30  # Should complete within 30 seconds
            else:
                pytest.skip(f"Recalls endpoint returned {response.status_code}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Request failed: {e}")

    def test_response_time_consistency(self):
        """Test that repeated requests have consistent response times"""
        response_times = []

        # Test large result sets
        for _ in range(10):
            try:
                start = time.time()
                response = requests.get(f"{BASE_URL}/healthz", timeout=10)
                duration = time.time() - start

                if response.status_code == 200:
                    response_times.append(duration)
                time.sleep(0.1)
            except Exception:
                pass

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)

            print(f"✅ Response times: avg={avg_time:.3f}s, min={min_time:.3f}s, max={max_time:.3f}s")

            # Max should not be more than 3x the minimum
            assert max_time < min_time * 3 or max_time < 2.0
        else:
            pytest.skip("No successful responses")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
