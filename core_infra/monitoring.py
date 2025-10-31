"""
Monitoring and Alerting System
Enterprise monitoring with Prometheus metrics and alerts

Features:
- Prometheus metrics exposition
- Custom application metrics
- Alert rules and thresholds
- Integration with Azure Monitor
- Slack/Email notifications
"""

import logging
import time

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# ====================
# Prometheus Metrics
# ====================

# HTTP Request Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Database Metrics
database_connections_active = Gauge("database_connections_active", "Number of active database connections")

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

database_errors_total = Counter("database_errors_total", "Total database errors", ["error_type"])

# Cache Metrics
cache_hits_total = Counter("cache_hits_total", "Total cache hits")

cache_misses_total = Counter("cache_misses_total", "Total cache misses")

cache_size_bytes = Gauge("cache_size_bytes", "Current cache size in bytes")

# Azure Blob Storage Metrics
azure_blob_uploads_total = Counter("azure_blob_uploads_total", "Total blob uploads", ["status"])

azure_blob_upload_duration_seconds = Histogram(
    "azure_blob_upload_duration_seconds",
    "Blob upload duration in seconds",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

azure_blob_storage_bytes = Gauge("azure_blob_storage_bytes", "Total bytes stored in Azure Blob Storage")

# Application Health Metrics
app_health_score = Gauge("app_health_score", "Application health score (0-100)")

app_uptime_seconds = Gauge("app_uptime_seconds", "Application uptime in seconds")

# Security Metrics
security_audit_failures_total = Counter("security_audit_failures_total", "Total security audit failures", ["severity"])

# API Endpoint Metrics
api_recalls_total = Counter("api_recalls_total", "Total recall queries", ["country", "status"])

api_barcode_scans_total = Counter("api_barcode_scans_total", "Total barcode scans")

api_visual_recognition_total = Counter("api_visual_recognition_total", "Total visual recognition requests")


# ====================
# Monitoring Manager
# ====================


class MonitoringManager:
    """
    Central monitoring and alerting manager
    """

    def __init__(self):
        self.start_time = time.time()
        self.alert_rules = self._define_alert_rules()

    def _define_alert_rules(self) -> list[dict]:
        """
        Define alert rules and thresholds
        """
        return [
            {
                "name": "HighErrorRate",
                "condition": "error_rate > 5%",
                "severity": "critical",
                "description": "HTTP error rate exceeds 5%",
            },
            {
                "name": "HighResponseTime",
                "condition": "p95_response_time > 2s",
                "severity": "warning",
                "description": "95th percentile response time exceeds 2 seconds",
            },
            {
                "name": "DatabaseConnectionPoolExhaustion",
                "condition": "db_pool_exhausted > 50",
                "severity": "critical",
                "description": "Database connection pool exhaustion count high",
            },
            {
                "name": "LowCacheHitRate",
                "condition": "cache_hit_rate < 50%",
                "severity": "warning",
                "description": "Cache hit rate below 50%",
            },
            {
                "name": "HealthScoreLow",
                "condition": "health_score < 70",
                "severity": "warning",
                "description": "Application health score below 70",
            },
            {
                "name": "HealthScoreCritical",
                "condition": "health_score < 50",
                "severity": "critical",
                "description": "Application health score below 50",
            },
            {
                "name": "SecurityAuditFailures",
                "condition": "security_failures > 10",
                "severity": "critical",
                "description": "Security audit failures detected",
            },
        ]

    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        Record HTTP request metrics
        """
        http_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

    def record_database_query(self, operation: str, duration: float, success: bool):
        """
        Record database query metrics
        """
        database_query_duration_seconds.labels(operation=operation).observe(duration)

        if not success:
            database_errors_total.labels(error_type=operation).inc()

    def record_cache_access(self, hit: bool):
        """
        Record cache access metrics
        """
        if hit:
            cache_hits_total.inc()
        else:
            cache_misses_total.inc()

    def record_blob_upload(self, duration: float, success: bool):
        """
        Record Azure Blob upload metrics
        """
        status = "success" if success else "failure"
        azure_blob_uploads_total.labels(status=status).inc()
        azure_blob_upload_duration_seconds.observe(duration)

    def update_health_score(self, score: int):
        """
        Update application health score
        """
        app_health_score.set(score)

    def update_uptime(self):
        """
        Update application uptime
        """
        uptime = time.time() - self.start_time
        app_uptime_seconds.set(uptime)

    def record_security_failure(self, severity: str):
        """
        Record security audit failure
        """
        security_audit_failures_total.labels(severity=severity).inc()

    def get_metrics(self) -> Response:
        """
        Get Prometheus metrics in exposition format
        """
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    def get_alert_rules(self) -> list[dict]:
        """
        Get all alert rules
        """
        return self.alert_rules

    def check_alerts(self) -> list[dict]:
        """
        Check if any alerts should be triggered

        Returns:
            List of active alerts
        """
        active_alerts = []

        # This would integrate with actual metrics collection
        # For now, returns empty list
        # In production, query Prometheus/Azure Monitor for metrics

        return active_alerts


# ====================
# Global Instance
# ====================

_monitoring_manager = None


def get_monitoring_manager() -> MonitoringManager:
    """
    Get global monitoring manager instance
    """
    global _monitoring_manager
    if _monitoring_manager is None:
        _monitoring_manager = MonitoringManager()
    return _monitoring_manager


# ====================
# Middleware
# ====================


async def monitoring_middleware(request, call_next):
    """
    FastAPI middleware for automatic request monitoring
    """
    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record metrics
        monitoring = get_monitoring_manager()
        monitoring.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

        return response

    except Exception:
        duration = time.time() - start_time
        monitoring = get_monitoring_manager()
        monitoring.record_http_request(
            method=request.method, endpoint=request.url.path, status_code=500, duration=duration
        )
        raise


if __name__ == "__main__":
    # Demo usage
    manager = get_monitoring_manager()

    # Simulate some metrics
    manager.record_http_request("GET", "/api/recalls", 200, 0.15)
    manager.record_http_request("POST", "/api/barcode", 200, 0.35)
    manager.record_database_query("SELECT", 0.005, True)
    manager.record_cache_access(hit=True)
    manager.record_blob_upload(1.2, success=True)
    manager.update_health_score(95)

    print("Monitoring system initialized")
    print(f"Alert rules defined: {len(manager.get_alert_rules())}")
