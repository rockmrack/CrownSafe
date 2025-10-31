"""
Azure Blob Storage Health Check and Monitoring
Enterprise-grade health checks for Azure Blob Storage connectivity and performance
"""

import logging
import time
from datetime import datetime
from typing import Any

from azure.core.exceptions import AzureError

from core_infra.azure_storage import AzureBlobStorageClient

logger = logging.getLogger(__name__)


class AzureStorageHealthCheck:
    """
    Comprehensive health check for Azure Blob Storage
    Monitors connectivity, performance, and storage capacity
    """

    def __init__(
        self,
        storage_client: AzureBlobStorageClient | None = None,
        performance_threshold_ms: float = 5000.0,
        storage_threshold_percent: float = 80.0,
    ):
        """
        Initialize health check monitor

        Args:
            storage_client: Azure Blob Storage client instance
            performance_threshold_ms: Performance warning threshold (milliseconds)
            storage_threshold_percent: Storage capacity warning threshold (percent)
        """
        self.storage_client = storage_client or AzureBlobStorageClient()
        self.performance_threshold_ms = performance_threshold_ms
        self.storage_threshold_percent = storage_threshold_percent

        # Health check metrics
        self.last_check_time: datetime | None = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.successful_checks = 0

    async def check_connectivity(self) -> dict[str, Any]:
        """
        Check basic Azure Blob Storage connectivity

        Returns:
            Dict with connectivity status and details
        """
        start_time = time.perf_counter()

        try:
            # Attempt to list blobs (minimal operation)
            self.storage_client.list_blobs(max_results=1)

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return {
                "status": "healthy",
                "connectivity": "ok",
                "response_time_ms": round(elapsed_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except AzureError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            logger.error(
                f"Azure storage connectivity check failed: {e}",
                extra={"response_time_ms": elapsed_ms},
            )

            return {
                "status": "unhealthy",
                "connectivity": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": round(elapsed_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def check_performance(self) -> dict[str, Any]:
        """
        Check Azure Blob Storage performance

        Returns:
            Dict with performance metrics
        """
        metrics = {
            "list_operation_ms": 0.0,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            # Test list operation performance
            start_time = time.perf_counter()
            self.storage_client.list_blobs(max_results=10)
            list_elapsed_ms = (time.perf_counter() - start_time) * 1000

            metrics["list_operation_ms"] = round(list_elapsed_ms, 2)

            # Check if performance is degraded
            if list_elapsed_ms > self.performance_threshold_ms:
                metrics["status"] = "degraded"
                metrics["warning"] = (
                    f"List operation took {list_elapsed_ms:.2f}ms (threshold: {self.performance_threshold_ms}ms)"
                )
                logger.warning(f"Azure storage performance degraded: {list_elapsed_ms:.2f}ms")

        except AzureError as e:
            metrics["status"] = "unhealthy"
            metrics["error"] = str(e)
            logger.error(f"Azure storage performance check failed: {e}")

        return metrics

    async def check_storage_capacity(self) -> dict[str, Any]:
        """
        Check Azure Blob Storage capacity and usage

        Note: Requires Azure Storage Account metrics API access
        This is a placeholder for future implementation

        Returns:
            Dict with storage capacity information
        """
        return {
            "status": "not_implemented",
            "message": "Storage capacity monitoring requires Azure Monitor API",
            "recommendation": "Configure Azure Monitor for capacity alerts",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def comprehensive_health_check(self) -> dict[str, Any]:
        """
        Run comprehensive health check with all tests

        Returns:
            Dict with complete health status
        """
        self.total_checks += 1
        self.last_check_time = datetime.utcnow()

        # Run all health checks
        connectivity_result = await self.check_connectivity()
        performance_result = await self.check_performance()
        capacity_result = await self.check_storage_capacity()

        # Determine overall status
        all_healthy = connectivity_result["status"] == "healthy" and performance_result["status"] in [
            "healthy",
            "degraded",
        ]

        if all_healthy:
            self.successful_checks += 1
            self.consecutive_failures = 0
            overall_status = "healthy"
        else:
            self.consecutive_failures += 1
            overall_status = "unhealthy"

        # Calculate uptime percentage
        uptime_percent = (self.successful_checks / self.total_checks * 100) if self.total_checks > 0 else 0.0

        return {
            "service": "azure_blob_storage",
            "status": overall_status,
            "checks": {
                "connectivity": connectivity_result,
                "performance": performance_result,
                "capacity": capacity_result,
            },
            "metrics": {
                "total_checks": self.total_checks,
                "successful_checks": self.successful_checks,
                "consecutive_failures": self.consecutive_failures,
                "uptime_percent": round(uptime_percent, 2),
                "last_check": self.last_check_time.isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class AzureStorageMetrics:
    """
    Collect and track Azure Blob Storage metrics
    """

    def __init__(self):
        self.upload_count = 0
        self.upload_bytes = 0
        self.download_count = 0
        self.download_bytes = 0
        self.error_count = 0
        self.sas_url_generation_count = 0

        # Performance tracking
        self.upload_times_ms = []
        self.download_times_ms = []
        self.sas_generation_times_ms = []

        self.start_time = datetime.utcnow()

    def record_upload(self, size_bytes: int, duration_ms: float):
        """Record upload operation"""
        self.upload_count += 1
        self.upload_bytes += size_bytes
        self.upload_times_ms.append(duration_ms)

        # Keep only last 100 measurements
        if len(self.upload_times_ms) > 100:
            self.upload_times_ms = self.upload_times_ms[-100:]

    def record_download(self, size_bytes: int, duration_ms: float):
        """Record download operation"""
        self.download_count += 1
        self.download_bytes += size_bytes
        self.download_times_ms.append(duration_ms)

        if len(self.download_times_ms) > 100:
            self.download_times_ms = self.download_times_ms[-100:]

    def record_sas_generation(self, duration_ms: float):
        """Record SAS URL generation"""
        self.sas_url_generation_count += 1
        self.sas_generation_times_ms.append(duration_ms)

        if len(self.sas_generation_times_ms) > 100:
            self.sas_generation_times_ms = self.sas_generation_times_ms[-100:]

    def record_error(self):
        """Record error"""
        self.error_count += 1

    def get_metrics(self) -> dict[str, Any]:
        """
        Get current metrics

        Returns:
            Dict with all collected metrics
        """
        uptime = datetime.utcnow() - self.start_time

        return {
            "operations": {
                "upload_count": self.upload_count,
                "upload_bytes": self.upload_bytes,
                "download_count": self.download_count,
                "download_bytes": self.download_bytes,
                "sas_url_generation_count": self.sas_url_generation_count,
                "error_count": self.error_count,
            },
            "performance": {
                "avg_upload_time_ms": (
                    round(sum(self.upload_times_ms) / len(self.upload_times_ms), 2) if self.upload_times_ms else 0.0
                ),
                "avg_download_time_ms": (
                    round(sum(self.download_times_ms) / len(self.download_times_ms), 2)
                    if self.download_times_ms
                    else 0.0
                ),
                "avg_sas_generation_time_ms": (
                    round(
                        sum(self.sas_generation_times_ms) / len(self.sas_generation_times_ms),
                        2,
                    )
                    if self.sas_generation_times_ms
                    else 0.0
                ),
            },
            "uptime": {
                "seconds": uptime.total_seconds(),
                "formatted": str(uptime),
            },
            "error_rate": (
                round(
                    self.error_count / (self.upload_count + self.download_count + 1) * 100,
                    2,
                )
                if (self.upload_count + self.download_count) > 0
                else 0.0
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset_metrics(self):
        """Reset all metrics (for testing or periodic reset)"""
        self.__init__()


# Global metrics instance
azure_storage_metrics = AzureStorageMetrics()
