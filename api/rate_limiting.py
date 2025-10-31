"""Rate limiting configuration and handlers
Uses Redis for distributed rate limiting across instances
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis

logger = logging.getLogger("app")


class RateLimitConfig:
    """Configuration for rate limiting
    """

    # Default limits per endpoint category
    SEARCH_LIMIT = 60  # 60 requests per minute for search
    DETAIL_LIMIT = 120  # 120 requests per minute for detail views
    HEALTH_LIMIT = 300  # 300 requests per minute for health checks
    DEFAULT_LIMIT = 100  # Default for other endpoints

    # Time window (seconds)
    WINDOW = 60

    @classmethod
    def get_redis_url(cls) -> str | None:
        """Get Redis URL from environment; do not default to localhost in prod."""
        return os.getenv("RATE_LIMIT_REDIS_URL") or os.getenv("REDIS_URL")


async def init_rate_limiter() -> bool:
    """Initialize FastAPI rate limiter with Redis

    Returns:
        True if successful, False otherwise

    """
    try:
        redis_url = RateLimitConfig.get_redis_url()
        if not redis_url:
            logger.info("Rate limiter: disabled (no RATE_LIMIT_REDIS_URL/REDIS_URL)")
            return False
        redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await redis.ping()
        await FastAPILimiter.init(redis)
        logger.info(f"Rate limiter initialized with Redis at {redis_url}")
        return True
    except Exception as e:
        logger.warning(f"Rate limiter init failed; continuing without it: {e}")
        return False


async def close_rate_limiter() -> None:
    """Close rate limiter connections
    """
    try:
        await FastAPILimiter.close()
        logger.info("Rate limiter closed")
    except Exception as e:
        logger.error(f"Error closing rate limiter: {e}")


async def rate_limit_exceeded_handler(request: Request, exc) -> JSONResponse:
    """Handler for rate limit exceeded errors
    Returns consistent error format
    """
    trace_id = getattr(request.state, "trace_id", None)

    # Get retry after time (default 60 seconds)
    retry_after = 60

    headers = {
        "Retry-After": str(retry_after),
        "X-RateLimit-Limit": str(exc.limit) if hasattr(exc, "limit") else "60",
        "X-RateLimit-Window": "60",
        "X-RateLimit-Retry-After": str(retry_after),
    }

    # Log the rate limit event
    logger.warning(
        "Rate limit exceeded",
        extra={
            "traceId": trace_id,
            "path": request.url.path,
            "method": request.method,
            "ip": request.client.host if request.client else None,
        },
    )

    return JSONResponse(
        content={
            "ok": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please slow down and try again later.",
                "retry_after": retry_after,
            },
            "traceId": trace_id,
        },
        status_code=429,
        headers=headers,
    )


def get_rate_limiter(times: int = 100, seconds: int = 60, key_func: callable | None = None) -> RateLimiter:
    """Factory function to create rate limiter dependencies

    Args:
        times: Number of allowed requests
        seconds: Time window in seconds
        key_func: Optional custom key function

    Returns:
        RateLimiter dependency

    """
    return RateLimiter(times=times, seconds=seconds, key_func=key_func)


# Pre-configured rate limiters for common use cases
class RateLimiters:
    """Pre-configured rate limiters for different endpoint types
    """

    # Heavy operations - 60 req/min
    search = RateLimiter(times=RateLimitConfig.SEARCH_LIMIT, seconds=RateLimitConfig.WINDOW)

    # Light operations - 120 req/min
    detail = RateLimiter(times=RateLimitConfig.DETAIL_LIMIT, seconds=RateLimitConfig.WINDOW)

    # Health checks - 300 req/min
    health = RateLimiter(times=RateLimitConfig.HEALTH_LIMIT, seconds=RateLimitConfig.WINDOW)

    # Default - 100 req/min
    default = RateLimiter(times=RateLimitConfig.DEFAULT_LIMIT, seconds=RateLimitConfig.WINDOW)

    # Strict - 10 req/min (for sensitive operations)
    strict = RateLimiter(times=10, seconds=RateLimitConfig.WINDOW)


@asynccontextmanager
async def rate_limit_lifespan():
    """Async context manager for rate limiter lifecycle
    Use with FastAPI lifespan
    """
    # Startup
    await init_rate_limiter()
    yield
    # Shutdown
    await close_rate_limiter()
