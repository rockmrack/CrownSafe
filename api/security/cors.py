"""Strict CORS configuration for production security
Only allows specific origins, no wildcards
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def get_allowed_origins() -> list[str]:
    """Get allowed CORS origins from environment

    Returns:
        List of allowed origin URLs

    """
    # Get from environment variable
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")

    # Parse comma-separated list
    if origins_env:
        origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    else:
        # Default to known Crown Safe domains
        origins = [
            "https://crownsafe.app",
            "https://app.crownsafe.app",
            "https://crownsafe.cureviax.ai",
            "https://www.crownsafe.app",
        ]

    # Add localhost for development if in dev mode
    if os.getenv("ENVIRONMENT", "production").lower() in (
        "development",
        "dev",
        "local",
    ):
        origins.extend(
            [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8080",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:8080",
            ],
        )

    # Remove duplicates while preserving order
    seen = set()
    unique_origins = []
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            unique_origins.append(origin)

    return unique_origins


def add_strict_cors(
    app: FastAPI,
    allowed_origins: list[str] | None = None,
    allow_credentials: bool = False,
    max_age: int = 600,
) -> None:
    """Add strict CORS configuration to FastAPI app

    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins (uses env if not provided)
        allow_credentials: Whether to allow credentials in CORS requests
        max_age: Max age for preflight cache (seconds)

    """
    # Get origins
    origins = allowed_origins or get_allowed_origins()

    if not origins:
        logger.warning("No CORS origins configured - defaulting to restrictive policy")
        origins = ["https://crownsafe.cureviax.ai"]

    # Log configuration
    logger.info(f"CORS configured with {len(origins)} allowed origins")
    for origin in origins[:5]:  # Log first 5
        logger.debug(f"  Allowed origin: {origin}")
    if len(origins) > 5:
        logger.debug(f"  ... and {len(origins) - 5} more")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # Specific origins only
        allow_credentials=allow_credentials,  # Default False for security
        allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Correlation-ID",
            "X-API-Version",
        ],
        max_age=max_age,  # 10 minutes preflight cache
        expose_headers=[
            "X-Request-ID",
            "X-API-Version",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
    )

    logger.info("Strict CORS middleware added")


class CORSConfig:
    """CORS configuration settings
    """

    # Production origins
    PRODUCTION_ORIGINS = [
        "https://crownsafe.app",
        "https://app.crownsafe.app",
        "https://www.crownsafe.app",
        "https://crownsafe.cureviax.ai",
        "https://api.crownsafe.app",
    ]

    # Staging origins
    STAGING_ORIGINS = [
        "https://staging.crownsafe.app",
        "https://staging-app.crownsafe.app",
        "https://crownsafe-staging.cureviax.ai",
    ]

    # Development origins
    DEVELOPMENT_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8080",
        "http://localhost:5173",  # Vite
        "http://localhost:4200",  # Angular
    ]

    @classmethod
    def get_origins_for_environment(cls, environment: str) -> list[str]:
        """Get appropriate origins based on environment

        Args:
            environment: Environment name (production, staging, development)

        Returns:
            List of allowed origins

        """
        env = environment.lower()

        if env == "production":
            return cls.PRODUCTION_ORIGINS
        elif env == "staging":
            return cls.PRODUCTION_ORIGINS + cls.STAGING_ORIGINS
        elif env in ("development", "dev", "local"):
            return cls.PRODUCTION_ORIGINS + cls.STAGING_ORIGINS + cls.DEVELOPMENT_ORIGINS
        else:
            # Unknown environment - be restrictive
            logger.warning(f"Unknown environment: {environment}")
            return cls.PRODUCTION_ORIGINS

    @classmethod
    def validate_origin(cls, origin: str) -> bool:
        """Validate if an origin is allowed

        Args:
            origin: Origin URL to validate

        Returns:
            True if origin is allowed

        """
        # Never allow wildcard
        if origin == "*":
            return False

        # Check against configured origins
        allowed = get_allowed_origins()
        return origin in allowed


def create_cors_middleware(app: FastAPI) -> None:
    """Factory function to create CORS middleware
    Alternative to add_strict_cors for more control
    """
    environment = os.getenv("ENVIRONMENT", "production")

    # Get origins based on environment
    if os.getenv("CORS_ALLOWED_ORIGINS"):
        # Use explicitly configured origins
        add_strict_cors(app)
    else:
        # Use environment-based defaults
        origins = CORSConfig.get_origins_for_environment(environment)
        add_strict_cors(app, allowed_origins=origins)


# Export main function
__all__ = [
    "add_strict_cors",
    "get_allowed_origins",
    "CORSConfig",
    "create_cors_middleware",
]
