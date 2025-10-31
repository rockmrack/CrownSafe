"""
FastAPI Application Factory
Creates and configures the BabyShield API application with all middleware and settings
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from utils.security.security_headers import configure_security_middleware

logger = logging.getLogger(__name__)


def create_app(
    environment: str = "development",
    config: Optional[object] = None,
    enable_docs: bool = True,
) -> FastAPI:
    """
    Create and configure FastAPI application

    Args:
        environment: Application environment (development, staging, production)
        config: Configuration object
        enable_docs: Whether to enable API documentation

    Returns:
        Configured FastAPI application
    """
    # Determine if we're in production (reserved for future environment-specific config)
    _ = environment == "production"

    # Create FastAPI app
    app = FastAPI(
        title="BabyShield API",
        description="Production-ready baby product safety checking system with 39-agency coverage",
        version="2.5.0",
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
        openapi_url="/openapi.json" if enable_docs else None,
        generate_unique_id_function=lambda route: f"{route.name}_{route.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}",
    )

    # Configure logging
    _configure_logging(app, environment)

    # Add middleware
    _configure_middleware(app, environment, config)

    # Register exception handlers
    _configure_exception_handlers(app)

    # Register routers (done separately in main_crownsafe.py)
    # This keeps router registration visible and easy to modify

    logger.info(f"✅ FastAPI application created for {environment} environment")

    return app


def _configure_logging(app: FastAPI, environment: str) -> None:
    """Configure application logging"""
    log_level = "INFO" if environment == "production" else "DEBUG"

    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    logger.info(f"Logging configured: level={log_level}")


def _configure_middleware(app: FastAPI, environment: str, config: Optional[object]) -> None:
    """Configure all application middleware"""

    # 1. Security headers and rate limiting
    configure_security_middleware(app, environment=environment)

    # 2. CORS - configure based on environment
    if environment == "production":
        # Production: Strict CORS
        allowed_origins = [
            "https://babyshield.cureviax.ai",
            "https://www.babyshield.com",
            "https://app.babyshield.com",
        ]
    else:
        # Development: Allow localhost
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8001",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    )
    logger.info(f"✅ CORS configured: {len(allowed_origins)} allowed origins")

    # 3. GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    logger.info("✅ GZip compression enabled")

    # 4. Trusted host (production only)
    if environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "babyshield.cureviax.ai",
                "www.babyshield.com",
                "api.babyshield.com",
            ],
        )
        logger.info("✅ Trusted host middleware enabled")

    # 5. Add structured logging middleware if available
    try:
        from utils.logging.middleware import LoggingMiddleware

        app.add_middleware(LoggingMiddleware)
        logger.info("✅ Structured logging middleware added")
    except ImportError:
        logger.warning("Structured logging middleware not available")

    # 6. Add Prometheus metrics middleware if available
    try:
        from prometheus_client import make_asgi_app

        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
        logger.info("✅ Prometheus metrics endpoint mounted at /metrics")
    except ImportError:
        logger.warning("Prometheus metrics not available")


def _configure_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers"""

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        """Handle ValueError exceptions"""
        logger.warning(f"ValueError: {str(exc)}")
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": str(exc), "type": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Handle unexpected exceptions"""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

        # Don't expose internal errors in production
        if os.getenv("ENVIRONMENT", "development") == "production":
            error_msg = "An internal error occurred"
        else:
            error_msg = str(exc)

        return JSONResponse(
            status_code=500,
            content={"success": False, "error": error_msg, "type": "internal_error"},
        )

    logger.info("✅ Exception handlers registered")


def register_routers(app: FastAPI) -> None:
    """
    Register all API routers

    This function is called from main_crownsafe.py to keep router
    registration visible and easy to modify
    """
    logger.info("🔧 Registering API routers...")

    # Import and register routers
    # (This is done in main_crownsafe.py for visibility)

    pass


def configure_startup_events(app: FastAPI) -> None:
    """Configure application startup events"""

    @app.on_event("startup")
    async def startup_event():
        """Run on application startup"""
        logger.info("🚀 BabyShield API starting up...")

        # Initialize database connection pool
        try:
            from core_infra.database import engine

            # Test database connection
            with engine.connect() as _:
                logger.info("✅ Database connection established")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")

        # Warm up cache
        try:
            from core_infra.smart_cache_warmer import warm_cache_now

            warm_cache_now()
            logger.info("✅ Cache warmed")
        except Exception as e:
            logger.warning(f"Cache warming skipped: {e}")

        logger.info("✅ Application startup complete")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Run on application shutdown"""
        logger.info("🛑 BabyShield API shutting down...")

        # Close database connections
        try:
            from core_infra.database import engine

            engine.dispose()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")

        logger.info("✅ Application shutdown complete")


def create_openapi_schema(app: FastAPI) -> dict:
    """
    Create custom OpenAPI schema with fixes

    Returns:
        OpenAPI schema dictionary
    """
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    # Add error response schema
    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "success": {"type": "boolean", "example": False},
            "error": {"type": "string", "example": "Error message"},
            "timestamp": {"type": "string", "format": "date-time"},
            "trace_id": {"type": "string", "example": "abc123"},
        },
        "required": ["success", "error"],
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema
