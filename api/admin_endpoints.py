"""
Admin Endpoints - Administrative user management
Requires admin role/permissions
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core_infra.database import get_db, User
from core_infra.auth import get_current_active_user
from api.schemas.common import ApiResponse, ok, fail
from api.pydantic_base import AppModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


class AdminUserListItem(AppModel):
    """User information for admin listing"""

    id: int
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool
    is_premium: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    scan_count: int = 0


def is_admin(current_user) -> bool:
    """
    Check if user has admin privileges.

    Args:
        current_user: The authenticated user

    Returns:
        True if user is admin, False otherwise
    """
    # Check various admin indicators
    if hasattr(current_user, "is_admin") and current_user.is_admin:
        return True
    if hasattr(current_user, "is_superuser") and current_user.is_superuser:
        return True
    if hasattr(current_user, "role") and current_user.role == "admin":
        return True

    # Check if user is staff
    if hasattr(current_user, "is_staff") and current_user.is_staff:
        return True

    return False


@router.get("/users", response_model=ApiResponse)
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get list of all users (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of users with basic information

    Raises:
        403: If user is not an admin
    """
    # Check if user has admin privileges
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")

    try:
        # Get users from database
        users = db.query(User).order_by(desc(User.created_at)).offset(skip).limit(limit).all()
        total_count = db.query(User).count()

        # Import ImageJob for scan count
        from core_infra.visual_agent_models import ImageJob

        # Build user list with scan counts
        user_list = []
        for user in users:
            scan_count = db.query(ImageJob).filter(ImageJob.user_id == user.id).count()

            user_data = {
                "id": user.id,
                "email": user.email,
                "username": getattr(user, "username", None),
                "full_name": getattr(user, "full_name", None),
                "is_active": getattr(user, "is_active", True),
                "is_premium": getattr(user, "is_premium", False),
                "created_at": user.created_at.isoformat() + "Z" if hasattr(user, "created_at") else None,
                "last_login": user.last_login.isoformat() + "Z"
                if hasattr(user, "last_login") and user.last_login
                else None,
                "scan_count": scan_count,
            }
            user_list.append(user_data)

        result = {
            "users": user_list,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "returned": len(user_list),
        }

        return ok(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        return fail(f"Failed to list users: {str(e)}", status=500)


@router.get("/users/{user_id}", response_model=ApiResponse)
async def get_user_details(
    user_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific user (admin only).

    Args:
        user_id: The ID of the user to fetch

    Returns:
        Detailed user information

    Raises:
        403: If user is not an admin
        404: If user not found
    """
    # Check if user has admin privileges
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's scan history
        from core_infra.visual_agent_models import ImageJob

        scan_count = db.query(ImageJob).filter(ImageJob.user_id == user.id).count()
        recent_scans = (
            db.query(ImageJob).filter(ImageJob.user_id == user.id).order_by(desc(ImageJob.created_at)).limit(10).all()
        )

        user_details = {
            "id": user.id,
            "email": user.email,
            "username": getattr(user, "username", None),
            "full_name": getattr(user, "full_name", None),
            "is_active": getattr(user, "is_active", True),
            "is_premium": getattr(user, "is_premium", False),
            "is_admin": is_admin(user),
            "created_at": user.created_at.isoformat() + "Z" if hasattr(user, "created_at") else None,
            "last_login": user.last_login.isoformat() + "Z"
            if hasattr(user, "last_login") and user.last_login
            else None,
            "scan_count": scan_count,
            "recent_scan_ids": [scan.id for scan in recent_scans],
            "notification_preferences": getattr(user, "notification_preferences", {}),
        }

        return ok(user_details)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user details: {e}", exc_info=True)
        return fail(f"Failed to fetch user details: {str(e)}", status=500)
