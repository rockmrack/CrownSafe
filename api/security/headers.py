"""
Security headers configuration
Adds comprehensive security headers to all responses
"""

import logging
from typing import Optional, Dict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(
        self,
        app,
        hsts_max_age: int = 63072000,  # 2 years
        include_subdomains: bool = True,
        preload: bool = True,
        frame_options: str = "DENY",
        content_type_options: str = "nosniff",
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[str] = None,
        cross_origin_opener_policy: str = "same-origin",
        cross_origin_embedder_policy: str = "require-corp",
        cross_origin_resource_policy: str = "cross-origin",
        content_security_policy: Optional[str] = None
    ):
        """
        Initialize security headers middleware
        
        Args:
            app: ASGI application
            hsts_max_age: HSTS max age in seconds
            include_subdomains: Include subdomains in HSTS
            preload: Enable HSTS preload
            frame_options: X-Frame-Options value
            content_type_options: X-Content-Type-Options value
            xss_protection: X-XSS-Protection value
            referrer_policy: Referrer-Policy value
            permissions_policy: Permissions-Policy value
            cross_origin_opener_policy: Cross-Origin-Opener-Policy value
            cross_origin_embedder_policy: Cross-Origin-Embedder-Policy value
            cross_origin_resource_policy: Cross-Origin-Resource-Policy value
            content_security_policy: Content-Security-Policy value (for HTML responses)
        """
        super().__init__(app)
        
        # Build HSTS header
        hsts_parts = [f"max-age={hsts_max_age}"]
        if include_subdomains:
            hsts_parts.append("includeSubDomains")
        if preload:
            hsts_parts.append("preload")
        self.hsts_header = "; ".join(hsts_parts)
        
        # Store other headers
        self.frame_options = frame_options
        self.content_type_options = content_type_options
        self.xss_protection = xss_protection
        self.referrer_policy = referrer_policy
        
        # Default permissions policy (restrictive)
        self.permissions_policy = permissions_policy or (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(), "
            "cross-origin-isolated=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "execution-while-not-rendered=(), "
            "execution-while-out-of-viewport=(), "
            "fullscreen=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "keyboard-map=(), "
            "magnetometer=(), "
            "microphone=(), "
            "midi=(), "
            "navigation-override=(), "
            "payment=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(), "
            "screen-wake-lock=(), "
            "sync-xhr=(), "
            "usb=(), "
            "web-share=(), "
            "xr-spatial-tracking=()"
        )
        
        self.cross_origin_opener_policy = cross_origin_opener_policy
        self.cross_origin_embedder_policy = cross_origin_embedder_policy
        self.cross_origin_resource_policy = cross_origin_resource_policy
        self.content_security_policy = content_security_policy
        
        logger.info("Security headers middleware configured")
    
    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to response
        """
        response = await call_next(request)
        
        # Apply security headers
        # These use setdefault to not override if already set
        
        # HSTS - Force HTTPS
        response.headers.setdefault(
            "Strict-Transport-Security",
            self.hsts_header
        )
        
        # Prevent MIME type sniffing
        response.headers.setdefault(
            "X-Content-Type-Options",
            self.content_type_options
        )
        
        # Prevent clickjacking
        response.headers.setdefault(
            "X-Frame-Options",
            self.frame_options
        )
        
        # XSS protection (legacy but still useful)
        response.headers.setdefault(
            "X-XSS-Protection",
            self.xss_protection
        )
        
        # Control referrer information
        response.headers.setdefault(
            "Referrer-Policy",
            self.referrer_policy
        )
        
        # Permissions policy (Feature policy replacement)
        response.headers.setdefault(
            "Permissions-Policy",
            self.permissions_policy
        )
        
        # Cross-origin policies
        response.headers.setdefault(
            "Cross-Origin-Opener-Policy",
            self.cross_origin_opener_policy
        )
        
        # For API responses, we typically don't need COEP
        # But include for completeness
        if self.cross_origin_embedder_policy:
            response.headers.setdefault(
                "Cross-Origin-Embedder-Policy",
                self.cross_origin_embedder_policy
            )
        
        response.headers.setdefault(
            "Cross-Origin-Resource-Policy",
            self.cross_origin_resource_policy
        )
        
        # CSP only for HTML responses
        # Skip for JSON API responses to avoid console warnings
        content_type = response.headers.get("content-type", "").lower()
        if self.content_security_policy and "text/html" in content_type:
            response.headers.setdefault(
                "Content-Security-Policy",
                self.content_security_policy
            )
        
        # Additional security headers for APIs
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        
        # Cache control for sensitive endpoints
        if "/api/v1/auth" in request.url.path or "/api/v1/user" in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response


def get_security_headers_dict() -> Dict[str, str]:
    """
    Get dictionary of security headers for manual application
    
    Returns:
        Dictionary of header names and values
    """
    return {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), "
            "gyroscope=(), accelerometer=()"
        ),
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "cross-origin",
        "X-Permitted-Cross-Domain-Policies": "none"
    }


def apply_security_headers(response: Response) -> Response:
    """
    Apply security headers to a response object
    
    Args:
        response: Response object
        
    Returns:
        Response with security headers
    """
    headers = get_security_headers_dict()
    for name, value in headers.items():
        response.headers.setdefault(name, value)
    return response


# Export
__all__ = [
    "SecurityHeadersMiddleware",
    "get_security_headers_dict",
    "apply_security_headers"
]
