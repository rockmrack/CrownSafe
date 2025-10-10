"""
Security Headers Middleware
Implements OWASP recommended security headers
"""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)
logger.info("📦 utils.security.security_headers module loaded!")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds comprehensive security headers to all responses

    Implements OWASP Top 10 security best practices:
    - Content Security Policy (CSP)
    - X-Frame-Options (Clickjacking protection)
    - X-Content-Type-Options (MIME sniffing protection)
    - Strict-Transport-Security (HTTPS enforcement)
    - X-XSS-Protection (XSS filter)
    - Referrer-Policy (Privacy)
    - Permissions-Policy (Feature restrictions)
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        csp_policy: str = None,
        enable_frame_options: bool = True,
        enable_xss_protection: bool = True,
    ):
        try:
            logger.info("🔧 SecurityHeadersMiddleware __init__ called!")
            logger.info(
                f"  enable_hsts={enable_hsts}, enable_csp={enable_csp}, enable_frame_options={enable_frame_options}"
            )
            super().__init__(app)
            self.enable_hsts = enable_hsts
            self.hsts_max_age = hsts_max_age
            self.enable_csp = enable_csp
            self.csp_policy = csp_policy or self._default_csp_policy()
            self.enable_frame_options = enable_frame_options
            self.enable_xss_protection = enable_xss_protection
            logger.info("✅ SecurityHeadersMiddleware __init__ completed!")
        except Exception as e:
            logger.error(f"❌ SecurityHeadersMiddleware __init__ FAILED: {e}")
            import traceback

            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def _default_csp_policy() -> str:
        """
        Default Content Security Policy

        This is a strict policy that prevents most XSS attacks.
        Adjust based on your frontend requirements.
        """
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https://api.babyshield.cureviax.ai; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 SecurityHeadersMiddleware EXECUTING for: {request.url.path}")

        response = await call_next(request)

        logger.info("🔍 Response received, adding security headers...")

        # 1. Content-Security-Policy (CSP)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = self.csp_policy
            logger.info("✅ Added Content-Security-Policy")

        # 2. X-Frame-Options (Clickjacking protection)
        if self.enable_frame_options:
            response.headers["X-Frame-Options"] = "DENY"

        # 3. X-Content-Type-Options (MIME sniffing protection)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 4. Strict-Transport-Security (HSTS)
        if self.enable_hsts:
            response.headers[
                "Strict-Transport-Security"
            ] = f"max-age={self.hsts_max_age}; includeSubDomains; preload"

        # 5. X-XSS-Protection (legacy, but still useful for older browsers)
        if self.enable_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        # 6. Referrer-Policy (privacy)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 7. Permissions-Policy (feature restrictions)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), " "microphone=(), " "camera=(), " "payment=(), " "usb=()"
        )

        # 8. X-Permitted-Cross-Domain-Policies (Adobe products)
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # 9. Cache-Control for sensitive endpoints
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/user")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        # 10. Remove server header (security through obscurity)
        if "Server" in response.headers:
            del response.headers["Server"]

        logger.info(
            f"✅ SecurityHeadersMiddleware completed. Total headers in response: {len(response.headers)}"
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware

    For production, use Redis-based rate limiting (slowapi, aiolimiter, etc.)
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10,
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._request_counts: dict = {}  # {ip: [timestamp1, timestamp2, ...]}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit before processing request"""
        import time

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Clean old entries (older than 1 minute)
        current_time = time.time()
        if client_ip in self._request_counts:
            self._request_counts[client_ip] = [
                ts for ts in self._request_counts[client_ip] if current_time - ts < 60
            ]
        else:
            self._request_counts[client_ip] = []

        # Check rate limit
        request_count = len(self._request_counts[client_ip])
        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Add current request timestamp
        self._request_counts[client_ip].append(current_time)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self._request_counts[client_ip])
        )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks"""

    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size before processing"""
        content_length = request.headers.get("content-length")

        if content_length:
            try:
                size = int(content_length)
                if size > self.max_body_size:
                    logger.warning(f"Request too large: {size} bytes (max {self.max_body_size})")
                    return Response(
                        content=f"Request body too large (max {self.max_body_size} bytes)",
                        status_code=413,
                    )
            except ValueError:
                pass  # Invalid Content-Length, let it through to be rejected later

        return await call_next(request)


def configure_security_middleware(app, environment: str = "production"):
    """
    Configure all security middleware for the application

    Args:
        app: FastAPI application instance
        environment: Application environment (development, staging, production)
    """
    # Determine security settings based on environment
    is_production = environment == "production"

    # 1. Request size limiting (always enabled)
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)  # 10MB

    # 2. Security headers (stricter in production)
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=is_production,  # Only enable HSTS in production
        hsts_max_age=31536000,
        enable_csp=True,
        enable_frame_options=True,
        enable_xss_protection=True,
    )

    # 3. Rate limiting (more lenient in development)
    if is_production:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
            burst_size=10,
        )
    else:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=120,  # More lenient for development
            burst_size=20,
        )

    logger.info(f"✅ Security middleware configured for {environment} environment")
