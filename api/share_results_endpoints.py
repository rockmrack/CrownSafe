"""
Share Results API Endpoints
Secure sharing of scan results and reports
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.orm import Session
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import uuid
import boto3

from core_infra.database import get_db
from db.models.share_token import ShareToken
from db.models.scan_history import ScanHistory, SafetyReport
from api.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

# Create router
share_router = APIRouter(prefix="/api/v1/share", tags=["share-results"])

# S3 Configuration
S3_BUCKET = os.getenv("S3_BUCKET", "babyshield-images")
s3_client = boto3.client("s3", region_name=os.getenv("S3_BUCKET_REGION", "us-east-1"))


def _is_uuid(s: str) -> bool:
    """Check if a string is a valid UUID"""
    try:
        uuid.UUID(str(s))
        return True
    except (ValueError, TypeError):
        return False


def _guess_s3_key(user_id: int, report_uuid: str, content_type: str) -> Optional[str]:
    """Guess S3 key for report by trying common layouts"""
    now = datetime.now(timezone.utc)
    year = now.strftime("%Y")
    month = now.strftime("%m")
    
    # Try common layouts that align with /baby/reports/download pathing
    candidates = [
        f"reports/{user_id}/{year}/{month}/safety_summary/{report_uuid}.pdf",
        f"reports/{user_id}/{year}/{month}/safety-summary/{report_uuid}.pdf",
        f"reports/{user_id}/{year}/{month}/{content_type}/{report_uuid}.pdf",
        f"reports/{user_id}/{year}/{month}/product_safety/{report_uuid}.pdf",
        f"reports/{user_id}/{year}/{month}/nursery_quarterly/{report_uuid}.pdf",
    ]
    
    for key in candidates:
        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=key)
            logger.info(f"Found S3 object at key: {key}")
            return key
        except Exception:
            continue
    
    logger.warning(f"No S3 object found for UUID {report_uuid} in any candidate path")
    return None


def create_share_token_for_s3(user_id: int, content_type: str, content_ref: str, s3_key: str, ttl_hours: int = 24) -> str:
    """Create share token for S3-based content without database record"""
    token = ShareToken.generate_token()
    expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
    
    # Create content snapshot for S3-based report
    content_snapshot = {
        "report_id": content_ref,
        "report_type": content_type,
        "pdf_available": True,
        "s3_key": s3_key,
        "created_via": "s3_uuid"
    }
    
    # Create share token record
    share_token = ShareToken(
        token=token,
        share_type=content_type,
        content_id=content_ref,
        created_by=user_id,
        expires_at=expires_at,
        max_views=None,
        password_protected=False,
        password_hash=None,
        allow_download=True,
        show_personal_info=False,
        content_snapshot=content_snapshot
    )
    
    return token, share_token


class ShareRequest(BaseModel):
    """Request model for creating a share link"""
    content_type: str = Field(..., description="Type of content (scan_result, report, safety_summary, nursery_quarterly)")
    content_id: Union[str, int] = Field(..., description="ID of the content to share (numeric ID or UUID)")
    user_id: int = Field(..., description="User creating the share")
    
    # Optional UUID field for reports
    report_uuid: Optional[str] = Field(None, description="Report UUID (alternative to content_id for reports)")
    
    # Share settings
    expires_in_hours: Optional[int] = Field(24, description="Hours until expiration (default 24)")
    max_views: Optional[int] = Field(None, description="Maximum number of views")
    password: Optional[str] = Field(None, description="Optional password protection")
    allow_download: bool = Field(True, description="Allow downloading PDFs")
    show_personal_info: bool = Field(False, description="Include personal information")


class EmailShareRequest(BaseModel):
    """Request model for sharing via email"""
    share_token: str = Field(..., description="Share token to send")
    recipient_email: EmailStr = Field(..., description="Recipient email address")
    sender_name: str = Field(..., description="Sender's name")
    message: Optional[str] = Field(None, description="Personal message to include")


class ShareResponse(BaseModel):
    """Response model for share creation"""
    success: bool
    share_token: str
    share_url: str
    expires_at: Optional[datetime]
    qr_code_url: Optional[str]


class SharedContentResponse(BaseModel):
    """Response model for viewing shared content"""
    success: bool
    content_type: str
    content: Dict[str, Any]
    allow_download: bool
    views_remaining: Optional[int]


@share_router.post("/create-dev", response_model=ApiResponse)
async def create_share_link_dev(
    request: ShareRequest
) -> ApiResponse:
    """
    Dev override version of create share link for testing (no database)
    """
    try:
        # Validate content type
        valid_content_types = ["scan_result", "report", "safety_summary", "nursery_quarterly", "product_safety"]
        if request.content_type not in valid_content_types:
            raise HTTPException(status_code=400, detail=f"Invalid content type: {request.content_type}. Supported types: {', '.join(valid_content_types)}")
        
        # Mock share creation for testing (no database)
        token = f"dev_token_{request.user_id}_{int(datetime.utcnow().timestamp())}"
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours or 24)
        
        # Generate URLs
        base_url = os.getenv("APP_BASE_URL", "https://babyshield.cureviax.ai")
        share_url = f"{base_url}/share/{token}"
        qr_code_url = f"{base_url}/api/v1/share/qr/{token}"
        
        # Store in memory for testing (in production, this would be in database)
        if not hasattr(create_share_link_dev, 'mock_shares'):
            create_share_link_dev.mock_shares = {}
        
        create_share_link_dev.mock_shares[token] = {
            "token": token,
            "share_type": request.content_type,
            "content_id": str(request.content_id),
            "created_by": request.user_id,
            "expires_at": expires_at,
            "is_active": True,
            "revoked_at": None,
            "content_snapshot": {
                "report_id": str(request.content_id),
                "report_type": request.content_type,
                "pdf_available": True,
                "created_via": "dev_override"
            }
        }
        
        response = ShareResponse(
            success=True,
            share_token=token,
            share_url=share_url,
            expires_at=expires_at,
            qr_code_url=qr_code_url
        )
        
        return ApiResponse(
            success=True,
            data=response.model_dump(),
            message="Share link created successfully (dev override)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating share link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create share link: {str(e)}")

@share_router.post("/create", response_model=ApiResponse)
async def create_share_link(
    request: ShareRequest,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Create a shareable link for scan results or reports
    
    Features:
    - Time-limited sharing (expires after X hours)
    - View count limits
    - Optional password protection
    - Secure token generation
    """
    try:
        # UUID/S3 branch - handle reports that exist in S3 but not in database
        if isinstance(request.content_id, str) and _is_uuid(request.content_id):
            logger.info(f"Processing UUID-based share request: {request.content_id}")
            
            # Try to find the S3 object
            s3_key = _guess_s3_key(request.user_id, request.content_id, request.content_type or "safety_summary")
            if not s3_key:
                raise HTTPException(status_code=404, detail=f"Report not found for UUID: {request.content_id}")
            
            # Create share token for S3-based content
            token, share_token = create_share_token_for_s3(
                user_id=request.user_id,
                content_type=request.content_type or "safety_summary",
                content_ref=request.content_id,
                s3_key=s3_key,
                ttl_hours=request.expires_in_hours or 24
            )
            
            # Add to database
            db.add(share_token)
            db.commit()
            
            # Generate URLs
            base_url = os.getenv("APP_BASE_URL", "https://babyshield.cureviax.ai")
            share_url = f"{base_url}/share/{token}"
            qr_code_url = f"{base_url}/api/v1/share/qr/{token}"
            
            response = ShareResponse(
                success=True,
                share_token=token,
                share_url=share_url,
                expires_at=share_token.expires_at,
                qr_code_url=qr_code_url
            )
            
            logger.info(f"Created UUID-based share token: {token}")
            return ApiResponse(success=True, data=response.model_dump())
        
        # Fall back to existing database-based logic
        # Validate content exists
        content_snapshot = None
        content_id_to_store = str(request.content_id)
        
        if request.content_type == "scan_result":
            # Get scan history (numeric ID only)
            if not isinstance(request.content_id, (int, str)) or _is_uuid(str(request.content_id)):
                raise HTTPException(status_code=400, detail="Scan results require numeric scan_id, not UUID")
            
            scan = db.query(ScanHistory).filter(
                ScanHistory.scan_id == request.content_id,
                ScanHistory.user_id == request.user_id
            ).first()
            
            if not scan:
                raise HTTPException(status_code=404, detail=f"Scan result not found for scan_id: {request.content_id}. Make sure the scan exists and belongs to user {request.user_id}")
            
            # Create content snapshot
            content_snapshot = {
                "scan_id": scan.scan_id,
                "product_name": scan.product_name,
                "brand": scan.brand,
                "barcode": scan.barcode,
                "scan_timestamp": scan.scan_timestamp.isoformat() if scan.scan_timestamp else None,
                "verdict": scan.verdict,
                "risk_level": scan.risk_level,
                "recalls_found": scan.recalls_found,
                "agencies_checked": scan.agencies_checked
            }
            
            # Remove personal info if not allowed
            if not request.show_personal_info:
                content_snapshot.pop("user_id", None)
        
        elif request.content_type in ["report", "safety_summary", "nursery_quarterly", "product_safety"]:
            # Handle reports - support both numeric ID and UUID
            report_uuid = request.report_uuid or str(request.content_id)
            
            # Check if it's a UUID (new report format)
            if _is_uuid(report_uuid):
                # UUID path - check if S3 object exists
                try:
                    s3_key = _guess_s3_key(request.user_id, report_uuid, request.content_type)
                    
                    # Check if S3 object exists
                    s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
                    
                    # Create content snapshot for UUID-based report
                    content_snapshot = {
                        "report_id": report_uuid,
                        "report_type": request.content_type,
                        "pdf_available": True,
                        "s3_key": s3_key,
                        "created_via": "uuid"
                    }
                    content_id_to_store = report_uuid
                    
                except Exception as e:
                    logger.warning(f"S3 object not found for report UUID {report_uuid}: {e}")
                    raise HTTPException(status_code=404, detail=f"Report not found for UUID: {report_uuid}. The report may not exist or may have been deleted.")
            
            else:
                # Numeric ID path - check database
                try:
                    numeric_id = int(request.content_id)
                    report = db.query(SafetyReport).filter(
                        SafetyReport.report_id == str(numeric_id),
                        SafetyReport.user_id == request.user_id
                    ).first()
                    
                    if not report:
                        raise HTTPException(status_code=404, detail=f"Report not found for report_id: {request.content_id}. Make sure the report exists and belongs to user {request.user_id}")
                    
                    # Create content snapshot
                    content_snapshot = {
                        "report_id": report.report_id,
                        "report_type": report.report_type,
                        "period_start": report.period_start.isoformat() if report.period_start else None,
                        "period_end": report.period_end.isoformat() if report.period_end else None,
                        "total_scans": report.total_scans,
                        "unique_products": report.unique_products,
                        "recalls_found": report.recalls_found,
                        "high_risk_products": report.high_risk_products,
                        "pdf_available": bool(report.pdf_path or report.s3_url),
                        "created_via": "database"
                    }
                    content_id_to_store = str(numeric_id)
                    
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid content_id format: {request.content_id}. Must be numeric ID or valid UUID.")
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid content type: {request.content_type}. Supported types: scan_result, report, safety_summary, nursery_quarterly, product_safety")
        
        # Generate share token
        token = ShareToken.generate_token()
        
        # Calculate expiration
        expires_at = None
        if request.expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
        
        # Hash password if provided
        password_hash = None
        if request.password:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            password_hash = pwd_context.hash(request.password)
        
        # Create share token record
        share_token = ShareToken(
            token=token,
            share_type=request.content_type,
            content_id=content_id_to_store,
            created_by=request.user_id,
            expires_at=expires_at,
            max_views=request.max_views,
            password_protected=bool(request.password),
            password_hash=password_hash,
            allow_download=request.allow_download,
            show_personal_info=request.show_personal_info,
            content_snapshot=content_snapshot
        )
        
        db.add(share_token)
        db.commit()
        
        # Generate URLs
        base_url = os.getenv("APP_BASE_URL", "https://babyshield.cureviax.ai")
        share_url = f"{base_url}/share/{token}"
        qr_code_url = f"{base_url}/api/v1/share/qr/{token}"
        
        response = ShareResponse(
            success=True,
            share_token=token,
            share_url=share_url,
            expires_at=expires_at,
            qr_code_url=qr_code_url
        )
        
        return ApiResponse(success=True, data=response.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.get("/view-dev/{token}", response_model=ApiResponse)
async def view_share_link_dev(
    token: str
) -> ApiResponse:
    """
    Dev override version of view share link for testing (no database)
    """
    try:
        # Get share token from in-memory storage
        if not hasattr(create_share_link_dev, 'mock_shares'):
            create_share_link_dev.mock_shares = {}
        
        share_data = create_share_link_dev.mock_shares.get(token)
        
        if not share_data:
            raise HTTPException(status_code=404, detail="Share link not found")
        
        # Check if expired
        if share_data["expires_at"] and share_data["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Share link has expired")
        
        # Check if revoked
        if not share_data["is_active"]:
            raise HTTPException(status_code=410, detail="Share link has been revoked")
        
        # Mock content for testing
        mock_content = {
            "report_id": share_data["content_id"],
            "report_type": share_data["share_type"],
            "title": f"Safety Report: {share_data['share_type']}",
            "summary": "This is a mock safety report for testing purposes",
            "created_at": share_data["expires_at"].isoformat(),  # Using expires_at as created_at for simplicity
            "expires_at": share_data["expires_at"].isoformat() if share_data["expires_at"] else None,
            "pdf_available": True,
            "created_via": "dev_override"
        }
        
        return ApiResponse(
            success=True,
            data={
                "content": mock_content,
                "allow_download": True,
                "views_remaining": None
            },
            message="Share content retrieved successfully (dev override)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing share link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to view share link: {str(e)}")

@share_router.get("/view/{token}", response_model=ApiResponse)
async def view_shared_content(
    token: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> ApiResponse:
    """
    View shared content via share token
    
    Features:
    - Token validation
    - Password verification if required
    - View count tracking
    - Expiration checking
    """
    try:
        # Get share token
        share_token = db.query(ShareToken).filter(
            ShareToken.token == token
        ).first()
        
        if not share_token:
            raise HTTPException(status_code=404, detail="Share link not found")
        
        # Validate token
        if not share_token.is_valid():
            raise HTTPException(status_code=410, detail="Share link has expired or reached view limit")
        
        # Check password if required
        if share_token.password_protected:
            if not password:
                raise HTTPException(status_code=401, detail="Password required")
            
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            if not pwd_context.verify(password, share_token.password_hash):
                raise HTTPException(status_code=401, detail="Invalid password")
        
        # Increment view count
        share_token.increment_view()
        db.commit()
        
        # Calculate views remaining
        views_remaining = None
        if share_token.max_views:
            views_remaining = max(0, share_token.max_views - share_token.view_count)
        
        # Return content
        response = SharedContentResponse(
            success=True,
            content_type=share_token.share_type,
            content=share_token.content_snapshot or {},
            allow_download=share_token.allow_download,
            views_remaining=views_remaining
        )
        
        return ApiResponse(success=True, data=response.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing shared content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.post("/email", response_model=ApiResponse)
async def share_via_email(
    request: EmailShareRequest,
    db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Share results via email
    
    Sends an email with the share link to the recipient
    """
    try:
        # Get share token to validate it exists
        share_token = db.query(ShareToken).filter(
            ShareToken.token == request.share_token
        ).first()
        
        if not share_token:
            raise HTTPException(status_code=404, detail="Share link not found")
        
        if not share_token.is_valid():
            raise HTTPException(status_code=410, detail="Share link has expired")
        
        # Prepare email content
        base_url = os.getenv("APP_BASE_URL", "https://babyshield.cureviax.ai")
        share_url = f"{base_url}/share/{request.share_token}"
        
        # Create email message
        subject = f"{request.sender_name} shared BabyShield safety results with you"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #1a237e;">BabyShield Safety Results</h2>
                    <p>Hi,</p>
                    <p><strong>{request.sender_name}</strong> has shared product safety results with you from BabyShield.</p>
                    
                    {f'<p style="background-color: #e3f2fd; padding: 15px; border-radius: 5px;"><em>{request.message}</em></p>' if request.message else ''}
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{share_url}" style="background-color: #2196f3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            View Safety Results
                        </a>
                    </div>
                    
                    <p style="color: #666; font-size: 14px;">
                        This link will expire in {(share_token.expires_at - datetime.utcnow()).total_seconds() / 3600:.0f} hours.
                        {f'It can be viewed {share_token.max_views - share_token.view_count} more time(s).' if share_token.max_views else ''}
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px;">
                        BabyShield helps parents make informed decisions about product safety.
                        <br>
                        <a href="https://babyshield.cureviax.ai" style="color: #2196f3;">Learn more about BabyShield</a>
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Send email (using configured SMTP settings)
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        
        if smtp_user and smtp_password:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = request.recipient_email
            
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            message = "Email sent successfully"
        else:
            # If SMTP not configured, just return the share URL
            message = f"Share link: {share_url} (Email service not configured)"
        
        return ApiResponse(
            success=True,
            data={
                "message": message,
                "share_url": share_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing via email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.delete("/revoke-dev/{token}", response_model=ApiResponse)
async def revoke_share_link_dev(
    token: str,
    user_id: int = Query(..., description="User revoking the share")
) -> ApiResponse:
    """
    Dev override version of revoke share link for testing (no database)
    """
    try:
        # Get share token from in-memory storage
        if not hasattr(create_share_link_dev, 'mock_shares'):
            create_share_link_dev.mock_shares = {}
        
        share_data = create_share_link_dev.mock_shares.get(token)
        
        if not share_data:
            raise HTTPException(status_code=404, detail="Share link not found or unauthorized")
        
        # Check authorization
        if share_data["created_by"] != user_id:
            raise HTTPException(status_code=404, detail="Share link not found or unauthorized")
        
        # Revoke the token
        share_data["is_active"] = False
        share_data["revoked_at"] = datetime.utcnow()
        
        return ApiResponse(
            success=True,
            data={"message": "Share link revoked successfully (dev override)"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking share link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to revoke share link: {str(e)}")

@share_router.delete("/revoke/{token}", response_model=ApiResponse)
async def revoke_share_link(
    token: str,
    user_id: int = Query(..., description="User revoking the share"),
    db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Revoke a share link
    
    Only the creator can revoke their share links
    """
    try:
        # Get share token
        share_token = db.query(ShareToken).filter(
            ShareToken.token == token,
            ShareToken.created_by == user_id
        ).first()
        
        if not share_token:
            raise HTTPException(status_code=404, detail="Share link not found or unauthorized")
        
        # Revoke the token
        share_token.is_active = False
        share_token.revoked_at = datetime.utcnow()
        db.commit()
        
        return ApiResponse(
            success=True,
            data={"message": "Share link revoked successfully"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking share link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.get("/my-shares", response_model=ApiResponse)
async def get_my_share_links(
    user_id: int = Query(..., description="User ID"),
    active_only: bool = Query(True, description="Only show active shares"),
    db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Get all share links created by a user
    """
    try:
        query = db.query(ShareToken).filter(
            ShareToken.created_by == user_id
        )
        
        if active_only:
            query = query.filter(ShareToken.is_active == True)
        
        shares = query.order_by(ShareToken.created_at.desc()).limit(50).all()
        
        share_list = []
        for share in shares:
            share_data = share.to_dict()
            # Add validity status
            share_data["is_valid"] = share.is_valid()
            share_list.append(share_data)
        
        return ApiResponse(
            success=True,
            data={
                "shares": share_list,
                "total": len(share_list)
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching user shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.get("/qr/{token}")
async def generate_share_qr_code(token: str):
    """
    Generate QR code for share link
    """
    try:
        import qrcode
        from io import BytesIO
        from fastapi.responses import StreamingResponse
        
        # Generate share URL
        base_url = os.getenv("APP_BASE_URL", "https://babyshield.cureviax.ai")
        share_url = f"{base_url}/share/{token}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(share_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        
        return StreamingResponse(img_bytes, media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@share_router.get("/preview-dev/{token}")
async def preview_share_link_dev(
    token: str
) -> HTMLResponse:
    """
    Dev override version of preview share link for testing (no database)
    """
    try:
        # Get share token from in-memory storage
        if not hasattr(create_share_link_dev, 'mock_shares'):
            create_share_link_dev.mock_shares = {}
        
        share_data = create_share_link_dev.mock_shares.get(token)
        
        if not share_data:
            raise HTTPException(status_code=404, detail="Share link not found")
        
        # Check if expired
        if share_data["expires_at"] and share_data["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Share link has expired")
        
        # Check if revoked
        if not share_data["is_active"]:
            raise HTTPException(status_code=410, detail="Share link has been revoked")
        
        # Mock HTML preview for testing
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Safety Report Preview (Dev Override)</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .footer {{ color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Safety Report Preview</h1>
                <p><strong>Report Type:</strong> {share_data['share_type']}</p>
                <p><strong>Report ID:</strong> {share_data['content_id']}</p>
                <p><strong>Created By:</strong> User {share_data['created_by']}</p>
                <p><strong>Expires:</strong> {share_data['expires_at']}</p>
            </div>
            <div class="content">
                <h2>Report Summary</h2>
                <p>This is a mock safety report for testing purposes. The actual report content would be displayed here.</p>
                <p><strong>Status:</strong> Active and accessible</p>
                <p><strong>Download:</strong> Available</p>
            </div>
            <div class="footer">
                <p>This is a development preview. Created via dev override.</p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing share link: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview share link: {str(e)}")

@share_router.get("/preview/{token}")
async def preview_shared_content(
    token: str,
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Generate a preview page for shared content
    
    This returns an HTML page that can be shared on social media
    """
    try:
        # Get share token
        share_token = db.query(ShareToken).filter(
            ShareToken.token == token
        ).first()
        
        if not share_token or not share_token.is_valid():
            html_content = """
            <html>
                <head><title>BabyShield - Link Expired</title></head>
                <body>
                    <h1>Share Link Expired</h1>
                    <p>This share link has expired or is no longer valid.</p>
                </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=410)
        
        # Generate preview HTML
        content = share_token.content_snapshot or {}
        
        if share_token.share_type == "scan_result":
            title = f"Product Safety: {content.get('product_name', 'Unknown Product')}"
            description = f"Risk Level: {content.get('risk_level', 'Unknown')} | Verdict: {content.get('verdict', 'No data')}"
        else:
            title = f"Safety Report: {content.get('report_type', 'Unknown Type')}"
            description = f"Products: {content.get('unique_products', 0)} | Recalls: {content.get('recalls_found', 0)}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BabyShield - {title}</title>
            <meta property="og:title" content="{title}" />
            <meta property="og:description" content="{description}" />
            <meta property="og:type" content="website" />
            <meta property="og:image" content="https://babyshield.cureviax.ai/logo.png" />
            <meta name="twitter:card" content="summary" />
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{ color: #1a237e; }}
                .info-box {{
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .button {{
                    background: #2196f3;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ BabyShield Safety Results</h1>
                <div class="info-box">
                    <h2>{title}</h2>
                    <p>{description}</p>
                </div>
                <p>This safety information has been shared with you via BabyShield.</p>
                <a href="/api/v1/share/view/{token}" class="button">View Full Results</a>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        html_content = """
        <html>
            <head><title>BabyShield - Error</title></head>
            <body>
                <h1>Error</h1>
                <p>An error occurred while loading the preview.</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=500)
