"""
Example of how to integrate observability into main_crownsafe.py
This shows the minimal changes needed to add all Task 4 features
"""

# ============================================================================
# ADD THESE IMPORTS TO YOUR main_crownsafe.py
# ============================================================================

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Observability imports
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
from prometheus_fastapi_instrumentator import Instrumentator

# ============================================================================
# LIFESPAN MANAGER (replaces @app.on_event decorators)
# ============================================================================


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Starting up...")

    # Initialize rate limiter
    rate_limit_enabled = await init_rate_limiter()
    if rate_limit_enabled:
        logger.info("✅ Rate limiting enabled")
    else:
        logger.warning("⚠️ Rate limiting disabled - Redis not available")

    yield

    # Shutdown
    import logging

    logger = logging.getLogger(__name__)
    logger.info("Shutting down...")
    await close_rate_limiter()
    logger.info("✅ Cleanup completed")


# ============================================================================
# CREATE APP WITH OBSERVABILITY
# ============================================================================


def create_app_with_observability() -> FastAPI:
    """
    Create FastAPI app with all observability features
    """

    # 1. Setup JSON logging FIRST
    setup_json_logging(os.getenv("LOG_LEVEL", "INFO"))

    # 2. Create app with lifespan
    app = FastAPI(title="BabyShield API", version="1.2.0", lifespan=app_lifespan)

    # 3. Add middleware (order matters!)
    # Correlation ID middleware
    app.add_middleware(
        CorrelationIdMiddleware, api_version=os.getenv("API_VERSION", "v1.2.0")
    )

    # Access logging middleware
    app.add_middleware(AccessLogMiddleware)

    # 4. Add error handlers
    app.add_exception_handler(
        RequestValidationError, errors.handle_request_validation_error
    )
    app.add_exception_handler(StarletteHTTPException, errors.handle_http_exception)
    app.add_exception_handler(Exception, errors.handle_generic_exception)

    # Rate limit error handler
    from fastapi_limiter import RateLimitExceeded

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # 5. Add Prometheus metrics
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(
        app, endpoint="/metrics", include_in_schema=False
    )

    # 6. Add system routes
    app.include_router(system.router, tags=["system"])

    return app


# ============================================================================
# EXAMPLE: ADD RATE LIMITING TO EXISTING ROUTES
# ============================================================================

# Instead of:
# @app.post("/api/v1/search/advanced")
# async def search_advanced(req: AdvancedSearchRequest):
#     ...

# Use:
# @app.post(
#     "/api/v1/search/advanced",
#     dependencies=[Depends(RateLimiters.search)]  # <-- Add this
# )
# async def search_advanced(req: AdvancedSearchRequest):
#     ...

# ============================================================================
# MINIMAL INTEGRATION FOR EXISTING main_crownsafe.py
# ============================================================================

"""
If you can't refactor the entire file, add this at the top of main_crownsafe.py:

# At the very top, before creating the app
from api.logging_setup import setup_json_logging
setup_json_logging("INFO")

# After creating the app
from api.observability_integration import setup_observability

# Right after: app = FastAPI(...)
setup_observability(app)

# Add lifespan events
@app.on_event("startup")
async def startup():
    from api.rate_limiting import init_rate_limiter
    await init_rate_limiter()

@app.on_event("shutdown") 
async def shutdown():
    from api.rate_limiting import close_rate_limiter
    await close_rate_limiter()

# For specific routes that need rate limiting:
from api.rate_limiting import RateLimiters
from fastapi import Depends

# Update your search endpoint:
@app.post(
    "/api/v1/search/advanced",
    dependencies=[Depends(RateLimiters.search)]
)
async def search_advanced(...):
    # Your existing code
    pass
"""

# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Create app with observability
    app = create_app_with_observability()

    # Add a test route
    @app.get("/test")
    async def test_endpoint():
        return {"message": "Observability is working!", "ok": True}

    # Run with uvicorn
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
