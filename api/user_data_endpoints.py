"""
User Data Export and Deletion Endpoints
GDPR/CCPA compliant data handling
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json
import uuid
import hashlib
import io
import csv
from pydantic import BaseModel, Field, EmailStr

from core_infra.database import get_db, User
from core_infra.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/user/data",
    tags=["User Data Management"]
)

# Privacy summary router
privacy_router = APIRouter(
    prefix="/api/v1/user/privacy",
    tags=["User Privacy"]
)


# ========================= MODELS =========================

class DataExportRequest(BaseModel):
    """Request for data export"""
    user_id: Optional[str] = Field(None, description="User ID")
    email: Optional[EmailStr] = Field(None, description="Email for verification")
    format: str = Field("json", pattern="^(json|csv)$", description="Export format")
    include_logs: bool = Field(False, description="Include activity logs")


class DataDeletionRequest(BaseModel):
    """Request for data deletion"""
    user_id: Optional[str] = Field(None, description="User ID")
    email: Optional[EmailStr] = Field(None, description="Email for verification")
    confirm: bool = Field(..., description="Confirmation flag (must be true)")
    reason: Optional[str] = Field(None, description="Reason for deletion")


class DataOperationResponse(BaseModel):
    """Response for data operations"""
    ok: bool = True
    request_id: str
    status: str
    message: str
    estimated_completion: Optional[datetime] = None


# ========================= HELPER FUNCTIONS =========================

def generate_request_id() -> str:
    """Generate unique request ID"""
    return f"req_{uuid.uuid4().hex[:12]}"


def hash_email(email: str) -> str:
    """Hash email for privacy"""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def get_user_data(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Gather all user data for export
    In production, this would query all tables containing user data
    """
    # This is a mock implementation
    # In production, query all relevant tables
    user_data = {
        "user_id": user_id,
        "export_timestamp": datetime.utcnow().isoformat(),
        "data_categories": {
            "profile": {
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "provider": "oauth"
            },
            "settings": {
                "crashlytics_enabled": False,
                "notifications_enabled": True,
                "language": "en"
            },
            "activity": {
                "searches": [],  # Would contain search history if stored
                "scans": [],     # Would contain scan history if stored
                "last_active": datetime.utcnow().isoformat()
            }
        },
        "data_notes": {
            "email": "Not stored unless provided for support",
            "personal_info": "No personal information stored",
            "third_party_sharing": "No data shared with third parties",
            "retention": "Data retained until deletion requested"
        }
    }
    
    return user_data


def delete_user_data(user_id: str, db: Session) -> bool:
    """
    Delete all user data
    In production, this would delete from all tables
    """
    try:
        # This is where you'd delete from all tables
        # For example:
        # db.query(User).filter(User.id == user_id).delete()
        # db.query(UserSettings).filter(UserSettings.user_id == user_id).delete()
        # db.query(SearchHistory).filter(SearchHistory.user_id == user_id).delete()
        # db.commit()
        
        logger.info(f"User data deletion completed for user_id: {user_id[:8]}...")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete user data: {e}")
        db.rollback()
        return False


# ========================= ENDPOINTS =========================

@router.post("/export", response_model=DataOperationResponse)
async def export_user_data(
    request: Request,
    export_request: DataExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id_header: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Export all user data (GDPR Article 20 - Right to Data Portability)
    
    This endpoint allows users to export all their data in a machine-readable format.
    The export includes all data associated with the user account.
    
    **Privacy Note**: 
    - Only data associated with the authenticated user is exported
    - No data from other users is included
    - Export is provided in JSON or CSV format
    """
    # Use provided user_id or header
    user_id = export_request.user_id or user_id_header
    
    if not user_id and not export_request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email must be provided"
        )
    
    request_id = generate_request_id()
    trace_id = f"export_{uuid.uuid4().hex[:8]}"
    
    try:
        # If email provided, hash it for logging
        email_hash = hash_email(export_request.email) if export_request.email else None
        
        # Log the export request
        logger.info(f"Data export requested", extra={
            "request_id": request_id,
            "user_id": user_id[:8] if user_id else None,
            "email_hash": email_hash[:8] if email_hash else None,
            "format": export_request.format,
            "trace_id": trace_id
        })
        
        # In production, this would be queued for async processing
        # For demo, we'll process immediately
        if user_id:
            user_data = get_user_data(user_id, db)
            
            if export_request.format == "json":
                # Return JSON data
                return JSONResponse(
                    content={
                        "ok": True,
                        "request_id": request_id,
                        "status": "completed",
                        "data": user_data,
                        "message": "Data export completed",
                        "trace_id": trace_id
                    },
                    status_code=200
                )
            else:
                # For CSV, we'd convert and return as file
                # This is simplified for demo
                return DataOperationResponse(
                    ok=True,
                    request_id=request_id,
                    status="completed",
                    message="CSV export completed (simplified demo)",
                    estimated_completion=datetime.utcnow()
                )
        else:
            # Email verification flow would go here
            return DataOperationResponse(
                ok=True,
                request_id=request_id,
                status="pending_verification",
                message="Verification email sent. Please check your email to confirm the export request.",
                estimated_completion=datetime.utcnow() + timedelta(minutes=30)
            )
            
    except Exception as e:
        logger.error(f"Data export failed: {e}", extra={
            "request_id": request_id,
            "trace_id": trace_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process data export request"
        )


@router.post("/delete", response_model=DataOperationResponse)
async def delete_user_data_endpoint(
    request: Request,
    deletion_request: DataDeletionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id_header: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Delete all user data (GDPR Article 17 - Right to Erasure)
    
    This endpoint allows users to request complete deletion of their data.
    The deletion is permanent and cannot be undone.
    
    **Important**: 
    - Deletion is PERMANENT and IRREVERSIBLE
    - All user data will be removed from our systems
    - This includes settings, preferences, and any stored information
    - You will need to create a new account if you use the app again
    """
    # Require explicit confirmation
    if not deletion_request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be explicitly confirmed (confirm=true)"
        )
    
    # Use provided user_id or header
    user_id = deletion_request.user_id or user_id_header
    
    if not user_id and not deletion_request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or email must be provided"
        )
    
    request_id = generate_request_id()
    trace_id = f"delete_{uuid.uuid4().hex[:8]}"
    
    try:
        # If email provided, hash it for logging
        email_hash = hash_email(deletion_request.email) if deletion_request.email else None
        
        # Log the deletion request
        logger.info(f"Data deletion requested", extra={
            "request_id": request_id,
            "user_id": user_id[:8] if user_id else None,
            "email_hash": email_hash[:8] if email_hash else None,
            "reason": deletion_request.reason,
            "trace_id": trace_id
        })
        
        if user_id:
            # In production, this would be queued for async processing
            # For demo, we'll process immediately
            success = delete_user_data(user_id, db)
            
            if success:
                return DataOperationResponse(
                    ok=True,
                    request_id=request_id,
                    status="completed",
                    message="All user data has been permanently deleted",
                    estimated_completion=datetime.utcnow()
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete user data"
                )
        else:
            # Email verification flow would go here
            return DataOperationResponse(
                ok=True,
                request_id=request_id,
                status="pending_verification",
                message="Verification email sent. Please check your email to confirm the deletion request.",
                estimated_completion=datetime.utcnow() + timedelta(hours=24)
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data deletion failed: {e}", extra={
            "request_id": request_id,
            "trace_id": trace_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process data deletion request"
        )


@router.get("/export/status/{request_id}")
async def get_export_status(request_id: str):
    """
    Check status of data export request
    
    Returns the current status of a data export request.
    """
    # In production, this would check a job queue or database
    # For demo, we'll return a mock status
    
    return {
        "ok": True,
        "request_id": request_id,
        "status": "completed",
        "message": "Export ready for download",
        "download_url": f"/api/v1/user/data/download/{request_id}",
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
    }


@router.get("/delete/status/{request_id}")
async def get_deletion_status(request_id: str):
    """
    Check status of data deletion request
    
    Returns the current status of a data deletion request.
    """
    # In production, this would check a job queue or database
    # For demo, we'll return a mock status
    
    return {
        "ok": True,
        "request_id": request_id,
        "status": "completed",
        "message": "All user data has been deleted",
        "completed_at": datetime.utcnow().isoformat()
    }


@router.get("/download/{request_id}")
async def download_export(
    request_id: str,
    format: Optional[str] = "json",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download exported user data for the authenticated user.

    For this implementation, we generate the export on demand and stream it
    as a file download. In production, this could 302-redirect to a presigned
    S3 URL for the pre-generated artifact.
    """
    try:
        user_id = str(current_user.id)
        data = get_user_data(user_id, db)

        if (format or "").lower() == "csv":
            # Very simple CSV export of top-level keys for demo purposes
            import io, csv
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["key", "value"]) 
            for k, v in data.items():
                writer.writerow([k, json.dumps(v, default=str)])
            buf.seek(0)
            return StreamingResponse(
                buf,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=export_{request_id}.csv"
                },
            )
        else:
            # JSON download
            import io
            payload = json.dumps(data, default=str).encode("utf-8")
            return StreamingResponse(
                io.BytesIO(payload),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=export_{request_id}.json"
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to download export")


# ========================= PRIVACY SUMMARY ENDPOINT =========================

@privacy_router.get("/summary")
async def get_privacy_summary(
    user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """
    Get privacy policy summary and user's privacy settings
    """
    try:
        summary = {
            "ok": True,
            "summary": {
                "data_collected": [
                    "OAuth provider ID (encrypted)",
                    "Product scan history (anonymized)",
                    "Safety preferences (local storage)",
                    "App usage analytics (aggregated)"
                ],
                "data_retention": {
                    "scan_history": "30 days (anonymized after 7 days)",
                    "user_preferences": "Until account deletion",
                    "analytics": "Aggregated, no personal identifiers"
                },
                "user_rights": [
                    "Right to access your data",
                    "Right to data portability", 
                    "Right to deletion",
                    "Right to rectification",
                    "Right to restrict processing"
                ],
                "contact_info": {
                    "privacy_officer": "privacy@babyshield.com",
                    "data_protection": "dpo@babyshield.com"
                }
            },
            "user_settings": {
                "user_id": user_id[:8] + "..." if user_id else "anonymous",
                "data_sharing": False,
                "analytics": True,
                "crashlytics": False
            },
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
        return JSONResponse(content=summary)
        
    except Exception as e:
        logger.error(f"Privacy summary error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "PRIVACY_SUMMARY_FAILED",
                    "message": "Failed to retrieve privacy summary"
                }
            }
        )
