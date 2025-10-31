"""Global error handlers for BabyShield API
Provides consistent error responses and logging.
"""

import logging
import traceback
from typing import Any

import redis.exceptions
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class BabyShieldException(Exception):
    """Base exception for BabyShield application."""

    def __init__(self, message: str, status_code: int = 500, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BabyShieldException):
    """Validation error."""

    def __init__(self, message: str, field: str | None = None) -> None:
        details = {"field": field} if field else {}
        super().__init__(message, status_code=400, details=details)


class NotFoundError(BabyShieldException):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: Any) -> None:
        message = f"{resource} not found: {identifier}"
        super().__init__(message, status_code=404, details={"resource": resource, "id": identifier})


class AuthenticationError(BabyShieldException):
    """Authentication error."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, status_code=401)


class AuthorizationError(BabyShieldException):
    """Authorization error."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, status_code=403)


class RateLimitError(BabyShieldException):
    """Rate limit exceeded error."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, status_code=429)


async def babyshield_exception_handler(request: Request, exc: BabyShieldException):
    """Handle BabyShield custom exceptions."""
    logger.warning(
        f"BabyShield exception: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions."""
    # Log 404/405 as INFO (normal not found), others as WARNING - DEPLOYMENT FIX
    if exc.status_code in (404, 405):
        logger.info(
            f"HTTP exception: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
            },
        )
    else:
        logger.warning(
            f"HTTP exception: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": exc.status_code,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "detail": exc.detail,  # Include standard FastAPI detail field
            "path": request.url.path,
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database exceptions."""
    logger.error(
        f"Database error: {exc!s}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    # Don't expose internal database errors in production
    message = "Database operation failed" if not logger.isEnabledFor(logging.DEBUG) else str(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": message,
            "type": "database_error",
            "path": request.url.path,
        },
    )


async def redis_exception_handler(request: Request, exc: redis.exceptions.RedisError):
    """Handle Redis exceptions."""
    logger.error(
        f"Redis error: {exc!s}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    # Continue without cache if Redis fails
    return JSONResponse(
        status_code=503,
        content={
            "error": True,
            "message": "Cache service temporarily unavailable",
            "type": "cache_error",
            "path": request.url.path,
        },
    )


async def validation_exception_handler(request: Request, exc: ValueError):
    """Handle validation exceptions."""
    logger.warning(
        f"Validation error: {exc!s}",
        extra={"path": request.url.path, "method": request.method},
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": True,
            "message": str(exc),
            "type": "validation_error",
            "path": request.url.path,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        f"Unhandled exception: {exc!s}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )

    # Don't expose internal errors in production
    message = "An unexpected error occurred" if not logger.isEnabledFor(logging.DEBUG) else str(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": message,
            "type": "internal_error",
            "path": request.url.path,
        },
    )


def register_error_handlers(app) -> None:
    """Register all error handlers with the FastAPI app."""
    import redis.exceptions
    from fastapi import HTTPException
    from sqlalchemy.exc import SQLAlchemyError

    # Register custom exception handlers
    app.add_exception_handler(BabyShieldException, babyshield_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, database_exception_handler)
    app.add_exception_handler(redis.exceptions.RedisError, redis_exception_handler)
    app.add_exception_handler(ValueError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("✅ Error handlers registered")
