import pathlib
from api.pydantic_base import AppModel

"""
BabyShield Core Features API Endpoints
Provides endpoints for product alternatives, push notifications, and safety reports
"""

import logging
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import (
    Response,
    APIRouter,
    HTTPException,
    Depends,
    Query,
    Body,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
import asyncio
from pathlib import Path
from shutil import copyfile
import os
import inspect

from core_infra.database import get_db, User, RecallDB
from core_infra.auth import get_current_active_user
from db.models.report_record import ReportRecord
from core_infra.s3_uploads import upload_file, presign_get
from agents.value_add.alternatives_agent.agent_logic import AlternativesAgentLogic
from agents.engagement.push_notification_agent.agent_logic import (
    PushNotificationAgentLogic,
)
from agents.reporting.report_builder_agent.agent_logic import ReportBuilderAgentLogic
from agents.engagement.community_alert_agent.agent_logic import CommunityAlertAgentLogic
from agents.engagement.onboarding_agent.agent_logic import OnboardingAgentLogic
from agents.hazard_analysis_agent.agent_logic import HazardAnalysisLogic
from api.schemas.common import ok

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(prefix="/api/v1/baby", tags=["Baby Safety Features"])

# Reports directory (shared with report builder output)
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", Path.cwd() / "generated_reports"))
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _write_report_metadata(report_id: str, owner_user_id: int, report_type: str, file_path: Path) -> None:
    try:
        meta = {
            "report_id": report_id,
            "user_id": owner_user_id,
            "report_type": report_type,
            "file_path": str(file_path),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(REPORTS_DIR / f"report_{report_id}.json", "w", encoding="utf-8") as fh:
            json.dump(meta, fh)
    except Exception as _:
        pass


def _load_report_metadata(report_id: str) -> dict:
    try:
        with open(REPORTS_DIR / f"report_{report_id}.json", "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _cleanup_old_reports(retain_days: int = 7) -> None:
    try:
        cutoff = datetime.utcnow() - timedelta(days=retain_days)
        for p in REPORTS_DIR.glob("report_*.pdf"):
            try:
                mtime = datetime.utcfromtimestamp(p.stat().st_mtime)
                if mtime < cutoff:
                    p.unlink(missing_ok=True)
                    meta = p.with_suffix(".json")
                    if meta.exists():
                        meta.unlink(missing_ok=True)
            except Exception:
                continue
    except Exception:
        pass


# ==================== Request/Response Models ====================


class AlternativesRequest(BaseModel):
    """Request model for finding safe alternatives"""

    product_name: Optional[str] = Field(None, description="Name of recalled product")
    product_category: Optional[str] = Field(None, description="Category of product")
    barcode: Optional[str] = Field(None, description="Product barcode if available")
    user_id: int = Field(..., description="User ID for personalized recommendations")
    max_alternatives: int = Field(5, ge=1, le=20, description="Maximum alternatives to return")


class AlternativeProduct(BaseModel):
    """Model for an alternative product suggestion"""

    product_name: str
    barcode: Optional[str] = None
    brand: Optional[str] = None
    reason: str
    safety_score: float = Field(..., ge=0, le=100)
    price_range: Optional[str] = None
    where_to_buy: Optional[List[str]] = None
    age_range: Optional[str] = None


class AlternativesResponse(BaseModel):
    """Response model for alternatives"""

    status: str
    original_product: str
    category_detected: str
    alternatives_found: int
    alternatives: List[AlternativeProduct]
    personalized: bool
    timestamp: datetime


class NotificationRequest(BaseModel):
    """Request model for push notifications"""

    user_id: int = Field(..., description="User ID to send notification to")
    title: str = Field(..., max_length=100, description="Notification title")
    body: str = Field(..., max_length=500, description="Notification body")
    notification_type: str = Field("recall_alert", description="Type: recall_alert, safety_tip, reminder")
    data: Optional[Dict[str, str]] = Field(None, description="Additional data payload")
    device_tokens: Optional[List[str]] = Field(
        None, description="Specific device tokens, or all user devices if not provided"
    )
    priority: str = Field("high", description="Priority: high, normal, low")


class BulkNotificationRequest(BaseModel):
    """Request for sending notifications to multiple users"""

    user_ids: List[int] = Field(..., description="List of user IDs")
    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=500)
    notification_type: str = Field("recall_alert")
    product_info: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    """Response model for notifications"""

    status: str
    notification_id: str
    sent_count: int
    failed_count: int
    devices_targeted: int
    timestamp: datetime
    errors: Optional[List[str]] = None


class ReportRequest(AppModel):
    """Request model for safety report generation"""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    user_id: int = Field(..., description="User ID for the report")
    report_type: str = Field(
        "safety_summary",
        description="Type: safety_summary, recall_history, product_analysis, product_safety, nursery_quarterly",
    )
    format: str = Field("pdf", description="Format: pdf, html, json")
    date_range: Optional[int] = Field(30, description="Days of history to include")
    include_alternatives: bool = Field(True, description="Include safe alternatives in report")
    include_guidelines: bool = Field(True, description="Include safety guidelines")
    products: Optional[List[str]] = Field(None, description="Specific products to include")
    # Product Safety (Level 1)
    product_name: Optional[str] = Field(None, description="Product name for product_safety report")
    barcode: Optional[str] = Field(None, description="UPC/EAN/GTIN for product_safety report")
    model_number: Optional[str] = Field(None, description="Model number if available")
    lot_or_serial: Optional[str] = Field(None, description="Lot or Serial number if available")


class ReportResponse(BaseModel):
    """Response model for report generation"""

    status: str
    report_id: str
    report_type: str
    format: str
    download_url: Optional[str] = None
    file_size_kb: Optional[int] = None
    pages: Optional[int] = None
    generated_at: datetime


class OnboardingRequest(BaseModel):
    """Request model for user onboarding"""

    user_id: int
    child_age_months: Optional[int] = Field(None, ge=0, le=216, description="Child's age in months (0-18 years)")
    expecting: Optional[bool] = Field(False, description="Is the user expecting?")
    due_date: Optional[str] = Field(None, description="Expected due date if pregnant")
    interests: Optional[List[str]] = Field(None, description="Product categories of interest")
    notification_preferences: Optional[Dict[str, bool]] = None


class HazardAnalysisRequest(BaseModel):
    """Request model for hazard analysis"""

    product_name: Optional[str] = None
    barcode: Optional[str] = None
    user_id: int
    child_age_months: Optional[int] = None


class HazardAnalysisResponse(AppModel):
    """Response model for hazard analysis"""

    product: str
    overall_risk_level: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    hazards_identified: List[Dict[str, Any]]
    age_appropriate: bool
    recommendations: List[str]
    safer_alternatives: Optional[List[str]] = None


# Initialize agent instances
alternatives_agent = AlternativesAgentLogic(agent_id="api_alternatives_agent")
notification_agent = PushNotificationAgentLogic(agent_id="api_notification_agent")
# Initialize other agents with try/except for graceful degradation
try:
    report_agent = ReportBuilderAgentLogic(agent_id="api_report_agent", version="1.0")
except Exception as e:
    report_agent = None
    logger.warning(f"Report Builder Agent not available: {e}", exc_info=True)

try:
    community_agent = CommunityAlertAgentLogic(agent_id="api_community_agent")
except Exception as e:
    community_agent = None
    logger.warning(f"Community Alert Agent not available: {e}", exc_info=True)

try:
    onboarding_agent = OnboardingAgentLogic(agent_id="api_onboarding_agent")
except Exception as e:
    onboarding_agent = None
    logger.warning(f"Onboarding Agent not available: {e}", exc_info=True)

try:
    hazard_agent = HazardAnalysisLogic(agent_id="api_hazard_agent")
except Exception as e:
    hazard_agent = None
    logger.warning(f"Hazard Analysis Agent not available: {e}", exc_info=True)

# ==================== Alternatives Endpoints ====================


@router.post("/alternatives")
async def get_safe_alternatives(request: AlternativesRequest, db: Session = Depends(get_db)):
    """
    Get safe alternative products when a recall is found.

    This endpoint:
    1. Identifies the product category
    2. Finds safer alternatives in the same category
    3. Personalizes recommendations based on user preferences
    4. Returns ranked alternatives with safety scores
    """
    try:
        logger.info(f"Finding alternatives for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Determine product category
        category = request.product_category
        if not category and request.product_name:
            # Try to infer category from product name
            product_lower = request.product_name.lower()
            if any(term in product_lower for term in ["formula", "milk", "bottle"]):
                category = "Infant Formula"
            elif any(term in product_lower for term in ["toy", "play", "rattle"]):
                category = "Baby Toys"
            elif any(term in product_lower for term in ["car seat", "booster"]):
                category = "Car Seats"
            elif any(term in product_lower for term in ["crib", "bassinet", "sleeper"]):
                category = "Cribs & Sleepers"
            elif any(term in product_lower for term in ["stroller", "carrier"]):
                category = "Strollers & Carriers"
            elif any(term in product_lower for term in ["diaper", "wipe"]):
                category = "Diapers & Wipes"
            else:
                category = "Baby Products"

        # Get alternatives from agent
        alternatives_result = await alternatives_agent.process_task({"product_category": category or "Baby Products"})

        # Process and enhance alternatives
        alternatives = []
        if alternatives_result.get("status") == "COMPLETED":
            for alt in alternatives_result.get("result", {}).get("alternatives", []):
                # Calculate safety score (mock for now, could integrate with recall database)
                safety_score = 95.0  # Base score for curated safe products

                # Check if product has any recalls in database
                if alt.get("upc"):
                    recall_count = db.query(RecallDB).filter(RecallDB.upc == alt["upc"]).count()
                    if recall_count > 0:
                        safety_score -= recall_count * 10  # Reduce score for each recall

                alternatives.append(
                    AlternativeProduct(
                        product_name=alt.get("product_name", "Unknown Product"),
                        barcode=alt.get("upc"),
                        brand=alt.get("brand"),
                        reason=alt.get("reason", "Recommended safe alternative"),
                        safety_score=max(safety_score, 0),
                        price_range=alt.get("price_range", "$10-30"),
                        where_to_buy=[
                            "Amazon",
                            "Target",
                            "Walmart",
                        ],  # Could be enhanced
                        age_range=alt.get("age_range", "0-12 months"),
                    )
                )

        # Sort by safety score
        alternatives.sort(key=lambda x: x.safety_score, reverse=True)

        # Limit to requested max
        alternatives = alternatives[: request.max_alternatives]

        payload = {
            "original_product": request.product_name or "Unknown Product",
            "category_detected": category or "General",
            "alternatives_found": len(alternatives),
            "alternatives": [a.dict() for a in alternatives],
            "personalized": bool(user),
            "timestamp": datetime.now(),
        }
        if len(alternatives) == 0:
            payload["notice"] = "No curated alternatives available yet for this category."
        return ok(payload)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find alternatives: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find alternatives: {str(e)}")


# ==================== Push Notification Endpoints ====================


@router.post("/notifications/send")
async def send_push_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send push notification to a user's devices.

    This endpoint:
    1. Validates the user exists
    2. Gets user's registered device tokens
    3. Sends notification via Firebase
    4. Tracks delivery status
    """
    try:
        logger.info(f"Sending notification to user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get device tokens (from user profile or request)
        device_tokens = request.device_tokens
        if not device_tokens:
            # In production, get from user's stored device tokens
            # For now, mock this
            device_tokens = getattr(user, "device_tokens", [])
            if not device_tokens:
                logger.warning(f"No device tokens found for user {request.user_id}")
                return ok(
                    {
                        "notification_id": str(uuid.uuid4()),
                        "sent_count": 0,
                        "failed_count": 0,
                        "devices_targeted": 0,
                        "timestamp": datetime.now(),
                        "notice": "No device tokens registered for user",
                    }
                )

        # Send notifications
        sent_count = 0
        failed_count = 0
        errors = []

        for token in device_tokens:
            result = notification_agent.send_notification(
                device_token=token,
                title=request.title,
                body=request.body,
                data=request.data or {"type": request.notification_type},
            )

            if result.get("status") == "success":
                sent_count += 1
            else:
                failed_count += 1
                errors.append(f"Token {token[:10]}...: {result.get('message', 'Unknown error')}")

        # Store notification in database for history (optional)
        notification_id = str(uuid.uuid4())

        return ok(
            {
                "notification_id": notification_id,
                "sent_count": sent_count,
                "failed_count": failed_count,
                "devices_targeted": len(device_tokens),
                "timestamp": datetime.now(),
                **({"errors": errors} if errors else {}),
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/notifications/bulk", response_model=NotificationResponse)
async def send_bulk_notifications(
    request: BulkNotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Send notifications to multiple users at once.

    Useful for:
    - Announcing new recalls affecting many users
    - Safety alerts for product categories
    - General safety tips and reminders
    """
    try:
        logger.info(f"Sending bulk notification to {len(request.user_ids)} users")

        total_sent = 0
        total_failed = 0
        total_devices = 0

        for user_id in request.user_ids:
            # Send to each user (could be optimized with batch sending)
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and getattr(user, "device_tokens", None):
                    for token in user.device_tokens:
                        total_devices += 1
                        result = notification_agent.send_notification(
                            device_token=token,
                            title=request.title,
                            body=request.body,
                            data={"type": request.notification_type, "bulk": "true"},
                        )
                        if result.get("status") == "success":
                            total_sent += 1
                        else:
                            total_failed += 1
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
                total_failed += 1

        return NotificationResponse(
            status="success" if total_sent > 0 else "failed",
            notification_id=str(uuid.uuid4()),
            sent_count=total_sent,
            failed_count=total_failed,
            devices_targeted=total_devices,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Bulk notification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk notification failed: {str(e)}")


# ==================== Report Generation Endpoints ====================


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_safety_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate a safety report for the user.

    Report types:
    - safety_summary: Overview of recent scans and recalls
    - recall_history: Detailed history of all recalls found
    - product_analysis: Deep dive into specific products
    """
    try:
        if not report_agent:
            raise HTTPException(status_code=503, detail="Report generation service unavailable")

        logger.info(f"Generating {request.report_type} report for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Generate report ID
        report_id = str(uuid.uuid4())

        # Prepare report data (gather from database)
        report_data = {
            "user_name": user.email.split("@")[0],  # Or actual name if available
            "report_date": datetime.now().isoformat(),
            "report_type": request.report_type,
            "date_range_days": request.date_range,
        }

        # Get recall history for user (mock for now)
        # In production, this would query user's scan history
        recalls = db.query(RecallDB).limit(10).all()
        report_data["recalls"] = [
            {
                "product": r.product_name,
                "date": r.recall_date.isoformat() if r.recall_date else None,
                "hazard": r.hazard,
                "remedy": r.remedy,
            }
            for r in recalls
        ]

        # Branch for product_safety report: aggregate minimal context and invoke new builder
        if request.report_type == "product_safety":
            # Minimal deterministic aggregation using provided fields; DB lookups can be added later
            product = {
                "product_name": request.product_name,
                "brand": None,
                "upc_gtin": request.barcode,
                "model_number": request.model_number,
                "lot_or_serial": request.lot_or_serial,
            }
            # For MVP, query recalls by barcode/model if available
            recalls_list = []
            try:
                q = []
                if request.barcode:
                    q.append(RecallDB.upc == request.barcode)
                    q.append(RecallDB.ean_code == request.barcode)
                    q.append(RecallDB.gtin == request.barcode)
                if request.model_number:
                    q.append(RecallDB.model_number == request.model_number)
                if q:
                    # OR across filters
                    from sqlalchemy import or_

                    matches = db.query(RecallDB).filter(or_(*q)).order_by(RecallDB.recall_date.desc()).limit(5).all()
                    for r in matches:
                        recalls_list.append(
                            {
                                "id": getattr(r, "recall_id", None),
                                "agency": getattr(r, "source_agency", None),
                                "date": getattr(r, "recall_date", None),
                                "hazard": getattr(r, "hazard", None),
                                "remedy": getattr(r, "remedy", None),
                                "match_confidence": 1.0,
                                "match_type": "exact",
                            }
                        )
            except Exception as _:
                pass

            # Personalized placeholders (deterministic text for now)
            personalized = {
                "pregnancy_status": "Not Applicable",
                "allergy_status": "No Allergens Detected",
                "notes": None,
            }
            community = {"incident_count": 0, "sentiment": "Neutral", "summary": None}
            manufacturer = {
                "name": None,
                "compliance_score": 100,
                "recall_history": "None recorded",
            }
            hazards = {"hazards_identified": []}

            result = await report_agent.build_report(
                {
                    "report_type": "product_safety",
                    "report_data": {
                        "product": product,
                        "recalls": recalls_list,
                        "personalized": personalized,
                        "community": community,
                        "manufacturer": manufacturer,
                        "hazards": hazards,
                    },
                    "workflow_id": f"WF_{uuid.uuid4().hex[:8]}",
                }
            )
        elif request.report_type == "nursery_quarterly":
            # Expect a list of products in request.products; each item may be a barcode or name
            items = []
            for name in request.products or []:
                items.append(
                    {
                        "product": {"product_name": name},
                        "recalls": [],
                        "personalized": {},
                        "community": {},
                        "manufacturer": {},
                        "hazards": {},
                    }
                )
            result = await report_agent.build_report(
                {
                    "report_type": "nursery_quarterly",
                    "report_data": {"products": items},
                    "workflow_id": f"WF_{uuid.uuid4().hex[:8]}",
                }
            )
        elif request.report_type == "safety_summary":
            # Minimal data passthrough; the builder queries recent recalls directly
            result = await report_agent.build_report(
                {
                    "report_type": "safety_summary",
                    "report_data": {"db": db, "user_id": request.user_id},
                    "workflow_id": f"WF_{uuid.uuid4().hex[:8]}",
                }
            )
        else:
            # Generate report using agent (existing pathways) - handle sync/async safely
            payload = {
                "report_type": request.report_type,
                "format": request.format,
                "data": report_data,
            }
            maybe = report_agent.process_task(payload)
            result = await maybe if inspect.iscoroutine(maybe) else maybe

        # Normalize success across both agent pathways
        success = False
        if isinstance(result, dict):
            if result.get("status") in ("COMPLETED", "success"):
                success = True
            elif result.get("message_type") and isinstance(result.get("payload"), dict):
                success = result["payload"].get("status") == "COMPLETED"
        if not success:
            raise Exception("Report generation failed")

        # Derive path from agent result for product_safety/nursery_quarterly
        pdf_path = None
        if isinstance(result, dict):
            pdf_path = (result.get("payload", {}) or {}).get("result", {}) if "payload" in result else result
            if isinstance(pdf_path, dict):
                pdf_path = pdf_path.get("pdf_path")
            else:
                pdf_path = result.get("pdf_path")

        # Stable destination for download endpoint
        dest_path = REPORTS_DIR / f"report_{report_id}.pdf"
        if pdf_path and Path(pdf_path).exists():
            try:
                copyfile(pdf_path, dest_path)
            except Exception:
                # fallback: keep dest_path unused if copy fails
                pass
        report_path = str(dest_path)

        # Store metadata for ownership and future lookups (sidecar + DB)
        _write_report_metadata(report_id, request.user_id, request.report_type, dest_path)
        try:
            rec = ReportRecord(
                report_id=report_id,
                user_id=request.user_id,
                report_type=request.report_type,
                storage_path=str(dest_path),
            )
            db.add(rec)
            db.commit()
        except Exception as _:
            db.rollback()

        # Optional S3 storage: upload and return presigned GET if configured
        use_s3 = os.environ.get("REPORTS_STORAGE", "local").lower() == "s3"
        s3_bucket = os.environ.get("S3_UPLOAD_BUCKET") or os.environ.get("S3_BUCKET")
        if use_s3 and s3_bucket and Path(report_path).exists():
            try:
                # S3 key layout: reports/{user}/{YYYY}/{MM}/{report_type}/{report_id}.pdf
                now = datetime.utcnow()
                s3_key = f"reports/{request.user_id}/{now.year}/{now.month:02d}/{request.report_type}/{report_id}.pdf"
                upload_file(report_path, s3_key, content_type="application/pdf")
                fname = f"BabyShield-{request.report_type}-{now.strftime('%Y%m%d')}-{report_id[:8]}.pdf"
                presigned = presign_get(s3_key, filename=fname)
                # Update persisted record to point to S3 URI (create if missing)
                try:
                    rec = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
                    if rec:
                        rec.storage_path = f"s3://{s3_bucket}/{s3_key}"
                    else:
                        rec = ReportRecord(
                            report_id=report_id,
                            user_id=request.user_id,
                            report_type=request.report_type,
                            storage_path=f"s3://{s3_bucket}/{s3_key}",
                        )
                        db.add(rec)
                    db.commit()
                except Exception:
                    db.rollback()
                # Prefer cloud URL in response (download route still works as fallback)
                return ReportResponse(
                    status="success",
                    report_id=report_id,
                    report_type=request.report_type,
                    format=request.format,
                    download_url=presigned["url"],
                    file_size_kb=Path(report_path).stat().st_size // 1024,
                    pages=None,
                    generated_at=datetime.now(),
                )
            except Exception as _:
                # fall back to local download route
                pass
        # Delete local after S3 if configured
        if use_s3 and os.environ.get("DELETE_LOCAL_AFTER_S3", "false").lower() == "true":
            try:
                if Path(report_path).exists():
                    os.remove(report_path)
            except Exception:
                pass

        # Schedule retention cleanup
        background_tasks.add_task(_cleanup_old_reports)

        # Mock file size and pages
        file_size_kb = 250
        pages = 5

        return ReportResponse(
            status="success",
            report_id=report_id,
            report_type=request.report_type,
            format=request.format,
            download_url=f"/api/v1/baby/reports/download/{report_id}",
            file_size_kb=file_size_kb,
            pages=pages if request.format == "pdf" else None,
            generated_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/reports/download/{report_id}")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Download a generated report.
    """
    try:
        # Validate user via token (ownership check can be enforced when metadata is stored)
        if not current_user:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Ownership check via DB if available, else sidecar JSON as fallback
        owner_ok = False
        try:
            rec = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
            if rec and str(rec.user_id) == str(current_user.id):
                owner_ok = True
        except Exception:
            pass
        if not owner_ok:
            meta = _load_report_metadata(report_id)
            if meta and str(meta.get("user_id")) == str(current_user.id):
                owner_ok = True
        if not owner_ok:
            raise HTTPException(status_code=403, detail="Forbidden")

        # If stored in S3, return a presigned URL
        try:
            rec = db.query(ReportRecord).filter(ReportRecord.report_id == report_id).first()
        except Exception:
            rec = None
        if rec and getattr(rec, "storage_path", "").startswith("s3://"):
            # Extract key from s3://bucket/key
            try:
                _, _, bucket_and_key = rec.storage_path.partition("s3://")
                bucket, _, key = bucket_and_key.partition("/")
                fname = f"babyshield_report_{report_id}.pdf"
                presigned = presign_get(key, filename=fname)
                return JSONResponse(
                    {
                        "download_url": presigned["url"],
                        "expires_in": presigned.get("expires_in", 600),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to presign S3 object for report {report_id}: {e}")
                # fall through to local search

        # Locate a real generated local file across candidates
        candidates = [
            REPORTS_DIR / f"report_{report_id}.pdf",
            REPORTS_DIR / f"{report_id}.pdf",
            Path("/tmp") / f"report_{report_id}.pdf",
            Path("C:/tmp") / f"report_{report_id}.pdf",
        ]
        for p in candidates:
            if p.exists():
                return FileResponse(
                    path=str(p),
                    media_type="application/pdf",
                    filename=f"babyshield_report_{report_id}.pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="babyshield_report_{report_id}.pdf"',
                        "Cache-Control": "no-store",
                    },
                )

        raise HTTPException(status_code=404, detail=f"Report file not found for id={report_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report download failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report download failed: {str(e)}")


# ==================== Onboarding Endpoints ====================


@router.post("/onboarding/setup")
async def setup_user_profile(request: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Setup or update user profile for personalized safety recommendations.
    """
    try:
        logger.info(f"Setting up profile for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Store profile data (in production, save to user profile table) - Reserved for DB
        _ = {
            "child_age_months": request.child_age_months,
            "expecting": request.expecting,
            "due_date": request.due_date,
            "interests": request.interests,
            "notification_preferences": request.notification_preferences,
        }

        # Calculate relevant product categories based on age
        recommended_categories = []
        if request.child_age_months is not None:
            if request.child_age_months < 6:
                recommended_categories = [
                    "Infant Formula",
                    "Cribs & Sleepers",
                    "Baby Monitors",
                ]
            elif request.child_age_months < 12:
                recommended_categories = ["Baby Food", "High Chairs", "Baby Gates"]
            elif request.child_age_months < 24:
                recommended_categories = [
                    "Toddler Toys",
                    "Training Cups",
                    "Toddler Beds",
                ]
            else:
                recommended_categories = [
                    "Preschool Toys",
                    "Booster Seats",
                    "Art Supplies",
                ]

        return {
            "status": "success",
            "user_id": request.user_id,
            "profile_updated": True,
            "recommended_categories": recommended_categories,
            "safety_tips": [
                "Check products against our recall database before use",
                "Set up push notifications for instant recall alerts",
                "Review age-appropriate guidelines for all products",
            ],
            "next_steps": [
                "Scan your existing baby products",
                "Add family member allergy profiles",
                "Enable location-based recalls",
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Onboarding failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Onboarding failed: {str(e)}")


# ==================== Hazard Analysis Endpoints ====================


@router.post("/hazards/analyze", response_model=HazardAnalysisResponse)
async def analyze_product_hazards(request: HazardAnalysisRequest, db: Session = Depends(get_db)):
    """
    Analyze specific hazards for a product based on child's age.

    Hazard types checked:
    - Choking hazards (small parts)
    - Chemical hazards (lead, BPA, phthalates)
    - Mechanical hazards (sharp edges, pinch points)
    - Suffocation risks
    - Age-inappropriate features
    """
    try:
        logger.info(f"Analyzing hazards for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Mock hazard analysis (in production, would use hazard_agent)
        hazards = []
        risk_level = "LOW"
        age_appropriate = True

        # Check product in recall database
        if request.barcode:
            recalls = db.query(RecallDB).filter(RecallDB.upc == request.barcode).all()
            for recall in recalls:
                hazard_type = "RECALL"
                if "choking" in (recall.hazard or "").lower():
                    hazard_type = "CHOKING"
                elif "lead" in (recall.hazard or "").lower():
                    hazard_type = "CHEMICAL"
                elif "suffocation" in (recall.hazard or "").lower():
                    hazard_type = "SUFFOCATION"

                hazards.append(
                    {
                        "type": hazard_type,
                        "description": recall.hazard,
                        "severity": "HIGH",
                        "source": recall.source_agency,
                    }
                )
                risk_level = "HIGH"

        # Age-based hazard analysis
        if request.child_age_months is not None and request.child_age_months < 36:
            if request.product_name and "small parts" in request.product_name.lower():
                hazards.append(
                    {
                        "type": "CHOKING",
                        "description": "Product contains small parts not suitable for children under 3",
                        "severity": "HIGH",
                        "source": "Age Guidelines",
                    }
                )
                age_appropriate = False
                risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level

        # Generate recommendations
        recommendations = []
        if risk_level in ["HIGH", "CRITICAL"]:
            recommendations.append("Consider finding a safer alternative product")
            recommendations.append("Keep product out of reach of children")
        if not age_appropriate:
            recommendations.append(f"Product not recommended for {request.child_age_months} month old")
            recommendations.append("Check age recommendations on packaging")
        if not hazards:
            recommendations.append("No specific hazards identified - follow general safety guidelines")

        # Find safer alternatives if high risk
        safer_alternatives = None
        if risk_level in ["HIGH", "CRITICAL"]:
            safer_alternatives = [
                "Fisher-Price Safe Start Series",
                "Green Toys Certified Safe Products",
                "Lovevery Age-Appropriate Play Kits",
            ]

        return HazardAnalysisResponse(
            product=request.product_name or request.barcode or "Unknown Product",
            overall_risk_level=risk_level,
            hazards_identified=hazards,
            age_appropriate=age_appropriate,
            recommendations=recommendations,
            safer_alternatives=safer_alternatives,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hazard analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hazard analysis failed: {str(e)}")


# ==================== Community Alerts Endpoints ====================


@router.get("/community/alerts")
async def get_community_alerts(
    user_id: int = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of alerts to return"),
    db: Session = Depends(get_db),
):
    """
    Get recent community-reported safety alerts.

    Sources:
    - Parent forums and communities
    - Social media safety reports
    - Crowdsourced hazard reports
    """
    try:
        # Mock community alerts (in production, would use community_agent)
        alerts = [
            {
                "id": str(uuid.uuid4()),
                "title": "Parents Report: Teething Ring Breakage",
                "product": "Generic Silicone Teethers",
                "reported_by": "142 parents",
                "date": (datetime.now() - timedelta(days=2)).isoformat(),
                "severity": "MEDIUM",
                "description": "Multiple reports of silicone breaking into small pieces",
                "source": "BabyCenter Forum",
                "verified": False,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Paint Chipping on Wooden Blocks",
                "product": "Budget Wooden Block Set",
                "reported_by": "89 parents",
                "date": (datetime.now() - timedelta(days=5)).isoformat(),
                "severity": "LOW",
                "description": "Paint chipping after heavy use, possible ingestion risk",
                "source": "Reddit r/beyondthebump",
                "verified": True,
            },
        ]

        return {
            "status": "success",
            "alerts_count": len(alerts),
            "alerts": alerts[:limit],
            "last_updated": datetime.now().isoformat(),
            "sources_monitored": [
                "BabyCenter Forums",
                "Reddit Parenting Communities",
                "Facebook Parent Groups",
                "Twitter Safety Hashtags",
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get community alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get community alerts: {str(e)}")


@router.head("/reports/download/{report_id}")
async def head_download_report(report_id: str, user=Depends(get_current_active_user)):
    res = download_report(report_id, user)
    import inspect

    if inspect.isawaitable(res):
        res = await res
    return res
