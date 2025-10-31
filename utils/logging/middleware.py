"""FastAPI Logging Middleware - Issue #32
"""

import time

from fastapi import Request

# Import BaseHTTPMiddleware with proper fallback
# FastAPI >= 0.95 uses starlette directly
# FastAPI < 0.95 re-exports from fastapi.middleware.base

try:
    from starlette.middleware.base import BaseHTTPMiddleware
except ImportError:
    from fastapi.middleware.base import BaseHTTPMiddleware
from utils.logging.structured_logger import log_error, log_performance, log_request


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate response time
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            # Log successful request
            log_request(request, response_time, response.status_code)

            # Log performance if slow
            if response_time > 1000:  # Log slow requests (>1s)
                log_performance(
                    "slow_request",
                    response_time,
                    url=str(request.url),
                    method=request.method,
                )

            return response

        except Exception as error:
            response_time = (time.time() - start_time) * 1000

            # Log error with context
            log_error(
                error,
                {
                    "url": str(request.url),
                    "method": request.method,
                    "response_time_ms": response_time,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

            raise error
