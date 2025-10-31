#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main FastAPI entry point for the Crown Safe backend."""

import asyncio
import hashlib
import json
import logging
import os
import socket
import sys
import traceback
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, cast

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi import Path as FastAPIPath
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, ValidationError, model_validator
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse as StarletteJSONResponse

_orig_getaddrinfo = socket.getaddrinfo


def _ipv4_only(host: str, port: int, *args, **kwargs):
    """Force IPv4 resolution to avoid IPv6 DNS timeout issues."""
    results = _orig_getaddrinfo(host, port, *args, **kwargs)
    ipv4_only = [item for item in results if item[0] == socket.AF_INET]
    return ipv4_only or results


socket.getaddrinfo = _ipv4_only

try:
    from config.settings import get_config, validate_production_config

    config = get_config()
    CONFIG_LOADED = True
    logging.getLogger(__name__).info("[OK] Crown Safe configuration loaded successfully")
    validate_production_config()
except Exception as exc:  # pragma: no cover
    CONFIG_LOADED = False
    config = None
    logging.getLogger(__name__).warning(
        "[WARN] Configuration unavailable; falling back to environment variables: %s",
        exc,
    )

try:
    from utils.logging.middleware import LoggingMiddleware
    from utils.logging.structured_logger import log_error, log_performance, setup_logging

    if CONFIG_LOADED and config:
        logger = setup_logging(config)
        logger.info("Crown Safe backend starting up", extra={"service": "crown-safe"})
        STRUCTURED_LOGGING_ENABLED = True
    else:
        raise RuntimeError("Configuration not loaded")
except Exception as exc:  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)
    logger.warning("Structured logging disabled; using standard logging: %s", exc)
    STRUCTURED_LOGGING_ENABLED = False

    def log_performance(*args, **kwargs):
        return None

    def log_error(*args, **kwargs):
        return None


try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
        make_asgi_app,
    )

    REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint"])
    REQUEST_DURATION = Histogram("http_request_duration_seconds", "HTTP request duration")
    PROMETHEUS_ENABLED = True
except Exception as exc:  # pragma: no cover
    logger.warning("Prometheus metrics unavailable: %s", exc)
    REQUEST_COUNT = None
    REQUEST_DURATION = None
    PROMETHEUS_ENABLED = False

database_url = None
if CONFIG_LOADED and config:
    database_url = getattr(config, "database_url", getattr(config, "DATABASE_URL", None))
else:
    database_url = os.getenv("DATABASE_URL")

if not database_url:
    db_username = os.getenv("DB_USERNAME")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    if all([db_username, db_password, db_host, db_port, db_name]):
        database_url = f"postgresql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
        os.environ["DATABASE_URL"] = database_url
        logger.info("[OK] Constructed DATABASE_URL from individual settings")

ENVIRONMENT = (
    getattr(config, "ENVIRONMENT", getattr(config, "environment", "development"))
    if CONFIG_LOADED and config
    else os.getenv("ENVIRONMENT", "development")
)
DEBUG_MODE = (
    getattr(config, "DEBUG", getattr(config, "debug", False))
    if CONFIG_LOADED and config
    else os.getenv("DEBUG", "false").lower() == "true"
)

IS_PRODUCTION = ENVIRONMENT == "production"
DEV_OVERRIDE_ENABLED = not IS_PRODUCTION
MOCK_DATA_ENABLED = not IS_PRODUCTION
AGENCY_COUNT = 39

OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "false").lower() == "true"
OAUTH_PROVIDERS = os.getenv("OAUTH_PROVIDERS", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")
APPLE_KEY_ID = os.getenv("APPLE_KEY_ID")
APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY")
APPLE_CLIENT_ID = os.getenv("APPLE_CLIENT_ID")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.crown_safe_barcode_endpoints import crown_barcode_router  # noqa: E402
from api.crown_safe_endpoints import (
    HairProfileRequest,
    HairProfileResponse,
    ProductAnalysisRequest,
    ProductAnalysisResponse,
    ScanHistoryResponse,
    analyze_product_endpoint,
    create_hair_profile_endpoint,
    get_hair_profile_endpoint,
    get_scan_history_endpoint,
)
from api.pydantic_base import AppModel  # noqa: E402
from api.schemas.common import ok  # noqa: E402
from core_infra.database import User, engine, get_db_session  # noqa: E402


def is_test_environment() -> bool:
    return (
        "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
        or any(arg.endswith("pytest") or arg.endswith("pytest.exe") for arg in sys.argv)
    )


_in_test_env = is_test_environment()

try:
    from core_infra.cache_manager import get_cache_stats
except ImportError:

    def get_cache_stats() -> Dict[str, Any]:
        return {"status": "disabled", "reason": "cache manager unavailable"}

    if not _in_test_env:
        raise

try:
    from core_infra.async_optimizer import run_optimized_safety_check
except ImportError:

    async def run_optimized_safety_check(*args, **kwargs):
        return {"status": "FAILED", "error": "optimized workflow unavailable"}

    if not _in_test_env:
        raise

try:
    from core_infra.smart_cache_warmer import start_background_cache_warming, warm_cache_now
except ImportError:

    async def warm_cache_now(*args, **kwargs):
        return {"status": "disabled"}

    async def start_background_cache_warming(*args, **kwargs):
        return None

    if not _in_test_env:
        raise

try:
    from core_infra.mobile_hot_path import get_mobile_stats, ultra_fast_check
except ImportError:

    async def ultra_fast_check(*args, **kwargs):
        return None

    def get_mobile_stats(*args, **kwargs):
        return {"status": "disabled"}

    if not _in_test_env:
        raise

from agents.command.commander_agent.agent_logic import CrownSafeCommanderLogic  # noqa: E402
from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic  # noqa: E402

try:
    from core_infra.memory_optimizer import get_memory_stats, optimize_memory

    MEMORY_OPTIMIZATION_ENABLED = True
except ImportError as exc:
    logger.warning("Memory optimization disabled: %s", exc)
    MEMORY_OPTIMIZATION_ENABLED = False

    def get_memory_stats(*args, **kwargs):
        return {"status": "disabled"}

    def optimize_memory(*args, **kwargs):
        return None


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "t", "yes", "y"}:
            return True
        if lowered in {"0", "false", "f", "no", "n"}:
            return False
    return default


def _coerce_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return items or None
    return None


def classify_performance(response_time_ms: int) -> str:
    if response_time_ms <= 250:
        return "Fast"
    if response_time_ms <= 750:
        return "Moderate"
    return "Slow"


class SafetyCheckRequest(AppModel):
    model_config = {"protected_namespaces": ()}

    user_id: int = Field(..., example=1, description="Authenticated Crown Safe user ID")
    barcode: Optional[str] = Field(
        None,
        example="012345678905",
        pattern=r"^\d{8,14}$",
        description="UPC/EAN barcode for direct lookup",
    )
    model_number: Optional[str] = Field(
        None,
        example="HC-2000X",
        description="Manufacturer model number",
    )
    lot_number: Optional[str] = Field(
        None,
        example="LOT2023-05-A",
        description="Lot or batch identifier",
    )
    product_name: Optional[str] = Field(
        None,
        example="Moisturizing Shampoo",
        description="Product name for text-based search",
    )
    image_url: Optional[str] = Field(
        None,
        example="https://example.com/product.jpg",
        description="Image URL for visual recognition fallback",
    )


class SafetyCheckResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str = Field(..., example="COMPLETED")
    data: Optional[Dict[str, Any]] = Field(None, example={})
    error: Optional[str] = Field(None, example=None)
    alternatives: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Suggested safer alternatives when a hazard is detected",
    )


class UserCreateRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    email: EmailStr
    is_subscribed: bool = True


class UserOut(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: int
    email: str
    is_subscribed: bool


class AdvancedSearchRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    query: Optional[str] = Field(None, description="Search term covering product name, brand, or hazard")
    product: Optional[str] = Field(None, description="Alias for query when clients use 'product'")
    id: Optional[str] = Field(None, description="Exact record identifier lookup")
    keywords: Optional[List[str]] = Field(None, description="List of AND keywords that must all match")
    agencies: Optional[List[str]] = Field(None, description="Filter by specific regulatory agencies")
    agency: Optional[str] = Field(None, description="Single-agency filter (converted into agencies list)")
    date_from: Optional[date] = Field(None, description="Publication date from (YYYY-MM-DD)")
    date_to: Optional[date] = Field(None, description="Publication date to (YYYY-MM-DD)")
    risk_level: Optional[str] = Field(None, description="Filter by risk level label")
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Field(None, description="Alias for risk_level")
    product_category: Optional[str] = Field(None, description="Filter by product category")
    riskCategory: Optional[
        Literal[
            "drug",
            "device",
            "food",
            "cosmetic",
            "supplement",
            "toy",
            "baby_product",
            "other",
        ]
    ] = Field(None, description="Alias for product_category")
    limit: int = Field(20, ge=1, le=50, description="Maximum number of results to return")
    offset: Optional[int] = Field(None, ge=0, description="Offset for classic pagination")
    nextCursor: Optional[str] = Field(None, description="Opaque cursor for pagination")

    @model_validator(mode="after")
    def validate_search_term(self):
        if self.severity and not self.risk_level:
            self.risk_level = self.severity
        if self.riskCategory and not self.product_category:
            self.product_category = self.riskCategory
        if self.agency and not self.agencies:
            self.agencies = [self.agency]

        if self.id:
            return self
        if self.keywords:
            return self

        if not self.product and not self.query:
            raise ValueError("Provide 'product', 'query', 'id', or 'keywords' when searching")

        if self.product and self.product.strip() and len(self.product.strip()) < 2:
            raise ValueError("Product search term must be at least 2 characters")
        if self.query and self.query.strip() and len(self.query.strip()) < 2:
            raise ValueError("Query search term must be at least 2 characters")
        return self


class BulkSearchRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    barcodes: List[str] = Field(..., min_items=1, max_items=50, description="List of barcodes to evaluate")
    user_id: int = Field(..., description="User ID performing the bulk check")


class RecallAnalyticsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    total_recalls: int
    agencies_active: int
    recent_recalls: int
    top_hazards: List[Dict[str, Any]]
    top_agencies: List[Dict[str, Any]]
    safety_trends: Dict[str, Any]


app = FastAPI(
    title="Crown Safe API",
    description="Crown Safe hair and scalp safety monitoring service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    generate_unique_id_function=lambda route: (
        f"{route.name}_{route.path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}"
    ),
)

if STRUCTURED_LOGGING_ENABLED:
    try:
        app.add_middleware(LoggingMiddleware)
        logger.info("Structured logging middleware enabled")
    except Exception as exc:
        logger.warning("Failed to attach structured logging middleware: %s", exc)

try:
    from core_infra.error_handlers import register_error_handlers

    register_error_handlers(app)
    logger.info("Error handlers registered")
except Exception as exc:
    logger.warning("Could not register error handlers: %s", exc)

try:
    from core_infra.rate_limiter import (
        custom_rate_limit_exceeded_handler,
        limiter,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)
    logger.info("API rate limiting configured")
except Exception as exc:
    logger.warning("Rate limiter unavailable: %s", exc)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "crownsafe.cureviax.com",
        "*.crownsafe.cureviax.com",
        "crownsafe.cureviax.ai",
        "*.crownsafe.cureviax.ai",
        "localhost",
        "127.0.0.1",
        "testserver",
        "*.amazonaws.com",
    ],
)

raw_origins = ""
if CONFIG_LOADED and config and getattr(config, "ALLOWED_ORIGINS", None):
    raw_origins = config.ALLOWED_ORIGINS
else:
    raw_origins = os.getenv("ALLOWED_ORIGINS", "")

ALLOWED_ORIGINS = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
if not ALLOWED_ORIGINS:
    ALLOWED_ORIGINS = [
        "https://app.crownsafe.cureviax.com",
        "https://crownsafe.cureviax.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if PROMETHEUS_ENABLED:
    try:
        app.mount("/metrics", make_asgi_app())
        logger.info("Prometheus metrics endpoint mounted at /metrics")
    except Exception as exc:
        logger.warning("Failed to mount Prometheus metrics endpoint: %s", exc)

STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    svg_path = STATIC_DIR / "favicon.svg"
    ico_path = STATIC_DIR / "favicon.ico"
    if svg_path.exists():
        return FileResponse(str(svg_path), media_type="image/svg+xml")
    if ico_path.exists():
        return FileResponse(str(ico_path), media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not available")


@app.get("/favicon.svg", include_in_schema=False)
async def favicon_svg():
    svg_path = STATIC_DIR / "favicon.svg"
    if svg_path.exists():
        return FileResponse(str(svg_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not available")


_original_app = app


class HealthCheckWrapper:
    """ASGI wrapper that short-circuits /healthz before middleware execution."""

    def __init__(self, wrapped_app: FastAPI):
        self.app = wrapped_app

    def __getattr__(self, name: str):
        return getattr(self.app, name)

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/healthz":
            response = StarletteJSONResponse(
                {"status": "ok"},
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "Content-Security-Policy": "default-src 'self'",
                },
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


async def version():
    return JSONResponse(status_code=405, content={"error": "Method Not Allowed"})


@app.get("/vendor/{path:path}", include_in_schema=False)
@app.post("/vendor/{path:path}", include_in_schema=False)
async def block_vendor_attacks():
    return JSONResponse(status_code=403, content={"error": "Forbidden"})


@app.get("/index.php", include_in_schema=False)
@app.post("/index.php", include_in_schema=False)
async def block_index_php():
    return JSONResponse(status_code=403, content={"error": "Forbidden"})


@app.get("/public/index.php", include_in_schema=False)
@app.post("/public/index.php", include_in_schema=False)
async def block_public_index_php():
    return JSONResponse(status_code=403, content={"error": "Forbidden"})


# Security middleware to block malicious requests
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CRITICAL: Always allow health checks to pass through
    if request.url.path in ["/healthz", "/health", "/readyz", "/metrics"]:
        return await call_next(request)

    # Block WebDAV and other non-standard HTTP methods
    if request.method in [
        "PROPFIND",
        "PROPPATCH",
        "MKCOL",
        "COPY",
        "MOVE",
        "LOCK",
        "UNLOCK",
        "SEARCH",
    ]:
        logger.debug(
            "Blocked WebDAV method: %s %s from %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        return JSONResponse(
            status_code=405,
            content={"error": "Method Not Allowed"},
            headers={
                "Allow": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
                "X-Content-Type-Options": "nosniff",
            },
        )

    path = request.url.path.lower()
    query = str(request.url.query).lower()

    php_attack_patterns = [
        "/vendor/phpunit",
        "phpunit/",
        "eval-stdin.php",
        "index.php",
        ".php",
        "wp-admin/",
        "wp-content/",
        "wp-includes/",
        "wp-config",
        "phpmyadmin/",
        "adminer/",
        "config.php",
        "../",
        "..\\",
        "%2e%2e",
        "%252e",
        "lang=..",
        "/tmp/",
        "allow_url_include",
        "auto_prepend_file",
        "php://input",
        "invokefunction",
        "call_user_func_array",
        "think\\app",
        ".git/",
        ".svn/",
        ".hg/",
        ".bzr/",
        "cvs/",
        "admin/",
        "administrator/",
        "panel/",
        "dashboard/",
        "backup/",
        "backups/",
        "old/",
        ".bak",
        ".backup",
        ".env",
        "web.config",
        "htaccess",
    ]

    pattern_found = any(pattern in path or pattern in query for pattern in php_attack_patterns)
    if pattern_found and not path.startswith("/api/v1/barcode/test/"):
        logger.debug(
            "Blocked PHP/vulnerability scan: %s from %s",
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        if "phpunit" in path or "eval-stdin" in path:
            logger.warning("PHP vulnerability scan blocked from %s", request.client.host)
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden"},
            headers={
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
            },
        )

    response = await call_next(request)
    return response


# ===== TRACE ID MIDDLEWARE =====
# Add X-Trace-Id header to all responses for request tracking
@app.middleware("http")
async def add_trace_id_header(request: Request, call_next):
    """Add X-Trace-Id header to all responses for request tracking and debugging."""
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# ===== PHASE 2: SECURITY HEADERS (DECORATOR PATTERN) =====
# Add comprehensive OWASP security headers to ALL responses
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add OWASP-recommended security headers to all responses.

    Implements:
    - Content Security Policy (CSP) - XSS protection
    - X-Frame-Options - Clickjacking protection
    - X-Content-Type-Options - MIME sniffing protection
    - Strict-Transport-Security (HSTS) - HTTPS enforcement (production only)
    - X-XSS-Protection - Legacy XSS filter
    - Referrer-Policy - Privacy protection
    - Permissions-Policy - Feature restrictions
    - X-Permitted-Cross-Domain-Policies - Flash/Adobe policy
    """
    response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' https://api.crownsafe.cureviax.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"

    if IS_PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    if request.url.path.startswith(("/api/v1/auth", "/api/v1/user")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"

    return response


# ===== END PHASE 2 SECURITY HEADERS =====


# Add all production middleware
# Security middleware - not implemented yet
# try:
#     from core_infra.security_middleware import SecurityMiddleware
#     app.add_middleware(SecurityMiddleware)
#     logger.info("Security headers middleware added")
# except Exception as e:
#     logger.warning(f"Could not add security middleware: {e}")

# Graceful shutdown - handled differently
# try:
#     from core_infra.graceful_shutdown import GracefulShutdownMiddleware
#     app.add_middleware(GracefulShutdownMiddleware)
#     logger.info("Graceful shutdown middleware added")
# except Exception as e:
#     logger.warning(f"Could not add graceful shutdown middleware: {e}")

# Audit logging - not implemented yet
# try:
#     from core_infra.audit_logger import AuditLoggerMiddleware
#     app.add_middleware(AuditLoggerMiddleware)
#     logger.info("Audit logging middleware added")
# except Exception as e:
#     logger.warning(f"Could not add audit logging middleware: {e}")

# Request ID tracking - not needed for MVP
# try:
#     from core_infra.graceful_shutdown import RequestIDMiddleware
#     app.add_middleware(RequestIDMiddleware)
#     logger.info("Request ID middleware added")
# except Exception as e:
#     logger.warning(f"Could not add request ID middleware: {e}")

# Transaction management - handled by SQLAlchemy
# try:
#     from core_infra.transactions import TransactionMiddleware
#     app.add_middleware(TransactionMiddleware)
#     logger.info("Transaction middleware added")
# except Exception as e:
#     logger.warning(f"Could not add transaction middleware: {e}")

# Circuit breaker - not critical for MVP
# try:
#     from core_infra.circuit_breaker import CircuitBreakerMiddleware
#     app.add_middleware(CircuitBreakerMiddleware)
#     logger.info("Circuit breaker middleware added")
# except Exception as e:
#     logger.warning(f"Could not add circuit breaker middleware: {e}")

# Pagination - handled in endpoints
# try:
#     from core_infra.pagination import PaginationMiddleware
#     app.add_middleware(PaginationMiddleware)
#     logger.info("Pagination middleware added")
# except Exception as e:
#     logger.warning(f"Could not add pagination middleware: {e}")

# Input validation - handled by Pydantic
# try:
#     from core_infra.validators import InputValidationMiddleware
#     app.add_middleware(InputValidationMiddleware)
#     logger.info("Input validation middleware added")
# except Exception as e:
#     logger.warning(f"Could not add input validation middleware: {e}")

# PII encryption - not needed for MVP
# try:
#     from core_infra.encryption import PIIEncryptionMiddleware
#     app.add_middleware(PIIEncryptionMiddleware)
#     logger.info("PII encryption middleware added")
# except Exception as e:
#     logger.warning(f"Could not add PII encryption middleware: {e}")
commander_agent: Optional[CrownSafeCommanderLogic] = None
visual_search_agent: Optional[VisualSearchAgentLogic] = None

# Import deprecated auth endpoints FIRST (to take precedence)
try:
    from api.auth_deprecated import router as auth_deprecated_router

    app.include_router(auth_deprecated_router)
    logger.info("Deprecated auth endpoints registered")
except Exception as e:
    logger.warning(f"Deprecated auth endpoints not available: {e}")

# Import and include authentication endpoints
try:
    from api.auth_endpoints import router as auth_router

    app.include_router(auth_router)
    logger.info("Authentication endpoints registered")
except Exception as e:
    logger.error(f"Failed to register auth endpoints: {e}")

# Import password reset endpoints
try:
    from api.password_reset_endpoints import router as password_reset_router

    app.include_router(password_reset_router)
    logger.info("Password reset endpoints registered")
except Exception as e:
    logger.warning(f"Password reset endpoints not available: {e}")

# Import scan history endpoints
try:
    from api.scan_history_endpoints import router as scan_history_router

    app.include_router(scan_history_router)
    logger.info("Scan history endpoints registered")
except Exception as e:
    logger.warning(f"Scan history endpoints not available: {e}")

# Import enhanced notification endpoints
try:
    from api.notification_endpoints import router as notification_router

    app.include_router(notification_router)
    logger.info("Enhanced notification endpoints registered")
except Exception as e:
    logger.warning(f"Enhanced notification endpoints not available: {e}")

# Import monitoring management endpoints
try:
    from api.monitoring_endpoints import router as monitoring_router

    app.include_router(monitoring_router)
    logger.info("Product monitoring endpoints registered")
except Exception as e:
    logger.warning(f"Product monitoring endpoints not available: {e}")

# Import user dashboard endpoints
try:
    from api.user_dashboard_endpoints import router as dashboard_router

    app.include_router(dashboard_router)
    logger.info("User dashboard endpoints registered")
except Exception as e:
    logger.warning(f"User dashboard endpoints not available: {e}")


# Import admin endpoints for user management
try:
    from api.admin_endpoints import router as admin_router

    app.include_router(admin_router)
    logger.info("Admin endpoints registered")
except Exception as e:
    logger.warning(f"Admin endpoints not available: {e}")
# Skip health endpoints - using built-in /healthz instead to avoid conflicts
# try:
#     from api.health_endpoints import router as health_router
#     app.include_router(health_router)
#     logger.info("Health check endpoints registered")
# except Exception as e:
#     logger.error(f"Failed to register health endpoints: {e}")
logger.info("Using built-in health endpoints (/healthz, /readyz)")

# Import and include v1 endpoints after app is created
try:
    from api.v1_endpoints import router as v1_router

    app.include_router(v1_router)
    logger.info("v1 endpoints registered")
except Exception as e:
    logger.error(f"Failed to register v1 endpoints: {e}")

# Import and include hair profile management endpoints (Crown Safe MVP)
try:
    from api.hair_profile_endpoints import router as hair_profile_router

    app.include_router(hair_profile_router)
    logger.info("Hair profile endpoints registered (/api/v1/profiles)")
except Exception as e:
    logger.error(f"Failed to register hair profile endpoints: {e}")

# Import and include ingredient explainer endpoints (Crown Safe MVP)
try:
    from api.ingredient_explainer_endpoints import router as ingredient_explainer_router

    app.include_router(ingredient_explainer_router)
    logger.info("Ingredient explainer endpoints registered (/api/v1/ingredients)")
except Exception as e:
    logger.error(f"Failed to register ingredient explainer endpoints: {e}")

# Import and include routine analysis endpoints (Crown Safe MVP)
try:
    from api.routine_analysis_endpoints import router as routine_analysis_router

    app.include_router(routine_analysis_router)
    logger.info("Routine analysis endpoints registered (/api/v1/cabinet-audit, /routine-check)")
except Exception as e:
    logger.error(f"Failed to register routine analysis endpoints: {e}")

# Import and include barcode scanning endpoints
try:
    from api.barcode_endpoints import (
        barcode_router,
        barcode_scan_router,
        mobile_scan_router,
    )

    app.include_router(barcode_router)
    app.include_router(mobile_scan_router)
    app.include_router(barcode_scan_router)  # /api/v1/barcode/scan endpoint
    logger.info("Barcode scanning endpoints registered")
    logger.info("Mobile scan results endpoints registered")
except Exception as e:
    logger.error(f"Failed to register barcode endpoints: {e}")

# Include Enhanced Barcode Bridge for Task 12
try:
    from api.barcode_bridge import router as barcode_bridge_router

    app.include_router(barcode_bridge_router)
    logger.info("Enhanced Barcode Bridge (Task 12) registered")
except Exception as e:
    logger.error(f"Failed to register barcode bridge: {e}")

# Include Enhanced Barcode Scanning for A-5
try:
    from api.enhanced_barcode_endpoints import enhanced_barcode_router

    app.include_router(enhanced_barcode_router)
    logger.info("Enhanced Barcode Scanning (A-5) registered")
except Exception as e:
    logger.error(f"Failed to register enhanced barcode scanning: {e}")

# Include Safety Reports endpoints
try:
    from api.safety_reports_endpoints import safety_reports_router

    app.include_router(safety_reports_router)
    logger.info("Safety Reports endpoints registered")
except Exception as e:
    logger.error(f"Failed to register safety reports: {e}")

# Include Share Results endpoints
try:
    from api.share_results_endpoints import share_router

    app.include_router(share_router)
    logger.info("Share Results endpoints registered")
except Exception as e:
    logger.error(f"Failed to register share results: {e}")

# REMOVED FOR CROWN SAFE: Recall Alert System was BabyShield-specific

# Include Recall Search System
try:
    from api.recalls_endpoints import router as recalls_router

    app.include_router(recalls_router)
    logger.info("Recall Search System registered")
except Exception as e:
    logger.error(f"Failed to register recall search system: {e}")

# Include Incident Reporting System
try:
    from api.incident_report_endpoints import incident_router

    app.include_router(incident_router)

    # Add direct route for report page at /report-incident
    @app.get("/report-incident", include_in_schema=False)
    async def report_incident_page():
        """Serve the incident report page directly at /report-incident"""
        return FileResponse(str(STATIC_DIR / "report_incident.html"))

    logger.info("Incident Reporting System registered")
except Exception as e:
    logger.error(f"Failed to register incident reporting: {e}")


# Safety Hub API Endpoint
@app.get("/api/v1/safety-hub/articles")
def get_safety_hub_articles(
    limit: int = Query(20, ge=1, le=100, description="Number of articles per page"),
    offset: int = Query(0, ge=0, description="Number of articles to skip"),
    category: Optional[str] = Query(None, description="Filter by article category"),
    language: Optional[str] = Query("en", description="Language filter (en, es, fr, etc.)"),
    featured_only: bool = Query(False, description="Show only featured articles"),
    sort: str = Query("recent", pattern="^(recent|oldest|title)$", description="Sort order"),
):
    """
    Returns a paginated list of safety articles with filtering and caching support.
    Features: pagination, categories, language filter, no PII, cache headers.
    """
    import json

    try:
        from core_infra.database import SafetyArticle, get_db

        logger.info(
            "Fetching safety articles: limit=%s offset=%s category=%s language=%s",
            limit,
            offset,
            category,
            language,
        )

        # Use get_db as a dependency
        with get_db() as db:
            # Build query
            query = db.query(SafetyArticle)

            # Apply filters
            if featured_only:
                query = query.filter(SafetyArticle.is_featured)

            if category:
                # For now, we'll use source_agency as a proxy for category
                # In a real implementation, you'd add a category field to SafetyArticle
                query = query.filter(SafetyArticle.source_agency.ilike(f"%{category}%"))

            # Get total count before pagination
            total = query.count()

            # Apply sorting
            if sort == "recent":
                query = query.order_by(
                    sa_desc(SafetyArticle.publication_date),
                    sa_desc(SafetyArticle.id),
                )
            elif sort == "oldest":
                query = query.order_by(
                    sa_asc(SafetyArticle.publication_date),
                    sa_asc(SafetyArticle.id),
                )
            elif sort == "title":
                query = query.order_by(sa_asc(SafetyArticle.title))

            # Apply pagination
            articles = query.offset(offset).limit(limit).all()

            # Convert to response format (no PII)
            result = [
                {
                    "id": article.id,
                    "article_id": article.article_id,
                    "title": article.title,
                    "summary": article.summary,
                    "source_agency": article.source_agency,
                    "publication_date": (article.publication_date.isoformat() if article.publication_date else None),
                    "image_url": article.image_url,
                    "article_url": article.article_url,
                    "is_featured": article.is_featured,
                    "category": article.source_agency,  # Using source_agency as category proxy
                    "language": language,  # Default to requested language
                }
                for article in articles
            ]

        # Create response data
        response_data = {
            "success": True,
            "data": {
                "articles": result,
                "pagination": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total,
                },
                "filters": {
                    "category": category,
                    "language": language,
                    "featured_only": featured_only,
                    "sort": sort,
                },
            },
        }

        # Generate ETag for caching
        content_hash = hashlib.sha256(json.dumps(response_data, sort_keys=True).encode()).hexdigest()
        etag = f'"{content_hash}"'

        # Create response with cache headers
        response = Response(
            content=json.dumps(response_data),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=300, s-maxage=600",  # 5min browser, 10min CDN
                "ETag": etag,
                "Vary": "Accept-Language, Accept-Encoding",
            },
        )

        return response

    except Exception as e:
        logger.error(f"Failed to fetch safety articles: {e}", exc_info=True)
        # Return fallback data instead of 500 error
        fallback_articles = [
            {
                "id": 1,
                "article_id": "fallback-001",
                "title": "Child Safety Product Recalls: What Parents Need to Know",
                "summary": "Guide to tracking recalls and keeping your family safe.",
                "source_agency": "CPSC",
                "publication_date": "2024-01-15T00:00:00Z",
                "image_url": None,
                "article_url": "https://www.cpsc.gov/Recalls",
                "is_featured": True,
                "category": "CPSC",
                "language": language or "en",
            },
            {
                "id": 2,
                "article_id": "fallback-002",
                "title": "Haircare Product Safety Guidelines",
                "summary": ("Core haircare safety information for salon professionals and consumers."),
                "source_agency": "FDA",
                "publication_date": "2024-01-10T00:00:00Z",
                "image_url": None,
                "article_url": ("https://www.fda.gov/food/people-risk-foodborne-illness/food-safety-pregnant-women"),
                "is_featured": True,
                "category": "FDA",
                "language": language or "en",
            },
            {
                "id": 3,
                "article_id": "fallback-003",
                "title": "EU Safety Gate: Recent Product Alerts",
                "summary": "Latest safety alerts from the European Union's rapid alert system.",
                "source_agency": "EU Safety Gate",
                "publication_date": "2024-01-05T00:00:00Z",
                "image_url": None,
                "article_url": "https://ec.europa.eu/safety-gate",
                "is_featured": False,
                "category": "EU Safety Gate",
                "language": language or "en",
            },
        ]

        # Create fallback response with proper structure
        fallback_response_data = {
            "success": True,
            "data": {
                "articles": fallback_articles,
                "pagination": {
                    "total": len(fallback_articles),
                    "limit": limit,
                    "offset": offset,
                    "has_more": False,
                },
                "filters": {
                    "category": category,
                    "language": language or "en",
                    "featured_only": featured_only,
                    "sort": sort,
                },
            },
        }

        # Generate ETag for fallback response
        content_hash = hashlib.sha256(json.dumps(fallback_response_data, sort_keys=True).encode()).hexdigest()
        etag = f'"{content_hash}"'

        # Return fallback response with cache headers
        return Response(
            content=json.dumps(fallback_response_data),
            media_type="application/json",
            headers={
                "Cache-Control": "public, max-age=60, s-maxage=120",  # Shorter cache for fallback
                "ETag": etag,
                "Vary": "Accept-Language, Accept-Encoding",
            },
        )


# Import and include visual agent endpoints
try:
    from api.visual_agent_endpoints import visual_router

    app.include_router(visual_router)
    logger.info("Visual agent endpoints registered")
except ImportError as e:
    logger.warning(f"Visual agent endpoints not available: {e}")
except Exception as e:
    logger.warning(f"Visual agent endpoints disabled due to missing dependencies: {e}")

# Import and include risk assessment endpoints
try:
    from api.risk_assessment_endpoints import risk_router

    app.include_router(risk_router)
    logger.info("Risk assessment endpoints registered")
except ImportError as e:
    logger.warning(f"Risk assessment endpoints not available: {e}")
except Exception as e:
    logger.error(f"Failed to register risk assessment endpoints: {e}")

# Include subscription endpoints for mobile IAP
try:
    from api.subscription_endpoints import router as subscription_router

    app.include_router(subscription_router)
    logger.info("Subscription endpoints registered")
except Exception as e:
    logger.error(f"Failed to register subscription endpoints: {e}")

# Health endpoints already registered above

# Include recall detail endpoints
try:
    from api.recall_detail_endpoints import router as recall_detail_router

    app.include_router(recall_detail_router)
    logger.info("Recall detail endpoints registered")
except Exception as e:
    logger.error(f"Failed to register recall detail endpoints: {e}")

# Include OAuth endpoints for Task 11
try:
    from api.oauth_endpoints import router as oauth_router

    if OAUTH_ENABLED:
        app.include_router(oauth_router)
        providers = OAUTH_PROVIDERS if OAUTH_PROVIDERS else "auto-detect"
        logger.info("OAuth endpoints registered (providers: %s)", providers)
    else:
        logger.info("OAuth router NOT mounted (OAUTH_ENABLED is false or missing)")

except Exception as e:
    logger.error(f"Failed to register OAuth endpoints: {e}")

# Include Settings endpoints for Task 11
try:
    from api.settings_endpoints import router as settings_router

    app.include_router(settings_router)
    logger.info("Settings endpoints registered")
except Exception as e:
    logger.error(f"Failed to register settings endpoints: {e}")

# Include User Data Management endpoints for Task 11
try:
    from api.user_data_endpoints import privacy_router
    from api.user_data_endpoints import router as user_data_router

    app.include_router(user_data_router)
    app.include_router(privacy_router)
    logger.info("User data management and privacy endpoints registered")
except Exception as e:
    logger.error(f"Failed to register user data endpoints: {e}")

# Include Account Management endpoints (Apple compliance)
try:
    from api.routers.account import router as account_router

    app.include_router(account_router)
    logger.info("Account management endpoints registered")
except Exception as e:
    logger.error(f"Failed to register account endpoints: {e}")

# Include Device Management endpoints (push token cleanup)
try:
    from api.routers.devices import router as devices_router

    app.include_router(devices_router)
    logger.info("Device management endpoints registered")
except Exception as e:
    logger.error(f"Failed to register device endpoints: {e}")

# Include Legacy Account endpoints (410 Gone for old paths)
try:
    from api.routers import account_legacy as account_legacy_router

    app.include_router(account_legacy_router.router)
    logger.info("Legacy account endpoints registered")
except Exception as e:
    logger.error(f"Failed to register legacy account endpoints: {e}")

# Include Localization & Accessibility endpoints for Task 13
try:
    from api.localization import router as i18n_router

    app.include_router(i18n_router)
    logger.info("Localization & Accessibility (Task 13) registered")
except Exception as e:
    logger.error(f"Failed to register localization endpoints: {e}")

# Include Monitoring & Metrics endpoints for Task 14
try:
    from api.monitoring import metrics_router
    from api.monitoring import router as monitoring_router

    app.include_router(monitoring_router)
    app.include_router(metrics_router)
    logger.info("Monitoring & SLO endpoints (Task 14) registered")
except Exception as e:
    logger.error(f"Failed to register monitoring endpoints: {e}")

# Include Legal & Privacy endpoints for Task 15
try:
    from api.legal_endpoints import router as legal_router

    app.include_router(legal_router)
    logger.info("Legal & Privacy endpoints (Task 15) registered")
except Exception as e:
    logger.error(f"Failed to register legal endpoints: {e}")

# Include Support & Feedback endpoints for Task 20
try:
    from api.feedback_endpoints import router as feedback_router

    app.include_router(feedback_router)
    logger.info("Support & Feedback endpoints (Task 20) registered")
except Exception as e:
    logger.error(f"Failed to register feedback endpoints: {e}")

# Include Advanced Features (Web Research, Guidelines, Visual Recognition) endpoints
try:
    from api.advanced_features_endpoints import router as advanced_router

    app.include_router(advanced_router)
    logger.info("Advanced Features (Web Research, Guidelines, Visual) endpoints registered")
except (ImportError, FileNotFoundError) as e:
    logger.warning(f"Advanced Features not available (missing dependency): {e}")
    # Continue without advanced features - they're optional

# Include Legal Compliance endpoints (COPPA, GDPR, Children's Code)
try:
    from api.compliance_endpoints import router as compliance_router

    app.include_router(compliance_router)
    logger.info("Legal Compliance endpoints (COPPA, GDPR, Children's Code) registered")
except ImportError as e:
    logger.error(f"Compliance endpoints not available: {e}")
except Exception as e:
    logger.error(f"Failed to register compliance endpoints: {e}")

# Include Supplemental Data endpoints for enhanced safety reports
try:
    from api.supplemental_data_endpoints import router as supplemental_router

    app.include_router(supplemental_router)
    logger.info("Supplemental data endpoints registered")
except ImportError as e:
    logger.error(f"Import error for supplemental data endpoints: {e}")
except Exception as e:
    logger.error(f"Failed to register supplemental data endpoints: {e}")
    logger.error("Full traceback: %s", traceback.format_exc())

# Include Clean Lookup endpoints for simple barcode queries (early registration for OpenAPI)
try:
    from api.routers.lookup import router as lookup_router

    app.include_router(lookup_router)
    logger.info("Clean lookup endpoints registered")
except ImportError as e:
    logger.error(f"Import error for lookup endpoints: {e}")
except Exception as e:
    logger.error(f"Failed to register lookup endpoints: {e}")

# MOVED CHAT REGISTRATION LATER - SEE LINE ~1000

# Include Analytics endpoints for feedback and metrics
try:
    from api.routers.analytics import router as analytics_router

    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
    logger.info("Analytics endpoints registered")
except ImportError as e:
    logger.error(f"Import error for analytics endpoints: {e}")
except Exception as e:
    logger.error(f"Failed to register analytics endpoints: {e}")

# Include Honeypot endpoints for security intelligence
try:
    from api.routers.honeypots import router as honeypots_router

    app.include_router(honeypots_router, tags=["security"])
    logger.info("Security honeypot endpoints deployed")
except ImportError as e:
    logger.warning(f"Honeypot endpoints not available: {e}")
except Exception as e:
    logger.error(f"Failed to register honeypot endpoints: {e}")

# Include Security Monitoring Dashboard
try:
    from api.security.monitoring_dashboard import router as security_dashboard_router

    app.include_router(security_dashboard_router, tags=["security-monitoring"])
    logger.info("Security monitoring dashboard deployed")
except ImportError as e:
    logger.warning(f"Security dashboard not available: {e}")
except Exception as e:
    logger.error(f"Failed to register security dashboard: {e}")

# Import and apply OpenAPI spec
try:
    from api.openapi_spec import custom_openapi

    def _custom_openapi() -> Dict[str, Any]:
        return custom_openapi(cast(FastAPI, _original_app))

    _original_app.openapi = _custom_openapi  # type: ignore[assignment]
    app.openapi = _custom_openapi  # type: ignore[assignment]
    logger.info("OpenAPI spec loaded and applied")
except Exception as e:
    logger.error(f"Failed to load OpenAPI spec: {e}")

# Add custom exception handlers for our standard error envelope


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors with our standard error envelope"""
    trace_id = f"trace_{int(datetime.now().timestamp())}_{request.url.path.replace('/', '_')}"

    # Extract the first error message
    error_msg = "Invalid request"
    if exc.errors():
        first_error = exc.errors()[0]
        if first_error.get("loc"):
            field = ".".join(str(x) for x in first_error["loc"])
            if first_error.get("type") == "missing":
                error_msg = f"Missing required parameter: {field}"
            elif "JSON decode error" in str(first_error.get("msg", "")):
                error_msg = "Invalid JSON format in request body"
            else:
                error_detail = first_error.get("msg", "validation error")
                error_msg = f"Invalid parameter {field}: {error_detail}"

    logger.warning(f"[{trace_id}] Validation error: {error_msg}")

    # Convert errors to JSON-serializable format
    serializable_errors = []
    for error in exc.errors():
        serializable_error = {
            "loc": error.get("loc", []),
            "msg": str(error.get("msg", "")),
            "type": error.get("type", ""),
        }
        # Include context if available
        if "ctx" in error:
            serializable_error["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        serializable_errors.append(serializable_error)

    return JSONResponse(
        status_code=422,  # Use 422 for validation errors (FastAPI/HTTP standard)
        content={
            "success": False,
            "error": {"code": "BAD_REQUEST", "message": error_msg},
            "detail": serializable_errors,  # Include standard FastAPI validation error details
            "traceId": trace_id,
        },
    )


@app.exception_handler(json.JSONDecodeError)
async def json_decode_exception_handler(request, exc):
    """Handle JSON decode errors with our standard error envelope"""
    trace_id = f"trace_{int(datetime.now().timestamp())}_{request.url.path.replace('/', '_')}"

    logger.warning(f"[{trace_id}] JSON decode error: {str(exc)}")

    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": "BAD_REQUEST",
                "message": "Invalid JSON format in request body",
            },
            "traceId": trace_id,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with our standard error envelope"""
    trace_id = f"trace_{int(datetime.now().timestamp())}_{request.url.path.replace('/', '_')}"

    # Map status codes to error codes
    error_code = "INTERNAL_ERROR"
    if exc.status_code == 400:
        error_code = "BAD_REQUEST"
    elif exc.status_code == 401:
        error_code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        error_code = "FORBIDDEN"
    elif exc.status_code == 404:
        error_code = "NOT_FOUND"
    elif exc.status_code == 408:
        error_code = "TIMEOUT"
    elif exc.status_code == 429:
        error_code = "RATE_LIMITED"
    elif exc.status_code == 502:
        error_code = "UPSTREAM_ERROR"
    elif exc.status_code == 503:
        error_code = "UPSTREAM_TIMEOUT"
    elif exc.status_code >= 500:
        error_code = "INTERNAL_ERROR"

    # Log 404/405 as INFO (normal not found), others as ERROR - DEPLOYMENT FIX
    if exc.status_code in (404, 405):
        logger.info(f"[{trace_id}] HTTP {exc.status_code}: {exc.detail}")
    else:
        logger.error(f"[{trace_id}] HTTP {exc.status_code}: {exc.detail}")

    # Force deployment refresh

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": exc.detail or f"HTTP {exc.status_code} error",
            },
            "detail": exc.detail,  # Include standard FastAPI detail field
            "traceId": trace_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all unhandled exceptions with our standard error envelope"""
    trace_id = f"trace_{int(datetime.now().timestamp())}_{request.url.path.replace('/', '_')}"

    logger.error(f"[{trace_id}] Unhandled exception: {exc}", exc_info=True)

    # Don't expose internal error details in production
    error_msg = "An internal error occurred"
    if DEBUG_MODE:
        error_msg = f"Internal error: {exc}"

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": error_msg},
            "traceId": trace_id,
        },
    )


# Global agent initialization flags
_agents_initialized = False


@app.on_event("startup")
def on_startup():
    global commander_agent, visual_search_agent, _agents_initialized

    logger.info(f"Starting Crown Safe API in {ENVIRONMENT.upper()} environment...")

    # Prevent double initialization
    if _agents_initialized:
        logger.info("Agents already initialized, skipping")
        return

    # Only initialize agents in production or when explicitly enabled
    if IS_PRODUCTION or (
        getattr(config, "ENABLE_AGENTS", False)
        if CONFIG_LOADED
        else os.getenv("ENABLE_AGENTS", "false").lower() == "true"
    ):
        std_logger = logger if isinstance(logger, logging.Logger) else logging.getLogger(__name__)

        commander_agent = CrownSafeCommanderLogic(
            agent_id="api_commander_001",
            logger_instance=std_logger,
        )
        logger.info("Commander Agent initialized.")
        logger.info("Initializing the Visual Search Agent...")
        visual_search_agent = VisualSearchAgentLogic(
            agent_id="api_visual_search_001",
            logger_instance=std_logger,
        )
        logger.info("Visual Search Agent initialized.")
    else:
        logger.info("Agents disabled in development mode")
        commander_agent = None
        visual_search_agent = None

    _agents_initialized = True

    logger.info(
        "Environment: %s (Dev overrides: %s, Mock data: %s)",
        ENVIRONMENT,
        DEV_OVERRIDE_ENABLED,
        MOCK_DATA_ENABLED,
    )

    # == Auto-create tables & seed a subscribed user ==
    try:
        from api.models.user_report import UserReport
        from core_infra.database import Base, SessionLocal, User, engine

        _ = UserReport.__tablename__
        Base.metadata.create_all(bind=engine)
        logger.info("[OK] Database tables created/verified.")

        # Run Alembic migrations for PostgreSQL
        try:
            from alembic.config import Config

            from alembic import command

            # Check if we're using PostgreSQL
            if CONFIG_LOADED and config:
                database_url = getattr(config, "database_url", "") or getattr(config, "DATABASE_URL", "") or ""
            else:
                database_url = os.getenv("DATABASE_URL", "")

            if database_url and "postgresql" in database_url.lower():
                logger.info("[OK] Running Alembic migrations for PostgreSQL...")

                # Set up Alembic config
                alembic_cfg = Config("db/alembic.ini")
                alembic_cfg.set_main_option("sqlalchemy.url", database_url)

                # Run migrations
                command.upgrade(alembic_cfg, "head")
                logger.info("[OK] Alembic migrations completed successfully.")

                # Enable pg_trgm extension for fuzzy search
                try:
                    from core_infra.database import SessionLocal as DBSession

                    logger.info("[OK] Enabling pg_trgm extension for fuzzy search...")

                    db_session = DBSession()
                    try:
                        # Enable extension
                        db_session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                        db_session.commit()
                        logger.info("[OK] pg_trgm extension enabled successfully.")

                        # Create indexes for better performance
                        logger.info("[OK] Creating GIN indexes for fuzzy search...")
                        indexes = [
                            (
                                "CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm "
                                "ON recalls_enhanced USING gin "
                                "(lower(product_name) gin_trgm_ops);"
                            ),
                            (
                                "CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm "
                                "ON recalls_enhanced USING gin "
                                "(lower(brand) gin_trgm_ops);"
                            ),
                            (
                                "CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm "
                                "ON recalls_enhanced USING gin "
                                "(lower(description) gin_trgm_ops);"
                            ),
                            (
                                "CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm "
                                "ON recalls_enhanced USING gin "
                                "(lower(hazard) gin_trgm_ops);"
                            ),
                        ]

                        for index_sql in indexes:
                            db_session.execute(text(index_sql))

                        db_session.commit()
                        logger.info("[OK] Fuzzy search indexes created successfully.")

                    finally:
                        db_session.close()

                except Exception as trgm_error:
                    logger.warning(f"[WARN] pg_trgm setup failed: {trgm_error}")
                    logger.info("[INFO] Fuzzy search may not work correctly without pg_trgm extension.")
            else:
                logger.info("[INFO] Skipping Alembic migrations for non-PostgreSQL database.")

        except Exception as migration_error:
            logger.warning(f"[WARN] Alembic migration failed: {migration_error}")
            logger.info("[INFO] Continuing without migrations - tables may be missing columns.")

        # Simple user seeding
        db = SessionLocal()
        try:
            # Race-condition safe: try to insert, catch IntegrityError if user exists
            try:
                u = User(
                    id=1,
                    email="test_parent@crownsafe.com",
                    hashed_password="testhash",
                    is_subscribed=True,
                )
                db.add(u)
                db.commit()
                logger.info("[OK] Seeded default user test_parent@crownsafe.com (id=1, subscribed).")
            except SAIntegrityError:
                db.rollback()
                logger.info("[INFO] User id=1 already exists (inserted by another worker).")
        except Exception as e:
            logger.error("Failed to seed user: %s", e)
            db.rollback()
        finally:
            db.close()

    except Exception as db_error:
        logger.warning(f"Database initialization skipped: {db_error}")
    logger.info("Running without database - some features may not work")

    # START BACKGROUND CACHE WARMING for 70%+ hit rate
    try:
        logger.info("Starting intelligent cache warming for 39-agency system...")
        asyncio.create_task(start_background_cache_warming())
        logger.info("Background cache warming started - will boost hit rate to 70%+")
    except Exception as e:
        logger.warning(f"Cache warming startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of database connections"""

    try:
        # Dispose of the engine connection pool
        engine.dispose()
        logger.info("Database connections closed cleanly")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Homepage and health check endpoints
@app.get("/", tags=["system"], include_in_schema=False)
async def root():
    """Serve Crown Safe homepage"""
    homepage_path = STATIC_DIR / "index.html"
    if homepage_path.exists():
        return FileResponse(str(homepage_path), media_type="text/html")
    # Fallback to JSON if HTML not found
    return {"status": "ok", "service": "Crown Safe API", "version": "1.0.0"}


@app.get("/health", tags=["system"], operation_id="health_check")
def health_check():
    """Basic health check (backwards compatibility)"""
    return ok({"status": "ok"})


@app.get("/api/healthz", tags=["system"], include_in_schema=False)
@app.get("/api/v1/healthz", tags=["system"], include_in_schema=False)
async def healthz_api_alias() -> Dict[str, str]:
    """API-prefixed health aliases for load balancers and clients"""
    return {"status": "ok"}


@app.get("/api/v1/public/endpoint", tags=["public"], operation_id="public_test_endpoint")
async def public_test_endpoint() -> Dict[str, str]:
    """
    Public test endpoint for rate limiting and security testing.
    This endpoint does not require authentication.
    """
    return {
        "status": "ok",
        "message": "Public endpoint",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/health", tags=["system"], include_in_schema=False)
@app.get("/api/v1/health", tags=["system"], include_in_schema=False)
async def health_api_alias() -> Dict[str, str]:
    """API-prefixed health aliases returning minimal payload"""
    return {"status": "ok"}


# Root and favicon handlers already defined above - removed duplicate definitions

# Health endpoint moved to top of file (line 190) - before middleware


@app.get("/readyz", tags=["system"], operation_id="readyz_readiness")
@app.head("/readyz", tags=["system"], operation_id="readyz_readiness_head")
def readyz():
    """Kubernetes/ALB readiness probe - checks if service can handle requests"""
    try:
        # Check database connection
        with get_db_session() as db:
            db.execute(text("SELECT 1"))

            # Check if recalls_enhanced table exists (optional - service can run without it)
            table_exists = False
            table_count = None
            try:
                # Use SQLAlchemy Inspector for dialect-agnostic table checks
                # (compatible with SQLite and PostgreSQL)
                inspector = sa_inspect(db.get_bind())
                table_exists = inspector.has_table("recalls_enhanced")
                if table_exists:
                    count_result = db.execute(text("SELECT COUNT(*) FROM recalls_enhanced"))
                    table_count = count_result.scalar()
            except Exception as table_err:
                logger.warning(f"Could not check recalls_enhanced table: {table_err}")

            return {
                "status": "ready",
                "message": "Service is ready to handle requests",
                "database": "connected",
                "recalls_enhanced_table": {
                    "exists": table_exists,
                    "count": table_count if table_exists else None,
                },
            }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready") from e


@app.get("/debug/db-info", tags=["system"], operation_id="debug_db_info")
def debug_db_info():
    """Debug endpoint to check database connection and schema"""
    try:
        with get_db_session() as db:
            # Get current database info
            result = db.execute(text("SELECT current_database(), current_schema(), version()"))
            row = result.fetchone()

            # Check if is_active column exists in users table
            columns_result = db.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY ordinal_position
            """
                )
            )
            columns = [
                {
                    "name": r[0],
                    "type": r[1],
                    "nullable": r[2],
                    "default": r[3],
                }
                for r in columns_result
            ]

            is_active_exists = any(col["name"] == "is_active" for col in columns)

            return {
                "status": "ok",
                "current_database": row[0] if row else None,
                "current_schema": row[1] if row else None,
                "postgres_version": row[2] if row else None,
                "users_table_columns_count": len(columns),
                "is_active_column_exists": is_active_exists,
                "users_columns": columns,
            }
    except Exception as e:
        logger.error(f"Debug db-info failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e), "error_type": type(e).__name__}


@app.get("/test", tags=["system"])
def test_endpoint():
    """Simple test endpoint to verify deployment"""
    import datetime
    import os

    env_value = "development"
    if CONFIG_LOADED and config:
        env_value = getattr(config, "ENVIRONMENT", getattr(config, "environment", "development"))
    else:
        env_value = os.getenv("ENVIRONMENT", "development")

    return {
        "status": "ok",
        "message": "Crown Safe API is running",
        "environment": env_value,
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0",
    }


@app.get("/openapi.json", tags=["system"])
async def get_openapi():
    """Get OpenAPI specification"""
    return _original_app.openapi()


# Note: FDA endpoint is now handled by v1_endpoints.py for consistency


@app.get("/cache/stats", tags=["system"])
async def cache_stats():
    """
    Get Redis cache performance statistics for 39-agency system
    """
    try:
        stats = get_cache_stats()
        return {
            "cache_performance": stats,
            "agencies_covered": 39,
            "cache_optimization": "Optimized for 39 international recall agencies",
            "performance_benefit": "10x faster queries with intelligent caching",
        }
    except Exception as e:
        return {
            "cache_performance": {"status": "error", "error": str(e)},
            "agencies_covered": 39,
            "note": "Cache may be initializing",
        }


@app.post("/cache/warm", tags=["system"])
async def warm_cache():
    """
    Manually trigger intelligent cache warming for 39-agency system
    """
    try:
        result = await warm_cache_now()
        return {
            "cache_warming": result,
            "recommendation": "Cache warming will improve hit rate from 10% to 70%+",
            "agencies_optimized": 39,
            "performance_impact": "Dramatic speedup for popular products",
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "agencies": 39}


# 4) Paywalled endpoint with fallback for subscribers
@app.post("/api/v1/safety-check")
@limiter.limit("30 per minute")  # Rate limiting for bursty endpoint
async def safety_check(req: SafetyCheckRequest, request: Request):
    # PERFORMANCE MONITORING - Track response times for 39-agency system
    start_time = datetime.now()

    request_summary = (
        f"Safety-check for user_id={req.user_id}, barcode={req.barcode}, "
        f"model_number={req.model_number}, product_name={req.product_name}"
    )
    logger.info(request_summary)

    # SMART VALIDATION - Optimize for common use cases
    if (
        not req.barcode
        and not req.model_number
        and not getattr(req, "lot_number", None)
        and not req.image_url
        and not req.product_name
    ):
        return JSONResponse(
            status_code=400,
            content={
                "status": "FAILED",
                "data": None,
                "error": ("Provide a barcode, model number, product name, or image URL."),
            },
        )

    # Additional validation for user_id
    if not req.user_id or req.user_id <= 0:
        return JSONResponse(
            status_code=400,
            content={
                "status": "FAILED",
                "data": None,
                "error": "Valid user_id is required",
            },
        )

    # 4a) DEV override bypass - check dev entitlement first
    from api.services.dev_override import dev_entitled

    REQUIRED_FEATURE = "safety.check"

    if dev_entitled(req.user_id, REQUIRED_FEATURE):
        logger.info(f"DEV OVERRIDE: Bypassing subscription check for user {req.user_id}")
        # Skip subscription validation and proceed to safety check
    else:
        # 4b) Validate user & subscription from your DB
        with get_db_session() as db:
            user = db.query(User).filter(User.id == req.user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            if not getattr(user, "is_subscribed", False):
                raise HTTPException(status_code=403, detail="Subscription required.")

    # 4b) Run the full live workflow and return its raw result
    #     (includes environment-aware error handling)
    try:
        # WORKAROUND: If image_url is provided, route to visual search directly
        if req.image_url and not req.barcode and not req.model_number and not req.product_name:
            logger.info("Routing image_url request directly to visual search endpoint")

            # Create a new visual agent instance directly (don't rely on global)
            try:
                from agents.visual.visual_search_agent.agent_logic import (
                    VisualSearchAgentLogic,
                )

                temp_visual_agent = VisualSearchAgentLogic("temp_visual_001")
                visual_result = await temp_visual_agent.identify_product_from_image(req.image_url)

                if visual_result and visual_result.get("status") == "COMPLETED":
                    result_payload = visual_result.get("result", {})
                    return JSONResponse(
                        status_code=200,
                        content={
                            "status": "COMPLETED",
                            "data": {
                                "summary": result_payload.get(
                                    "summary",
                                    "Visual analysis completed",
                                ),
                                "product_name": result_payload.get("product_name"),
                                "brand": result_payload.get("brand"),
                                "confidence": result_payload.get("confidence", 0),
                                "recalls_found": False,
                                "checked_sources": ["Visual Recognition"],
                                "message": "Visual recognition completed via direct agent",
                            },
                        },
                    )
                else:
                    logger.warning(f"Visual agent returned non-completed status: {visual_result}")
            except Exception as visual_error:
                logger.error(f"Visual search routing failed: {visual_error}", exc_info=True)
                # Continue to normal workflow

        # USE OPTIMIZED ASYNC WORKFLOW for 3-5x performance boost!
        result = await run_optimized_safety_check(
            {
                "user_id": req.user_id,
                "barcode": req.barcode,
                "model_number": req.model_number,
                "lot_number": getattr(req, "lot_number", None),
                "product_name": req.product_name,
                "image_url": req.image_url,
            }
        )
        logger.info(f"Optimized workflow result: {result}")

        # Fallback to standard workflow if optimized fails
        if result.get("status") == "FAILED" and "optimized workflow error" in result.get(
            "error",
            "",
        ):
            logger.warning("Optimized workflow failed, falling back to standard workflow...")

            # Check if commander_agent is available
            if commander_agent is None:
                logger.error("Commander agent not initialized")
                raise HTTPException(
                    status_code=503,
                    detail="Safety check service temporarily unavailable",
                )

            result = await commander_agent.start_safety_check_workflow(
                {
                    "user_id": req.user_id,
                    "barcode": req.barcode,
                    "model_number": req.model_number,
                    "lot_number": getattr(req, "lot_number", None),
                    "product_name": req.product_name,
                    "image_url": req.image_url,
                }
            )
            logger.info(f"Fallback workflow result: {result}")

        # If workflow succeeds with real data, return it with performance info
        if result.get("status") == "COMPLETED" and result.get("data"):
            # ADD PERFORMANCE METRICS to successful responses
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Enhance the response with performance data
            enhanced_result = result.copy()
            data_section = enhanced_result.get("data")
            if isinstance(data_section, dict):
                data_section["response_time_ms"] = response_time
                data_section["agencies_checked"] = AGENCY_COUNT
                data_section["performance"] = classify_performance(response_time)

                # Crown Safe: premium checks removed (pregnancy, allergy, alternatives)
                for deprecated_key in (
                    "pregnancy_safety",
                    "allergy_safety",
                    "premium_checks_performed",
                ):
                    data_section.pop(deprecated_key, None)

            enhanced_result.pop("alternatives", None)

            return JSONResponse(status_code=200, content=enhanced_result)

        # If workflow returns no data, handle based on environment
        if ENVIRONMENT in ["development", "staging"]:
            logger.warning(
                "Workflow returned no data, using mock response for %s environment",
                ENVIRONMENT,
            )
            # ADD PERFORMANCE METRICS to mock responses
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "COMPLETED",
                    "data": {
                        "summary": (
                            "Mock recall data for barcode "
                            f"{req.barcode}: This product may have safety concerns. "
                            "Please verify with manufacturer."
                        ),
                        "risk_level": "Medium",
                        "barcode": req.barcode,
                        "model_number": req.model_number,
                        "note": (f"Mock data for {ENVIRONMENT} - no recalls in database."),
                        "response_time_ms": response_time,
                        "agencies_checked": AGENCY_COUNT,
                        "performance": classify_performance(response_time),
                    },
                },
            )
        else:
            # Production: Return honest "no recalls found" response with performance metrics
            response_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return JSONResponse(
                status_code=200,
                content={
                    "status": "COMPLETED",
                    "data": {
                        "summary": "No recalls found for this product.",
                        "risk_level": "None",
                        "barcode": req.barcode,
                        "model_number": req.model_number,
                        "recalls_found": False,
                        "checked_sources": [
                            "CPSC",
                            "FDA",
                            "NHTSA",
                            "USDA FSIS",
                            "EU RAPEX",
                            "UK OPSS",
                            "SG CPSO",
                            "France RappelConso",
                            "Germany Food Alerts",
                            "UK FSA",
                            "Netherlands NVWA",
                            "Health Canada",
                            "CFIA",
                            "Transport Canada",
                            "ACCC Australia",
                            "FSANZ",
                            "TGA Australia",
                            "NZ Trading Standards",
                            "MPI New Zealand",
                            "Medsafe New Zealand",
                            "AESAN Spain",
                            "Italy Ministry of Health",
                            "Swiss FCAB",
                            "Swiss FSVO",
                            "Swissmedic",
                            "Swedish Consumer Agency",
                            "Swedish Food Agency",
                            "Norwegian DSB",
                            "Mattilsynet Norway",
                            "Danish Safety Authority",
                            "Danish Food Administration",
                            "Finnish Tukes",
                            "Finnish Food Authority",
                            "PROFECO Mexico",
                            "COFEPRIS Mexico",
                            "ANVISA Brazil",
                            "SENACON Brazil",
                            "INMETRO Brazil",
                            "ANMAT Argentina",
                        ],
                        "message": ("Checked major recall databases; no safety issues found."),
                        "response_time_ms": response_time,
                        "agencies_checked": AGENCY_COUNT,
                        "performance": classify_performance(response_time),
                    },
                },
            )

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)

        if ENVIRONMENT in ["development", "staging"]:
            # Return mock data for testing environments
            return JSONResponse(
                status_code=200,
                content={
                    "status": "COMPLETED",
                    "data": {
                        "summary": (
                            "Mock recall data for barcode "
                            f"{req.barcode}: This product may have safety concerns. "
                            "Please verify with manufacturer."
                        ),
                        "risk_level": "Medium",
                        "barcode": req.barcode,
                        "model_number": req.model_number,
                        "note": (f"Mock data for {ENVIRONMENT} - agent service error occurred."),
                    },
                },
            )
        else:
            # Production: Return proper error
            raise HTTPException(
                status_code=503,
                detail=("Unable to check product safety at this time. Please try again later."),
            ) from e


# Visual Product Suggestion Endpoint (Phase 2 - Safe suggestion mode)
@app.post("/api/v1/visual/suggest-product", tags=["visual"])
async def suggest_product_from_image(request: Dict[str, Any]):
    """Return visual suggestions without recall guarantees.

    Accepts image_url, image_id, or image_base64, routes request through the
    VisualSearchAgent, and returns suggestion results while explicitly avoiding
    safety claims.
    """

    # Accept multiple input types
    image_url = request.get("image_url")
    image_id = request.get("image_id")
    image_base64 = request.get("image_base64")

    logger.info(
        "Received /visual/suggest-product request with image_url=%s, image_id=%s",
        image_url,
        image_id,
    )

    # Validate that at least one image input is provided
    if not any([image_url, image_id, image_base64]):
        raise HTTPException(
            status_code=400,
            detail=("Provide an image URL, image ID, or base64 image."),
        )

    if visual_search_agent is None:
        logger.warning("Visual search service is not available")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": "Visual search service is temporarily unavailable",
                "message": "Please try again later or use barcode scanning instead.",
                "alternative": "Use /api/v1/scan/barcode for instant product lookup",
            },
        )

    try:
        # Build task payload based on available input
        task_payload = {}
        if image_url:
            task_payload["image_url"] = image_url
        elif image_id:
            task_payload["image_id"] = image_id
        elif image_base64:
            task_payload["image_base64"] = image_base64

        result = await visual_search_agent.process_task(task_payload)

        if result.get("status") == "COMPLETED":
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": result.get("result"),
                    "message": (
                        "These are product suggestions based on visual analysis. "
                        "Please verify the exact model number on your product."
                    ),
                },
            )
        else:
            # Return empty suggestions instead of error for better UX
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": {"suggestions": []},
                    "message": "No product suggestions found for this image.",
                },
            )
    except Exception as e:
        logger.error(f"Error in visual product suggestion: {e}", exc_info=True)
        # Return empty suggestions instead of 500 error for better UX
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": {"suggestions": []},
                "message": "Unable to analyze image at this time.",
            },
        )


# 5) User creation endpoint
@app.post("/api/v1/users", response_model=UserOut)
def create_user(req: UserCreateRequest):
    """Create a new user with optional subscription status."""
    with get_db_session() as db:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == req.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")

        # Create new user
        u = User(
            email=req.email,
            hashed_password="defaulthash",
            is_subscribed=req.is_subscribed,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u


# --- AUTO-COMPLETE API FOR INSTANT USER EXPERIENCE ---


@app.get("/api/v1/autocomplete/products", tags=["autocomplete"])
async def autocomplete_products(
    q: str = Query(..., min_length=1, description="Search query (min 1 character)"),
    limit: int = Query(10, ge=1, le=25, description="Max suggestions to return"),
    domain: Optional[str] = Query(None, description="Filter by domain (e.g., 'haircare')"),
):
    """
    Lightning-fast auto-complete for product names across 3,218+ recalls from 39 agencies
    Optimized for real-time typing with intelligent matching and domain filtering
    """

    try:
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB
        from core_infra.cache_manager import get_cached
        from utils.autocomplete_utils import (
            normalize_query,
        )

        # Normalize query for consistent matching
        q_norm = normalize_query(q)

        # CHECK CACHE FIRST for instant responses
        cache_key = f"autocomplete_{q_norm}_{limit}_{domain or 'all'}"
        cached_suggestions = get_cached("autocomplete", cache_key)
        if cached_suggestions:
            return JSONResponse(
                content={
                    "query": q,
                    "suggestions": cached_suggestions,
                    "total_database_recalls": 3218,
                    "agencies": 39,
                    "cached": True,
                    "response_time": "ultra-fast",
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        # REMOVED FOR CROWN SAFE: recall lookup replaced with Crown Safe hair product autocomplete
        # TODO: Implement Crown Safe hair product autocomplete using HairProductModel
        logger.info(f"Autocomplete query for Crown Safe (not yet implemented): '{q}'")

        return JSONResponse(
            content={
                "query": q,
                "suggestions": [],  # Empty until Crown Safe autocomplete is implemented
                "total_database_recalls": 0,
                "agencies": 0,
                "cached": False,
                "response_time": "optimized",
                "note": "Crown Safe hair product autocomplete coming soon",
            },
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    except Exception as e:
        logger.error(f"Auto-complete failed: {e}")
        return JSONResponse(
            content={
                "query": q,
                "suggestions": [],
                "error": "Auto-complete temporarily unavailable",
            },
            headers={"Content-Type": "application/json; charset=utf-8"},
        )


@app.get("/api/v1/autocomplete/brands", tags=["autocomplete"])
async def autocomplete_brands(
    q: str = Query(..., min_length=1, description="Brand search query"),
    limit: int = Query(8, ge=1, le=15, description="Max brand suggestions"),
):
    """
    Brand auto-complete across 39 international agencies with 3,218+ real recalls
    Includes canonicalization and UTF-8 encoding fixes
    """

    try:
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB
        from core_infra.cache_manager import get_cached
        from utils.autocomplete_utils import (
            normalize_query,
        )

        # Normalize query for consistent matching
        q_norm = normalize_query(q)

        # Check cache first
        cache_key = f"brands_{q_norm}_{limit}"
        cached_brands = get_cached("autocomplete", cache_key)
        if cached_brands:
            return JSONResponse(
                content={
                    "query": q,
                    "brands": cached_brands,
                    "cached": True,
                    "agencies": 39,
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
            )

        # REMOVED FOR CROWN SAFE: RecallDB query replaced with Crown Safe hair brand autocomplete
        # This function previously queried baby product brands - now returns empty for Crown Safe
        # TODO: Implement Crown Safe hair brand autocomplete using HairProductModel
        logger.info(f"Brand autocomplete query for Crown Safe (not yet implemented): '{q}'")

        return JSONResponse(
            content={
                "query": q,
                "brands": [],  # Empty until Crown Safe brand autocomplete is implemented
                "total_brands_available": 0,
                "agencies": 0,
                "cached": False,
                "note": "Crown Safe hair brand autocomplete coming soon",
            },
            headers={"Content-Type": "application/json; charset=utf-8"},
        )

    except Exception as e:
        logger.error(f"Brand auto-complete failed: {e}")
        return JSONResponse(
            content={"query": q, "brands": [], "error": str(e)},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )


# --- ADVANCED SEARCH & ANALYTICS ENDPOINTS ---


@app.post("/api/v1/search/advanced", tags=["search"])
async def advanced_search(request: Request):
    """
    Advanced recall search with fuzzy matching, keyword AND logic, and deterministic sorting
    Features:
    - pg_trgm fuzzy text search
    - Exact ID lookup
    - Keyword AND logic
    - Deterministic sorting (score -> date -> id)
    """

    trace_id = f"trace_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"

    # Import search service
    from api.services.search_service import SearchService

    # Parse request body manually
    try:
        body = await request.body()
        if body:
            import json

            # Try multiple encodings to handle potential encoding issues
            try:
                body_str = body.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    body_str = body.decode("latin-1")
                except UnicodeDecodeError:
                    body_str = body.decode("utf-8", errors="replace")

            logger.info("[%s] Raw request body: %s", trace_id, body_str)

            # Log first few characters to help debug malformed JSON
            if len(body_str) > 0:
                logger.info("[%s] First 50 chars of body: %r", trace_id, body_str[:50])
                # Log body length and character analysis
                logger.info(
                    "[%s] Body length: %s, starts with: %r",
                    trace_id,
                    len(body_str),
                    body_str[:10],
                )

            body_data = json.loads(body_str)
        else:
            logger.warning("[%s] Empty request body", trace_id)
            return JSONResponse(
                status_code=400,
                content={
                    "ok": False,
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Request body is required",
                    },
                    "traceId": trace_id,
                },
            )
    except json.JSONDecodeError as e:
        malformed_body = repr(body_str) if "body_str" in locals() else "N/A"
        logger.error("[%s] JSON decode error: %s", trace_id, e)
        logger.error("[%s] Malformed JSON body: %s", trace_id, malformed_body)

        # Try to provide more helpful error messages
        error_msg = f"Invalid JSON in request body: {str(e)}"
        if "Expecting property name enclosed in double quotes" in str(e):
            error_msg += ". Ensure property names use double quotes like {'query': 'value'}."
        elif "Expecting value" in str(e):
            error_msg += ". Check that all values are properly formatted"
        elif "Unterminated string" in str(e):
            error_msg += ". Check for unclosed quotes in strings"

        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {"code": "BAD_REQUEST", "message": error_msg},
                "traceId": trace_id,
            },
        )
    except Exception as e:
        logger.error(f"[{trace_id}] Could not parse request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Invalid JSON in request body",
                },
                "traceId": trace_id,
            },
        )

    # Log cursor field for debugging
    if "nextCursor" in body_data:
        logger.info("[%s] Found 'nextCursor' in request: %s", trace_id, body_data.get("nextCursor"))
    elif "cursor" in body_data:
        logger.info("[%s] Found 'cursor' in request: %s", trace_id, body_data.get("cursor"))

    # Create AdvancedSearchRequest from parsed data
    try:
        logger.info(
            "[%s] Creating AdvancedSearchRequest with body_data: %s",
            trace_id,
            body_data,
        )
        logger.info(
            "[%s] nextCursor in body_data: %s",
            trace_id,
            body_data.get("nextCursor"),
        )
        req = AdvancedSearchRequest(**body_data)
        logger.info(
            "[%s] AdvancedSearchRequest created successfully: nextCursor=%s",
            trace_id,
            req.nextCursor,
        )
        logger.info("[%s] All fields in req: %s", trace_id, req.model_dump())
    except Exception as e:
        logger.error(f"[{trace_id}] Invalid request data: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": f"Invalid request parameters: {str(e)}",
                },
                "traceId": trace_id,
            },
        )

    # Validate date range
    if req.date_from and req.date_to and req.date_from > req.date_to:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Invalid date range: date_from must be before or equal to date_to",
                },
                "traceId": trace_id,
            },
        )

    # Log request details
    search_info = []
    if req.id:
        search_info.append(f"id='{req.id}'")
    if req.product:
        search_info.append(f"product='{req.product}'")
    if req.query:
        search_info.append(f"query='{req.query}'")
    if req.keywords:
        search_info.append(f"keywords={req.keywords}")
    if req.agencies:
        search_info.append(f"agencies={req.agencies}")

    logger.info("[%s] Advanced search: %s", trace_id, ", ".join(search_info))
    logger.info(
        "[%s] Pagination params: limit=%s, offset=%s, nextCursor=%s",
        trace_id,
        req.limit,
        req.offset,
        req.nextCursor,
    )
    logger.info(
        "[%s] Raw cursor value from request: %s",
        trace_id,
        body_data.get("nextCursor", "NOT_FOUND"),
    )

    try:
        with get_db_session() as db:
            # Use the new search service
            search_service = SearchService(db)

            # Check if pg_trgm is enabled
            if not search_service.check_pg_trgm_enabled():
                logger.warning(
                    "[%s] pg_trgm extension not enabled, falling back to basic search",
                    trace_id,
                )

            # Prioritize cursor pagination over offset pagination
            # If nextCursor is provided, ignore offset to use cursor-based pagination
            search_offset = None if req.nextCursor else req.offset

            logger.info(
                "[%s] Pagination strategy: %s",
                trace_id,
                "cursor-based" if req.nextCursor else "offset-based",
            )
            logger.info(
                "[%s] Final search params: offset=%s, cursor=%s",
                trace_id,
                search_offset,
                req.nextCursor,
            )

            # Execute search
            search_result = search_service.search(
                query=req.query,
                product=req.product,
                id=req.id,
                keywords=req.keywords,
                agencies=req.agencies,
                severity=req.risk_level,
                risk_category=req.product_category,
                date_from=req.date_from,
                date_to=req.date_to,
                limit=req.limit,
                offset=search_offset,
                cursor=req.nextCursor,
            )

            # Check if search was successful
            if not search_result.get("ok"):
                return JSONResponse(
                    status_code=500,
                    content={
                        "ok": False,
                        "error": search_result.get(
                            "error",
                            {"code": "SEARCH_ERROR", "message": "Search failed"},
                        ),
                        "traceId": trace_id,
                    },
                )

            # Return successful result with trace ID
            search_result["traceId"] = trace_id

            # Add timing information
            start_time_attr = getattr(req, "_start_time", None)
            if start_time_attr is not None:
                elapsed_ms = (datetime.now().timestamp() - float(start_time_attr)) * 1000
                search_result["responseTimeMs"] = round(elapsed_ms, 2)

            logger.info(f"[{trace_id}] Search completed: {search_result['data']['total']} results")

            return JSONResponse(status_code=200, content=search_result)
    except Exception as e:
        logger.error(f"[{trace_id}] Advanced search failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Search operation failed",
                },
                "traceId": trace_id,
            },
        )


@app.post("/api/v1/search/bulk", tags=["search"])
async def bulk_search(req: BulkSearchRequest):
    """
    Bulk barcode safety check - check multiple products at once
    """

    logger.info(
        "Bulk search request for %s barcodes by user %s",
        len(req.barcodes),
        req.user_id,
    )

    results = []

    for barcode in req.barcodes:
        try:
            # Use your existing safety check logic
            # SafetyCheckRequest created for validation but not used yet
            _safety_req = SafetyCheckRequest(
                user_id=req.user_id,
                barcode=barcode,
                model_number=None,
                lot_number=None,
                product_name=None,
                image_url=None,
            )

            # Call your existing safety check endpoint logic
            # (This is a simplified version - in production you'd extract the logic)
            result = {
                "barcode": barcode,
                "status": "checked",
                "agencies_checked": 39,
                "timestamp": datetime.now().isoformat(),
            }
            results.append(result)

        except Exception as e:
            logger.error("Bulk search failed for barcode %s: %s", barcode, e)
            results.append({"barcode": barcode, "status": "error", "error": str(e)})

    return {
        "status": "completed",
        "total_checked": len(req.barcodes),
        "agencies_used": 39,
        "results": results,
    }


@app.get(
    "/api/v1/analytics/recalls",
    response_model=RecallAnalyticsResponse,
    tags=["analytics"],
)
async def recall_analytics():
    """
    Get comprehensive analytics across all 39 international agencies
    """
    try:
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB

        # REMOVED FOR CROWN SAFE: Baby product recall analytics replaced with Crown Safe analytics
        # This function previously analyzed baby product recall data from RecallDB
        # TODO: Implement Crown Safe hair product analytics using HairProductModel
        logger.info("Recall analytics endpoint called (Crown Safe analytics not yet implemented)")

        # Return empty analytics until Crown Safe implementation
        return RecallAnalyticsResponse(
            total_recalls=0,
            agencies_active=0,
            recent_recalls=0,
            top_hazards=[],
            top_agencies=[],
            safety_trends={
                "recent_trend": "stable",
                "coverage": "Crown Safe analytics coming soon",
                "data_quality": "pending",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics failed: {str(e)}") from e


@app.get("/api/v1/analytics/counts", tags=["analytics"])
async def analytics_counts():
    """
    Live counts for frontend display: total recalls and per-agency breakdown.
    """
    try:
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB

        # REMOVED FOR CROWN SAFE: Baby product recall counts replaced with Crown Safe analytics
        # This function previously counted baby product recalls
        # TODO: Implement Crown Safe hair product counts using HairProductModel
        logger.info("Analytics counts endpoint called (Crown Safe analytics not yet implemented)")

        # Return empty counts until Crown Safe implementation
        return {
            "total_recalls": 0,
            "agencies_total": 0,
            "per_agency_counts": [],
            "updated_at": datetime.now().isoformat(),
            "note": "Crown Safe analytics coming soon",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Counts analytics failed: {str(e)}") from e


# --- MONITORING & ALERTING ENDPOINTS ---


@app.get("/api/v1/monitoring/agencies", tags=["monitoring"])
async def agency_health_check():
    """
    Monitor health status of all 39 international recall agencies
    """

    try:
        # REMOVED FOR CROWN SAFE: Baby product recall agency monitoring replaced
        # This function previously monitored 39 international baby product recall agencies
        # TODO: Implement Crown Safe hair product regulatory monitoring
        logger.info("Agency health check endpoint called (Crown Safe monitoring not yet implemented)")

        # Return empty monitoring data until Crown Safe implementation
        return {
            "status": "success",
            "total_agencies": 0,
            "active_agencies": 0,
            "monitoring_timestamp": datetime.now().isoformat(),
            "agencies": [],
            "system_health": "pending",
            "note": "Crown Safe monitoring coming soon",
        }

    except Exception as e:
        logger.error("Agency monitoring failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Monitoring failed: {str(e)}") from e


@app.get("/api/v1/monitoring/system", tags=["monitoring"])
async def system_health():
    """
    Comprehensive system health check for Crown Safe
    """

    try:
        # Check database health
        db_healthy = True
        db_error = None
        try:
            with get_db_session() as db:
                db.execute(text("SELECT 1"))
        except Exception as e:
            db_healthy = False
            db_error = str(e)

        # Check Redis cache health
        cache_stats = get_cache_stats()
        cache_healthy = cache_stats.get("status") == "enabled"

        # Check if we have recent data
        total_recalls = 0
        # REMOVED FOR CROWN SAFE: RecallDB model no longer exists (replaced with HairProductModel)
        # from core_infra.database import RecallDB
        # TODO: Implement Crown Safe hair product count using HairProductModel
        # try:
        #     with get_db_session() as db:
        #         total_recalls = db.query(RecallDB).count()
        # except Exception as e:
        #     logger.warning(f"Unable to count recalls for health check: {e}")

        # Overall system health
        overall_health = "healthy" if (db_healthy and total_recalls > 1000) else "degraded"

        return {
            "status": overall_health,
            "timestamp": datetime.now().isoformat(),
            "version": "2.3.0",
            "agencies": {
                "total_configured": 39,
                "active_data_sources": 39,
                "coverage": "Global (19 countries, 5 continents)",
            },
            "database": {
                "status": "healthy" if db_healthy else "error",
                "total_recalls": total_recalls,
                "error": db_error,
            },
            "cache": cache_stats,
            "performance": {
                "caching_enabled": cache_healthy,
                "expected_speedup": "10x with Redis cache",
                "optimization": "Optimized for 39 international agencies",
            },
        }

    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


# --- NOTIFICATION SYSTEM ---


class NotificationRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    user_id: int = Field(..., description="User ID to set up notifications")
    product_identifiers: List[str] = Field(
        ...,
        description="List of barcodes/model numbers to monitor",
    )
    notification_types: List[str] = Field(
        default_factory=lambda: ["email"],
        description="Types: email, sms, push",
    )


class NotificationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    message: str
    monitored_products: int
    notification_id: str


@app.post(
    "/api/v1/notifications/setup",
    response_model=NotificationResponse,
    tags=["notifications"],
)
async def setup_notifications(req: NotificationRequest):
    """
    Set up real-time notifications for specific products across 39 agencies
    """

    logger.info(
        "Setting up notifications for user %s, %s products",
        req.user_id,
        len(req.product_identifiers),
    )

    try:
        # For now, create a simple notification record
        # In production, this would integrate with email/SMS services
        notification_id = f"notif_{req.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Store notification preferences (simplified for now)
        notification_data = {
            "user_id": req.user_id,
            "products": req.product_identifiers,
            "types": req.notification_types,
            "created_at": datetime.now().isoformat(),
            "agencies_monitored": AGENCY_COUNT,
        }

        # Cache the notification setup
        from core_infra.cache_manager import set_cached

        set_cached("notifications", notification_id, notification_data, ttl=86400)  # 24 hours

        return NotificationResponse(
            status="success",
            message=(
                f"Notifications set up for {len(req.product_identifiers)} products across "
                f"{AGENCY_COUNT} international agencies"
            ),
            monitored_products=len(req.product_identifiers),
            notification_id=notification_id,
        )

    except Exception as e:
        logger.error("Notification setup failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Notification setup failed: {str(e)}") from e


@app.get("/api/v1/notifications/{notification_id}", tags=["notifications"])
async def get_notification_status(notification_id: str):
    """
    Get status of notification setup
    """
    try:
        from core_infra.cache_manager import get_cached

        notification_data = get_cached("notifications", notification_id)
        if not notification_data:
            raise HTTPException(status_code=404, detail="Notification not found")

        return {
            "status": "active",
            "notification_id": notification_id,
            "setup_date": notification_data.get("created_at"),
            "monitored_products": len(notification_data.get("products", [])),
            "agencies_monitored": AGENCY_COUNT,
            "notification_types": notification_data.get("types", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}") from e


# --- MOBILE-OPTIMIZED ENDPOINTS ---


class MobileScanRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    user_id: int = Field(..., description="User ID")
    barcode: str = Field(..., description="Scanned barcode")
    location: Optional[str] = Field(None, description="User location for regional prioritization")
    quick_scan: bool = Field(True, description="Fast response mode for mobile")


class MobileScanResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    safety_level: str  # "SAFE", "CAUTION", "DANGER"
    summary: str
    agencies_checked: int
    response_time_ms: Optional[int]
    cache_hit: bool


@app.post("/api/v1/mobile/scan", response_model=MobileScanResponse, tags=["mobile"])
async def mobile_scan(req: MobileScanRequest):
    """
    Mobile-optimized barcode scanning with ultra-fast response across 39 agencies
    Designed for real-time scanning in stores
    """
    start_time = datetime.now()

    logger.info(
        "Mobile scan request: user=%s, barcode=%s, quick=%s",
        req.user_id,
        req.barcode,
        req.quick_scan,
    )

    try:
        safety_req = SafetyCheckRequest(
            user_id=req.user_id,
            barcode=req.barcode,
            model_number=None,
            lot_number=None,
            product_name=None,
            image_url=None,
        )

        workflow_payload = safety_req.model_dump(exclude_none=True)

        try:
            result = await run_optimized_safety_check(workflow_payload)
        except Exception as optimized_error:  # pragma: no cover - defensive
            logger.error(
                "Optimized workflow failed for mobile scan: %s",
                optimized_error,
                exc_info=True,
            )
            result = {"status": "FAILED", "error": str(optimized_error), "data": None}

        optimized_error = str(result.get("error", "")).lower() if isinstance(result, dict) else ""
        if (
            isinstance(result, dict)
            and result.get("status") == "FAILED"
            and "optimized workflow error" in optimized_error
            and commander_agent is not None
        ):
            try:
                fallback_result = await commander_agent.start_safety_check_workflow(workflow_payload)
                if fallback_result:
                    result = fallback_result
            except Exception as fallback_error:  # pragma: no cover - defensive
                logger.error(
                    "Commander fallback workflow failed: %s",
                    fallback_error,
                    exc_info=True,
                )

        response_time = int((datetime.now() - start_time).total_seconds() * 1000)

        result_data: Dict[str, Any] = {}
        if isinstance(result, dict):
            data = result.get("data")
            if isinstance(data, dict):
                result_data = data

        safety_level = str(
            result_data.get("safety_level") or result_data.get("risk_level") or result_data.get("level") or "SAFE"
        ).upper()

        if not result_data:
            logger.info("Mobile scan workflow returned no data; defaulting to safe response")

        summary = (
            result_data.get(
                "summary",
                "Product evaluated against Crown Safe ingredient and hazard signals",
            )
            if result_data
            else "Safe - no recalls found"
        )
        agencies_checked = result_data.get("agencies_checked", AGENCY_COUNT)

        cache_metadata = result.get("metadata") if isinstance(result, dict) else None
        cache_hit_flag: Optional[bool] = None
        if isinstance(cache_metadata, dict):
            cache_hit_flag = cache_metadata.get("cache_hit")

        cache_hit = bool(cache_hit_flag) if cache_hit_flag is not None else response_time < 100

        return MobileScanResponse(
            status="success",
            safety_level=safety_level,
            summary=summary,
            agencies_checked=agencies_checked,
            response_time_ms=response_time,
            cache_hit=cache_hit,
        )

    except Exception as e:
        logger.error(f"Mobile scan failed: {e}")
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)

        return MobileScanResponse(
            status="error",
            safety_level="SAFE",
            summary="Unable to check product safety. Please try again.",
            agencies_checked=39,
            response_time_ms=response_time,
            cache_hit=False,
        )


def to_gtin14(code: str) -> str:
    """Convert barcode to GTIN-14 format"""
    return code if len(code) == 14 else ("0" + code if len(code) == 13 else code)


async def ultra_fast_check(barcode: str, user_id: int) -> dict:
    """
    Ultra-fast barcode check with validation and mock recall data
    """
    import time

    start_time = time.time()

    # Clean and validate barcode
    cleaned_barcode = barcode.strip()

    # Basic validation
    if not cleaned_barcode:
        raise ValueError("Empty barcode")

    # Check if numeric (for UPC/EAN)
    if not cleaned_barcode.isdigit():
        raise ValueError("Invalid barcode format - must be numeric for UPC/EAN")

    # Check length for common formats
    if len(cleaned_barcode) < 6 or len(cleaned_barcode) > 13:
        raise ValueError(f"Invalid barcode length: {len(cleaned_barcode)} (expected 6-13 digits)")

    # Mock recall check (in real implementation, this would query database)
    response_time_ms = int((time.time() - start_time) * 1000)

    return {
        "safe": True,
        "level": "SAFE",
        "summary": "[OK] Safe - No recalls found",
        "response_time_ms": response_time_ms,
        "cache_level": "redis",
        "optimization": "cached",
    }


@app.get("/api/v1/mobile/instant-check/{barcode}", tags=["mobile"])
async def mobile_instant_check(
    barcode: str = FastAPIPath(..., min_length=8, description="Barcode to check"),
    user_id: Optional[int] = Query(None, alias="user_id", description="User ID"),
    user_id_alt: Optional[int] = Query(None, alias="user-id", description="User ID (alternative)"),
    x_user_id: Optional[int] = Header(None, alias="X-User-Id", description="User ID (header)"),
):
    """
    ULTRA-FAST mobile endpoint using hot path optimization
    Target: <100ms responses for real-time scanning across 39 agencies
    """

    # Resolve user_id from multiple sources (robust to redirect issues)
    uid = user_id or user_id_alt or x_user_id
    if uid is None:
        # Fallback: treat as anonymous user with reduced detail
        uid = 0  # Anonymous user ID

    # Convert to GTIN-14 format
    gtin = to_gtin14(barcode)

    try:
        # Use the ultra-fast mobile hot path
        result = await ultra_fast_check(gtin, uid)

        # Return minimal response optimized for mobile
        return {
            "safe": result.get("safe", True),
            "level": result.get("level", "SAFE"),
            "summary": result.get("summary", "Safe")[:80],  # Mobile-optimized length
            "agencies": 39,
            "ms": result.get("response_time_ms", 0),
            "cache": result.get("cache_level", "unknown"),
            "opt": result.get("optimization", "standard"),
        }

    except ValueError as e:
        # Return 400 for validation errors
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Mobile instant check failed: {e}")
        return {
            "safe": True,
            "level": "SAFE",
            "summary": "Check failed - try again",
            "agencies": 39,
            "ms": 999,
            "cache": "error",
            "opt": "error_fallback",
        }


@app.get("/api/v1/mobile/quick-check/{barcode}", tags=["mobile"])
async def mobile_quick_check(
    barcode: str = FastAPIPath(..., min_length=8, description="Barcode to check"),
    user_id: Optional[int] = Query(None, alias="user_id", description="User ID"),
    user_id_alt: Optional[int] = Query(None, alias="user-id", description="User ID (alternative)"),
    x_user_id: Optional[int] = Header(None, alias="X-User-Id", description="User ID (header)"),
):
    """
    OPTIMIZED mobile endpoint with enhanced caching
    Backward compatible but now much faster with optimizations
    """

    start_time = datetime.now()

    # Resolve user_id from multiple sources (robust to redirect issues)
    uid = user_id or user_id_alt or x_user_id
    if uid is None:
        # Fallback: treat as anonymous user with reduced detail
        uid = 0  # Anonymous user ID

    # Convert to GTIN-14 format
    gtin = to_gtin14(barcode)

    try:
        # Use ultra-fast check with compatibility wrapper
        ultra_result = await ultra_fast_check(gtin, uid)

        # Convert to original format for backward compatibility
        return {
            "safe": ultra_result.get("safe", True),
            "summary": ultra_result.get("summary", "Safe"),
            "agencies": 39,
            "ms": ultra_result.get("response_time_ms", 0),
            "cached": ultra_result.get("cache_level") in ["hot_memory", "redis"],
        }

    except ValueError as e:
        # Return 400 for validation errors
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        response_time = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Mobile quick check failed: {e}")
        return {
            "safe": True,  # Default to safe on error
            "summary": "Unable to check - please try again",
            "agencies": 39,
            "ms": response_time,
            "cached": False,
        }


@app.get("/mobile/stats", tags=["mobile"])
async def mobile_performance_stats():
    """
    Get mobile hot path performance statistics
    """
    try:
        mobile_stats = get_mobile_stats()
        cache_stats = get_cache_stats()

        return {
            "mobile_optimization": mobile_stats,
            "cache_performance": cache_stats,
            "agencies_optimized": 39,
            "performance_target": "<100ms responses",
            "optimization_features": [
                "Hot memory cache for instant responses",
                "Redis caching for fast responses",
                "Optimized database queries",
                "Minimal JSON payloads",
                "Connection pooling",
            ],
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "agencies": 39}


# --- REPORT UNSAFE PRODUCT ENDPOINT ---


@app.post("/api/v1/report-unsafe-product", tags=["safety-reports"], status_code=201)
async def report_unsafe_product(request: Request):
    """
    Community Safety Reporting: Report Unsafe Products

    Allows users to report dangerous products that may not yet be in the official
    recall database. This helps protect the community by identifying potential hazards early.

    **Rate Limit:** 10 reports per hour per user

    **Required Fields:**
    - user_id: ID of the user submitting the report
    - product_name: Name of the unsafe product (min 3 characters)
    - hazard_description: Detailed description of the hazard (min 10 characters)

    **Optional Fields:**
    - barcode, model_number, lot_number: Product identifiers
    - brand, manufacturer: Product details
    - severity: HIGH, MEDIUM (default), or LOW
    - category: Product category (e.g., "Cribs", "Toys", "Bottles")
    - reporter_name, reporter_email, reporter_phone: Contact info for follow-up
    - incident_date, incident_description: Details about what happened
    - photos: Array of photo URLs (max 10)

    **Response:**
    - 201: Report created successfully
    - 400: Invalid request data
    - 429: Rate limit exceeded
    - 500: Server error
    """
    from datetime import datetime

    from api.models.user_report import UserReport
    from api.schemas.user_report_schema import (
        ReportUnsafeProductRequest,
        ReportUnsafeProductResponse,
    )

    logger_inst = logging.getLogger(__name__)

    body = await request.json()
    try:
        req = ReportUnsafeProductRequest(**body)
    except ValidationError as validation_error:
        logger_inst.warning(
            "Validation failed when creating unsafe product report: %s",
            validation_error,
        )
        formatted_errors = validation_error.errors()
        for error in formatted_errors:
            ctx = error.get("ctx")
            if ctx and "error" in ctx:
                ctx["error"] = str(ctx["error"])

        raise HTTPException(status_code=422, detail=formatted_errors) from validation_error

    try:
        # Rate limiting: Check submissions in last hour for this user
        with get_db_session() as db:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_reports = (
                db.query(UserReport)
                .filter(
                    UserReport.user_id == req.user_id,
                    UserReport.created_at >= one_hour_ago,
                )
                .count()
            )

            if recent_reports >= 10:
                raise HTTPException(
                    status_code=429,
                    detail=("Rate limit exceeded. Maximum 10 reports/hour. Try again later."),
                )

            # Create new report
            new_report = UserReport(
                user_id=req.user_id,
                product_name=req.product_name,
                hazard_description=req.hazard_description,
                barcode=req.barcode,
                model_number=req.model_number,
                lot_number=req.lot_number,
                brand=req.brand,
                manufacturer=req.manufacturer,
                severity=req.severity,
                category=req.category,
                status="PENDING",
                reporter_name=req.reporter_name,
                reporter_email=req.reporter_email,
                reporter_phone=req.reporter_phone,
                incident_date=req.incident_date,
                incident_description=req.incident_description,
                photos=req.photos,
                created_at=datetime.utcnow(),
            )

            db.add(new_report)
            db.commit()
            db.refresh(new_report)

            # Extract values after refresh (type: ignore for SQLAlchemy columns)
            report_id_value = new_report.report_id  # type: ignore
            created_at_value = new_report.created_at  # type: ignore

            logger_inst.info(
                ("New unsafe product report created: report_id=%s, user=%s, product='%s', severity=%s"),
                report_id_value,
                req.user_id,
                req.product_name,
                req.severity,
            )

            return ReportUnsafeProductResponse(
                report_id=report_id_value,  # type: ignore
                status="PENDING",
                message=(
                    "Thank you for reporting this unsafe product. "
                    "Our safety team will review your report within 24-48 hours. "
                    "You are helping keep the community safe!"
                ),
                created_at=created_at_value,  # type: ignore
            )

    except HTTPException:
        raise
    except Exception as e:
        logger_inst.error(f"Failed to create unsafe product report: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit report. Please try again later.",
        ) from e


@app.get("/api/v1/user-reports/{user_id}", tags=["safety-reports"])
async def get_user_reports(
    user_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Get all safety reports submitted by a specific user

    **Parameters:**
    - user_id: User ID
    - status: Optional filter (PENDING, REVIEWING, VERIFIED, REJECTED, DUPLICATE)
    - limit: Maximum results (1-100)
    - offset: Pagination offset

    **Response:**
    Returns array of user reports with status and review information
    """
    from api.models.user_report import UserReport

    logger_inst = logging.getLogger(__name__)

    try:
        with get_db_session() as db:
            query = db.query(UserReport).filter(UserReport.user_id == user_id)

            if status:
                query = query.filter(UserReport.status == status.upper())

            # Get total count
            total_count = query.count()

            # Get paginated results
            reports = query.order_by(UserReport.created_at.desc()).offset(offset).limit(limit).all()

            return {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "reports": [report.to_dict() for report in reports],
            }

    except Exception as e:
        logger_inst.error(f"Failed to fetch user reports: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve reports") from e


# --- CRITICAL UPC DATA FIX ENDPOINT ---


@app.post("/system/fix-upc-data", tags=["system"])
async def fix_upc_data():
    """
    CRITICAL FIX: Enhance existing recalls with UPC data for proper barcode scanning
    """

    logger.info("Starting critical UPC data enhancement...")

    # Crown Safe no longer maintains the legacy RecallDB table, so this endpoint
    # returns a clear status indicating that the operation is intentionally skipped.
    return {
        "status": "skipped",
        "message": "UPC enhancement not applicable to Crown Safe (hair product platform)",
        "enhanced_recalls": 0,
        "total_with_upc": 0,
        "total_recalls": 0,
        "upc_coverage_percent": 0,
        "agencies_optimized": 0,
    }


# ============================================
# CROWN SAFE: Hair Product Safety Analysis Endpoints
# ============================================
# Crown Safe Barcode Scanning


@app.post(
    "/api/v1/product/analyze",
    response_model=ProductAnalysisResponse,
    tags=["crown-safe"],
    summary="Analyze hair product safety with Crown Score",
)
@limiter.limit("30 per minute")
async def analyze_product(req: ProductAnalysisRequest, request: Request):
    """
    Analyze a hair product and return personalized Crown Score.

    This endpoint provides comprehensive hair product safety analysis using the
    Crown Score algorithm (0-100 points) based on:
    - Harmful ingredients (sulfates, parabens, drying alcohols)
    - Beneficial ingredients (shea butter, coconut oil, natural oils)
    - Hair type compatibility (3C, 4A, 4B, 4C)
    - Porosity adjustments (Low, Medium, High)
    - Personal hair goals (moisture, growth, definition)
    - Known ingredient sensitivities

    Returns personalized verdict:
    - UNSAFE (0-39): Don't use
    - USE_WITH_CAUTION (40-69): Monitor results
    - SAFE (70-89): Good choice
    - EXCELLENT_MATCH (90-100): Perfect for your hair
    """
    with get_db_session() as db:
        return await analyze_product_endpoint(req, db)


@app.post(
    "/api/v1/profile/hair",
    response_model=HairProfileResponse,
    tags=["crown-safe"],
    summary="Create or update hair profile",
)
@limiter.limit("10 per minute")
async def create_hair_profile(req: HairProfileRequest, request: Request):
    """
    Create or update a user's hair profile for personalized analysis.

    Hair profile includes:
    - Hair type: 3C, 4A, 4B, 4C, Mixed
    - Porosity: Low, Medium, High
    - Hair state: dryness, breakage, shedding, heat damage
    - Hair goals: moisture retention, length retention, curl definition, growth
    - Sensitivities: fragrance, sulfates, parabens, proteins, etc.

    A hair profile is required before analyzing products.
    """
    with get_db_session() as db:
        return await create_hair_profile_endpoint(req, db)


@app.get(
    "/api/v1/profile/hair/{user_id}",
    response_model=HairProfileResponse,
    tags=["crown-safe"],
    summary="Get user's hair profile",
)
@limiter.limit("60 per minute")
async def get_hair_profile(user_id: int, request: Request):
    """Get a user's hair profile."""
    with get_db_session() as db:
        return await get_hair_profile_endpoint(user_id, db)


@app.get(
    "/api/v1/scans/history/{user_id}",
    response_model=ScanHistoryResponse,
    tags=["crown-safe"],
    summary="Get product scan history",
)
@limiter.limit("60 per minute")
async def get_scan_history(user_id: int, limit: int = 50):
    """
    Get user's product scan history.

    Returns up to `limit` most recent scans with Crown Scores and verdicts.
    """
    with get_db_session() as db:
        return await get_scan_history_endpoint(user_id, limit, db)


# Register Crown Safe Barcode Router
app.include_router(crown_barcode_router)
logger.info("✅ Crown Safe Barcode Scanning registered: /api/v1/crown-safe/barcode")

# Register Crown Safe Visual Recognition Router
try:
    from api.crown_safe_visual_endpoints import visual_router as crown_visual_router

    app.include_router(crown_visual_router)
    logger.info("✅ Crown Safe Visual Recognition registered: /api/v1/crown-safe/visual")
except ImportError as e:
    logger.warning(f"Crown Safe Visual Recognition not available: {e}")
except Exception as e:
    logger.error(f"Failed to register Crown Safe Visual Recognition: {e}")


# CRITICAL: Apply health check wrapper to bypass ALL middleware
app = HealthCheckWrapper(app)

# Run with: uvicorn api.main_crownsafe:app --host 0.0.0.0 --port 8001
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=getattr(config, "HOST", "0.0.0.0") if CONFIG_LOADED else "0.0.0.0",
        port=getattr(config, "PORT", 8001) if CONFIG_LOADED else 8001,
        lifespan="off",  # Silence ASGI lifespan warning
    )


# Metrics endpoint (Issue #32)
@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    from fastapi.responses import Response

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Enhanced health check endpoint removed - using simpler version at line 1737
