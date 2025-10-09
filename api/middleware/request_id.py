"""
Request ID Middleware for request tracing and debugging.

This middleware adds a unique request ID to every request,
which is included in response headers and can be used for log correlation.
"""
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.
    
    The request ID is:
    - Generated as a UUID4
    - Stored in request.state.request_id
    - Added to response headers as X-Request-ID
    - Can be used for log correlation and debugging
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Add request ID to request and response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            Response with X-Request-ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in request state for access in route handlers
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
