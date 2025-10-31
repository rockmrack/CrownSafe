"""Security integration module for Task 6
Wires all security features into the FastAPI app.
"""

import logging
import os

from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

# Import security modules
from api.middleware.size_limit import SizeLimitMiddleware
from api.middleware.ua_block import UserAgentBlocker
from api.security.cors import add_strict_cors
from api.security.headers import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


def setup_security(app: FastAPI) -> None:
    """Configure all security features for the FastAPI app.

    This function adds all security middleware in the correct order.
    Middleware order matters - they execute in reverse order of addition.

    Args:
        app: FastAPI application instance

    """
    logger.info("Setting up security middleware")

    # 1. Size limit middleware (early rejection of large requests)
    # This should be early to prevent resource consumption
    max_bytes = int(os.getenv("MAX_REQUEST_BYTES", "100000"))
    app.add_middleware(SizeLimitMiddleware, max_bytes=max_bytes)
    logger.info(f"Request size limit: {max_bytes} bytes")

    # 2. User-Agent blocking (reject malicious scanners)
    # Enable only if explicitly configured
    if os.getenv("ENABLE_UA_BLOCKING", "true").lower() == "true":
        app.add_middleware(UserAgentBlocker)
        logger.info("User-Agent blocking enabled")
    else:
        logger.info("User-Agent blocking disabled")

    # 3. Security headers middleware
    # Adds comprehensive security headers to all responses
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware added")

    # 4. Response compression (GZip)
    # Only compress responses larger than 1KB
    minimum_size = int(os.getenv("GZIP_MINIMUM_SIZE", "1024"))
    app.add_middleware(GZipMiddleware, minimum_size=minimum_size)
    logger.info(f"GZip compression enabled (min size: {minimum_size} bytes)")

    # 5. CORS configuration (strict origins)
    # Should be one of the last middleware to add
    add_strict_cors(app)
    logger.info("Strict CORS configured")

    logger.info("Security setup complete")


def get_security_config() -> dict:
    """Get current security configuration.

    Returns:
        Dictionary with security settings

    """
    return {
        "max_request_bytes": int(os.getenv("MAX_REQUEST_BYTES", "100000")),
        "cors_origins": os.getenv("CORS_ALLOWED_ORIGINS", "").split(","),
        "ua_blocking_enabled": os.getenv("ENABLE_UA_BLOCKING", "true").lower() == "true",
        "gzip_minimum_size": int(os.getenv("GZIP_MINIMUM_SIZE", "1024")),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "hsts_enabled": True,
        "frame_options": "DENY",
        "content_type_options": "nosniff",
        "xss_protection": "1; mode=block",
        "referrer_policy": "strict-origin-when-cross-origin",
    }


def validate_security_config() -> None:
    """Validate security configuration and warn about issues."""
    config = get_security_config()

    # Check CORS origins
    if not config["cors_origins"][0]:
        logger.warning("No CORS origins configured - using defaults")

    # Check environment
    if config["environment"].lower() in ("development", "dev", "local"):
        logger.warning("Running in development mode - some security features may be relaxed")

    # Check request size limit
    if config["max_request_bytes"] > 1_000_000:  # 1MB
        logger.warning(f"Large request size limit: {config['max_request_bytes']} bytes")

    logger.info(f"Security config validated: {config['environment']} environment")


# Integration example for main.py
INTEGRATION_EXAMPLE = """
# Add to your main_crownsafe.py:

from api.security.integration import setup_security, validate_security_config

# Validate config on startup
validate_security_config()

# Setup all security features
setup_security(app)

# Or add individual components:

from api.middleware.size_limit import SizeLimitMiddleware
from api.middleware.ua_block import UserAgentBlocker
from api.security.cors import add_strict_cors
from api.security.headers import SecurityHeadersMiddleware
from starlette.middleware.gzip import GZipMiddleware

# Add in order (reverse execution)
app.add_middleware(SizeLimitMiddleware)
app.add_middleware(UserAgentBlocker)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
add_strict_cors(app)

# Use secure input validation:

from api.models.search_validation import SecureAdvancedSearchRequest

@app.post("/api/v1/search/advanced")
async def search_advanced(request: SecureAdvancedSearchRequest):
    # Input is validated and bounded
    pass
"""


class SecurityDefaults:
    """Default security settings."""

    # Request limits
    MAX_REQUEST_SIZE = 100_000  # 100KB
    MAX_UPLOAD_SIZE = 5_000_000  # 5MB

    # Field limits
    MAX_STRING_LENGTH = 128
    MAX_KEYWORD_LENGTH = 32
    MAX_KEYWORDS = 8
    MAX_AGENCIES = 10
    MAX_PAGE_SIZE = 50

    # CORS
    PRODUCTION_ORIGINS = [
        "https://babyshield.app",
        "https://app.babyshield.app",
        "https://www.babyshield.app",
        "https://babyshield.cureviax.ai",
    ]

    # Compression
    GZIP_MIN_SIZE = 1024  # 1KB

    # Rate limits (from Task 4)
    SEARCH_RATE_LIMIT = 60  # per minute
    DETAIL_RATE_LIMIT = 120  # per minute

    @classmethod
    def apply_to_env(cls) -> None:
        """Apply defaults to environment if not set."""
        defaults = {
            "MAX_REQUEST_BYTES": str(cls.MAX_REQUEST_SIZE),
            "GZIP_MINIMUM_SIZE": str(cls.GZIP_MIN_SIZE),
            "CORS_ALLOWED_ORIGINS": ",".join(cls.PRODUCTION_ORIGINS),
        }

        for key, value in defaults.items():
            if not os.getenv(key):
                os.environ[key] = value
                logger.debug(f"Set default {key}={value}")


# Export
__all__ = [
    "SecurityDefaults",
    "get_security_config",
    "setup_security",
    "validate_security_config",
]
