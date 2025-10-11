"""
Admin privacy management routes for DSAR processing
Allows administrators to manage and process privacy requests
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import Session

from api.security.admin_auth import require_admin
from api.errors import APIError
from core_infra.database import get_db
from db.models.privacy_request import PrivacyRequest
from api.utils.privacy import mask_email, PrivacyDataExporter

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/admin/privacy",
    tags=["admin", "privacy"],
    dependencies=[Depends(require_admin)],  # All routes require admin auth
)


class UpdatePrivacyRequest(BaseModel):
    """
    Model for updating privacy request status
    """

    status: str = Field(
        ...,
        pattern="^(verifying|processing|done|rejected|cancelled)$",
        description="New status for the request",
    )
    notes: Optional[str] = Field(None, max_length=2000, description="Admin notes about the request")
    rejection_reason: Optional[str] = Field(
        None, max_length=500, description="Reason for rejection (if status=rejected)"
    )
    export_url: Optional[str] = Field(
        None, description="Export download URL (if status=done for export requests)"
    )


class PrivacyRequestFilter(BaseModel):
    """
    Filters for privacy request queries
    """

    kind: Optional[str] = Field(None, pattern="^(export|delete|rectify|access|restrict|object)$")
    status: Optional[str] = Field(
        None, pattern="^(queued|verifying|processing|done|rejected|expired|cancelled)$"
    )
    jurisdiction: Optional[str] = Field(
        None, pattern="^(gdpr|uk_gdpr|ccpa|pipeda|lgpd|appi|other)$"
    )
    overdue_only: bool = False
    email_search: Optional[str] = None


def create_response(data: dict, request: Request, status_code: int = 200) -> JSONResponse:
    """Create standard JSON response with trace ID"""
    return JSONResponse(
        content={
            "ok": True,
            "data": data,
            "traceId": getattr(request.state, "trace_id", None),
        },
        status_code=status_code,
    )


@router.get("/requests")
async def list_privacy_requests(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Number of requests to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    kind: Optional[str] = Query(None, description="Filter by request type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    overdue_only: bool = Query(False, description="Show only overdue requests"),
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    List privacy requests with filtering and pagination

    Returns privacy requests ordered by submission date (newest first).
    Sensitive data like email addresses are masked.
    """
    try:
        # Build query
        query = db.query(PrivacyRequest)

        # Apply filters
        if kind:
            query = query.filter(PrivacyRequest.kind == kind)

        if status:
            query = query.filter(PrivacyRequest.status == status)

        if jurisdiction:
            query = query.filter(PrivacyRequest.jurisdiction == jurisdiction)

        if overdue_only:
            # Filter for overdue requests
            now = datetime.now(timezone.utc)
            query = query.filter(
                and_(
                    PrivacyRequest.status.in_(["queued", "verifying", "processing"]),
                    PrivacyRequest.submitted_at < now - timedelta(days=30),  # Basic SLA
                )
            )

        # Order by submission date (newest first)
        query = query.order_by(PrivacyRequest.submitted_at.desc())

        # Get total count
        total = query.count()

        # Apply pagination
        requests = query.offset(offset).limit(limit).all()

        # Format results
        items = []
        for req in requests:
            item = {
                "id": str(req.id),
                "kind": req.kind,
                "status": req.status,
                "email_masked": mask_email(req.email),
                "jurisdiction": req.jurisdiction,
                "source": req.source,
                "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
                "verified_at": req.verified_at.isoformat() if req.verified_at else None,
                "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                "sla_days": req.sla_days,
                "is_overdue": req.is_overdue,
                "days_elapsed": req.days_elapsed,
                "notes": req.notes,
            }
            items.append(item)

        logger.info(
            "Admin listed privacy requests",
            extra={
                "admin": admin,
                "filters": {
                    "kind": kind,
                    "status": status,
                    "jurisdiction": jurisdiction,
                    "overdue_only": overdue_only,
                },
                "results": len(items),
                "total": total,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(
            {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
                "hasMore": (offset + limit) < total,
            },
            request,
        )

    except Exception as e:
        logger.error(f"Failed to list privacy requests: {e}")
        raise APIError(
            status_code=500,
            code="LIST_REQUESTS_FAILED",
            message="Failed to retrieve privacy requests",
        )


@router.get("/requests/{request_id}")
async def get_privacy_request_details(
    request_id: str,
    request: Request,
    show_pii: bool = Query(False, description="Include PII in response"),
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific privacy request

    By default, PII is masked. Set show_pii=true to see full details.
    """
    try:
        # Validate UUID
        try:
            UUID(request_id)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_REQUEST_ID",
                message="Invalid request ID format",
            )

        # Query request
        privacy_request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()

        if not privacy_request:
            raise APIError(
                status_code=404,
                code="REQUEST_NOT_FOUND",
                message="Privacy request not found",
            )

        # Format response
        data = privacy_request.to_dict(include_pii=show_pii)

        logger.info(
            "Admin viewed privacy request",
            extra={
                "admin": admin,
                "request_id": request_id,
                "show_pii": show_pii,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(data, request)

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to get privacy request {request_id}: {e}")
        raise APIError(
            status_code=500,
            code="GET_REQUEST_FAILED",
            message="Failed to retrieve privacy request",
        )


@router.patch("/requests/{request_id}")
async def update_privacy_request_status(
    request_id: str,
    body: UpdatePrivacyRequest,
    request: Request,
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update the status of a privacy request

    Allows admins to move requests through the processing pipeline:
    queued → verifying → processing → done/rejected
    """
    try:
        # Validate UUID
        try:
            UUID(request_id)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_REQUEST_ID",
                message="Invalid request ID format",
            )

        # Get request
        privacy_request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()

        if not privacy_request:
            raise APIError(
                status_code=404,
                code="REQUEST_NOT_FOUND",
                message="Privacy request not found",
            )

        # Validate status transition
        current_status = privacy_request.status
        new_status = body.status

        # Check if transition is valid
        valid_transitions = {
            "queued": ["verifying", "processing", "rejected", "cancelled"],
            "verifying": ["processing", "rejected", "cancelled"],
            "processing": ["done", "rejected", "cancelled"],
            "done": [],  # Terminal state
            "rejected": [],  # Terminal state
            "cancelled": [],  # Terminal state
            "expired": [],  # Terminal state
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise APIError(
                status_code=400,
                code="INVALID_STATUS_TRANSITION",
                message=f"Cannot transition from {current_status} to {new_status}",
            )

        # Update status
        privacy_request.status = new_status

        # Update additional fields based on status
        if new_status == "verifying":
            privacy_request.verified_at = datetime.now(timezone.utc)

        elif new_status == "done":
            privacy_request.set_completed(
                export_url=body.export_url if privacy_request.kind == "export" else None
            )

        elif new_status == "rejected":
            privacy_request.set_rejected(
                body.rejection_reason or "Request rejected by administrator"
            )

        elif new_status == "cancelled":
            privacy_request.status = "cancelled"
            privacy_request.completed_at = datetime.now(timezone.utc)

        # Add admin notes if provided
        if body.notes:
            existing_notes = privacy_request.notes or ""
            timestamp = datetime.now(timezone.utc).isoformat()
            privacy_request.notes = (
                f"{existing_notes}\n[{timestamp}] Admin ({admin}): {body.notes}".strip()
            )

        # Save changes
        db.commit()
        db.refresh(privacy_request)

        logger.info(
            "Admin updated privacy request status",
            extra={
                "admin": admin,
                "request_id": request_id,
                "old_status": current_status,
                "new_status": new_status,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(
            {
                "id": str(privacy_request.id),
                "status": privacy_request.status,
                "previous_status": current_status,
                "updated_by": admin,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            request,
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to update privacy request {request_id}: {e}")
        raise APIError(
            status_code=500,
            code="UPDATE_REQUEST_FAILED",
            message="Failed to update privacy request",
        )


@router.get("/statistics")
async def privacy_request_statistics(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Get privacy request statistics and metrics

    Provides overview of DSAR requests for compliance reporting.
    """
    try:
        since_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Overall statistics
        total_requests = (
            db.query(func.count(PrivacyRequest.id))
            .filter(PrivacyRequest.submitted_at >= since_date)
            .scalar()
            or 0
        )

        # By kind
        by_kind = (
            db.query(PrivacyRequest.kind, func.count(PrivacyRequest.id))
            .filter(PrivacyRequest.submitted_at >= since_date)
            .group_by(PrivacyRequest.kind)
            .all()
        )

        # By status
        by_status = (
            db.query(PrivacyRequest.status, func.count(PrivacyRequest.id))
            .filter(PrivacyRequest.submitted_at >= since_date)
            .group_by(PrivacyRequest.status)
            .all()
        )

        # By jurisdiction
        by_jurisdiction = (
            db.query(PrivacyRequest.jurisdiction, func.count(PrivacyRequest.id))
            .filter(PrivacyRequest.submitted_at >= since_date)
            .group_by(PrivacyRequest.jurisdiction)
            .all()
        )

        # Average processing time for completed requests
        avg_processing_time = (
            db.query(
                func.avg(
                    func.extract(
                        "epoch",
                        PrivacyRequest.completed_at - PrivacyRequest.submitted_at,
                    )
                )
            )
            .filter(
                and_(
                    PrivacyRequest.status == "done",
                    PrivacyRequest.submitted_at >= since_date,
                    PrivacyRequest.completed_at.isnot(None),
                )
            )
            .scalar()
        )

        # Overdue requests
        now = datetime.now(timezone.utc)
        overdue_count = (
            db.query(func.count(PrivacyRequest.id))
            .filter(
                and_(
                    PrivacyRequest.status.in_(["queued", "verifying", "processing"]),
                    PrivacyRequest.submitted_at < now - timedelta(days=30),
                )
            )
            .scalar()
            or 0
        )

        # Format statistics
        stats = {
            "period": {
                "days": days,
                "from": since_date.isoformat(),
                "to": now.isoformat(),
            },
            "overview": {
                "total_requests": total_requests,
                "pending": db.query(func.count(PrivacyRequest.id))
                .filter(PrivacyRequest.status.in_(["queued", "verifying", "processing"]))
                .scalar()
                or 0,
                "completed": db.query(func.count(PrivacyRequest.id))
                .filter(PrivacyRequest.status == "done")
                .scalar()
                or 0,
                "rejected": db.query(func.count(PrivacyRequest.id))
                .filter(PrivacyRequest.status == "rejected")
                .scalar()
                or 0,
                "overdue": overdue_count,
            },
            "by_kind": {kind: count for kind, count in by_kind},
            "by_status": {status: count for status, count in by_status},
            "by_jurisdiction": {juris: count for juris, count in by_jurisdiction},
            "processing_metrics": {
                "average_days": round(avg_processing_time / 86400, 1)
                if avg_processing_time
                else None,
                "sla_compliance_rate": round((1 - (overdue_count / total_requests)) * 100, 1)
                if total_requests > 0
                else 100,
            },
        }

        logger.info(
            "Admin viewed privacy statistics",
            extra={
                "admin": admin,
                "days": days,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(stats, request)

    except Exception as e:
        logger.error(f"Failed to get privacy statistics: {e}")
        raise APIError(
            status_code=500,
            code="STATISTICS_FAILED",
            message="Failed to retrieve privacy statistics",
        )


@router.post("/requests/{request_id}/process")
async def process_privacy_request(
    request_id: str,
    request: Request,
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Manually trigger processing of a privacy request

    This would typically integrate with background jobs to actually
    export or delete user data.
    """
    try:
        # Validate UUID
        try:
            UUID(request_id)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_REQUEST_ID",
                message="Invalid request ID format",
            )

        # Get request
        privacy_request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()

        if not privacy_request:
            raise APIError(
                status_code=404,
                code="REQUEST_NOT_FOUND",
                message="Privacy request not found",
            )

        if privacy_request.status not in ["queued", "verifying"]:
            raise APIError(
                status_code=400,
                code="INVALID_STATUS",
                message=f"Cannot process request in status: {privacy_request.status}",
            )

        # Update to processing status
        privacy_request.status = "processing"
        privacy_request.verified_at = privacy_request.verified_at or datetime.now(timezone.utc)

        # Add note
        timestamp = datetime.now(timezone.utc).isoformat()
        notes = privacy_request.notes or ""
        privacy_request.notes = (
            f"{notes}\n[{timestamp}] Processing initiated by admin ({admin})".strip()
        )

        db.commit()

        # Here you would trigger actual processing:
        # - For export: gather data and create export file
        # - For delete: remove user data from systems
        # - For rectify: update incorrect data
        # This would typically be done via Celery task or similar

        logger.info(
            "Admin triggered privacy request processing",
            extra={
                "admin": admin,
                "request_id": request_id,
                "kind": privacy_request.kind,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(
            {
                "id": str(privacy_request.id),
                "status": "processing",
                "message": "Request processing initiated. Check back for updates.",
            },
            request,
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to process privacy request {request_id}: {e}")
        raise APIError(
            status_code=500,
            code="PROCESS_REQUEST_FAILED",
            message="Failed to process privacy request",
        )


@router.get("/export-template")
async def get_export_template(request: Request, admin: str = Depends(require_admin)):
    """
    Get template structure for data exports

    Shows the standard format used for GDPR/CCPA data exports.
    """
    try:
        exporter = PrivacyDataExporter()

        # Sample data structure
        sample_data = {
            "user_profile": {
                "email": "user@example.com",
                "created_at": "2024-01-01T00:00:00Z",
                "last_active": "2024-12-01T00:00:00Z",
            },
            "support_tickets": [
                {
                    "id": "ticket-001",
                    "subject": "Question about recall",
                    "created_at": "2024-06-01T00:00:00Z",
                    "status": "resolved",
                }
            ],
            "api_usage": {
                "total_requests": 150,
                "last_request": "2024-12-01T00:00:00Z",
            },
        }

        template = exporter.create_export_package(sample_data)

        return create_response(
            {
                "template": template,
                "formats_available": ["json", "csv"],
                "notes": "This is the standard format for user data exports",
            },
            request,
        )

    except Exception as e:
        logger.error(f"Failed to get export template: {e}")
        raise APIError(
            status_code=500,
            code="TEMPLATE_FAILED",
            message="Failed to retrieve export template",
        )


# Export router
__all__ = ["router"]
