"""
Task 16: Security Middleware for BabyShield API
Implements IP allowlisting, security headers, and request validation
"""

import os
import time
import logging
import ipaddress
import hashlib
import hmac
from typing import Optional, List, Set, Callable
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import secrets

logger = logging.getLogger(__name__)

# ========================= IP ALLOWLIST MIDDLEWARE =========================


class IPAllowlistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict admin endpoints to specific IP addresses
    """

    def __init__(
        self, app, admin_paths: List[str] = None, allowed_ips: List[str] = None
    ):
        super().__init__(app)
        self.admin_paths = admin_paths or [
            "/admin",
            "/api/v1/admin",
            "/monitoring",
            "/metrics",
            "/api/v1/monitoring",
        ]

        # Get allowed IPs from environment or use defaults
        env_ips = os.environ.get("ADMIN_ALLOWED_IPS", "").split(",")
        self.allowed_ips = allowed_ips or env_ips or []

        # Parse IP networks
        self.allowed_networks = self._parse_ip_networks(self.allowed_ips)

        logger.info(f"IP Allowlist configured for paths: {self.admin_paths}")
        logger.info(f"Allowed IPs/Networks: {self.allowed_ips}")

    def _parse_ip_networks(self, ip_list: List[str]) -> Set[ipaddress.IPv4Network]:
        """Parse IP addresses and CIDR ranges"""
        networks = set()

        for ip_str in ip_list:
            ip_str = ip_str.strip()
            if not ip_str:
                continue

            try:
                # Try to parse as network (handles both IPs and CIDR)
                network = ipaddress.ip_network(ip_str, strict=False)
                networks.add(network)
            except ValueError as e:
                logger.warning(f"Invalid IP/Network: {ip_str} - {e}")

        return networks

    def _is_admin_path(self, path: str) -> bool:
        """Check if the path is an admin endpoint"""
        path_lower = path.lower()
        return any(
            path_lower.startswith(admin_path.lower()) for admin_path in self.admin_paths
        )

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Check if the client IP is in the allowlist"""

        # If no allowlist configured, deny all (secure by default)
        if not self.allowed_networks:
            return False

        # Allow localhost in development
        if client_ip in ["127.0.0.1", "::1", "localhost"]:
            env = os.environ.get("ENVIRONMENT", "production")
            if env in ["development", "local", "test"]:
                return True

        try:
            ip_addr = ipaddress.ip_address(client_ip)

            # Check if IP is in any allowed network
            for network in self.allowed_networks:
                if ip_addr in network:
                    return True
        except ValueError:
            logger.warning(f"Invalid client IP format: {client_ip}")

        return False

    def _get_real_ip(self, request: Request) -> str:
        """Get the real client IP, considering proxies"""

        # Check X-Forwarded-For header (from load balancer/proxy)
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first
            client_ip = x_forwarded_for.split(",")[0].strip()
        # Check X-Real-IP header
        elif request.headers.get("X-Real-IP"):
            client_ip = request.headers.get("X-Real-IP")
        # Fallback to direct client
        else:
            client_ip = request.client.host

        return client_ip

    async def dispatch(self, request: Request, call_next):
        """Process the request"""

        # Check if this is an admin path
        if self._is_admin_path(request.url.path):
            client_ip = self._get_real_ip(request)

            # Check IP allowlist
            if not self._is_ip_allowed(client_ip):
                logger.warning(
                    f"Blocked admin access from IP: {client_ip} to path: {request.url.path}"
                )

                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Access denied",
                        "message": "Your IP address is not authorized to access this resource",
                    },
                )

            logger.info(
                f"Allowed admin access from IP: {client_ip} to path: {request.url.path}"
            )

        # Process the request
        response = await call_next(request)
        return response


# ========================= SECURITY HEADERS MIDDLEWARE =========================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""

        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers[
            "Permissions-Policy"
        ] = "geolocation=(), microphone=(), camera=()"

        # HSTS (only in production with HTTPS)
        if os.environ.get("ENVIRONMENT") == "production":
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains; preload"

        # CSP (Content Security Policy)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        return response


# ========================= REQUEST VALIDATION MIDDLEWARE =========================


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate and sanitize incoming requests
    """

    def __init__(self, app, max_body_size: int = 10485760):  # 10MB default
        super().__init__(app)
        self.max_body_size = max_body_size
        self.blocked_patterns = [
            # SQL injection patterns
            "union select",
            "drop table",
            "insert into",
            "delete from",
            "update set",
            "exec(",
            "execute(",
            # Path traversal
            "../",
            "..\\",
            # Command injection
            "; cat ",
            "&& cat ",
            "| cat ",
            "`cat ",
            # XXE
            "<!DOCTYPE",
            "<!ENTITY",
            # Script injection
            "<script",
            "javascript:",
            "onerror=",
            "onclick=",
        ]

    def _contains_malicious_pattern(self, text: str) -> bool:
        """Check if text contains malicious patterns"""
        if not text:
            return False

        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.blocked_patterns)

    async def dispatch(self, request: Request, call_next):
        """Validate request"""

        # Check Content-Length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            logger.warning(f"Request body too large: {content_length} bytes")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "Request body too large"},
            )

        # Check URL for malicious patterns
        if self._contains_malicious_pattern(str(request.url)):
            logger.warning(f"Malicious URL pattern detected: {request.url}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid request"},
            )

        # Check headers for malicious patterns
        for header_name, header_value in request.headers.items():
            if self._contains_malicious_pattern(header_value):
                logger.warning(f"Malicious header pattern detected: {header_name}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid request headers"},
                )

        # Process request
        response = await call_next(request)
        return response


# ========================= API KEY AUTHENTICATION =========================


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication on specific endpoints
    """

    def __init__(self, app, protected_paths: List[str] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/v1/admin"]

        # Get API keys from environment
        self.valid_api_keys = set()
        api_keys_str = os.environ.get("API_KEYS", "")
        if api_keys_str:
            self.valid_api_keys = {k.strip() for k in api_keys_str.split(",")}

        # Generate a default key if none configured (development only)
        if not self.valid_api_keys and os.environ.get("ENVIRONMENT") == "development":
            default_key = secrets.token_urlsafe(32)
            self.valid_api_keys.add(default_key)
            logger.warning(
                f"No API keys configured. Generated development key: {default_key}"
            )

    def _requires_api_key(self, path: str) -> bool:
        """Check if path requires API key"""
        return any(path.startswith(p) for p in self.protected_paths)

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key using constant-time comparison"""
        if not api_key or not self.valid_api_keys:
            return False

        # Use constant-time comparison to prevent timing attacks
        for valid_key in self.valid_api_keys:
            if secrets.compare_digest(api_key, valid_key):
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        """Check API key if required"""

        if self._requires_api_key(request.url.path):
            # Check for API key in header
            api_key = request.headers.get("X-API-Key")

            # Also check query parameter as fallback
            if not api_key:
                api_key = request.query_params.get("api_key")

            if not self._validate_api_key(api_key):
                logger.warning(f"Invalid API key attempt for path: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "Unauthorized",
                        "message": "Invalid or missing API key",
                    },
                    headers={"WWW-Authenticate": "ApiKey"},
                )

        response = await call_next(request)
        return response


# ========================= HMAC REQUEST SIGNING =========================


class HMACMiddleware(BaseHTTPMiddleware):
    """
    Middleware for HMAC request signing validation
    """

    def __init__(self, app, protected_paths: List[str] = None):
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/v1/webhook"]
        self.secret = os.environ.get("HMAC_SECRET", secrets.token_bytes(32))
        self.time_window = 300  # 5 minutes

    def _requires_hmac(self, path: str) -> bool:
        """Check if path requires HMAC"""
        return any(path.startswith(p) for p in self.protected_paths)

    def _validate_hmac(
        self, request_body: bytes, signature: str, timestamp: str
    ) -> bool:
        """Validate HMAC signature"""

        # Check timestamp to prevent replay attacks
        try:
            req_timestamp = int(timestamp)
            current_timestamp = int(time.time())

            if abs(current_timestamp - req_timestamp) > self.time_window:
                logger.warning("HMAC timestamp outside allowed window")
                return False
        except (ValueError, TypeError):
            logger.warning("Invalid HMAC timestamp")
            return False

        # Calculate expected signature
        message = f"{timestamp}.{request_body.decode('utf-8')}"
        expected_sig = hmac.new(
            self.secret if isinstance(self.secret, bytes) else self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison
        return secrets.compare_digest(signature, expected_sig)

    async def dispatch(self, request: Request, call_next):
        """Validate HMAC if required"""

        if self._requires_hmac(request.url.path):
            # Get signature and timestamp from headers
            signature = request.headers.get("X-Signature")
            timestamp = request.headers.get("X-Timestamp")

            if not signature or not timestamp:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Missing signature or timestamp"},
                )

            # Read request body
            body = await request.body()

            # Validate HMAC
            if not self._validate_hmac(body, signature, timestamp):
                logger.warning(f"Invalid HMAC signature for path: {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Invalid signature"},
                )

        response = await call_next(request)
        return response


# ========================= CORS SECURITY =========================


def get_cors_middleware_config():
    """
    Get CORS configuration for FastAPI CORSMiddleware
    """

    # Get allowed origins from environment
    allowed_origins_str = os.environ.get("CORS_ALLOWED_ORIGINS", "")

    if allowed_origins_str:
        allowed_origins = [o.strip() for o in allowed_origins_str.split(",")]
    else:
        # Default for development
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://babyshield.cureviax.ai",
        ]

    return {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["X-Total-Count", "X-Page", "X-Per-Page"],
        "max_age": 3600,
    }


# ========================= USAGE EXAMPLE =========================

"""
# In your main FastAPI application (api/main_babyshield.py):

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.security_middleware import (
    IPAllowlistMiddleware,
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    APIKeyMiddleware,
    get_cors_middleware_config
)

app = FastAPI()

# Add security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestValidationMiddleware, max_body_size=10485760)

# Add IP allowlist for admin endpoints
app.add_middleware(
    IPAllowlistMiddleware,
    admin_paths=["/admin", "/api/v1/admin", "/monitoring"],
    allowed_ips=["192.168.1.0/24", "10.0.0.0/8", "203.0.113.45"]
)

# Add API key middleware
app.add_middleware(
    APIKeyMiddleware,
    protected_paths=["/api/v1/admin", "/api/v1/internal"]
)

# Add CORS middleware
cors_config = get_cors_middleware_config()
app.add_middleware(CORSMiddleware, **cors_config)
"""
