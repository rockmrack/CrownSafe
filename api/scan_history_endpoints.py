"""
Scan History Endpoints - Shows users their past scans
"""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from api.pydantic_base import AppModel
from api.schemas.common import ApiResponse, fail, ok
from core_infra.auth import get_current_active_user
from core_infra.database import get_db
from core_infra.visual_agent_models import ImageExtraction, ImageJob, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["User"])


class ScanHistoryItem(AppModel):
    """Single scan history item"""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    job_id: str
    scan_date: datetime
    status: str
    product_name: str | None = None
    brand_name: str | None = None
    model_number: str | None = None
    upc_code: str | None = None
    confidence_score: float | None = None
    confidence_level: str | None = None
    has_recalls: bool = False
    recall_count: int = 0
    image_url: str | None = None
    processing_time_ms: int | None = None


class ScanHistoryResponse(AppModel):
    """Scan history response"""

    total_scans: int
    scans: list[ScanHistoryItem]
    page: int
    page_size: int
    has_more: bool


@router.get("/scan-history", response_model=ApiResponse)
async def get_scan_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    days: int | None = Query(None, ge=1, le=365, description="Filter by last N days"),
    status: str | None = Query(None, description="Filter by status"),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get user's scan history with pagination and filters

    Returns:
    - List of past scans with product info and recall status
    - Pagination info
    """
    try:
        # Build query
        query = db.query(ImageJob).filter(ImageJob.user_id == current_user.id)

        # Apply filters
        if days:
            since_date = datetime.utcnow() - timedelta(days=days)
            query = query.filter(ImageJob.created_at >= since_date)

        if status:
            try:
                status_enum = JobStatus[status.upper()]
                query = query.filter(ImageJob.status == status_enum)
            except KeyError:
                pass  # Ignore invalid status

        # Get total count
        total_scans = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        jobs = query.order_by(desc(ImageJob.created_at)).offset(offset).limit(page_size).all()

        # Build response items
        scan_items = []
        for job in jobs:
            # Get extraction data if available
            extraction = db.query(ImageExtraction).filter_by(job_id=job.id).first()

            # Calculate processing time
            processing_time_ms = None
            if job.started_at and job.completed_at:
                processing_time_ms = int((job.completed_at - job.started_at).total_seconds() * 1000)

            # REMOVED FOR CROWN SAFE: Recall checking no longer applicable
            has_recalls = False
            recall_count = 0
            # if extraction and extraction.upc_code:
            #     # Check against recalls table (RecallDB removed)
            #     from core_infra.database import RecallDB
            #     recalls = db.query(RecallDB).filter(...).count()
            #     if recalls > 0:
            #         has_recalls = True
            #         recall_count = recalls

            scan_item = ScanHistoryItem(
                job_id=job.id,
                scan_date=job.created_at,
                status=job.status.value,
                product_name=extraction.product_name if extraction else None,
                brand_name=extraction.brand_name if extraction else None,
                model_number=extraction.model_number if extraction else None,
                upc_code=extraction.upc_code if extraction else None,
                confidence_score=job.confidence_score,
                confidence_level=job.confidence_level.value if job.confidence_level else None,
                has_recalls=has_recalls,
                recall_count=recall_count,
                image_url=job.s3_presigned_url,
                processing_time_ms=processing_time_ms,
            )
            scan_items.append(scan_item)

        # Build response
        response = ScanHistoryResponse(
            total_scans=total_scans,
            scans=scan_items,
            page=page,
            page_size=page_size,
            has_more=(offset + page_size) < total_scans,
        )

        return ok(response.model_dump())

    except Exception as e:
        logger.error(f"Error fetching scan history: {e}", exc_info=True)
        return fail(f"Failed to fetch scan history: {str(e)}", status=500)


@router.get("/scan-history/{job_id}", response_model=ApiResponse)
async def get_scan_details(
    job_id: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific scan

    Returns:
    - Full scan details including extraction results
    """
    try:
        # Get job ensuring it belongs to user
        job = db.query(ImageJob).filter(and_(ImageJob.id == job_id, ImageJob.user_id == current_user.id)).first()

        if not job:
            return fail("Scan not found", code="NOT_FOUND", status=404)

        # Get extraction data
        extraction = db.query(ImageExtraction).filter_by(job_id=job.id).first()

        # Build detailed response
        details = {
            "job_id": job.id,
            "scan_date": job.created_at.isoformat() + "Z",
            "status": job.status.value,
            "processing_steps": {
                "virus_scanned": job.virus_scanned,
                "normalized": job.normalized,
                "barcode_extracted": job.barcode_extracted,
                "ocr_completed": job.ocr_completed,
                "labels_extracted": job.labels_extracted,
            },
            "confidence": {
                "score": job.confidence_score,
                "level": job.confidence_level.value if job.confidence_level else None,
            },
            "timing": {
                "created_at": job.created_at.isoformat() + "Z",
                "started_at": job.started_at.isoformat() + "Z" if job.started_at else None,
                "completed_at": job.completed_at.isoformat() + "Z" if job.completed_at else None,
            },
            "error_message": job.error_message,
        }

        if extraction:
            details["extraction"] = {
                "product_name": extraction.product_name,
                "brand_name": extraction.brand_name,
                "model_number": extraction.model_number,
                "serial_number": extraction.serial_number,
                "lot_number": extraction.lot_number,
                "upc_code": extraction.upc_code,
                "ocr_text": extraction.ocr_text,
                "ocr_confidence": extraction.ocr_confidence,
                "barcodes": extraction.barcodes,
                "labels": extraction.labels,
                "warning_labels": extraction.warning_labels,
                "age_recommendations": extraction.age_recommendations,
                "certifications": extraction.certifications,
            }

        return ok(details)

    except Exception as e:
        logger.error(f"Error fetching scan details: {e}", exc_info=True)
        return fail(f"Failed to fetch scan details: {str(e)}", status=500)


@router.delete("/scan-history/{job_id}", response_model=ApiResponse)
async def delete_scan(
    job_id: str,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a scan from history

    Note: This soft-deletes by marking status, actual data retained for compliance
    """
    try:
        # Get job ensuring it belongs to user
        job = db.query(ImageJob).filter(and_(ImageJob.id == job_id, ImageJob.user_id == current_user.id)).first()

        if not job:
            return fail("Scan not found", code="NOT_FOUND", status=404)

        # Soft delete by changing status
        job.status = JobStatus.FAILED
        job.error_message = "Deleted by user"
        db.commit()

        return ok({"message": "Scan deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting scan: {e}", exc_info=True)
        return fail(f"Failed to delete scan: {str(e)}", status=500)


@router.get("/scan-statistics", response_model=ApiResponse)
async def get_scan_statistics(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get user's scanning statistics

    Returns:
    - Total scans
    - Scans by status
    - Recent activity
    - Product categories scanned
    """
    try:
        # Get all user's jobs
        jobs = db.query(ImageJob).filter(ImageJob.user_id == current_user.id).all()

        # Calculate statistics
        total_scans = len(jobs)
        completed_scans = len([j for j in jobs if j.status == JobStatus.COMPLETED])
        failed_scans = len([j for j in jobs if j.status == JobStatus.FAILED])

        # Get scans by time period
        now = datetime.utcnow()
        today_scans = len([j for j in jobs if j.created_at.date() == now.date()])
        week_scans = len([j for j in jobs if (now - j.created_at).days <= 7])
        month_scans = len([j for j in jobs if (now - j.created_at).days <= 30])

        # Get unique products scanned
        extractions = db.query(ImageExtraction).join(ImageJob).filter(ImageJob.user_id == current_user.id).all()

        unique_products = set()
        unique_brands = set()
        for ext in extractions:
            if ext.product_name:
                unique_products.add(ext.product_name)
            if ext.brand_name:
                unique_brands.add(ext.brand_name)

        # Calculate average confidence
        avg_confidence = 0
        confidence_scores = [j.confidence_score for j in jobs if j.confidence_score]
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)

        stats = {
            "total_scans": total_scans,
            "completed_scans": completed_scans,
            "failed_scans": failed_scans,
            "success_rate": (completed_scans / total_scans * 100) if total_scans > 0 else 0,
            "average_confidence": round(avg_confidence, 2),
            "activity": {
                "today": today_scans,
                "this_week": week_scans,
                "this_month": month_scans,
            },
            "products": {
                "unique_products": len(unique_products),
                "unique_brands": len(unique_brands),
                "top_brands": list(unique_brands)[:5],  # Top 5 brands
            },
            "member_since": (
                current_user.created_at.isoformat() + "Z" if hasattr(current_user, "created_at") else None
            ),
        }

        return ok(stats)

    except Exception as e:
        logger.error(f"Error fetching scan statistics: {e}", exc_info=True)
        return fail(f"Failed to fetch statistics: {str(e)}", status=500)


# ============================================================================
# USER PROFILE ENDPOINTS
# ============================================================================


class UserProfileResponse(AppModel):
    """User profile information"""

    id: int
    email: str
    username: str | None = None
    full_name: str | None = None
    is_active: bool
    is_premium: bool = False
    created_at: datetime
    last_login: datetime | None = None
    scan_count: int = 0
    notification_preferences: dict = {}


class UserProfileUpdateRequest(AppModel):
    """User profile update request"""

    username: str | None = None
    full_name: str | None = None
    notification_preferences: dict | None = None


@router.get("/profile", response_model=ApiResponse)
async def get_user_profile(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get current user's profile information.

    Returns:
        User profile data including account details and preferences
    """
    try:
        # Count user's scans
        scan_count = db.query(ImageJob).filter(ImageJob.user_id == current_user.id).count()

        profile_data = {
            "id": current_user.id,
            "email": current_user.email,
            "username": getattr(current_user, "username", None),
            "full_name": getattr(current_user, "full_name", None),
            "is_active": getattr(current_user, "is_active", True),
            "is_premium": getattr(current_user, "is_premium", False),
            "created_at": current_user.created_at.isoformat() + "Z"
            if hasattr(current_user, "created_at")
            else datetime.utcnow().isoformat() + "Z",
            "last_login": current_user.last_login.isoformat() + "Z"
            if hasattr(current_user, "last_login") and current_user.last_login
            else None,
            "scan_count": scan_count,
            "notification_preferences": getattr(current_user, "notification_preferences", {}),
        }

        return ok(profile_data)

    except Exception as e:
        logger.error(f"Error fetching user profile: {e}", exc_info=True)
        return fail(f"Failed to fetch profile: {str(e)}", status=500)


@router.put("/profile", response_model=ApiResponse)
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update current user's profile information.

    Args:
        profile_update: Profile fields to update

    Returns:
        Updated user profile data
    """
    try:
        # Update allowed fields
        if profile_update.username is not None:
            if hasattr(current_user, "username"):
                current_user.username = profile_update.username

        if profile_update.full_name is not None:
            if hasattr(current_user, "full_name"):
                current_user.full_name = profile_update.full_name

        if profile_update.notification_preferences is not None:
            if hasattr(current_user, "notification_preferences"):
                current_user.notification_preferences = profile_update.notification_preferences

        # Update last_modified timestamp if exists
        if hasattr(current_user, "updated_at"):
            current_user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(current_user)

        # Return updated profile
        profile_data = {
            "id": current_user.id,
            "email": current_user.email,
            "username": getattr(current_user, "username", None),
            "full_name": getattr(current_user, "full_name", None),
            "is_active": getattr(current_user, "is_active", True),
            "is_premium": getattr(current_user, "is_premium", False),
            "created_at": current_user.created_at.isoformat() + "Z"
            if hasattr(current_user, "created_at")
            else datetime.utcnow().isoformat() + "Z",
            "notification_preferences": getattr(current_user, "notification_preferences", {}),
        }

        return ok(profile_data, message="Profile updated successfully")

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user profile: {e}", exc_info=True)
        return fail(f"Failed to update profile: {str(e)}", status=500)


@router.get("/{user_id}/profile", response_model=ApiResponse)
async def get_other_user_profile(
    user_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Attempt to get another user's profile.
    This endpoint is intentionally restricted to test authorization boundaries.

    Args:
        user_id: The ID of the user to fetch

    Returns:
        403 Forbidden if trying to access another user's data
    """
    # Authorization check: Users can only access their own profile
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You can only view your own profile.",
        )

    # If accessing own profile, return it
    try:
        from core_infra.database import User

        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        scan_count = db.query(ImageJob).filter(ImageJob.user_id == user.id).count()

        profile_data = {
            "id": user.id,
            "email": user.email,
            "username": getattr(user, "username", None),
            "full_name": getattr(user, "full_name", None),
            "is_active": getattr(user, "is_active", True),
            "created_at": (user.created_at.isoformat() + "Z" if hasattr(user, "created_at") else None),
            "scan_count": scan_count,
        }

        return ok(profile_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}", exc_info=True)
        return fail(f"Failed to fetch profile: {str(e)}", status=500)
