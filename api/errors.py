"""
Unified error handling for consistent API responses
All errors follow the same JSON structure with correlation IDs
"""

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")


def create_error_payload(code: str, message: str, trace_id: str | None = None, **extra) -> dict[str, Any]:
    """
    Create standardized error payload

    Args:
        code: Error code (e.g., "INVALID_PARAMETERS")
        message: Human-readable error message
        trace_id: Request correlation ID
        **extra: Additional error details

    Returns:
        Error payload dictionary
    """
    error_data = {"code": code, "message": message}

    # Add extra fields if provided
    for key, value in extra.items():
        if value is not None:
            error_data[key] = value

    return {"ok": False, "error": error_data, "traceId": trace_id or "unknown"}


async def json_error_response(status_code: int, code: str, message: str, request: Request, **extra) -> JSONResponse:
    """
    Create JSON error response with trace ID

    Args:
        status_code: HTTP status code
        code: Error code
        message: Error message
        request: FastAPI request object
        **extra: Additional error details

    Returns:
        JSONResponse with error payload
    """
    trace_id = getattr(request.state, "trace_id", None)

    # Log the error
    logger.warning(
        f"API error: {code}",
        extra={
            "traceId": trace_id,
            "error_code": code,
            "status_code": status_code,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        content=create_error_payload(code, message, trace_id, **extra),
        status_code=status_code,
    )


async def handle_request_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors (422)
    """
    # Extract field errors
    errors = exc.errors()

    # Format error details
    field_errors = []
    unknown_fields = []

    for error in errors:
        location = ".".join(str(x) for x in error.get("loc", []))
        error_type = error.get("type", "")

        if error_type == "extra_forbidden":
            # Unknown field
            field_name = error.get("loc", ["unknown"])[-1]
            unknown_fields.append(str(field_name))
        else:
            # Field validation error
            field_errors.append(
                {
                    "field": location,
                    "message": error.get("msg", "Invalid value"),
                    "type": error_type,
                }
            )

    # Prepare extra data
    extra = {}
    if field_errors:
        extra["validation_errors"] = field_errors
    if unknown_fields:
        extra["unknown"] = unknown_fields
        code = "INVALID_PARAMETERS"
        message = f"Unknown parameter(s): {', '.join(unknown_fields)}"
    else:
        code = "VALIDATION_ERROR"
        message = "Invalid request data"

    return await json_error_response(status_code=422, code=code, message=message, request=request, **extra)


async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions (4xx, 5xx)
    """
    # Map status codes to error codes
    status_code_mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        406: "NOT_ACCEPTABLE",
        409: "CONFLICT",
        410: "GONE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_ERROR",
        501: "NOT_IMPLEMENTED",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }

    # Default code from mapping
    code = status_code_mapping.get(exc.status_code, "HTTP_ERROR")

    # Check for specific error types in exception detail
    if exc.status_code == 400:
        detail_str = str(exc.detail).lower()
        if "cursor" in detail_str:
            if "filter" in detail_str and "mismatch" in detail_str:
                code = "INVALID_CURSOR_FILTER_MISMATCH"
            else:
                code = "INVALID_CURSOR"

    # Get message from exception or use default
    if isinstance(exc.detail, str):
        message = exc.detail
    elif isinstance(exc.detail, dict):
        message = exc.detail.get("message", f"HTTP {exc.status_code} error")
        # Pass through any extra fields
        extra = {k: v for k, v in exc.detail.items() if k != "message"}
        return await json_error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            request=request,
            **extra,
        )
    else:
        message = f"HTTP {exc.status_code} error"

    return await json_error_response(status_code=exc.status_code, code=code, message=message, request=request)


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions (500)
    """
    trace_id = getattr(request.state, "trace_id", None)

    # Log the full exception with traceback
    logger.exception(
        "Unhandled exception",
        extra={
            "traceId": trace_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    # Don't expose internal error details in production
    return JSONResponse(
        content=create_error_payload(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
            trace_id=trace_id,
        ),
        status_code=500,
    )


class APIError(HTTPException):
    """
    Custom API exception for consistent error responses

    Usage:
        raise APIError(
            status_code=400,
            code="INVALID_INPUT",
            message="The provided input is invalid",
            details={"field": "email", "reason": "invalid format"}
        )
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        detail = {"message": message}
        if details:
            detail.update(details)
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
