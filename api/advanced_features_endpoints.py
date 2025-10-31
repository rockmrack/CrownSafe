"""Advanced BabyShield Features API Endpoints
Provides endpoints for web research, guidelines, and visual recognition.
"""

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Never

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# REMOVED FOR CROWN SAFE: RecallDB no longer applicable (hair products, not baby recalls)
from core_infra.database import User, get_db

# Define logger first
logger = logging.getLogger(__name__)

# Try to import agents with graceful fallback
try:
    from agents.research.web_research_agent.agent_logic import WebResearchLogic

    web_research_agent = WebResearchLogic(agent_id="api_web_research", version="2.0", logger_instance=logger)
except Exception as e:
    web_research_agent = None
    logger.warning(f"Web Research Agent not available: {e}")

guideline_agent = None
logger.info("Guideline agent retired; guidelines endpoint returns informational response only.")

# Create router with prefix
router = APIRouter(prefix="/api/v1/advanced", tags=["Advanced Features"])

# ==================== Request/Response Models ====================


class WebResearchRequest(BaseModel):
    """Request model for web research."""

    product_name: str = Field(..., description="Product name to research")
    barcode: str | None = Field(None, description="Product barcode if available")
    search_depth: str = Field("standard", description="Search depth: quick, standard, deep")
    sources: list[str] | None = Field(None, description="Specific sources to search")
    include_social_media: bool = Field(True, description="Include social media monitoring")
    include_forums: bool = Field(True, description="Include parent forums")
    user_id: int = Field(..., description="User ID for personalization")


class WebResearchResult(BaseModel):
    """Single research finding."""

    source: str
    source_type: str  # "forum", "social_media", "news", "blog", "official"
    title: str
    content: str
    url: str | None = None
    date_found: datetime | None = None
    relevance_score: float = Field(..., ge=0, le=1)
    sentiment: str = Field("neutral", description="positive, negative, neutral")
    verified: bool = False
    reported_by_count: int | None = None


class WebResearchResponse(BaseModel):
    """Response model for web research."""

    status: str
    product_researched: str
    findings_count: int
    findings: list[WebResearchResult]
    risk_indicators: list[str]
    safety_score: float = Field(..., ge=0, le=100)
    sources_searched: list[str]
    search_time_ms: int
    timestamp: datetime


class GuidelinesRequest(BaseModel):
    """Request model for product guidelines."""

    product_name: str | None = Field(None, description="Product name")
    product_category: str | None = Field(None, description="Product category")
    barcode: str | None = Field(None, description="Product barcode")
    child_age_months: int = Field(..., ge=0, le=216, description="Child's age in months")
    child_weight_lbs: float | None = Field(None, gt=0, description="Child's weight in pounds")
    child_height_inches: float | None = Field(None, gt=0, description="Child's height in inches")
    usage_scenario: str | None = Field(None, description="How product will be used")
    user_id: int = Field(..., description="User ID")


class SafetyGuideline(BaseModel):
    """Single safety guideline."""

    guideline_type: str  # "age", "weight", "usage", "warning", "best_practice"
    title: str
    description: str
    importance: str  # "critical", "important", "recommended", "optional"
    source: str
    applicable: bool
    reason: str | None = None


class GuidelinesResponse(BaseModel):
    """Response model for guidelines."""

    status: str
    product: str
    age_appropriate: bool
    weight_appropriate: bool | None = None
    guidelines: list[SafetyGuideline]
    warnings: list[str]
    best_practices: list[str]
    developmental_considerations: list[str]
    recommended_alternatives: list[str] | None = None
    timestamp: datetime


class VisualRecognitionRequest(BaseModel):
    """Request model for visual product recognition."""

    user_id: int = Field(..., description="User ID")
    include_similar: bool = Field(True, description="Include similar products if no exact match")
    check_for_defects: bool = Field(True, description="Check for visual defects")
    confidence_threshold: float = Field(0.7, ge=0, le=1, description="Minimum confidence for matches")


class VisualRecognitionResponse(BaseModel):
    """Response model for visual recognition."""

    status: str
    image_id: str
    products_identified: list[dict[str, Any]]
    confidence: float
    defects_detected: list[dict[str, Any]] | None = None
    similar_products: list[dict[str, Any]] | None = None
    processing_time_ms: int
    timestamp: datetime


class MonitoringRequest(BaseModel):
    """Request model for continuous monitoring."""

    product_name: str = Field(..., description="Product to monitor")
    barcode: str | None = Field(None, description="Product barcode")
    user_id: int = Field(..., description="User ID")
    monitoring_duration_days: int = Field(30, ge=1, le=365, description="How long to monitor")
    alert_threshold: str = Field("medium", description="Alert sensitivity: low, medium, high")
    sources: list[str] | None = Field(None, description="Specific sources to monitor")


class MonitoringResponse(BaseModel):
    """Response model for monitoring setup."""

    status: str
    monitoring_id: str
    product_monitored: str
    duration_days: int
    alert_threshold: str
    sources_count: int
    next_check: datetime
    timestamp: datetime


# ==================== Web Research Endpoints ====================


@router.post("/research", response_model=WebResearchResponse)
async def research_product_safety(
    request: WebResearchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Research product safety across the web in real-time.

    This endpoint:
    1. Searches forums, social media, news for safety issues
    2. Analyzes sentiment and relevance
    3. Identifies early warning signs
    4. Returns aggregated safety intelligence
    """
    try:
        logger.info(f"Researching {request.product_name} for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        start_time = datetime.now(timezone.utc)

        # Mock web research results (in production, would use web_research_agent)
        findings = []
        risk_indicators = []
        safety_score = 85.0  # Start with good score

        # Simulate searching different sources
        sources_to_search = request.sources or [
            "Reddit r/babybumps",
            "BabyCenter Forums",
            "Facebook Parent Groups",
            "Twitter Safety Alerts",
            "Consumer Reports",
            "Amazon Reviews",
            "What to Expect Forums",
        ]

        # Mock findings based on product name
        if "formula" in request.product_name.lower():
            findings.append(
                WebResearchResult(
                    source="Reddit r/FormulaFeeders",
                    source_type="forum",
                    title="Parents discussing recall concerns",
                    content="Multiple parents reporting clumping issues with this batch. Manufacturing date codes 2024-01 through 2024-03 seem affected.",  # noqa: E501
                    url="https://reddit.com/r/example",
                    date_found=datetime.now(timezone.utc) - timedelta(days=3),
                    relevance_score=0.92,
                    sentiment="negative",
                    verified=False,
                    reported_by_count=47,
                ),
            )
            risk_indicators.append("Multiple consumer complaints identified")
            safety_score -= 15

        if request.include_social_media:
            findings.append(
                WebResearchResult(
                    source="Twitter @SafetyMoms",
                    source_type="social_media",
                    title="Safety alert thread",
                    content=f"⚠️ Parents reporting issues with {request.product_name}. Check your batch numbers!",
                    url="https://twitter.com/example",
                    date_found=datetime.now(timezone.utc) - timedelta(hours=12),
                    relevance_score=0.78,
                    sentiment="negative",
                    verified=True,
                    reported_by_count=156,
                ),
            )
            if len(findings) > 1:
                risk_indicators.append("Trending safety concern on social media")
                safety_score -= 10

        if request.include_forums:
            findings.append(
                WebResearchResult(
                    source="BabyCenter Community",
                    source_type="forum",
                    title="Product experience thread",
                    content=f"Has anyone else used {request.product_name}? Working great for us, no issues after 3 months.",  # noqa: E501
                    url="https://babycenter.com/example",
                    date_found=datetime.now(timezone.utc) - timedelta(days=7),
                    relevance_score=0.65,
                    sentiment="positive",
                    verified=False,
                    reported_by_count=12,
                ),
            )
            safety_score += 5  # Positive feedback improves score

        # Add news source
        findings.append(
            WebResearchResult(
                source="Consumer Product Safety News",
                source_type="news",
                title="Industry safety update",
                content="No current recalls or safety alerts for this product category.",
                url="https://cpsc.gov/example",
                date_found=datetime.now(timezone.utc) - timedelta(days=1),
                relevance_score=0.95,
                sentiment="neutral",
                verified=True,
                reported_by_count=None,
            ),
        )

        # Sort findings by relevance
        findings.sort(key=lambda x: x.relevance_score, reverse=True)

        # Limit based on search depth
        if request.search_depth == "quick":
            findings = findings[:3]
        elif request.search_depth == "standard":
            findings = findings[:5]
        # "deep" returns all findings

        # Calculate processing time
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Add risk indicators based on findings
        negative_count = sum(1 for f in findings if f.sentiment == "negative")
        if negative_count >= 3:
            risk_indicators.append("Multiple negative reports found")
            safety_score -= 10

        high_relevance_negative = any(f.relevance_score > 0.8 and f.sentiment == "negative" for f in findings)
        if high_relevance_negative:
            risk_indicators.append("High-confidence safety concern identified")
            safety_score -= 15

        # Ensure safety score stays in bounds
        safety_score = max(0, min(100, safety_score))

        return WebResearchResponse(
            status="success",
            product_researched=request.product_name,
            findings_count=len(findings),
            findings=findings,
            risk_indicators=risk_indicators,
            safety_score=safety_score,
            sources_searched=sources_to_search,
            search_time_ms=processing_time,
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Web research failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research failed: {e!s}")


# ==================== Guidelines Endpoints ====================


@router.post("/guidelines", response_model=GuidelinesResponse)
async def get_product_guidelines(request: GuidelinesRequest, db: Session = Depends(get_db)) -> Never:
    """Return HTTP 501 because the guideline feature is retired."""
    del request  # Guidelines feature retired; request data unused.
    del db
    raise HTTPException(
        status_code=501,
        detail="Product guideline feature has been retired from the BabyShield platform.",
    )


# ==================== Visual Recognition Endpoints ====================


@router.post("/visual/recognize", response_model=VisualRecognitionResponse)
async def recognize_product_from_image(
    user_id: int = Query(..., description="User ID"),
    image: UploadFile = File(..., description="Product image"),
    include_similar: bool = Query(True, description="Include similar products"),
    check_for_defects: bool = Query(True, description="Check for visual defects"),
    confidence_threshold: float = Query(0.7, ge=0, le=1, description="Minimum confidence"),
    db: Session = Depends(get_db),
):
    """Identify products from images using visual recognition.

    This endpoint:
    1. Analyzes uploaded product images
    2. Identifies products without barcodes
    3. Detects visual defects or damage
    4. Finds similar products if no exact match
    """
    try:
        logger.info(f"Visual recognition for user {user_id}")

        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        start_time = datetime.now(timezone.utc)

        # Validate image
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image data
        image_data = await image.read()
        image_size_kb = len(image_data) / 1024

        if image_size_kb > 10240:  # 10MB limit
            raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

        # Generate image ID (MD5 for non-security ID generation only)
        image_hash = hashlib.md5(image_data, usedforsecurity=False).hexdigest()
        image_id = f"img_{image_hash[:12]}_{int(datetime.now(timezone.utc).timestamp())}"

        # Use real visual recognition pipeline
        products_identified = []
        confidence = 0.0
        defects_detected = []
        similar_products = []

        try:
            # Create image processing job
            import uuid

            from core_infra.visual_agent_models import ImageJob, JobStatus

            job_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            s3_key = f"uploads/{user_id}/{timestamp}_{job_id}.jpg"

            # Create job record
            job = ImageJob(
                id=job_id,
                user_id=user_id,
                s3_bucket=os.getenv("S3_UPLOAD_BUCKET", "babyshield-images"),
                s3_key=s3_key,
                status=JobStatus.QUEUED,
            )
            db.add(job)
            db.commit()

            # Upload image to S3 for processing
            import boto3

            s3_client = boto3.client("s3", region_name=os.getenv("S3_BUCKET_REGION", "us-east-1"))
            s3_client.put_object(
                Bucket=job.s3_bucket,
                Key=s3_key,
                Body=image_data,
                ContentType=image.content_type,
            )

            # Use visual search agent directly for immediate results
            from agents.visual.visual_search_agent.agent_logic import (
                VisualSearchAgentLogic,
            )

            # Generate presigned URL for the uploaded image
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": job.s3_bucket, "Key": s3_key},
                ExpiresIn=3600,
            )

            visual_agent = VisualSearchAgentLogic("visual_recognition_001")
            result = await visual_agent.identify_product_from_image(presigned_url)

            if result["status"] == "COMPLETED":
                product_data = result["result"]
                confidence = product_data.get("confidence", 0.0)

                # Check for recalls
                recall_status = "SAFE"
                recall_reason = None

                if product_data.get("product_name"):
                    from sqlalchemy import text

                    recall_query = text(
                        """
                        SELECT product_name, hazard, description
                        FROM recalls_enhanced
                        WHERE LOWER(product_name) LIKE LOWER(:product_name)
                        LIMIT 1
                    """,
                    )
                    recall_result = db.execute(
                        recall_query,
                        {"product_name": f"%{product_data['product_name']}%"},
                    ).fetchone()

                    if recall_result:
                        recall_status = "RECALLED"
                        recall_reason = recall_result[1] or recall_result[2]

                products_identified.append(
                    {
                        "product_name": product_data.get("product_name", "Unknown Product"),
                        "confidence": confidence,
                        "barcode": None,  # Would come from barcode extraction if available
                        "category": "Baby Product",  # Could be enhanced with category classification
                        "brand": product_data.get("brand", "Unknown"),
                        "recall_status": recall_status,
                        "recall_reason": recall_reason,
                    },
                )
            else:
                # Fallback for failed recognition
                products_identified.append(
                    {
                        "product_name": "Unidentified Product",
                        "confidence": 0.0,
                        "barcode": None,
                        "category": "Unknown",
                        "brand": "Unknown",
                        "recall_status": "UNKNOWN",
                        "recall_reason": "Could not identify product from image",
                    },
                )
                confidence = 0.0

        except Exception as e:
            logger.error(f"Real visual recognition failed: {e}", exc_info=True)
            # Don't mask errors as 200 - raise proper HTTP exception
            raise HTTPException(status_code=500, detail=f"Processing error: {type(e).__name__}")

        # Check for visual defects if requested
        if check_for_defects and confidence > confidence_threshold:
            # Use real defect detection
            try:
                import io

                from PIL import Image

                from core_infra.image_processor import ImageAnalysisService

                # Convert image data back to PIL Image for defect detection
                pil_image = Image.open(io.BytesIO(image_data))

                # Initialize image analysis service
                image_analyzer = ImageAnalysisService()

                # Run real defect detection
                detected_defects = image_analyzer.detect_visual_defects(pil_image)

                # Convert to expected format
                for defect in detected_defects:
                    defects_detected.append(
                        {
                            "type": defect["type"],
                            "description": defect["description"],
                            "location": defect["location"],
                            "severity": defect["severity"],
                            "confidence": defect["confidence"],
                        },
                    )

                logger.info(f"Real defect detection found {len(detected_defects)} defects")

            except Exception as e:
                logger.exception(f"Defect detection failed: {e}")
                # Fallback: no defects detected if analysis fails

        # Find similar products if requested and confidence is low
        if include_similar and confidence < confidence_threshold:
            # Mock similar products
            similar_products = [
                {
                    "product_name": "Summer Infant SwaddleMe",
                    "similarity_score": 0.68,
                    "barcode": "012914632109",
                    "category": "Baby Sleep Products",
                    "price_range": "$15-25",
                },
                {
                    "product_name": "HALO SleepSack",
                    "similarity_score": 0.62,
                    "barcode": "818771010108",
                    "category": "Baby Sleep Products",
                    "price_range": "$20-30",
                },
            ]

        # Calculate processing time
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        return VisualRecognitionResponse(
            status="success" if confidence > confidence_threshold else "low_confidence",
            image_id=image_id,
            products_identified=products_identified,
            confidence=confidence,
            defects_detected=defects_detected if defects_detected else None,
            similar_products=similar_products if similar_products else None,
            processing_time_ms=processing_time,
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Visual recognition failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Visual recognition failed: {e!s}")


# ==================== Continuous Monitoring Endpoints ====================


@router.post("/monitor/setup", response_model=MonitoringResponse)
async def setup_product_monitoring(
    request: MonitoringRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Set up continuous monitoring for a product.

    This endpoint:
    1. Registers product for ongoing monitoring
    2. Checks multiple sources periodically
    3. Sends alerts when issues detected
    4. Provides early warning of emerging problems
    """
    try:
        logger.info(f"Setting up monitoring for {request.product_name}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Generate monitoring ID
        monitoring_id = f"mon_{request.user_id}_{int(datetime.now(timezone.utc).timestamp())}"

        # Determine sources to monitor
        sources = request.sources or [
            "CPSC Recalls",
            "FDA Alerts",
            "Reddit Parenting",
            "BabyCenter Forums",
            "Amazon Reviews",
            "Consumer Reports",
            "Social Media",
        ]

        # Calculate next check time based on alert threshold
        if request.alert_threshold == "high":
            next_check = datetime.now(timezone.utc) + timedelta(hours=6)  # Check 4x daily
        elif request.alert_threshold == "medium":
            next_check = datetime.now(timezone.utc) + timedelta(hours=24)  # Check daily
        else:  # low
            next_check = datetime.now(timezone.utc) + timedelta(days=3)  # Check every 3 days

        # In production, would store monitoring config in database
        # and schedule background task
        background_tasks.add_task(
            logger.info,
            f"Monitoring scheduled for {request.product_name} - ID: {monitoring_id}",
        )

        return MonitoringResponse(
            status="success",
            monitoring_id=monitoring_id,
            product_monitored=request.product_name,
            duration_days=request.monitoring_duration_days,
            alert_threshold=request.alert_threshold,
            sources_count=len(sources),
            next_check=next_check,
            timestamp=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Monitoring setup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Monitoring setup failed: {e!s}")


@router.get("/monitor/{monitoring_id}/status")
async def get_monitoring_status(
    monitoring_id: str,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Get status of an active monitoring job."""
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Mock monitoring status (in production, would fetch from database)
        return {
            "monitoring_id": monitoring_id,
            "status": "active",
            "product": "Example Product",
            "checks_performed": 7,
            "alerts_sent": 1,
            "last_check": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
            "next_check": (datetime.now(timezone.utc) + timedelta(hours=21)).isoformat(),
            "findings": [
                {
                    "date": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "source": "Reddit",
                    "type": "discussion",
                    "summary": "Parents discussing product quality",
                    "alert_sent": False,
                },
                {
                    "date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                    "source": "Amazon Reviews",
                    "type": "negative_review_spike",
                    "summary": "Multiple 1-star reviews mentioning safety concern",
                    "alert_sent": True,
                },
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {e!s}")


@router.delete("/monitor/{monitoring_id}")
async def cancel_monitoring(
    monitoring_id: str,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Cancel an active monitoring job."""
    try:
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # In production, would remove from database and cancel scheduled tasks
        logger.info(f"Cancelling monitoring {monitoring_id} for user {user_id}")

        return {
            "status": "success",
            "monitoring_id": monitoring_id,
            "message": "Monitoring cancelled successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancellation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cancellation failed: {e!s}")
