"""
Admin authentication for secure admin endpoints
Uses API key authentication with rate limiting
"""

import hashlib
import hmac
import logging
import os
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from api.errors import APIError

logger = logging.getLogger(__name__)

# Get admin key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
ADMIN_KEY_HASH = hashlib.sha256(ADMIN_API_KEY.encode()).hexdigest() if ADMIN_API_KEY else ""

# Optional: Multiple admin keys for different services
ADMIN_KEYS = {
    key.strip(): name
    for name, key in [
        ("primary", os.getenv("ADMIN_API_KEY", "")),
        ("secondary", os.getenv("ADMIN_API_KEY_SECONDARY", "")),
        ("monitoring", os.getenv("ADMIN_API_KEY_MONITORING", "")),
    ]
    if key.strip()
}

# API key header scheme
api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin(request: Request, x_admin_key: Optional[str] = Depends(api_key_header)) -> str:
    """
    Require admin authentication via API key

    Args:
        request: FastAPI request object
        x_admin_key: Admin API key from header

    Returns:
        Admin identifier (for audit logging)

    Raises:
        HTTPException: 401 if unauthorized
    """
    trace_id = getattr(request.state, "trace_id", None)

    # Check if admin key is configured
    if not ADMIN_API_KEY:
        logger.error("Admin API key not configured", extra={"traceId": trace_id})
        raise APIError(
            status_code=503,
            code="ADMIN_NOT_CONFIGURED",
            message="Admin API is not configured",
        )

    # Check if key provided
    if not x_admin_key:
        logger.warning(
            "Admin access attempted without key",
            extra={
                "traceId": trace_id,
                "path": request.url.path,
                "ip": request.client.host if request.client else None,
            },
        )
        raise APIError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Admin authentication required",
        )

    # Validate key (constant time comparison)
    if not hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        # Check secondary keys
        admin_name = ADMIN_KEYS.get(x_admin_key)
        if not admin_name:
            logger.warning(
                "Admin access denied - invalid key",
                extra={
                    "traceId": trace_id,
                    "path": request.url.path,
                    "ip": request.client.host if request.client else None,
                    "key_prefix": x_admin_key[:8] + "..." if len(x_admin_key) > 8 else "***",
                },
            )
            raise APIError(
                status_code=401,
                code="UNAUTHORIZED",
                message="Invalid admin credentials",
            )

        # Valid secondary key
        logger.info(
            f"Admin access granted to {admin_name}",
            extra={"traceId": trace_id, "admin": admin_name, "path": request.url.path},
        )
        return admin_name

    # Valid primary key
    logger.info(
        "Admin access granted",
        extra={"traceId": trace_id, "admin": "primary", "path": request.url.path},
    )

    return "admin"


async def optional_admin(request: Request, x_admin_key: Optional[str] = Depends(api_key_header)) -> Optional[str]:
    """
    Optional admin authentication
    Returns admin identifier if authenticated, None otherwise

    Args:
        request: FastAPI request object
        x_admin_key: Admin API key from header

    Returns:
        Admin identifier or None
    """
    if not x_admin_key or not ADMIN_API_KEY:
        return None

    # Check if valid
    if hmac.compare_digest(x_admin_key, ADMIN_API_KEY):
        return "admin"

    # Check secondary keys
    return ADMIN_KEYS.get(x_admin_key)


class AdminRateLimit:
    """
    Special rate limits for admin endpoints
    """

    # Admin endpoints have lower rate limits for security
    INGEST_LIMIT = 5  # 5 ingestions per hour
    REINDEX_LIMIT = 10  # 10 reindexes per hour
    QUERY_LIMIT = 60  # 60 queries per minute

    @classmethod
    def get_ingest_limiter(cls):
        """Rate limiter for ingestion endpoints"""
        from api.rate_limiting import RateLimiter

        return RateLimiter(times=cls.INGEST_LIMIT, seconds=3600)

    @classmethod
    def get_reindex_limiter(cls):
        """Rate limiter for reindex endpoints"""
        from api.rate_limiting import RateLimiter

        return RateLimiter(times=cls.REINDEX_LIMIT, seconds=3600)

    @classmethod
    def get_query_limiter(cls):
        """Rate limiter for query endpoints"""
        from api.rate_limiting import RateLimiter

        return RateLimiter(times=cls.QUERY_LIMIT, seconds=60)


def validate_admin_key(key: str) -> bool:
    """
    Validate an admin key format

    Args:
        key: API key to validate

    Returns:
        True if valid format
    """
    # Must be at least 32 characters
    if len(key) < 32:
        return False

    # Should be alphanumeric with some symbols
    if not all(c.isalnum() or c in "-_" for c in key):
        return False

    return True


def generate_admin_key() -> str:
    """
    Generate a secure admin API key

    Returns:
        Random 64-character API key
    """
    import secrets

    return secrets.token_urlsafe(48)  # ~64 chars after base64


# Export
__all__ = [
    "require_admin",
    "optional_admin",
    "AdminRateLimit",
    "validate_admin_key",
    "generate_admin_key",
]
