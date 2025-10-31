"""Request size limit middleware
Prevents oversized payloads from consuming server resources
"""

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class SizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce maximum request body size
    Returns 413 Payload Too Large for oversized requests
    """

    def __init__(self, app, max_bytes: int | None = None) -> None:
        """Initialize size limit middleware

        Args:
            app: ASGI application
            max_bytes: Maximum request size in bytes (default from env or 100KB)

        """
        super().__init__(app)
        self.max_bytes = max_bytes or int(os.getenv("MAX_REQUEST_BYTES", "100000"))
        logger.info(f"Request size limit configured: {self.max_bytes} bytes ({self.max_bytes / 1024:.1f} KB)")

    async def dispatch(self, request: Request, call_next):
        """Process request with size validation
        """
        # Get trace ID for error responses
        trace_id = getattr(request.state, "trace_id", None)

        # Check Content-Length header first (fast rejection)
        content_length_header = request.headers.get("content-length")

        if content_length_header:
            try:
                content_length = int(content_length_header)
                if content_length > self.max_bytes:
                    logger.warning(
                        f"Request rejected: Content-Length {content_length} exceeds limit {self.max_bytes}",
                        extra={
                            "traceId": trace_id,
                            "path": request.url.path,
                            "content_length": content_length,
                            "max_bytes": self.max_bytes,
                        },
                    )
                    return JSONResponse(
                        content={
                            "ok": False,
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body too large. Maximum size is {self.max_bytes} bytes.",
                                "max_bytes": self.max_bytes,
                                "received_bytes": content_length,
                            },
                            "traceId": trace_id,
                        },
                        status_code=413,
                        headers={"Content-Type": "application/json"},
                    )
            except (ValueError, TypeError):
                # Invalid Content-Length header, continue to read body
                pass

        # For streaming or missing Content-Length, read and check body
        try:
            # Read body with size limit
            body_chunks = []
            total_size = 0

            # Use request.stream() for chunked reading
            async for chunk in request.stream():
                total_size += len(chunk)

                if total_size > self.max_bytes:
                    logger.warning(
                        f"Request rejected: Body size {total_size} exceeds limit during streaming",
                        extra={
                            "traceId": trace_id,
                            "path": request.url.path,
                            "total_size": total_size,
                            "max_bytes": self.max_bytes,
                        },
                    )
                    return JSONResponse(
                        content={
                            "ok": False,
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": f"Request body too large. Maximum size is {self.max_bytes} bytes.",
                                "max_bytes": self.max_bytes,
                            },
                            "traceId": trace_id,
                        },
                        status_code=413,
                        headers={"Content-Type": "application/json"},
                    )

                body_chunks.append(chunk)

            # Reconstruct body for downstream use
            body = b"".join(body_chunks)

            # Store body for reuse (important for downstream handlers)
            request._body = body

            # Log large requests (but still within limit)
            if total_size > self.max_bytes * 0.8:  # 80% of limit
                logger.info(
                    f"Large request: {total_size} bytes ({total_size / self.max_bytes * 100:.1f}% of limit)",
                    extra={
                        "traceId": trace_id,
                        "path": request.url.path,
                        "size": total_size,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error reading request body: {e}",
                extra={"traceId": trace_id, "path": request.url.path, "error": str(e)},
            )
            return JSONResponse(
                content={
                    "ok": False,
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Error reading request body",
                    },
                    "traceId": trace_id,
                },
                status_code=400,
            )

        # Process request normally
        response = await call_next(request)

        return response


class ConfigurableSizeLimits:
    """Configuration for different endpoint size limits
    """

    # Default limits
    DEFAULT_LIMIT = 100_000  # 100KB
    SEARCH_LIMIT = 50_000  # 50KB for search
    UPLOAD_LIMIT = 5_000_000  # 5MB for file uploads

    @classmethod
    def get_limit_for_path(cls, path: str) -> int:
        """Get size limit based on endpoint path

        Args:
            path: Request path

        Returns:
            Size limit in bytes

        """
        if "/upload" in path or "/image" in path:
            return cls.UPLOAD_LIMIT
        elif "/search" in path:
            return cls.SEARCH_LIMIT
        else:
            return cls.DEFAULT_LIMIT
