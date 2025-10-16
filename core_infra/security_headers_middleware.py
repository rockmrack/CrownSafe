"""
Security Headers Middleware for App Store Readiness
Adds security headers to all API responses
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

API_VERSION = "1.2.0"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to response
        """
        response = await call_next(request)

        # Security headers
        # Resolve API version from the OpenAPI spec once, then reuse
        v = getattr(request.app.state, "_openapi_version", None)
        if not v:
            try:
                v = request.app.openapi().get("info", {}).get("version", "unknown")
            except Exception:
                v = "unknown"
            request.app.state._openapi_version = v

        response.headers["X-API-Version"] = v
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # HSTS (only for production)
        response.headers[
            "Strict-Transport-Security"
        ] = "max-age=63072000; includeSubDomains; preload"

        # Cache control for security
        if request.url.path.startswith("/api/"):
            response.headers[
                "Cache-Control"
            ] = "no-store, no-cache, must-revalidate, private"

        return response


class EnhancedCORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware for mobile app support
    """

    def __init__(self, app, allowed_origins=None, allow_credentials=True):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.allow_credentials = allow_credentials

    async def dispatch(self, request: Request, call_next):
        """
        Handle CORS headers
        """
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=204)
            origin = request.headers.get("origin", "*")

            # Set CORS headers
            if origin in self.allowed_origins or "*" in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = (
                    origin if origin != "*" else "*"
                )
            else:
                response.headers["Access-Control-Allow-Origin"] = self.allowed_origins[
                    0
                ]

            response.headers[
                "Access-Control-Allow-Methods"
            ] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers[
                "Access-Control-Allow-Headers"
            ] = "Content-Type, Authorization, X-API-Key"
            response.headers["Access-Control-Max-Age"] = "86400"

            if self.allow_credentials and origin != "*":
                response.headers["Access-Control-Allow-Credentials"] = "true"

            return response

        # Regular request
        response = await call_next(request)

        # Add CORS headers to response
        origin = request.headers.get("origin", "*")
        if origin in self.allowed_origins or "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = (
                origin if origin != "*" else "*"
            )
        else:
            response.headers["Access-Control-Allow-Origin"] = self.allowed_origins[0]

        if self.allow_credentials and origin != "*":
            response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers[
            "Access-Control-Expose-Headers"
        ] = "X-API-Version, X-Total-Count"

        return response
