"""Correlation ID Middleware for request tracking
Ensures every request has a unique trace ID for debugging and monitoring
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to all requests and responses
    """

    def __init__(self, app: ASGIApp, api_version: str = "v1.2.0") -> None:
        super().__init__(app)
        self.api_version = api_version

    async def dispatch(self, request: Request, call_next):
        """Process request with correlation ID
        """
        # Get or generate correlation ID
        correlation_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Trace-ID")
            or f"trace_{uuid.uuid4().hex[:16]}_{int(time.time())}"
        )

        # Store in request state for use in handlers
        request.state.trace_id = correlation_id
        request.state.correlation_id = correlation_id

        # Track request timing
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Add correlation headers to response
        response.headers["X-Request-ID"] = correlation_id
        response.headers["X-Correlation-ID"] = correlation_id
        # Get once per process, then reuse
        v = getattr(request.app.state, "_openapi_version", None)
        if not v:
            try:
                v = request.app.openapi().get("info", {}).get("version", "unknown")
            except Exception:
                v = "unknown"
            request.app.state._openapi_version = v

        response.headers["X-API-Version"] = v
        response.headers["Server-Timing"] = f"app;dur={duration_ms}"

        # Add security headers (only if not already set)
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")

        # Add performance headers
        response.headers["X-Response-Time"] = f"{duration_ms}ms"

        return response
