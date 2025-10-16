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
        raise HTTPException(
            status_code=403, detail="Access denied. Admin privileges required."
        )

    try:
        # Get users from database
        users = (
            db.query(User)
            .order_by(desc(User.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )
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
                "created_at": user.created_at.isoformat() + "Z"
                if hasattr(user, "created_at")
                else None,
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
        raise HTTPException(
            status_code=403, detail="Access denied. Admin privileges required."
        )

    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user's scan history
        from core_infra.visual_agent_models import ImageJob

        scan_count = db.query(ImageJob).filter(ImageJob.user_id == user.id).count()
        recent_scans = (
            db.query(ImageJob)
            .filter(ImageJob.user_id == user.id)
            .order_by(desc(ImageJob.created_at))
            .limit(10)
            .all()
        )

        user_details = {
            "id": user.id,
            "email": user.email,
            "username": getattr(user, "username", None),
            "full_name": getattr(user, "full_name", None),
            "is_active": getattr(user, "is_active", True),
            "is_premium": getattr(user, "is_premium", False),
            "is_admin": is_admin(user),
            "created_at": user.created_at.isoformat() + "Z"
            if hasattr(user, "created_at")
            else None,
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


@router.post("/database/enable-pg-trgm", response_model=ApiResponse)
async def enable_pg_trgm_extension(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Enable pg_trgm PostgreSQL extension for fuzzy text search (admin only).

    This endpoint enables the trigram extension and creates GIN indexes
    for optimal search performance.

    Returns:
        Status of the operation with details

    Raises:
        403: If user is not an admin
        500: If database operation fails
    """
    # Check if user has admin privileges
    if not is_admin(current_user):
        raise HTTPException(
            status_code=403, detail="Access denied. Admin privileges required."
        )

    try:
        from sqlalchemy import text

        logger.info("Admin triggering pg_trgm extension enablement...")

        # Check if extension already exists
        result = db.execute(
            text(
                "SELECT extname, extversion FROM pg_extension WHERE extname = 'pg_trgm';"
            )
        )
        existing = result.fetchone()

        if existing:
            logger.info(f"pg_trgm already enabled (version {existing[1]})")
            extension_status = "already_enabled"
            extension_version = existing[1]
        else:
            # Enable the extension
            db.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            db.commit()
            logger.info("pg_trgm extension enabled successfully")
            extension_status = "newly_enabled"
            extension_version = "latest"

        # Test the similarity function
        test_result = db.execute(text("SELECT similarity('baby', 'baby');"))
        similarity_row = test_result.fetchone()
        similarity_score = similarity_row[0] if similarity_row else 0.0

        # Check for existing indexes
        idx_check = db.execute(
            text(
                """
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'recalls_enhanced' 
                AND indexname LIKE '%trgm%'
            """
            )
        )
        existing_indexes = [row[0] for row in idx_check.fetchall()]

        # Create indexes if they don't exist
        indexes_created = []
        if not existing_indexes:
            logger.info("Creating GIN indexes for pg_trgm...")

            index_definitions = [
                (
                    "CREATE INDEX IF NOT EXISTS idx_recalls_product_trgm ON "
                    "recalls_enhanced USING gin (lower(product_name) gin_trgm_ops);"
                ),
                (
                    "CREATE INDEX IF NOT EXISTS idx_recalls_brand_trgm ON "
                    "recalls_enhanced USING gin (lower(brand) gin_trgm_ops);"
                ),
                (
                    "CREATE INDEX IF NOT EXISTS idx_recalls_description_trgm ON "
                    "recalls_enhanced USING gin (lower(description) gin_trgm_ops);"
                ),
                (
                    "CREATE INDEX IF NOT EXISTS idx_recalls_hazard_trgm ON "
                    "recalls_enhanced USING gin (lower(hazard) gin_trgm_ops);"
                ),
            ]

            for idx_sql in index_definitions:
                idx_name = idx_sql.split("idx_recalls_")[1].split(" ON")[0]
                db.execute(text(idx_sql))
                indexes_created.append(idx_name)
                logger.info(f"Created index: {idx_name}")

            db.commit()
            logger.info("All GIN indexes created successfully")
            index_status = "created"
        else:
            index_status = "already_exist"
            logger.info(f"Indexes already exist: {existing_indexes}")

        result = {
            "success": True,
            "extension_status": extension_status,
            "extension_version": extension_version,
            "similarity_test": similarity_score,
            "index_status": index_status,
            "existing_indexes": existing_indexes,
            "indexes_created": indexes_created,
            "message": "pg_trgm extension is now enabled and configured",
        }

        logger.info(f"pg_trgm enablement complete: {result}")
        return ok(result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling pg_trgm: {e}", exc_info=True)
        db.rollback()
        return fail(f"Failed to enable pg_trgm: {str(e)}", status=500)
