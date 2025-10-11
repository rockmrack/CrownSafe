"""
Common Endpoint Helpers
Reduces code duplication across endpoint files
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from fastapi import HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core_infra.database import get_db, User
from core_infra.auth import get_current_active_user

logger = logging.getLogger(__name__)


class StandardResponse(BaseModel):
    """Standard API response format"""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()
    trace_id: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Paginated API response format"""

    success: bool
    data: List[Any]
    total: int
    limit: int
    offset: int
    has_more: bool
    next_cursor: Optional[str] = None
    timestamp: str = datetime.utcnow().isoformat()


def success_response(
    data: Any = None, message: Optional[str] = None, trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response

    Args:
        data: Response data
        message: Optional success message
        trace_id: Optional trace ID for debugging

    Returns:
        Dictionary with standardized response format
    """
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "trace_id": trace_id,
    }


def error_response(
    error: str, status_code: int = 500, trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response

    Args:
        error: Error message
        status_code: HTTP status code
        trace_id: Optional trace ID for debugging

    Returns:
        Dictionary with standardized error format
    """
    return {
        "success": False,
        "error": error,
        "timestamp": datetime.utcnow().isoformat(),
        "trace_id": trace_id,
        "status_code": status_code,
    }


def paginated_response(
    items: List[Any],
    total: int,
    limit: int,
    offset: int,
    next_cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a standardized paginated response

    Args:
        items: List of items for current page
        total: Total number of items
        limit: Items per page
        offset: Current offset
        next_cursor: Optional cursor for next page

    Returns:
        Dictionary with paginated response format
    """
    has_more = (offset + limit) < total

    return {
        "success": True,
        "data": items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": has_more,
            "next_cursor": next_cursor,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_user_or_404(user_id: int, db: Session) -> User:
    """
    Get user by ID or raise 404 error

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found"
        )
    return user


def require_subscription(user: User) -> None:
    """
    Check if user has active subscription

    Args:
        user: User object

    Raises:
        HTTPException: If user doesn't have active subscription
    """
    if not getattr(user, "is_subscribed", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required for this feature",
        )


def require_admin(user: User) -> None:
    """
    Check if user is admin

    Args:
        user: User object

    Raises:
        HTTPException: If user is not admin
    """
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )


def validate_pagination(
    limit: int, offset: int, max_limit: int = 100
) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters

    Args:
        limit: Requested limit
        offset: Requested offset
        max_limit: Maximum allowed limit

    Returns:
        Tuple of (validated_limit, validated_offset)
    """
    # Ensure limit is within bounds
    limit = max(1, min(limit, max_limit))

    # Ensure offset is non-negative
    offset = max(0, offset)

    # Prevent extremely large offsets (DoS protection)
    if offset > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Offset too large (max 10000)",
        )

    return limit, offset


def generate_trace_id(prefix: str = "") -> str:
    """
    Generate a unique trace ID for request tracking

    Args:
        prefix: Optional prefix for trace ID

    Returns:
        Unique trace ID string
    """
    import uuid

    trace_id = f"{prefix}{uuid.uuid4().hex[:12]}"
    return trace_id


def log_endpoint_call(
    endpoint: str,
    user_id: Optional[int] = None,
    params: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
) -> None:
    """
    Log endpoint call with context

    Args:
        endpoint: Endpoint name
        user_id: Optional user ID
        params: Optional request parameters
        trace_id: Optional trace ID
    """
    log_data = {
        "endpoint": endpoint,
        "user_id": user_id,
        "params": params,
        "trace_id": trace_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info(f"Endpoint called: {endpoint}", extra=log_data)


def handle_db_error(
    e: Exception, operation: str = "database operation"
) -> HTTPException:
    """
    Convert database error to HTTP exception

    Args:
        e: Exception that occurred
        operation: Description of operation that failed

    Returns:
        HTTPException with appropriate status code and message
    """
    logger.error(f"Database error during {operation}: {str(e)}")

    # Check for specific error types
    error_msg = str(e).lower()

    if "unique constraint" in error_msg or "duplicate" in error_msg:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Resource already exists"
        )
    elif "foreign key" in error_msg:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reference to related resource",
        )
    elif "not found" in error_msg:
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {operation} failed",
        )


def require_feature_flag(flag_name: str, user: User = None) -> None:
    """
    Check if feature flag is enabled

    Args:
        flag_name: Name of feature flag
        user: Optional user for user-specific flags

    Raises:
        HTTPException: If feature is not enabled
    """
    # In a real implementation, check feature flags from database or config
    # For now, just a placeholder
    enabled_flags = ["chat", "visual_recognition", "barcode_scanning"]

    if flag_name not in enabled_flags:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{flag_name}' is not enabled",
        )


class EndpointWrapper:
    """
    Wrapper class for common endpoint patterns

    Provides standard error handling, logging, and response formatting
    """

    @staticmethod
    def wrap(
        func: Callable,
        endpoint_name: str,
        require_auth: bool = True,
        require_sub: bool = False,
        log_params: bool = True,
    ) -> Callable:
        """
        Wrap an endpoint function with common functionality

        Args:
            func: Endpoint function to wrap
            endpoint_name: Name of endpoint for logging
            require_auth: Whether authentication is required
            require_sub: Whether subscription is required
            log_params: Whether to log parameters

        Returns:
            Wrapped function
        """

        async def wrapper(*args, **kwargs):
            trace_id = generate_trace_id(f"{endpoint_name}_")

            try:
                # Log call
                if log_params:
                    log_endpoint_call(endpoint_name, params=kwargs, trace_id=trace_id)

                # Execute function
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )

                # Return standardized response
                if isinstance(result, dict) and "success" in result:
                    return result  # Already formatted
                else:
                    return success_response(data=result, trace_id=trace_id)

            except HTTPException:
                raise  # Re-raise HTTP exceptions
            except Exception as e:
                logger.error(f"Error in {endpoint_name}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal error: {str(e)}",
                )

        return wrapper


# Import asyncio for checking coroutines
import asyncio
