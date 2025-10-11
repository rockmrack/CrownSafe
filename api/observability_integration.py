"""
Observability Integration Module
Wires all observability features into the FastAPI app
"""

import os
import logging
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi_limiter.depends import RateLimiter
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_fastapi_instrumentator import Instrumentator

# Import our modules
from api.middleware import CorrelationIdMiddleware, AccessLogMiddleware
from api.logging_setup import setup_json_logging
from api import errors
from api.rate_limiting import (
    init_rate_limiter,
    close_rate_limiter,
    rate_limit_exceeded_handler,
    RateLimiters,
)
from api.routes import system

logger = logging.getLogger("app")


def setup_observability(app: FastAPI):
    """
    Configure all observability features for the FastAPI app

    This should be called BEFORE adding routes to ensure proper middleware order

    Args:
        app: FastAPI application instance
    """

    # 1. Setup JSON logging (do this first)
    log_level = os.getenv("LOG_LEVEL", "INFO")
    setup_json_logging(log_level)
    logger.info("Observability setup starting")

    # 2. Add middleware (order matters - correlation should be early)
    # Correlation ID middleware (adds trace IDs to requests)
    api_version = os.getenv("API_VERSION", "v1.2.0")
    app.add_middleware(CorrelationIdMiddleware, api_version=api_version)
    logger.info("Correlation ID middleware added")

    # Access logging middleware (logs all requests)
    app.add_middleware(AccessLogMiddleware)
    logger.info("Access log middleware added")

    # 3. Add exception handlers for unified error responses
    app.add_exception_handler(RequestValidationError, errors.handle_request_validation_error)
    app.add_exception_handler(StarletteHTTPException, errors.handle_http_exception)
    app.add_exception_handler(Exception, errors.handle_generic_exception)
    logger.info("Error handlers configured")

    # 4. Setup Prometheus metrics
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/api/v1/healthz", "/api/v1/readyz"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False, tags=["monitoring"])
    logger.info("Prometheus metrics configured at /metrics")

    # 5. Add system routes
    app.include_router(system.router, tags=["system"])
    logger.info("System routes added")

    # 6. Setup rate limiting handlers
    from fastapi_limiter import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limit handler configured")

    logger.info("Observability setup completed")


async def on_startup(app: FastAPI):
    """
    Startup event handler for async initialization
    """
    # Initialize rate limiter
    rate_limit_enabled = await init_rate_limiter()
    if rate_limit_enabled:
        logger.info("Rate limiting enabled")
    else:
        logger.warning("Rate limiting disabled - Redis not available")


async def on_shutdown(app: FastAPI):
    """
    Shutdown event handler for cleanup
    """
    # Close rate limiter
    await close_rate_limiter()
    logger.info("Cleanup completed")


def add_rate_limited_routes(app: FastAPI):
    """
    Example of adding rate limits to specific routes
    This should be called AFTER routes are defined
    """

    # Import here to avoid circular imports
    from fastapi import APIRouter

    # Example: Add rate limiting to search endpoint
    @app.post(
        "/api/v1/search/advanced",
        dependencies=[Depends(RateLimiters.search)],
        tags=["search"],
    )
    async def search_advanced_rate_limited():
        # This is a wrapper - actual implementation should be in the route
        pass

    # Example: Add rate limiting to recall detail
    @app.get(
        "/api/v1/recall/{recall_id}",
        dependencies=[Depends(RateLimiters.detail)],
        tags=["recalls"],
    )
    async def get_recall_rate_limited(recall_id: str):
        # This is a wrapper - actual implementation should be in the route
        pass


# Example integration code for main.py
INTEGRATION_EXAMPLE = """
# Add this to your main_babyshield.py or app factory:

from api.observability_integration import setup_observability, on_startup, on_shutdown

# Setup observability BEFORE adding routes
setup_observability(app)

# Add startup/shutdown events
@app.on_event("startup")
async def startup_event():
    await on_startup(app)

@app.on_event("shutdown")
async def shutdown_event():
    await on_shutdown(app)

# For rate limiting specific routes, use dependencies:
from api.rate_limiting import RateLimiters
from fastapi import Depends

@app.post(
    "/api/v1/search/advanced",
    dependencies=[Depends(RateLimiters.search)]
)
async def search_advanced(...):
    # Your existing implementation
    pass
"""
