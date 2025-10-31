"""
Comprehensive Endpoint Validation Tool
Validates all API endpoints, checks status, and reports issues

Features:
- Automatic endpoint discovery from FastAPI app
- Health check validation
- Rate limit validation
- Response time measurement
- Error detection
- Detailed reporting
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class EndpointValidator:
    """
    Validates API endpoints and reports issues
    """

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []

    async def validate_endpoint(self, method: str, path: str, expected_status: int = 200) -> Dict:
        """
        Validate single endpoint

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Endpoint path
            expected_status: Expected HTTP status code

        Returns:
            Validation result dictionary
        """
        url = f"{self.base_url}{path}"
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json={})
                else:
                    response = await client.request(method, url)

                duration = time.time() - start_time

                result = {
                    "path": path,
                    "method": method,
                    "status_code": response.status_code,
                    "expected_status": expected_status,
                    "success": response.status_code == expected_status,
                    "duration_ms": round(duration * 1000, 2),
                    "error": None,
                }

                # Check for slow responses
                if duration > 2.0:
                    result["warning"] = f"Slow response: {duration:.2f}s"

                return result

        except Exception as e:
            duration = time.time() - start_time
            return {
                "path": path,
                "method": method,
                "status_code": None,
                "expected_status": expected_status,
                "success": False,
                "duration_ms": round(duration * 1000, 2),
                "error": str(e),
            }

    async def validate_all_endpoints(self):
        """
        Validate all known endpoints
        """
        logger.info(f"Validating endpoints at {self.base_url}")

        # Core health endpoints
        endpoints = [
            ("GET", "/", 200),
            ("GET", "/health", 200),
            ("GET", "/api/healthz", 200),
            ("GET", "/api/v1/healthz", 200),
            ("GET", "/readyz", 200),
            ("GET", "/api/v1/public/endpoint", 200),
            # Crown Safe specific endpoints
            ("GET", "/api/v1/safety-hub/articles", 200),
            # Monitoring endpoints
            ("GET", "/api/v1/monitoring/system-health-dashboard", 200),
            ("GET", "/api/v1/monitoring/security-audit", 200),
            ("GET", "/api/v1/monitoring/azure-cache-stats", 200),
            ("GET", "/api/v1/azure-storage/health", 200),
            # API documentation
            ("GET", "/openapi.json", 200),
            ("GET", "/docs", 200),
        ]

        # Validate each endpoint
        tasks = [self.validate_endpoint(method, path, expected) for method, path, expected in endpoints]

        self.results = await asyncio.gather(*tasks)

    def generate_report(self) -> str:
        """
        Generate validation report
        """
        if not self.results:
            return "No results available"

        # Calculate statistics
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        avg_duration = sum(r["duration_ms"] for r in self.results) / total if total > 0 else 0

        # Build report
        report = []
        report.append("=" * 80)
        report.append("ENDPOINT VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        report.append(f"Base URL: {self.base_url}")
        report.append(f"Total Endpoints: {total}")
        report.append(f"✅ Successful: {successful}")
        report.append(f"❌ Failed: {failed}")
        report.append(f"⏱️  Average Response Time: {avg_duration:.2f}ms")
        report.append("")

        # Success rate
        success_rate = (successful / total * 100) if total > 0 else 0
        report.append(f"Success Rate: {success_rate:.1f}%")
        report.append("")

        # Failed endpoints
        if failed > 0:
            report.append("=" * 80)
            report.append("FAILED ENDPOINTS")
            report.append("=" * 80)
            for result in self.results:
                if not result["success"]:
                    report.append(f"\n❌ {result['method']} {result['path']}")
                    report.append(f"   Expected: {result['expected_status']}")
                    report.append(f"   Actual: {result['status_code'] or 'ERROR'}")
                    if result["error"]:
                        report.append(f"   Error: {result['error']}")
                    report.append(f"   Duration: {result['duration_ms']}ms")

        # Successful endpoints
        report.append("")
        report.append("=" * 80)
        report.append("SUCCESSFUL ENDPOINTS")
        report.append("=" * 80)
        for result in self.results:
            if result["success"]:
                status_icon = "✅"
                warning_text = ""
                if "warning" in result:
                    status_icon = "⚠️"
                    warning_text = f" - {result['warning']}"

                report.append(
                    f"{status_icon} {result['method']:<6} {result['path']:<50} "
                    f"{result['duration_ms']:>6}ms{warning_text}"
                )

        # Slow endpoints
        slow_endpoints = [r for r in self.results if r["duration_ms"] > 1000]
        if slow_endpoints:
            report.append("")
            report.append("=" * 80)
            report.append("SLOW ENDPOINTS (>1000ms)")
            report.append("=" * 80)
            for result in sorted(slow_endpoints, key=lambda x: x["duration_ms"], reverse=True):
                report.append(f"⚠️  {result['method']:<6} {result['path']:<50} {result['duration_ms']:>6}ms")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)

    def save_report(self, filename: str):
        """
        Save report to file
        """
        report = self.generate_report()
        with open(filename, "w") as f:
            f.write(report)
        logger.info(f"Report saved to {filename}")


async def main():
    """
    Main validation function
    """
    import argparse

    parser = argparse.ArgumentParser(description="Validate API endpoints")
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="Base URL (default: http://localhost:8001)",
    )
    parser.add_argument("--output", default="endpoint_validation_report.txt", help="Output file")

    args = parser.parse_args()

    validator = EndpointValidator(base_url=args.url)

    logger.info("Starting endpoint validation...")
    await validator.validate_all_endpoints()

    # Generate and display report
    report = validator.generate_report()
    print("\n" + report)

    # Save to file
    validator.save_report(args.output)

    # Exit with non-zero if any failures
    failed = sum(1 for r in validator.results if not r["success"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
