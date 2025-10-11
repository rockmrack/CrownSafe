"""
Enhanced Health Check Endpoints.

Provides detailed health status for all system components
including database, cache, and external service dependencies.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from core_infra.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/healthz")
async def basic_health_check():
    """
    Basic health check endpoint.

    Returns:
        Simple OK status for load balancers and monitoring
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check with component status.

    Checks:
    - Database connectivity and latency
    - Redis cache (if configured)
    - Memory cache statistics
    - System information

    Returns:
        Detailed status of all system components

    Example Response:
        {
            "status": "healthy",
            "timestamp": "2025-10-09T12:00:00",
            "response_time_ms": 15.2,
            "version": "abc123",
            "checks": {
                "database": {"status": "healthy", "latency_ms": 5.2},
                "cache": {"status": "healthy", "hit_rate": 0.75},
                "redis": {"status": "not_configured"}
            }
        }
    """
    start_time = time.time()
    checks = {}
    overall_status = "healthy"

    # ============ Database Check ============
    try:
        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - db_start) * 1000

        checks["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency, 2),
        }

        # Check if database is too slow
        if db_latency > 100:
            checks["database"]["warning"] = "High latency detected"
            overall_status = "degraded"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        overall_status = "unhealthy"

    # ============ Memory Cache Check ============
    try:
        from core_infra.cache import get_all_cache_stats

        cache_stats = get_all_cache_stats()
        checks["memory_cache"] = {
            "status": "healthy",
            "caches": cache_stats,
        }
    except ImportError:
        checks["memory_cache"] = {"status": "not_available"}
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        checks["memory_cache"] = {
            "status": "error",
            "error": str(e),
        }

    # ============ Redis Check ============
    try:
        from core_infra.redis_client import redis_client

        redis_start = time.time()
        await redis_client.ping()
        redis_latency = (time.time() - redis_start) * 1000

        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round(redis_latency, 2),
        }
    except ImportError:
        checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        checks["redis"] = {
            "status": "unavailable",
            "error": str(e),
        }
        # Redis is optional, don't mark as unhealthy

    # ============ Sentry Check ============
    try:
        import sentry_sdk

        if sentry_sdk.Hub.current.client:
            checks["sentry"] = {"status": "configured"}
        else:
            checks["sentry"] = {"status": "not_configured"}
    except ImportError:
        checks["sentry"] = {"status": "not_installed"}

    # ============ External APIs Check ============
    # Add checks for external services if needed
    checks["external_apis"] = {
        "status": "not_checked",
        "note": "External API health checks not implemented",
    }

    # ============ Calculate Response Time ============
    response_time_ms = (time.time() - start_time) * 1000

    # ============ Build Response ============
    import os

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": round(response_time_ms, 2),
        "version": os.getenv("GIT_COMMIT", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "checks": checks,
    }

    # Return appropriate status code
    if overall_status == "unhealthy":
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.

    Returns 200 if the service is ready to accept traffic,
    503 if not ready yet (e.g., database not connected).
    """
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "error": str(e)},
        )


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe.

    Returns 200 if the service is alive (process is running).
    This should never fail unless the process is completely dead.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
