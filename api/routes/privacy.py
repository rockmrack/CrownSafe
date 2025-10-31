"""
User privacy API routes for GDPR/CCPA compliance
Handles data export, deletion, and privacy information requests
"""

import logging
import os

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import and_
from sqlalchemy.orm import Session

from api.errors import APIError
from api.rate_limiting import RateLimiter
from api.utils.privacy import (
    detect_jurisdiction,
    email_hash,
    format_dsar_response,
    mask_email,
    normalize_email,
    privacy_audit_log,
    validate_email,
)
from core_infra.database import get_db
from db.models.privacy_request import PrivacyRequest

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/user", tags=["privacy"])

# Rate limiter for DSAR endpoints (5 per hour per IP)
dsar_limiter = RateLimiter(times=5, seconds=3600)


class DSARRequest(BaseModel):
    """
    Data Subject Access Request model
    """

    email: EmailStr = Field(..., description="User email for export/delete")
    jurisdiction: str | None = Field(
        None,
        description="Privacy jurisdiction (gdpr|ccpa|pipeda|other)",
        pattern="^(gdpr|uk_gdpr|ccpa|pipeda|lgpd|appi|other)$",
    )
    source: str | None = Field(
        None,
        description="Request source (ios|android|web|api)",
        pattern="^(ios|android|web|email|api)$",
    )
    reason: str | None = Field(None, max_length=500, description="Optional reason for request")
    metadata: dict | None = Field(None, description="Additional metadata")

    @field_validator("email")
    def validate_email_format(cls, v):
        """Validate email format"""
        if not validate_email(v):
            raise ValueError("Invalid email format")
        return normalize_email(v)


class DSARResponse(BaseModel):
    """
    Standard DSAR response model
    """

    ok: bool = True
    message: str
    sla_days: int
    request_id: str | None = None
    status: str = "queued"
    submitted_at: str | None = None


def create_response(data: dict, request: Request, status_code: int = 200) -> JSONResponse:
    """
    Create standard JSON response with trace ID

    Args:
        data: Response data
        request: FastAPI request object
        status_code: HTTP status code

    Returns:
        JSON response
    """
    return JSONResponse(
        content={
            "ok": True,
            "data": data,
            "traceId": getattr(request.state, "trace_id", None),
        },
        status_code=status_code,
    )


@router.post("/data/export", response_model=DSARResponse, dependencies=[Depends(dsar_limiter)])
@privacy_audit_log
async def request_data_export(
    request: Request,
    body: DSARRequest,
    user_agent: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Request export of all user data

    This endpoint allows users to request a copy of all their personal data
    in compliance with GDPR Article 15 (Right of Access) and CCPA.

    The request will be processed within the legal SLA (30 days for GDPR, 45 for CCPA).
    Users will receive an email with a secure download link when ready.
    """
    try:
        # Detect jurisdiction if not provided
        client_ip = request.client.host if request.client else None
        if not body.jurisdiction:
            body.jurisdiction = detect_jurisdiction(ip_address=client_ip)

        # Check for existing pending request
        existing = (
            db.query(PrivacyRequest)
            .filter(
                and_(
                    PrivacyRequest.email_hash == email_hash(body.email),
                    PrivacyRequest.kind == "export",
                    PrivacyRequest.status.in_(["queued", "verifying", "processing"]),
                )
            )
            .first()
        )

        if existing:
            logger.info(f"Duplicate export request for {mask_email(body.email)}")
            return JSONResponse(
                content={
                    "ok": True,
                    "data": format_dsar_response("export", "pending", body.jurisdiction),
                    "traceId": getattr(request.state, "trace_id", None),
                },
                status_code=200,
            )

        # Create new request
        privacy_request = PrivacyRequest.create_request(
            kind="export",
            email=body.email,
            jurisdiction=body.jurisdiction,
            source=body.source or "api",
            trace_id=getattr(request.state, "trace_id", None),
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"reason": body.reason, **(body.metadata or {})},
        )

        db.add(privacy_request)
        db.commit()
        db.refresh(privacy_request)

        logger.info(
            "Data export request created",
            extra={
                "request_id": str(privacy_request.id),
                "jurisdiction": body.jurisdiction,
                "source": body.source,
                "email_hash": privacy_request.email_hash[:8] + "...",
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        response_data = format_dsar_response("export", "queued", body.jurisdiction)
        response_data["request_id"] = str(privacy_request.id)
        response_data["submitted_at"] = privacy_request.submitted_at.isoformat()

        return create_response(response_data, request)

    except Exception as e:
        logger.error(f"Failed to create export request: {e}")
        raise APIError(
            status_code=500,
            code="EXPORT_REQUEST_FAILED",
            message="Failed to submit export request",
        )


@router.post("/data/delete", response_model=DSARResponse, dependencies=[Depends(dsar_limiter)])
@privacy_audit_log
async def request_data_deletion(
    request: Request,
    body: DSARRequest,
    user_agent: str | None = Header(None),
    db: Session = Depends(get_db),
):
    """
    Request deletion of all user data

    This endpoint allows users to request deletion of all their personal data
    in compliance with GDPR Article 17 (Right to Erasure) and CCPA.

    The deletion is permanent and cannot be undone. Users will receive
    email confirmation when the deletion is complete.
    """
    try:
        # Detect jurisdiction if not provided
        client_ip = request.client.host if request.client else None
        if not body.jurisdiction:
            body.jurisdiction = detect_jurisdiction(ip_address=client_ip)

        # Check for existing pending request
        existing = (
            db.query(PrivacyRequest)
            .filter(
                and_(
                    PrivacyRequest.email_hash == email_hash(body.email),
                    PrivacyRequest.kind == "delete",
                    PrivacyRequest.status.in_(["queued", "verifying", "processing"]),
                )
            )
            .first()
        )

        if existing:
            logger.info(f"Duplicate deletion request for {mask_email(body.email)}")
            return JSONResponse(
                content={
                    "ok": True,
                    "data": format_dsar_response("delete", "pending", body.jurisdiction),
                    "traceId": getattr(request.state, "trace_id", None),
                },
                status_code=200,
            )

        # Create new request
        privacy_request = PrivacyRequest.create_request(
            kind="delete",
            email=body.email,
            jurisdiction=body.jurisdiction,
            source=body.source or "api",
            trace_id=getattr(request.state, "trace_id", None),
            ip_address=client_ip,
            user_agent=user_agent,
            metadata={"reason": body.reason, **(body.metadata or {})},
        )

        db.add(privacy_request)
        db.commit()
        db.refresh(privacy_request)

        logger.info(
            "Data deletion request created",
            extra={
                "request_id": str(privacy_request.id),
                "jurisdiction": body.jurisdiction,
                "source": body.source,
                "email_hash": privacy_request.email_hash[:8] + "...",
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        response_data = format_dsar_response("delete", "queued", body.jurisdiction)
        response_data["request_id"] = str(privacy_request.id)
        response_data["submitted_at"] = privacy_request.submitted_at.isoformat()

        # Send verification email (would be implemented with email service)
        # await send_deletion_verification_email(body.email, privacy_request.verification_token)

        return create_response(response_data, request)

    except Exception as e:
        logger.error(f"Failed to create deletion request: {e}")
        raise APIError(
            status_code=500,
            code="DELETION_REQUEST_FAILED",
            message="Failed to submit deletion request",
        )


@router.get("/privacy/summary")
async def privacy_summary(request: Request):
    """
    Get privacy policy summary and links

    Returns key privacy information including DPO contact, retention periods,
    and links to legal documents.
    """
    try:
        summary = {
            "dpo_email": os.getenv("PRIVACY_DPO_EMAIL", "support@babyshield.app"),
            "retention_periods": {
                "support_emails": "1 year",
                "crash_logs": "90 days",
                "api_logs": "30 days",
                "dsar_records": f"{os.getenv('PRIVACY_RETENTION_YEARS', '3')} years",
            },
            "links": {
                "privacy_policy": "/legal/privacy",
                "terms_of_service": "/legal/terms",
                "data_deletion": "/legal/data-deletion",
                "export_data": "/api/v1/user/data/export",
                "delete_data": "/api/v1/user/data/delete",
            },
            "data_collected": {
                "mandatory": [],
                "optional": [
                    "email (only if you contact support or submit DSAR)",
                    "device info (only if diagnostics enabled)",
                    "crash logs (only if enabled)",
                ],
            },
            "third_party_sharing": False,
            "tracking": False,
            "advertising": False,
            "children_under_13": False,
            "jurisdictions_covered": [
                "GDPR (EU)",
                "UK GDPR",
                "CCPA/CPRA (California)",
                "PIPEDA (Canada)",
                "LGPD (Brazil)",
                "APPI (Japan)",
            ],
            "notes": "BabyShield provides informational safety data only. This service is NOT medical advice.",
            "last_updated": "2025-08-27",
        }

        return create_response(summary, request)

    except Exception as e:
        logger.error(f"Failed to get privacy summary: {e}")
        raise APIError(
            status_code=500,
            code="PRIVACY_SUMMARY_FAILED",
            message="Failed to retrieve privacy summary",
        )


@router.post("/privacy/verify/{token}")
async def verify_privacy_request(token: str, request: Request, db: Session = Depends(get_db)):
    """
    Verify a privacy request via email token

    This endpoint is used to verify DSAR requests sent via email verification links.
    """
    try:
        # Find request by token
        privacy_request = db.query(PrivacyRequest).filter(PrivacyRequest.verification_token == token).first()

        if not privacy_request:
            raise APIError(
                status_code=404,
                code="INVALID_TOKEN",
                message="Invalid or expired verification token",
            )

        if privacy_request.status != "queued":
            raise APIError(
                status_code=400,
                code="ALREADY_VERIFIED",
                message="Request already verified or processed",
            )

        # Mark as verified
        privacy_request.set_verified()
        db.commit()

        logger.info(
            "Privacy request verified",
            extra={
                "request_id": str(privacy_request.id),
                "kind": privacy_request.kind,
                "traceId": getattr(request.state, "trace_id", None),
            },
        )

        return create_response(
            {
                "message": "Request verified successfully. Processing will begin shortly.",
                "request_id": str(privacy_request.id),
                "kind": privacy_request.kind,
                "status": privacy_request.status,
            },
            request,
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to verify privacy request: {e}")
        raise APIError(
            status_code=500,
            code="VERIFICATION_FAILED",
            message="Failed to verify request",
        )


@router.get("/privacy/status/{request_id}")
async def check_request_status(request_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Check status of a privacy request

    Users can check the status of their DSAR request using the request ID.
    """
    try:
        # Validate UUID format
        from uuid import UUID

        try:
            UUID(request_id)
        except ValueError:
            raise APIError(
                status_code=400,
                code="INVALID_REQUEST_ID",
                message="Invalid request ID format",
            )

        # Find request
        privacy_request = db.query(PrivacyRequest).filter(PrivacyRequest.id == request_id).first()

        if not privacy_request:
            raise APIError(
                status_code=404,
                code="REQUEST_NOT_FOUND",
                message="Privacy request not found",
            )

        # Return status (without PII)
        return create_response(
            {
                "request_id": str(privacy_request.id),
                "kind": privacy_request.kind,
                "status": privacy_request.status,
                "submitted_at": privacy_request.submitted_at.isoformat(),
                "verified_at": privacy_request.verified_at.isoformat() if privacy_request.verified_at else None,
                "completed_at": privacy_request.completed_at.isoformat() if privacy_request.completed_at else None,
                "sla_days": privacy_request.sla_days,
                "is_overdue": privacy_request.is_overdue,
                "days_elapsed": privacy_request.days_elapsed,
            },
            request,
        )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to check request status: {e}")
        raise APIError(
            status_code=500,
            code="STATUS_CHECK_FAILED",
            message="Failed to check request status",
        )


# Additional endpoints for other GDPR rights


@router.post("/data/rectify", dependencies=[Depends(dsar_limiter)])
async def request_data_rectification(request: Request, body: DSARRequest, db: Session = Depends(get_db)):
    """
    Request rectification of inaccurate data (GDPR Article 16)
    """
    # Similar implementation to export/delete
    # Would create a "rectify" type request
    return create_response(format_dsar_response("rectify", "queued", body.jurisdiction or "other"), request)


@router.post("/data/restrict", dependencies=[Depends(dsar_limiter)])
async def request_processing_restriction(request: Request, body: DSARRequest, db: Session = Depends(get_db)):
    """
    Request restriction of processing (GDPR Article 18)
    """
    return create_response(
        format_dsar_response("restrict", "queued", body.jurisdiction or "other"),
        request,
    )


@router.post("/data/object", dependencies=[Depends(dsar_limiter)])
async def object_to_processing(request: Request, body: DSARRequest, db: Session = Depends(get_db)):
    """
    Object to data processing (GDPR Article 21)
    """
    return create_response(format_dsar_response("object", "queued", body.jurisdiction or "other"), request)


# Export router
__all__ = ["router"]
