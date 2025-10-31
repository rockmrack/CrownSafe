"""Crown Safe Performance and Load Testing
Automated performance benchmarking for critical endpoints.

Features:
- Concurrent request testing
- Response time measurement
- Throughput calculation
- Error rate tracking
- Cache performance validation
- Health endpoint stress testing
"""

import asyncio
import statistics
import time
from typing import Any

import httpx


class LoadTester:
    """Performance and load testing framework
    Tests system behavior under concurrent load.
    """

    def __init__(self, base_url: str = "http://localhost:8001") -> None:
        """Initialize load tester.

        Args:
            base_url: Base URL of API to test

        """
        self.base_url = base_url
        self.results = []

    async def test_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        num_requests: int = 100,
        concurrent_requests: int = 10,
    ) -> dict[str, Any]:
        """Load test a specific endpoint.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            num_requests: Total number of requests
            concurrent_requests: Number of concurrent requests

        Returns:
            Dictionary with performance metrics

        """
        url = f"{self.base_url}{endpoint}"
        results = {
            "endpoint": endpoint,
            "method": method,
            "num_requests": num_requests,
            "concurrent_requests": concurrent_requests,
            "response_times": [],
            "status_codes": [],
            "errors": [],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create batches of concurrent requests
            batches = [
                list(range(i, min(i + concurrent_requests, num_requests)))
                for i in range(0, num_requests, concurrent_requests)
            ]

            for batch in batches:
                tasks = []
                for _ in batch:
                    tasks.append(self._make_request(client, url, method))

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        results["errors"].append(str(result))
                    else:
                        results["response_times"].append(result["response_time"])
                        results["status_codes"].append(result["status_code"])

        # Calculate metrics
        response_times = results["response_times"]
        if response_times:
            results["metrics"] = {
                "total_requests": len(response_times),
                "successful_requests": len([s for s in results["status_codes"] if 200 <= s < 300]),
                "failed_requests": len([s for s in results["status_codes"] if s >= 400]),
                "error_count": len(results["errors"]),
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_response_time": statistics.median(response_times),
                "p95_response_time": (
                    statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times)
                ),
                "p99_response_time": (
                    statistics.quantiles(response_times, n=100)[98]
                    if len(response_times) > 100
                    else max(response_times)
                ),
                "requests_per_second": len(response_times) / sum(response_times) if sum(response_times) > 0 else 0,
            }

        return results

    async def _make_request(self, client: httpx.AsyncClient, url: str, method: str) -> dict[str, Any]:
        """Make single HTTP request and measure time."""
        start_time = time.time()

        try:
            if method.upper() == "GET":
                response = await client.get(url)
            elif method.upper() == "POST":
                response = await client.post(url, json={})
            else:
                response = await client.request(method, url)

            response_time = time.time() - start_time

            return {
                "response_time": response_time,
                "status_code": response.status_code,
            }

        except Exception as e:
            return {"response_time": time.time() - start_time, "status_code": 0, "error": str(e)}

    async def run_comprehensive_load_test(self) -> dict[str, Any]:
        """Run comprehensive load tests on critical endpoints.

        Returns:
            Dictionary with all test results

        """
        test_suite = {
            "test_timestamp": time.time(),
            "base_url": self.base_url,
            "tests": {},
        }

        # Test critical endpoints
        endpoints_to_test = [
            ("/health", "GET", 200, 20),
            ("/api/healthz", "GET", 200, 20),
            ("/api/v1/monitoring/system-health-dashboard", "GET", 100, 10),
            ("/api/v1/monitoring/security-audit", "GET", 50, 5),
            ("/api/v1/monitoring/azure-cache-stats", "GET", 100, 10),
            ("/api/v1/monitoring/azure-storage", "GET", 50, 5),
        ]

        for endpoint, method, num_requests, concurrent in endpoints_to_test:
            print(f"Testing {endpoint}...")
            result = await self.test_endpoint(endpoint, method, num_requests, concurrent)
            test_suite["tests"][endpoint] = result

        # Calculate overall metrics
        all_response_times = []
        all_status_codes = []
        all_errors = []

        for test_result in test_suite["tests"].values():
            all_response_times.extend(test_result.get("response_times", []))
            all_status_codes.extend(test_result.get("status_codes", []))
            all_errors.extend(test_result.get("errors", []))

        if all_response_times:
            test_suite["overall_metrics"] = {
                "total_requests": len(all_response_times),
                "successful_requests": len([s for s in all_status_codes if 200 <= s < 300]),
                "failed_requests": len([s for s in all_status_codes if s >= 400]),
                "error_count": len(all_errors),
                "avg_response_time": statistics.mean(all_response_times),
                "min_response_time": min(all_response_times),
                "max_response_time": max(all_response_times),
                "median_response_time": statistics.median(all_response_times),
                "success_rate": (
                    len([s for s in all_status_codes if 200 <= s < 300]) / len(all_status_codes) * 100
                    if all_status_codes
                    else 0
                ),
            }

        return test_suite


async def main() -> None:
    """Run load tests."""
    tester = LoadTester()

    print("Starting comprehensive load test...")
    print("=" * 60)

    results = await tester.run_comprehensive_load_test()

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    # Print overall metrics
    if "overall_metrics" in results:
        metrics = results["overall_metrics"]
        print("\nOverall Performance:")
        print(f"  Total Requests: {metrics['total_requests']}")
        print(f"  Successful: {metrics['successful_requests']}")
        print(f"  Failed: {metrics['failed_requests']}")
        print(f"  Success Rate: {metrics['success_rate']:.2f}%")
        print(f"  Avg Response Time: {metrics['avg_response_time'] * 1000:.2f}ms")
        print(f"  Min Response Time: {metrics['min_response_time'] * 1000:.2f}ms")
        print(f"  Max Response Time: {metrics['max_response_time'] * 1000:.2f}ms")
        print(f"  Median Response Time: {metrics['median_response_time'] * 1000:.2f}ms")

    # Print per-endpoint results
    print("\n" + "-" * 60)
    print("Per-Endpoint Results:")
    print("-" * 60)

    for endpoint, test_result in results["tests"].items():
        if "metrics" in test_result:
            m = test_result["metrics"]
            print(f"\n{endpoint}:")
            print(f"  Requests: {m['total_requests']}")
            print(f"  Success: {m['successful_requests']}")
            print(f"  Avg Time: {m['avg_response_time'] * 1000:.2f}ms")
            print(f"  P95 Time: {m['p95_response_time'] * 1000:.2f}ms")
            print(f"  P99 Time: {m['p99_response_time'] * 1000:.2f}ms")
            print(f"  RPS: {m['requests_per_second']:.2f}")

    print("\n" + "=" * 60)
    print("Load test completed!")


if __name__ == "__main__":
    asyncio.run(main())
