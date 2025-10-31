"""Rate Limiting for BabyShield API
Prevents API abuse and ensures fair usage.
"""

import os

import redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Get Redis URL from environment (prefer RATE_LIMIT_REDIS_URL)
# Fallback to in-memory storage when not provided or unreachable
REDIS_URL = os.getenv("RATE_LIMIT_REDIS_URL") or os.getenv("REDIS_URL")


def get_identifier(request: Request) -> str:
    """Get identifier for rate limiting
    Uses IP address or authenticated user ID.
    """
    # Try to get authenticated user first
    if hasattr(request.state, "user") and request.state.user:
        return f"user:{request.state.user.id}"

    # Fall back to IP address
    return get_remote_address(request)


def _build_limiter() -> Limiter:
    """Create a Limiter that fails open to in-memory if Redis is not configured or unreachable."""
    storage_uri = None
    if REDIS_URL:
        try:
            # Probe Redis quickly; if it fails, we will fall back to memory
            r = redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
            r.ping()
            storage_uri = REDIS_URL
        except Exception:
            storage_uri = None  # fail-open to in-memory
    return Limiter(
        key_func=get_identifier,
        default_limits=["100 per minute", "1000 per hour"],
        storage_uri=storage_uri,
        headers_enabled=True,
    )


# Create rate limiter instance (with safe fallback)
limiter = _build_limiter()


# Custom rate limit exceeded handler
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom handler for rate limit exceeded."""
    response = JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": f"Rate limit exceeded: {getattr(exc, 'detail', 'Too many requests')}",
            },
        },
    )

    # Add retry-after header
    response.headers["Retry-After"] = str(exc.retry_after) if hasattr(exc, "retry_after") else "60"

    # Add rate limit headers
    response.headers["X-RateLimit-Limit"] = str(exc.limit) if hasattr(exc, "limit") else "100"
    response.headers["X-RateLimit-Remaining"] = "0"
    response.headers["X-RateLimit-Reset"] = str(exc.reset) if hasattr(exc, "reset") else ""

    return response


# Rate limit decorators for different tiers
def standard_limit():
    """Standard rate limit for general endpoints."""
    return limiter.limit("100 per minute")


def strict_limit():
    """Strict rate limit for expensive operations."""
    return limiter.limit("20 per minute")


def relaxed_limit():
    """Relaxed rate limit for lightweight operations."""
    return limiter.limit("300 per minute")


def auth_limit():
    """Rate limit for authentication endpoints."""
    return limiter.limit("5 per minute")


# IP-based rate limiting for unauthenticated requests
def ip_limit():
    """IP-based rate limiting."""
    return limiter.limit("50 per minute", key_func=get_remote_address)


# Dynamic rate limiting based on user tier (optional)
def get_user_rate_limit(request: Request) -> str:
    """Get rate limit based on user tier
    Can be extended to support different user tiers.
    """
    if hasattr(request.state, "user") and request.state.user:
        # Premium users could get higher limits
        # if request.state.user.is_premium:
        #     return "500 per minute"
        return "200 per minute"  # Authenticated users
    return "50 per minute"  # Anonymous users


def dynamic_limit():
    """Dynamic rate limit based on user tier."""
    return limiter.limit(get_user_rate_limit)


# Utility function to check remaining rate limit
async def get_rate_limit_status(request: Request) -> dict:
    """Get current rate limit status for the requester."""
    identifier = get_identifier(request)

    try:
        # Connect to Redis
        r = redis.from_url(REDIS_URL)

        # Get current counts
        minute_key = f"LIMITER/{identifier}/100 per minute"
        hour_key = f"LIMITER/{identifier}/1000 per hour"

        minute_count = r.get(minute_key) or 0
        hour_count = r.get(hour_key) or 0

        return {
            "identifier": identifier,
            "limits": {
                "per_minute": {
                    "limit": 100,
                    "remaining": max(0, 100 - int(minute_count)),
                    "reset_in_seconds": r.ttl(minute_key) if minute_key else 60,
                },
                "per_hour": {
                    "limit": 1000,
                    "remaining": max(0, 1000 - int(hour_count)),
                    "reset_in_seconds": r.ttl(hour_key) if hour_key else 3600,
                },
            },
        }
    except Exception as e:
        return {"error": f"Could not get rate limit status: {e!s}"}


# Middleware to add user to request state
async def add_user_to_request(request: Request, call_next):
    """Middleware to add authenticated user to request state."""
    # This will be populated by the authentication middleware
    if not hasattr(request.state, "user"):
        request.state.user = None

    return await call_next(request)
