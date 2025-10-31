"""
System health and readiness endpoints
Provides health checks for monitoring and orchestration
"""

import logging
import os
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

logger = logging.getLogger("app")

router = APIRouter()


@router.get("/api/v1/healthz")
async def healthz(response: Response) -> dict[str, Any]:
    """
    Basic health check endpoint
    Returns 200 if the service is running

    Used for:
    - Kubernetes liveness probe
    - Load balancer health checks
    - Basic uptime monitoring
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    return {
        "ok": True,
        "status": "healthy",
        "service": "babyshield-api",
        "version": os.getenv("API_VERSION", "v1.2.0"),
    }


@router.get("/api/v1/readyz")
async def readyz(response: Response) -> JSONResponse:
    """
    Readiness check endpoint
    Checks all critical dependencies

    Returns:
    - 200 if all dependencies are ready
    - 503 if any dependency is down

    Used for:
    - Kubernetes readiness probe
    - Pre-deployment checks
    - Dependency monitoring
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    checks = {"db": False, "redis": False}

    # Check database connection
    try:
        from core_infra.database import get_db_session

        with get_db_session() as db:
            result = db.execute(text("SELECT 1"))
            result.scalar()
        checks["db"] = True
        logger.debug("Database check passed")
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        checks["db"] = False

    # Check Redis connection (for rate limiting)
    try:
        redis_url = os.getenv("RATE_LIMIT_REDIS_URL", "redis://localhost:6379/0")
        redis = Redis.from_url(redis_url, decode_responses=True)
        await redis.ping()
        await redis.close()
        checks["redis"] = True
        logger.debug("Redis check passed")
    except Exception as e:
        logger.warning(f"Redis check failed: {e}")
        checks["redis"] = False

    # Determine overall status
    all_ready = all(checks.values())
    status = "ready" if all_ready else "degraded"
    status_code = 200 if all_ready else 503

    response_data = {
        "ok": all_ready,
        "status": status,
        "dependencies": checks,
        "service": "babyshield-api",
        "version": os.getenv("API_VERSION", "v1.2.0"),
    }

    if not all_ready:
        # Log which dependencies are failing
        failed = [name for name, ok in checks.items() if not ok]
        logger.warning(f"Readiness check failed. Down: {', '.join(failed)}")

    return JSONResponse(content=response_data, status_code=status_code)


@router.get("/api/v1/status")
async def status(response: Response) -> dict[str, Any]:
    """
    Detailed status endpoint
    Provides comprehensive system information
    """
    import platform
    from datetime import datetime

    import psutil

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    # Get system metrics
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.1)

    return {
        "ok": True,
        "service": "babyshield-api",
        "version": os.getenv("API_VERSION", "v1.2.0"),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.utcnow().isoformat(),
        "system": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
        },
    }
