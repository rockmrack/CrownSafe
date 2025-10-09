"""
Authentication utilities for BabyShield API.
Provides current user context for authenticated requests.
"""
from typing import Optional
from uuid import UUID
import logging


class User:
    """Simple user model for authentication context."""

    def __init__(self, id: UUID, email: Optional[str] = None):
        self.id = id
        self.email = email


# Global current user context (in production, this would be request-scoped)
current_user: Optional[User] = None


def get_current_user() -> Optional[User]:
    """
    Get the current authenticated user.

    In production, this would extract user info from JWT token or session.
    For now, returns None to indicate no authentication.

    Returns:
        User object if authenticated, None otherwise
    """
    # TODO: Implement proper JWT/session-based authentication
    # For now, return None to indicate no user context
    logging.debug("get_current_user called - no authentication implemented yet")
    return current_user


def set_current_user(user: Optional[User]) -> None:
    """
    Set the current user context (for testing/development).

    Args:
        user: User object to set as current user
    """
    global current_user
    current_user = user
    logging.debug(f"Current user set to: {user.id if user else None}")


def clear_current_user() -> None:
    """Clear the current user context."""
    global current_user
    current_user = None
    logging.debug("Current user cleared")


def require_auth() -> User:
    """
    Require authentication and return the current user.

    Returns:
        Current user object

    Raises:
        RuntimeError: If no user is authenticated
    """
    user = get_current_user()
    if not user:
        raise RuntimeError("Authentication required")
    return user
