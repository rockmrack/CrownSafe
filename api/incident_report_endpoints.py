"""Incident Report API Endpoints
Handles crowdsourced safety incident reporting.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, UTC
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from api.schemas.common import ApiResponse
from core_infra.database import SessionLocal, get_db
from core_infra.rate_limiter import limiter
from core_infra.s3_uploads import upload_file
from db.models.incident_report import (
    AgencyNotification,
    IncidentCluster,
    IncidentReport,
    IncidentStatus,
    IncidentType,
    SeverityLevel,
)

# from models import NotificationHistory  # Not used in this module

logger = logging.getLogger(__name__)

# Create router
incident_router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


# JSON-based request models
class IncidentSubmitRequest(BaseModel):
    """JSON request model for incident submission."""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    title: str = Field(..., description="Brief title of the incident")
    description: str = Field(..., description="Detailed description of what happened")
    product_barcode: str | None = Field(None, description="Product barcode if available")
    product_name: str | None = Field(None, description="Product name if known")
    brand_name: str | None = Field(None, description="Brand name if known")
    model_number: str | None = Field(None, description="Model number if available")
    incident_type: str = Field("safety_concern", description="Type of incident")
    severity_level: str = Field("medium", description="Severity level")
    user_id: int | None = Field(None, description="User ID if authenticated")


class IncidentAnalyzer:
    """Analyzes incidents for patterns and triggers alerts."""

    # Thresholds for triggering alerts
    ALERT_THRESHOLDS = {
        "immediate": 3,  # 3 similar incidents trigger immediate review
        "trending": 5,  # 5 incidents in 7 days = trending
        "critical": 1,  # 1 critical severity triggers immediate alert
        "agency_notify": 10,  # 10 incidents triggers agency notification
    }

    @classmethod
    async def analyze_incident(cls, incident: IncidentReport, db: Session) -> dict[str, Any]:
        """Analyze a new incident for patterns and clusters."""
        analysis_result = {
            "cluster_id": None,
            "similar_count": 0,
            "alert_triggered": False,
            "agency_notified": False,
            "risk_level": "low",
        }

        try:
            # Find similar incidents
            similar_incidents = cls._find_similar_incidents(incident, db)
            analysis_result["similar_count"] = len(similar_incidents)

            # Check if this should join an existing cluster
            cluster = cls._find_or_create_cluster(incident, similar_incidents, db)
            if cluster:
                incident.cluster_id = cluster.id
                analysis_result["cluster_id"] = cluster.id

                # Update cluster statistics
                cls._update_cluster_stats(cluster, incident, db)

                # Check alert thresholds
                if cluster.incident_count >= cls.ALERT_THRESHOLDS["immediate"]:
                    analysis_result["alert_triggered"] = True
                    await cls._trigger_alert(cluster, db)

                if cluster.incident_count >= cls.ALERT_THRESHOLDS["agency_notify"]:
                    analysis_result["agency_notified"] = True
                    await cls._notify_agency(cluster, db)

                # Calculate risk level
                analysis_result["risk_level"] = cls._calculate_risk_level(cluster)

            # Special handling for critical incidents
            if incident.severity_level == SeverityLevel.CRITICAL:
                analysis_result["alert_triggered"] = True
                await cls._trigger_critical_alert(incident, db)

            db.commit()

        except Exception as e:
            logger.exception(f"Error analyzing incident: {e}")
            db.rollback()

        return analysis_result

    @classmethod
    def _find_similar_incidents(
        cls, incident: IncidentReport, db: Session, days_back: int = 30,
    ) -> list[IncidentReport]:
        """Find incidents similar to the given one."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

        # Search for similar product and incident type
        similar = (
            db.query(IncidentReport)
            .filter(
                and_(
                    IncidentReport.created_at >= cutoff_date,
                    IncidentReport.id != incident.id,
                    or_(
                        func.lower(IncidentReport.product_name).contains(incident.product_name.lower()),
                        and_(
                            IncidentReport.brand_name == incident.brand_name,
                            IncidentReport.incident_type == incident.incident_type,
                        ),
                    ),
                ),
            )
            .all()
        )

        return similar

    @classmethod
    def _find_or_create_cluster(
        cls,
        incident: IncidentReport,
        similar_incidents: list[IncidentReport],
        db: Session,
    ) -> IncidentCluster | None:
        """Find existing cluster or create new one."""
        # Check if similar incidents already have a cluster
        for similar in similar_incidents:
            if similar.cluster_id:
                cluster = db.query(IncidentCluster).filter(IncidentCluster.id == similar.cluster_id).first()
                if cluster:
                    return cluster

        # Create new cluster if we have enough incidents
        if len(similar_incidents) >= 2:  # At least 2 similar + this one = 3
            cluster_id = f"CLUSTER_{uuid.uuid4().hex[:8].upper()}"
            cluster = IncidentCluster(
                id=cluster_id,
                product_name=incident.product_name,
                brand_name=incident.brand_name,
                incident_type=incident.incident_type,
                incident_count=1,
                first_incident_date=incident.incident_date,
                last_incident_date=incident.incident_date,
                risk_score=0.0,
            )
            db.add(cluster)

            # Update similar incidents to join cluster
            for similar in similar_incidents:
                similar.cluster_id = cluster_id

            return cluster

        return None

    @classmethod
    def _update_cluster_stats(cls, cluster: IncidentCluster, incident: IncidentReport, db: Session) -> None:
        """Update cluster statistics with new incident."""
        cluster.incident_count += 1
        cluster.last_incident_date = incident.incident_date

        # Update severity distribution
        severity_dist = cluster.severity_distribution or {}
        severity_key = incident.severity_level.value
        severity_dist[severity_key] = severity_dist.get(severity_key, 0) + 1
        cluster.severity_distribution = severity_dist

        # Calculate risk score
        cluster.risk_score = cls._calculate_cluster_risk_score(cluster)

        # Check if trending
        recent_count = (
            db.query(IncidentReport)
            .filter(
                and_(
                    IncidentReport.cluster_id == cluster.id,
                    IncidentReport.created_at >= datetime.now(UTC) - timedelta(days=7),
                ),
            )
            .count()
        )

        cluster.trending = recent_count >= cls.ALERT_THRESHOLDS["trending"]
        cluster.updated_at = datetime.now(UTC)

    @classmethod
    def _calculate_risk_level(cls, cluster: IncidentCluster) -> str:
        """Calculate risk level based on cluster data."""
        if cluster.risk_score >= 8.0:
            return "critical"
        if cluster.risk_score >= 6.0:
            return "high"
        if cluster.risk_score >= 4.0:
            return "medium"
        return "low"

    @classmethod
    def _calculate_cluster_risk_score(cls, cluster: IncidentCluster) -> float:
        """Calculate risk score for a cluster (0-10)."""
        score = 0.0

        # Factor 1: Incident count (max 3 points)
        score += min(cluster.incident_count / 10 * 3, 3.0)

        # Factor 2: Severity distribution (max 4 points)
        severity_dist = cluster.severity_distribution or {}
        critical_count = severity_dist.get("critical", 0)
        severe_count = severity_dist.get("severe", 0)

        if critical_count > 0:
            score += 4.0
        elif severe_count >= 3:
            score += 3.5
        elif severe_count > 0:
            score += 2.0

        # Factor 3: Trending (max 2 points)
        if cluster.trending:
            score += 2.0

        # Factor 4: Time concentration (max 1 point)
        if cluster.last_incident_date and cluster.first_incident_date:
            days_span = (cluster.last_incident_date - cluster.first_incident_date).days
            if days_span <= 7 and cluster.incident_count >= 5:
                score += 1.0

        return min(score, 10.0)

    @classmethod
    async def _trigger_alert(cls, cluster: IncidentCluster, db: Session) -> None:
        """Trigger internal alert for cluster."""
        logger.warning(f"ALERT: Cluster {cluster.id} has {cluster.incident_count} incidents")

        # Mark cluster as alerted
        cluster.alert_triggered = True
        cluster.alert_triggered_at = datetime.now(UTC)

        # In production, this would notify safety team
        # For now, log the alert
        logger.info(f"Safety team notified about cluster {cluster.id}")

    @classmethod
    async def _trigger_critical_alert(cls, incident: IncidentReport, db: Session) -> None:
        """Trigger immediate alert for critical incident."""
        logger.critical(f"CRITICAL INCIDENT: {incident.product_name} - {incident.incident_type.value}")

        # In production, this would page on-call safety team
        # Send immediate notifications to safety team
        pass

    @classmethod
    async def _notify_agency(cls, cluster: IncidentCluster, db: Session) -> None:
        """Notify regulatory agency about cluster."""
        logger.info(f"Notifying CPSC about cluster {cluster.id}")

        # Create agency notification record
        notification = AgencyNotification(
            agency="CPSC",
            cluster_id=cluster.id,
            notification_type="threshold_alert",
            incident_count=cluster.incident_count,
            severity_summary=cluster.severity_distribution,
            sent_via="api",
            notification_data={
                "product": cluster.product_name,
                "brand": cluster.brand_name,
                "incident_type": cluster.incident_type.value,
                "risk_score": cluster.risk_score,
            },
        )
        db.add(notification)

        # Mark cluster as notified
        cluster.cpsc_notified = True
        cluster.cpsc_notified_at = datetime.now(UTC)

        # In production, this would call CPSC API
        # For now, log the notification
        logger.info(f"CPSC notified about {cluster.incident_count} incidents for {cluster.product_name}")


# Background task wrapper for incident analysis
def analyze_incident_background(incident_id: int) -> None:
    """Background task to analyze an incident.
    Creates its own database session to avoid DetachedInstanceError.
    """
    db = SessionLocal()
    try:
        # Fetch incident by ID
        incident = db.query(IncidentReport).filter(IncidentReport.id == incident_id).first()

        if not incident:
            logger.warning(f"Incident {incident_id} not found for background analysis")
            return

        # Run async analysis
        asyncio.run(IncidentAnalyzer.analyze_incident(incident, db))

    except Exception as e:
        logger.error(
            f"Background incident analysis failed for incident {incident_id}: {e}",
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()


# API Endpoints


@incident_router.post("/submit", response_model=ApiResponse)
@limiter.limit("20 per minute")  # Rate limiting for incidents endpoint
async def submit_incident_report(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # Form fields
    product_name: str = Form(...),
    incident_type: str = Form(...),
    incident_date: str = Form(...),
    severity_level: str = Form(...),
    description: str = Form(...),
    brand_name: str | None = Form(None),
    product_model_number: str | None = Form(None, alias="model_number"),
    barcode: str | None = Form(None),
    child_age_months: int | None = Form(None),
    reporter_email: str | None = Form(None),
    # File uploads
    product_photos: list[UploadFile] = File(None),
    incident_photos: list[UploadFile] = File(None),
):
    """Submit a new incident report
    Accepts multipart/form-data with photos.
    """
    try:
        # Generate report ID
        report_id = f"INC_{datetime.now(UTC).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"

        # Upload photos to S3
        product_photo_urls = []
        incident_photo_urls = []

        if product_photos:
            for photo in product_photos:
                if photo.filename:
                    s3_key = f"incidents/{report_id}/product/{photo.filename}"
                    url = await upload_file(photo.file, s3_key)
                    if url:
                        product_photo_urls.append(url)

        if incident_photos:
            for photo in incident_photos:
                if photo.filename:
                    s3_key = f"incidents/{report_id}/incident/{photo.filename}"
                    url = await upload_file(photo.file, s3_key)
                    if url:
                        incident_photo_urls.append(url)

        # Create incident report
        incident = IncidentReport(
            product_name=product_name,
            brand_name=brand_name,
            model_number=product_model_number,
            barcode=barcode,
            incident_type=IncidentType(incident_type),
            incident_date=datetime.fromisoformat(incident_date),
            severity_level=SeverityLevel(severity_level),
            incident_description=description,
            child_age_months=child_age_months,
            reporter_email=reporter_email,
            photo_urls=product_photo_urls + incident_photo_urls,
            status=IncidentStatus.SUBMITTED,
        )

        db.add(incident)
        db.flush()  # Get the ID
        incident_id = incident.id  # Capture ID before session closes

        # Analyze incident in background (pass ID only, not session)
        background_tasks.add_task(analyze_incident_background, incident_id)

        db.commit()

        # Send confirmation email if provided
        if reporter_email:
            # In production, send confirmation email
            pass

        logger.info(f"Incident report submitted: {report_id}")

        return ApiResponse(
            success=True,
            data={
                "report_id": report_id,
                "incident_id": incident.id,
                "status": "submitted",
                "message": "Thank you for helping keep children safe!",
            },
        )

    except Exception as e:
        logger.error(f"Error submitting incident report: {e}", exc_info=True)
        db.rollback()
        # Return safe fallback response instead of 500
        return ApiResponse(
            success=False,
            data={
                "report_id": f"ERROR-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
                "incident_id": None,
                "status": "error",
                "message": "Incident reporting service temporarily unavailable. Please try again later.",
            },
        )


@incident_router.post("/submit-json", response_model=ApiResponse)
async def submit_incident_json(
    request: IncidentSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Submit a new incident report via JSON (tolerant of unknown barcodes).

    This endpoint accepts JSON data and creates incidents even when the product
    barcode is not found in our catalog. It marks the product as not found.
    """
    try:
        # REMOVED FOR CROWN SAFE: Product lookup no longer uses RecallDB
        product_id = None
        product_found = False

        # if request.product_barcode:
        #     # Look for product in our database (RecallDB removed)
        #     from core_infra.database import RecallDB
        #     product = db.query(RecallDB).filter(...).first()
        #     if product:
        #         product_id = product.id
        #         product_found = True

        # Generate report ID
        report_id = f"INC-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

        # Create incident report (tolerant of missing products)
        incident = IncidentReport(
            product_name=request.product_name or "Unknown Product",
            brand_name=request.brand_name,
            model_number=request.model_number,
            barcode=request.product_barcode,
            incident_type=IncidentType(request.incident_type),
            incident_date=datetime.now(UTC),
            severity_level=SeverityLevel(request.severity_level),
            incident_description=request.description,
            reporter_email=None,  # Not provided in JSON request
            photo_urls=[],  # No photos in JSON request
            status=IncidentStatus.SUBMITTED,
        )

        db.add(incident)
        db.flush()  # Get the ID

        # Get incident ID before session closes
        incident_id = incident.id

        db.commit()

        # Analyze incident in background (session is now closed, pass ID only)
        background_tasks.add_task(analyze_incident_background, incident_id)

        logger.info(f"Incident report submitted via JSON: {report_id}")

        return ApiResponse(
            success=True,
            data={
                "report_id": report_id,
                "incident_id": incident_id,
                "status": "submitted",
                "product_found": product_found,
                "product_id": product_id,
                "message": "Thank you for helping keep children safe! Your report has been submitted.",
            },
        )

    except Exception as e:
        logger.error(f"Error submitting incident report via JSON: {e}", exc_info=True)
        db.rollback()
        # Return safe fallback response instead of 500
        return ApiResponse(
            success=False,
            data={
                "report_id": f"ERROR-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
                "incident_id": None,
                "status": "error",
                "product_found": False,
                "product_id": None,
                "message": "Incident reporting service temporarily unavailable. Please try again later.",
            },
        )


# Add alias route for singular "incident" path
@incident_router.post("/incident/submit", response_model=ApiResponse)
async def submit_incident_json_alias(
    request: IncidentSubmitRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Alias for /submit-json endpoint using singular "incident" path."""
    return await submit_incident_json(request, background_tasks, db)


@incident_router.get("/clusters", response_model=ApiResponse)
async def get_incident_clusters(trending_only: bool = False, min_incidents: int = 3, db: Session = Depends(get_db)):
    """Get current incident clusters for monitoring."""
    query = db.query(IncidentCluster)

    if trending_only:
        query = query.filter(IncidentCluster.trending)

    query = query.filter(IncidentCluster.incident_count >= min_incidents)

    clusters = query.order_by(IncidentCluster.risk_score.desc()).limit(50).all()

    return ApiResponse(
        success=True,
        data={
            "clusters": [
                {
                    "cluster_id": c.id,
                    "product_name": c.product_name,
                    "brand_name": c.brand_name,
                    "incident_type": c.incident_type.value,
                    "incident_count": c.incident_count,
                    "risk_score": c.risk_score,
                    "risk_level": IncidentAnalyzer._calculate_risk_level(c),
                    "trending": c.trending,
                    "alert_triggered": c.alert_triggered,
                    "cpsc_notified": c.cpsc_notified,
                    "first_incident": c.first_incident_date.isoformat() if c.first_incident_date else None,
                    "last_incident": c.last_incident_date.isoformat() if c.last_incident_date else None,
                }
                for c in clusters
            ],
        },
    )


@incident_router.get("/stats", response_model=ApiResponse)
async def get_incident_statistics(days: int = 30, db: Session = Depends(get_db)):
    """Get incident reporting statistics."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Total incidents
    total_incidents = db.query(IncidentReport).filter(IncidentReport.created_at >= cutoff_date).count()

    # By severity
    severity_stats = (
        db.query(IncidentReport.severity_level, func.count(IncidentReport.id))
        .filter(IncidentReport.created_at >= cutoff_date)
        .group_by(IncidentReport.severity_level)
        .all()
    )

    # By type
    type_stats = (
        db.query(IncidentReport.incident_type, func.count(IncidentReport.id))
        .filter(IncidentReport.created_at >= cutoff_date)
        .group_by(IncidentReport.incident_type)
        .all()
    )

    # Active clusters
    active_clusters = db.query(IncidentCluster).filter(IncidentCluster.trending).count()

    return ApiResponse(
        success=True,
        data={
            "period_days": days,
            "total_incidents": total_incidents,
            "severity_breakdown": {s.value: count for s, count in severity_stats},
            "type_breakdown": {t.value: count for t, count in type_stats},
            "active_clusters": active_clusters,
            "agencies_notified": (
                db.query(AgencyNotification).filter(AgencyNotification.sent_at >= cutoff_date).count()
            ),
        },
    )


# DEV OVERRIDE ENDPOINTS - For testing without database dependencies


@incident_router.post("/submit-dev", response_model=ApiResponse)
async def submit_incident_dev(request: IncidentSubmitRequest):
    """DEV OVERRIDE: Submit incident report without database dependencies."""
    try:
        # Generate report ID
        report_id = f"INC-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"

        # Simulate product lookup
        product_found = False
        if request.product_barcode:
            # Simulate known/unknown product logic
            product_found = request.product_barcode.startswith("123")

        # Simulate PII stripping in response
        safe_description = request.description
        if "john.doe@example.com" in safe_description:
            safe_description = safe_description.replace("john.doe@example.com", "[EMAIL_REDACTED]")
        if "555-123-4567" in safe_description:
            safe_description = safe_description.replace("555-123-4567", "[PHONE_REDACTED]")

        return ApiResponse(
            success=True,
            data={
                "incident_id": report_id,
                "status": "submitted",
                "product_found": product_found,
                "description": safe_description,
                "created_at": datetime.now(UTC).isoformat(),
            },
        )

    except Exception as e:
        logger.exception(f"Error in dev incident submission: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@incident_router.get("/clusters-dev", response_model=ApiResponse)
async def get_incident_clusters_dev(trending_only: bool = False, min_incidents: int = 3):
    """DEV OVERRIDE: Get incident clusters without database dependencies."""
    try:
        # Mock cluster data
        mock_clusters = [
            {
                "cluster_id": "CLUSTER-001",
                "product_name": "Test Product A",
                "brand_name": "Test Brand",
                "incident_type": "safety_concern",
                "incident_count": 5,
                "risk_score": 8.5,
                "risk_level": "high",
                "trending": True,
                "alert_triggered": False,
                "cpsc_notified": False,
                "first_incident": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
                "last_incident": datetime.now(UTC).isoformat(),
            },
            {
                "cluster_id": "CLUSTER-002",
                "product_name": "Test Product B",
                "brand_name": "Test Brand",
                "incident_type": "injury",
                "incident_count": 3,
                "risk_score": 6.2,
                "risk_level": "medium",
                "trending": False,
                "alert_triggered": False,
                "cpsc_notified": False,
                "first_incident": (datetime.now(UTC) - timedelta(days=3)).isoformat(),
                "last_incident": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            },
        ]

        # Apply filters
        filtered_clusters = mock_clusters
        if trending_only:
            filtered_clusters = [c for c in filtered_clusters if c["trending"]]

        filtered_clusters = [c for c in filtered_clusters if c["incident_count"] >= min_incidents]

        return ApiResponse(success=True, data={"clusters": filtered_clusters})

    except Exception as e:
        logger.exception(f"Error in dev clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


@incident_router.get("/stats-dev", response_model=ApiResponse)
async def get_incident_statistics_dev(days: int = 30):
    """DEV OVERRIDE: Get incident statistics without database dependencies."""
    try:
        # Mock statistics data
        mock_stats = {
            "period_days": days,
            "total_incidents": 15 if days >= 7 else 0,
            "severity_breakdown": {"critical": 2, "high": 5, "medium": 6, "low": 2},
            "type_breakdown": {
                "safety_concern": 8,
                "injury": 4,
                "malfunction": 2,
                "recall": 1,
            },
            "active_clusters": 2 if days >= 7 else 0,
            "agencies_notified": 1 if days >= 7 else 0,
        }

        return ApiResponse(success=True, data=mock_stats)

    except Exception as e:
        logger.exception(f"Error in dev stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e!s}")


# Serve the HTML page
@incident_router.get("/report-page", response_class=HTMLResponse)
async def serve_report_page(request: Request):
    """Serve the incident report HTML page."""
    try:
        # Return the static HTML file
        return FileResponse("static/report_incident.html")
    except Exception as e:
        logger.exception(f"Error serving report page: {e}")
        raise HTTPException(status_code=500, detail="Could not load report page")
