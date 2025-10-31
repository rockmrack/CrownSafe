"""Access Log Middleware for structured request logging
Logs all requests with correlation IDs and metrics
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Create dedicated access logger
access_logger = logging.getLogger("access")


class AccessLogMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with structured data
    """

    async def dispatch(self, request: Request, call_next):
        """Log request details with correlation ID
        """
        # Track timing
        start_time = time.perf_counter()

        # Get trace ID from request state (set by CorrelationIdMiddleware)
        trace_id = getattr(request.state, "trace_id", None) or "no-trace-id"

        # Get client info
        client_host = None
        if request.client:
            client_host = request.client.host

        # Process request
        response = None
        error_occurred = False
        error_message = None

        try:
            response = await call_next(request)
        except Exception as e:
            error_occurred = True
            error_message = str(e)
            # Re-raise to let error handlers deal with it
            raise
        finally:
            # Calculate duration
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Prepare log data
            log_data = {
                "traceId": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query) if request.url.query else None,
                "status": response.status_code if response else 500,
                "duration_ms": duration_ms,
                "ip": client_host,
                "ua": request.headers.get("user-agent", "-"),
                "referer": request.headers.get("referer", None),
            }

            # Add error info if applicable
            if error_occurred:
                log_data["error"] = error_message
                log_data["status"] = 500

            # Log the request
            if error_occurred or (response and response.status_code >= 500):
                access_logger.error("request_error", extra=log_data)
            elif response and response.status_code >= 400:
                # Log 404/405 as INFO (normal not found), others as WARNING
                if response.status_code in (404, 405):
                    access_logger.info("request_not_found", extra=log_data)
                else:
                    access_logger.warning("request_warning", extra=log_data)
            else:
                access_logger.info("request", extra=log_data)

        return response
