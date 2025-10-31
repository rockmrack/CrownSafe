from api.pydantic_base import AppModel

"""
Risk Assessment API Endpoints
Provides endpoints for product risk analysis, report generation, and data ingestion
"""

import asyncio  # noqa: E402
import logging  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402, timezone
from typing import Any  # noqa: E402

from fastapi import (  # noqa: E402
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from sqlalchemy import func, or_  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from core_infra.barcode_scanner import BarcodeScanner  # noqa: E402
from core_infra.database import get_db  # noqa: E402
from core_infra.risk_assessment_models import (  # noqa: E402
    CompanyComplianceProfile,
    DataIngestionJob,
    DataSource,
    ProductDataSource,
    ProductGoldenRecord,
    ProductRiskProfile,
    RiskAssessmentReport,
    SafetyIncident,
)
from core_infra.risk_report_generator import RiskReportGenerator  # noqa: E402
from core_infra.risk_scoring_engine import RiskScoringEngine  # noqa: E402
from core_infra.safety_data_connectors import (  # noqa: E402
    CommercialDatabaseConnector,
    CPSCDataConnector,
    DataUnificationEngine,
    EUSafetyGateConnector,
)

logger = logging.getLogger(__name__)

# Create router
risk_router = APIRouter(prefix="/api/v1/risk-assessment", tags=["Risk Assessment"])


# Request/Response Models
class RiskAssessmentRequest(AppModel):
    """Request model for risk assessment."""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    product_name: str | None = Field(None, description="Product name to search")
    upc: str | None = Field(None, description="UPC barcode")
    gtin: str | None = Field(None, description="GTIN identifier")
    manufacturer: str | None = Field(None, description="Manufacturer name")
    model_number: str | None = Field(None, description="Model number")
    include_report: bool = Field(True, description="Generate full report")
    report_format: str = Field("pdf", description="Report format: pdf, html, json")


class RiskAssessmentResponse(BaseModel):
    """Response model for risk assessment."""

    product_id: str
    product_name: str
    risk_score: float
    risk_level: str
    confidence: float
    risk_factors: dict[str, Any]
    recommendations: list[str]
    report_url: str | None = None
    disclaimers: dict[str, str]
    assessment_id: str
    timestamp: datetime


class DataIngestionRequest(BaseModel):
    """Request model for data ingestion."""

    sources: list[str] = Field(default=["CPSC", "EU_SAFETY_GATE"], description="Data sources to ingest")
    start_date: datetime | None = Field(None, description="Start date for data range")
    end_date: datetime | None = Field(None, description="End date for data range")
    product_filter: str | None = Field(None, description="Product category filter")
    full_sync: bool = Field(False, description="Perform full sync vs incremental")


class ProductSearchRequest(AppModel):
    """Request model for product search."""

    query: str = Field(..., description="Search query")
    search_type: str = Field("name", description="Search type: name, upc, gtin, manufacturer")
    limit: int = Field(10, ge=1, le=100)
    include_risk_score: bool = Field(True)


# Initialize components
risk_engine = RiskScoringEngine()
report_generator = RiskReportGenerator()
barcode_scanner = BarcodeScanner()
data_unification = DataUnificationEngine()


@risk_router.get("", response_model=dict)
async def get_risk_assessment_info():
    """Get risk assessment service information and available endpoints."""
    return {
        "success": True,
        "data": {
            "service": "Risk Assessment API",
            "version": "1.0.0",
            "description": "Comprehensive risk assessment for products and ingredients",
            "endpoints": {
                "assess": "POST /assess - Assess product risk",
                "assess_barcode": "POST /assess/barcode - Assess by barcode",
                "assess_image": "POST /assess/image - Assess by image",
                "profile": "GET /profile/{product_id} - Get risk profile",
                "report": "GET /report/{report_id} - Get risk report",
                "ingest": "POST /ingest - Trigger data ingestion",
                "search": "GET /search - Search products",
                "stats": "GET /stats - Get risk statistics",
            },
        },
    }


@risk_router.post("", response_model=dict)
async def risk_assessment_root_post():
    """POST endpoint for root risk assessment path - redirects to proper endpoint."""
    return {
        "success": False,
        "error": {
            "code": "ENDPOINT_NOT_FOUND",
            "message": "Please use the specific risk assessment endpoints. POST requests should go to /assess, /assess/barcode, or /assess/image",  # noqa: E501
            "available_endpoints": {
                "assess": "POST /assess - Assess product risk",
                "assess_barcode": "POST /assess/barcode - Assess by barcode",
                "assess_image": "POST /assess/image - Assess by image",
            },
        },
    }


@risk_router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_product_risk(
    request: RiskAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Perform comprehensive risk assessment for a product.

    This endpoint:
    1. Searches for or creates a product golden record
    2. Fetches latest safety data from multiple sources
    3. Calculates dynamic risk score
    4. Generates detailed report (optional)
    5. Returns risk assessment with recommendations
    """
    try:
        # Step 1: Find or create product golden record
        product = await _find_or_create_product(request, db)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Step 2: Fetch latest incident data
        incidents = db.query(SafetyIncident).filter(SafetyIncident.product_id == product.id).all()

        # Step 3: Get company profile
        company_profile = None
        if product.manufacturer:
            company_profile = (
                db.query(CompanyComplianceProfile)
                .filter(CompanyComplianceProfile.company_name == product.manufacturer)
                .first()
            )

        # Step 4: Calculate risk score
        risk_components = risk_engine.calculate_risk_score(product, incidents, company_profile, db)

        # Step 5: Update or create risk profile
        risk_profile = db.query(ProductRiskProfile).filter(ProductRiskProfile.product_id == product.id).first()

        if not risk_profile:
            risk_profile = ProductRiskProfile(product_id=product.id)
            db.add(risk_profile)

        # Update risk profile
        risk_profile.risk_score = risk_components.total_score
        risk_profile.risk_level = risk_components.risk_level
        risk_profile.severity_score = risk_components.severity_score
        risk_profile.recency_score = risk_components.recency_score
        risk_profile.volume_score = risk_components.volume_score
        risk_profile.violation_score = risk_components.violation_score
        risk_profile.compliance_score = risk_components.compliance_score
        risk_profile.last_calculated = datetime.now(timezone.utc)

        # Update incident counts
        risk_profile.total_incidents = len(incidents)
        risk_profile.total_injuries = sum(1 for i in incidents if i.incident_type == "injury")
        risk_profile.total_deaths = sum(1 for i in incidents if i.incident_type == "death")

        db.commit()

        # Step 6: Generate report (if requested)
        report_url = None
        if request.include_report:
            report_data = report_generator.generate_report(
                product,
                risk_profile,
                risk_components,
                incidents,
                company_profile,
                request.report_format,
            )

            # Save report record
            report_record = RiskAssessmentReport(
                product_id=product.id,
                report_type="full",
                risk_score=risk_components.total_score,
                risk_level=risk_components.risk_level,
                report_url=report_data["report_url"],
                report_format=request.report_format,
                status="published",
                executive_summary=risk_engine.generate_risk_narrative(risk_components),
                risk_factors=risk_components.__dict__,
                disclaimers=report_generator.disclaimers["general"],
                limitations=report_generator.disclaimers["ai_limitations"],
            )
            db.add(report_record)
            db.commit()

            report_url = report_data["report_url"]

        # Step 7: Generate recommendations
        recommendations = report_generator._generate_recommendations(risk_components)

        # Step 8: Trigger background data refresh
        background_tasks.add_task(refresh_product_data, product.id, product.gtin or product.upc)

        # Return response
        return RiskAssessmentResponse(
            product_id=product.id,
            product_name=product.product_name,
            risk_score=round(risk_components.total_score, 1),
            risk_level=risk_components.risk_level,
            confidence=risk_components.confidence,
            risk_factors={
                "severity": {
                    "score": round(risk_components.severity_score, 1),
                    "details": risk_components.severity_details,
                },
                "recency": {
                    "score": round(risk_components.recency_score, 1),
                    "details": risk_components.recency_details,
                },
                "volume": {
                    "score": round(risk_components.volume_score, 1),
                    "details": risk_components.volume_details,
                },
                "violations": {
                    "score": round(risk_components.violation_score, 1),
                    "details": risk_components.violation_details,
                },
                "compliance": {
                    "score": round(risk_components.compliance_score, 1),
                    "details": risk_components.compliance_details,
                },
            },
            recommendations=recommendations,
            report_url=report_url,
            disclaimers={
                "general": report_generator.disclaimers["general"],
                "action": report_generator.disclaimers["action"],
            },
            assessment_id=f"ASM-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Risk assessment failed: {e}", exc_info=True)
        # Return safe fallback response instead of 500
        return RiskAssessmentResponse(
            product_id="unknown",
            product_name=request.product_name or "Unknown Product",
            risk_score=0.0,
            risk_level="unknown",
            confidence=0.0,
            risk_factors={
                "severity": {"score": 0.0, "details": "Assessment unavailable"},
                "recency": {"score": 0.0, "details": "Assessment unavailable"},
                "volume": {"score": 0.0, "details": "Assessment unavailable"},
                "violations": {"score": 0.0, "details": "Assessment unavailable"},
                "compliance": {"score": 0.0, "details": "Assessment unavailable"},
            },
            recommendations=["Risk assessment service temporarily unavailable"],
            report_url=None,
            disclaimers={
                "general": "Risk assessment service is temporarily unavailable",
                "action": "Please try again later",
            },
            assessment_id=f"ERROR-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            timestamp=datetime.now(timezone.utc),
        )


@risk_router.post("/assess/barcode")
async def assess_by_barcode(
    barcode: str = Query(..., description="UPC/EAN/GTIN barcode"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Quick risk assessment by barcode scan
    Integrates with Phase 1 barcode scanner.
    """
    try:
        # Use barcode scanner from Phase 1
        scan_result = barcode_scanner.scan_text(barcode)

        if not scan_result.success:
            raise HTTPException(status_code=400, detail="Invalid barcode")

        # Extract product identifiers from ScanResult
        request = RiskAssessmentRequest(upc=scan_result.raw_data, gtin=scan_result.gtin, include_report=True)

        # Perform assessment
        return await assess_product_risk(request, background_tasks, db)

    except Exception as e:
        logger.exception(f"Barcode assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@risk_router.post("/assess/image")
async def assess_by_image(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Risk assessment from product image
    Integrates with Phase 2 visual agent.
    """
    try:
        # Read image file
        image_bytes = await file.read()

        # Use Phase 2 image processing
        # This would typically queue the image for processing
        # For now, we'll try to extract barcodes directly

        # Try barcode extraction
        import cv2
        import numpy as np

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        scan_result = barcode_scanner.scan_image(image)

        if not scan_result.success:
            return JSONResponse(
                status_code=202,
                content={
                    "status": "processing",
                    "message": "Image queued for visual analysis. Check back for results.",
                    "job_id": f"IMG-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
                },
            )

        # Found barcode, assess immediately
        request = RiskAssessmentRequest(upc=scan_result.raw_data, gtin=scan_result.gtin, include_report=True)

        return await assess_product_risk(request, background_tasks, db)

    except Exception as e:
        logger.exception(f"Image assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@risk_router.get("/profile/{product_id}")
async def get_risk_profile(
    product_id: str,
    include_history: bool = Query(False, description="Include historical risk scores"),
    db: Session = Depends(get_db),
):
    """Get detailed risk profile for a product."""
    try:
        # Get product
        product = db.query(ProductGoldenRecord).filter(ProductGoldenRecord.id == product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Get risk profile
        risk_profile = db.query(ProductRiskProfile).filter(ProductRiskProfile.product_id == product_id).first()

        if not risk_profile:
            raise HTTPException(status_code=404, detail="Risk profile not found")

        response = {
            "product": {
                "id": product.id,
                "name": product.product_name,
                "brand": product.brand,
                "manufacturer": product.manufacturer,
                "gtin": product.gtin,
                "upc": product.upc,
            },
            "risk_profile": {
                "risk_score": risk_profile.risk_score,
                "risk_level": risk_profile.risk_level,
                "last_calculated": risk_profile.last_calculated,
                "total_incidents": risk_profile.total_incidents,
                "total_injuries": risk_profile.total_injuries,
                "total_deaths": risk_profile.total_deaths,
                "units_affected": risk_profile.units_affected,
                "risk_trend": risk_profile.risk_trend,
            },
            "scores": {
                "severity": risk_profile.severity_score,
                "recency": risk_profile.recency_score,
                "volume": risk_profile.volume_score,
                "violations": risk_profile.violation_score,
                "compliance": risk_profile.compliance_score,
            },
        }

        # Add historical data if requested
        if include_history and risk_profile.trend_data:
            response["history"] = risk_profile.trend_data

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (404, 400) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get risk profile for {product_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve risk profile")


@risk_router.get("/report/{report_id}")
async def get_report(
    report_id: str,
    format: str = Query("pdf", description="Report format: pdf, html, json"),
    db: Session = Depends(get_db),
):
    """Download risk assessment report."""
    try:
        # Get report record
        report = db.query(RiskAssessmentReport).filter(RiskAssessmentReport.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Return report URL or regenerate
        if report.report_url:
            return {
                "report_url": report.report_url,
                "format": report.report_format,
                "generated_at": report.generated_at,
                "expires_at": report.generated_at + timedelta(days=1),
            }
        # Regenerate report (reserved for regeneration logic)
        _ = db.query(ProductGoldenRecord).filter(ProductGoldenRecord.id == report.product_id).first()

        # ... regeneration logic ...

        return {"message": "Report regeneration in progress"}

    except HTTPException:
        # Re-raise HTTP exceptions (404, 400) as-is
        raise
    except Exception as e:
        logger.error(f"Failed to get report for {report_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve report")


@risk_router.post("/ingest")
async def trigger_data_ingestion(
    request: DataIngestionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger data ingestion from safety sources."""
    try:
        # Create ingestion job
        job = DataIngestionJob(
            source_type=",".join(request.sources),
            job_type="full" if request.full_sync else "incremental",
            status="queued",
            scheduled_at=datetime.now(timezone.utc),
            configuration={
                "start_date": request.start_date.isoformat() if request.start_date else None,
                "end_date": request.end_date.isoformat() if request.end_date else None,
                "product_filter": request.product_filter,
            },
        )
        db.add(job)
        db.commit()

        # Queue ingestion tasks
        for source in request.sources:
            background_tasks.add_task(ingest_from_source, source, job.id, request.start_date, request.end_date)

        return {
            "job_id": job.id,
            "status": "queued",
            "sources": request.sources,
            "message": f"Data ingestion job queued for {len(request.sources)} sources",
        }

    except Exception as e:
        logger.exception(f"Failed to trigger ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@risk_router.get("/search")
async def search_products(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    include_risk: bool = Query(True, description="Include risk scores"),
    db: Session = Depends(get_db),
):
    """Search products with risk information."""
    try:
        # Search products
        query = db.query(ProductGoldenRecord)

        # Apply search filters
        search_filter = or_(
            ProductGoldenRecord.product_name.ilike(f"%{q}%"),
            ProductGoldenRecord.brand.ilike(f"%{q}%"),
            ProductGoldenRecord.manufacturer.ilike(f"%{q}%"),
            ProductGoldenRecord.model_number.ilike(f"%{q}%"),
            ProductGoldenRecord.upc == q,
            ProductGoldenRecord.gtin == q,
        )

        products = query.filter(search_filter).limit(limit).all()

        results = []
        for product in products:
            result = {
                "id": product.id,
                "name": product.product_name,
                "brand": product.brand,
                "manufacturer": product.manufacturer,
                "upc": product.upc,
                "gtin": product.gtin,
            }

            # Add risk information if requested
            if include_risk and product.risk_profile:
                result["risk"] = {
                    "score": product.risk_profile.risk_score,
                    "level": product.risk_profile.risk_level,
                    "last_updated": product.risk_profile.last_calculated,
                }

            results.append(result)

        return {"query": q, "count": len(results), "results": results}

    except Exception as e:
        logger.exception(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@risk_router.get("/stats")
async def get_risk_statistics(db: Session = Depends(get_db)):
    """Get system-wide risk statistics."""
    try:
        stats = {
            "total_products": db.query(func.count(ProductGoldenRecord.id)).scalar(),
            "total_assessments": db.query(func.count(RiskAssessmentReport.id)).scalar(),
            "risk_distribution": {},
            "recent_high_risk": [],
            "data_sources": {},
        }

        # Risk distribution
        risk_levels = (
            db.query(ProductRiskProfile.risk_level, func.count(ProductRiskProfile.id))
            .group_by(ProductRiskProfile.risk_level)
            .all()
        )

        stats["risk_distribution"] = {level: count for level, count in risk_levels}

        # Recent high-risk products
        high_risk = (
            db.query(ProductRiskProfile)
            .filter(ProductRiskProfile.risk_level.in_(["high", "critical"]))
            .order_by(ProductRiskProfile.last_calculated.desc())
            .limit(5)
            .all()
        )

        for profile in high_risk:
            product = profile.product
            stats["recent_high_risk"].append(
                {
                    "product_name": product.product_name,
                    "risk_score": profile.risk_score,
                    "risk_level": profile.risk_level,
                },
            )

        # Data source statistics
        source_counts = (
            db.query(ProductDataSource.source_type, func.count(ProductDataSource.id))
            .group_by(ProductDataSource.source_type)
            .all()
        )

        stats["data_sources"] = {source: count for source, count in source_counts}

        return stats

    except Exception as e:
        logger.exception(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
async def _find_or_create_product(request: RiskAssessmentRequest, db: Session) -> ProductGoldenRecord | None:
    """Find existing product or create new golden record."""
    # Try to find by identifiers
    if request.gtin:
        product = db.query(ProductGoldenRecord).filter(ProductGoldenRecord.gtin == request.gtin).first()
        if product:
            return product

    if request.upc:
        product = db.query(ProductGoldenRecord).filter(ProductGoldenRecord.upc == request.upc).first()
        if product:
            return product

    # Try to find by name and manufacturer
    if request.product_name:
        query = db.query(ProductGoldenRecord).filter(
            ProductGoldenRecord.product_name.ilike(f"%{request.product_name}%"),
        )

        if request.manufacturer:
            query = query.filter(ProductGoldenRecord.manufacturer.ilike(f"%{request.manufacturer}%"))

        if request.model_number:
            query = query.filter(ProductGoldenRecord.model_number == request.model_number)

        product = query.first()
        if product:
            return product

    # Create new product if we have enough information
    if request.product_name or request.upc or request.gtin:
        product = ProductGoldenRecord(
            product_name=request.product_name or f"Unknown Product ({request.upc or request.gtin})",
            upc=request.upc,
            gtin=request.gtin,
            manufacturer=request.manufacturer,
            model_number=request.model_number,
            confidence_score=0.5,  # Low confidence for new products
        )
        db.add(product)
        db.commit()

        # Fetch additional data from commercial sources
        if request.upc or request.gtin:
            await enrich_product_data(product, db)

        return product

    return None


async def enrich_product_data(product: ProductGoldenRecord, db: Session) -> None:
    """Enrich product data from commercial sources."""
    try:
        commercial_connector = CommercialDatabaseConnector()

        barcode = product.upc or product.gtin
        if barcode:
            product_data = await commercial_connector.lookup_product_by_barcode(barcode)

            if product_data:
                # Update product with commercial data
                if not product.product_name or product.product_name.startswith("Unknown"):
                    product.product_name = product_data.get("product_name", product.product_name)

                if not product.brand:
                    product.brand = product_data.get("brand")

                if not product.primary_image_url:
                    images = product_data.get("images", [])
                    if images:
                        product.primary_image_url = images[0]

                # Add data source record
                source_record = ProductDataSource(
                    product_id=product.id,
                    source_type=DataSource.COMMERCIAL_DB.value,
                    source_name=product_data.get("source", "commercial"),
                    raw_data=product_data,
                    fetched_at=datetime.now(timezone.utc),
                )
                db.add(source_record)
                db.commit()

    except Exception as e:
        logger.exception(f"Failed to enrich product data: {e}")


async def refresh_product_data(product_id: str, barcode: str | None = None) -> None:
    """Background task to refresh product data from all sources."""
    logger.info(f"Refreshing data for product {product_id}")

    # This would typically:
    # 1. Query CPSC for latest recalls
    # 2. Check EU Safety Gate
    # 3. Update commercial data
    # 4. Recalculate risk score

    # Placeholder for actual implementation
    await asyncio.sleep(1)


async def ingest_from_source(
    source: str,
    job_id: str,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Background task to ingest data from a specific source."""
    logger.info(f"Starting ingestion from {source} for job {job_id}")

    try:
        if source == "CPSC":
            connector = CPSCDataConnector()
            _ = await connector.fetch_recalls(start_date, end_date)  # records
            # Process records...

        elif source == "EU_SAFETY_GATE":
            connector = EUSafetyGateConnector()
            _ = await connector.fetch_alerts(start_date)  # records
            # Process records...

    except Exception as e:
        logger.exception(f"Ingestion failed for {source}: {e}")
