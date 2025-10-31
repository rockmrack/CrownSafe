"""Crown Safe System Health Dashboard
Unified monitoring endpoint for all enterprise health metrics

Features:
- Aggregates health from all subsystems
- Security audit status
- Azure Storage health
- Cache performance metrics
- Connection pool statistics
- Database connectivity
- Overall system health score
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SystemHealthDashboard:
    """Unified health dashboard for Crown Safe
    Aggregates metrics from all monitoring subsystems
    """

    def __init__(self):
        """Initialize health dashboard"""
        self.startup_time = datetime.utcnow()

    def get_comprehensive_health(self) -> dict[str, Any]:
        """Get comprehensive system health status
        Aggregates metrics from all subsystems

        Returns:
            Dictionary with complete health information
        """
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
            "subsystems": {},
            "overall_health_score": 100.0,
        }

        # Security audit status
        try:
            security_status = self._get_security_status()
            health_data["subsystems"]["security"] = security_status

            # Reduce health score for security issues
            if security_status["status"] == "fail":
                risk_level = security_status.get("risk_level", "UNKNOWN")
                if risk_level == "CRITICAL":
                    health_data["overall_health_score"] -= 50
                elif risk_level == "HIGH":
                    health_data["overall_health_score"] -= 30
                elif risk_level == "MEDIUM":
                    health_data["overall_health_score"] -= 15
                else:
                    health_data["overall_health_score"] -= 5

        except Exception as e:
            logger.error(f"Failed to get security status: {e}")
            health_data["subsystems"]["security"] = {
                "status": "error",
                "error": str(e),
            }
            health_data["overall_health_score"] -= 10

        # Azure Storage health
        try:
            azure_health = self._get_azure_storage_health()
            health_data["subsystems"]["azure_storage"] = azure_health

            if azure_health["status"] != "healthy":
                health_data["overall_health_score"] -= 20

        except Exception as e:
            logger.error(f"Failed to get Azure Storage health: {e}")
            health_data["subsystems"]["azure_storage"] = {
                "status": "error",
                "error": str(e),
            }
            health_data["overall_health_score"] -= 15

        # Cache performance
        try:
            cache_stats = self._get_cache_stats()
            health_data["subsystems"]["cache"] = cache_stats

            # Check cache hit rate
            hit_rate = cache_stats.get("hit_rate_percent", 0)
            if hit_rate < 50:
                health_data["overall_health_score"] -= 10
            elif hit_rate < 70:
                health_data["overall_health_score"] -= 5

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            health_data["subsystems"]["cache"] = {"status": "error", "error": str(e)}

        # Connection pool statistics
        try:
            pool_stats = self._get_connection_pool_stats()
            health_data["subsystems"]["connection_pool"] = pool_stats

            # Check pool exhaustion
            exhaustion_count = pool_stats.get("pool_exhaustion_count", 0)
            if exhaustion_count > 100:
                health_data["overall_health_score"] -= 15
            elif exhaustion_count > 50:
                health_data["overall_health_score"] -= 10
            elif exhaustion_count > 10:
                health_data["overall_health_score"] -= 5

        except Exception as e:
            logger.error(f"Failed to get connection pool stats: {e}")
            health_data["subsystems"]["connection_pool"] = {
                "status": "error",
                "error": str(e),
            }

        # Database connectivity
        try:
            db_health = self._get_database_health()
            health_data["subsystems"]["database"] = db_health

            if db_health["status"] != "healthy":
                health_data["overall_health_score"] -= 25

        except Exception as e:
            logger.error(f"Failed to get database health: {e}")
            health_data["subsystems"]["database"] = {
                "status": "error",
                "error": str(e),
            }
            health_data["overall_health_score"] -= 20

        # Set overall status based on health score
        if health_data["overall_health_score"] >= 90:
            health_data["status"] = "healthy"
        elif health_data["overall_health_score"] >= 70:
            health_data["status"] = "degraded"
        elif health_data["overall_health_score"] >= 50:
            health_data["status"] = "warning"
        else:
            health_data["status"] = "critical"

        # Ensure health score doesn't go negative
        health_data["overall_health_score"] = max(0.0, health_data["overall_health_score"])

        return health_data

    def _get_security_status(self) -> dict[str, Any]:
        """Get security audit status"""
        try:
            from core_infra.security_validator import security_validator

            audit_results = security_validator.comprehensive_security_audit()
            return {
                "status": audit_results["overall_status"],
                "risk_level": audit_results.get("risk_level", "UNKNOWN"),
                "total_checks": audit_results.get("total_checks", 0),
                "failures": audit_results.get("total_failures", 0),
                "warnings": audit_results.get("total_warnings", 0),
            }
        except Exception as e:
            logger.error(f"Security status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def _get_azure_storage_health(self) -> dict[str, Any]:
        """Get Azure Storage health status"""
        try:
            from core_infra.azure_storage import AzureBlobStorageClient
            from core_infra.azure_storage_health import (
                AzureStorageHealthCheck,
                azure_storage_metrics,
            )

            # Create health checker
            client = AzureBlobStorageClient()
            health_checker = AzureStorageHealthCheck(client)

            # Run comprehensive health check
            health_result = health_checker.comprehensive_health_check()

            return {
                "status": health_result["status"],
                "connectivity": health_result["connectivity"]["status"],
                "performance": health_result["performance"]["status"],
                "metrics": {
                    "upload_count": azure_storage_metrics.upload_count,
                    "download_count": azure_storage_metrics.download_count,
                    "error_count": azure_storage_metrics.error_count,
                    "uptime_percent": azure_storage_metrics.get_uptime_percentage(),
                },
            }
        except Exception as e:
            logger.error(f"Azure Storage health check failed: {e}")
            return {"status": "error", "error": str(e)}

    def _get_cache_stats(self) -> dict[str, Any]:
        """Get cache performance statistics"""
        try:
            from core_infra.azure_storage_cache import get_cache_manager

            cache_manager = get_cache_manager()
            stats = cache_manager.get_cache_stats()

            return {
                "cache_enabled": stats["cache_enabled"],
                "hit_rate_percent": stats["hit_rate_percent"],
                "total_requests": stats["total_requests"],
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
            }
        except Exception as e:
            logger.error(f"Cache stats retrieval failed: {e}")
            return {"cache_enabled": False, "error": str(e)}

    def _get_connection_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics"""
        try:
            from core_infra.azure_connection_pool import get_connection_pool

            pool = get_connection_pool()
            stats = pool.get_stats()

            return {
                "available_connections": stats["available_connections"],
                "in_use_connections": stats["in_use_connections"],
                "reuse_rate_percent": stats["reuse_rate_percent"],
                "pool_exhaustion_count": stats["pool_exhaustion_count"],
            }
        except Exception as e:
            logger.error(f"Connection pool stats retrieval failed: {e}")
            return {"error": str(e)}

    def _get_database_health(self) -> dict[str, Any]:
        """Get database connectivity health"""
        try:
            from sqlalchemy import text

            from core_infra.database import SessionLocal

            db = SessionLocal()
            try:
                # Simple connectivity test
                db.execute(text("SELECT 1"))
                db.close()

                return {"status": "healthy", "connectivity": "ok"}
            except Exception as e:
                return {"status": "unhealthy", "error": str(e)}

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "error", "error": str(e)}


# Global dashboard instance
system_health_dashboard = SystemHealthDashboard()
