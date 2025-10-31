"""
Security middleware for BabyShield
Adds security headers and protections
"""

import secrets
from typing import Callable

from fastapi import Request
from fastapi.responses import Response


class SecurityHeadersMiddleware:
    """
    Add security headers to all responses
    """

    def __init__(self, app, strict_mode: bool = True):
        self.app = app
        self.strict_mode = strict_mode

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Generate nonce for CSP
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce

        # Process request
        response = await call_next(request)

        # Add security headers

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS (only in production)
        if self.strict_mode:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            "style-src 'self' 'unsafe-inline'",  # Allow inline styles for now
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        permissions = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions)

        # Custom security headers
        response.headers["X-Powered-By"] = "BabyShield"  # Hide framework info

        return response


class CORSSecurityMiddleware:
    """
    Secure CORS configuration
    """

    def __init__(self, app, allowed_origins: list = None):
        self.app = app
        self.allowed_origins = allowed_origins or ["https://app.babyshield.com"]

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Get origin
        origin = request.headers.get("origin")

        # Check if origin is allowed
        if origin in self.allowed_origins:
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Max-Age"] = "3600"
        else:
            response = await call_next(request)

        return response


def add_security_headers(app):
    """
    Add all security middleware to app
    """
    import os

    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    # Add trusted host middleware
    allowed_hosts = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # Add security headers
    strict_mode = os.getenv("ENVIRONMENT", "development") == "production"
    app.add_middleware(SecurityHeadersMiddleware, strict_mode=strict_mode)

    # Add secure CORS
    allowed_origins = (
        os.getenv("ALLOWED_ORIGINS", "").split(",")
        if os.getenv("ALLOWED_ORIGINS")
        else [
            "https://app.babyshield.com",
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    )
    app.add_middleware(CORSSecurityMiddleware, allowed_origins=allowed_origins)
