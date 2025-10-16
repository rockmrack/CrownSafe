"""
Safety Reports API Endpoints
Generate comprehensive safety summaries for users
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
import uuid
import logging

from core_infra.database import get_db, User, RecallDB
from db.models.scan_history import ScanHistory, SafetyReport
from agents.reporting.report_builder_agent.agent_logic import ReportBuilderAgentLogic
from api.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

# Create router
safety_reports_router = APIRouter(
    prefix="/api/v1/safety-reports", tags=["safety-reports"]
)


class SafetyReportRequest(BaseModel):
    """Request model for generating safety reports"""

    user_id: int = Field(..., description="User ID")
    report_type: str = Field(
        "90_day",
        description="Type of report (90_day, 30_day, weekly, quarterly_nursery)",
    )
    include_details: bool = Field(
        True, description="Include detailed product information"
    )
    generate_pdf: bool = Field(True, description="Generate PDF version")
    nursery_id: Optional[int] = Field(
        None, description="Nursery ID for nursery-specific reports"
    )


class SafetySummaryStats(BaseModel):
    """Summary statistics for safety report"""

    total_scans: int
    unique_products: int
    recalls_found: int
    high_risk_products: int
    medium_risk_products: int
    low_risk_products: int
    most_scanned_category: Optional[str]
    most_scanned_brand: Optional[str]
    safety_score: float  # 0-100 score based on scan results


class ProductScanSummary(BaseModel):
    """Summary of a scanned product"""

    product_name: str
    brand: Optional[str]
    barcode: Optional[str]
    scan_count: int
    first_scanned: datetime
    last_scanned: datetime
    risk_level: str
    recalls_found: int
    verdict: str


class NurseryProductCategory(BaseModel):
    """Nursery product categorization"""

    category: str
    product_count: int
    high_risk_count: int
    recall_count: int
    products: List[ProductScanSummary]


class NurseryReportStats(BaseModel):
    """Statistics specific to nursery safety audit"""

    total_products: int
    categories_audited: int
    critical_items: int  # Cribs, car seats, high chairs
    feeding_items: int  # Bottles, formula, food
    toy_items: int  # Toys, play equipment
    clothing_items: int  # Clothes, blankets
    furniture_items: int  # Cribs, changing tables, dressers
    safety_equipment: int  # Gates, monitors, locks
    recalls_found: int
    expired_products: int
    compliance_score: float  # 0-100 score for overall nursery safety
    recommendations: List[str]


class SafetyReportResponse(BaseModel):
    """Response model for safety report generation"""

    success: bool
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    statistics: SafetySummaryStats
    products: List[ProductScanSummary]
    pdf_url: Optional[str]
    message: str


@safety_reports_router.post("/generate", response_model=ApiResponse)
async def generate_safety_report(
    request: SafetyReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate a comprehensive safety report for a user

    This is the main report generation endpoint that handles all report types.
    """
    try:
        logger.info(
            f"Generating safety report for user {request.user_id}, type: {request.report_type}"
        )

        # Check if user exists
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Generate report based on type
        if request.report_type == "90_day":
            return await generate_90_day_report(request, background_tasks, db)
        elif request.report_type == "quarterly_nursery":
            return await generate_quarterly_nursery_report(
                request, background_tasks, db
            )
        else:
            # Default to 90-day report
            return await generate_90_day_report(request, background_tasks, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating safety report: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate safety report: {str(e)}"
        )


@safety_reports_router.post("/generate-90-day-dev", response_model=ApiResponse)
async def generate_90_day_report_dev(request: SafetyReportRequest) -> ApiResponse:
    """
    Dev override version of 90-day report generation for testing
    """
    try:
        # Check dev override for premium features
        from api.services.dev_override import dev_entitled

        REQUIRED_FEATURE = "safety.comprehensive"

        if not dev_entitled(request.user_id, REQUIRED_FEATURE):
            raise HTTPException(
                status_code=402,
                detail="Subscription required for 90-day report generation",
            )

        # Mock report generation
        report_id = f"report_90d_{request.user_id}_{int(datetime.now().timestamp())}"

        return ApiResponse(
            success=True,
            data={
                "report_id": report_id,
                "user_id": request.user_id,
                "report_type": "90_day",
                "status": "generated",
                "download_url": f"https://example.com/reports/{report_id}.pdf",
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                "message": "90-day safety report generated successfully",
            },
            message="90-day report generated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating 90-day report: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate 90-day report: {str(e)}"
        )


@safety_reports_router.post("/generate-90-day", response_model=ApiResponse)
async def generate_90_day_report(
    request: SafetyReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """
    Generate a comprehensive 90-day safety summary report

    Includes:
    - All products scanned in the last 90 days
    - Safety statistics and trends
    - Recall alerts and high-risk products
    - PDF generation for download
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)

        # Get user's scan history for the period
        scan_history = (
            db.query(ScanHistory)
            .filter(
                and_(
                    ScanHistory.user_id == request.user_id,
                    ScanHistory.scan_timestamp >= start_date,
                    ScanHistory.scan_timestamp <= end_date,
                )
            )
            .order_by(desc(ScanHistory.scan_timestamp))
            .all()
        )

        if not scan_history:
            return ApiResponse(
                success=True,
                data={
                    "report_id": None,
                    "message": "No scans found in the last 90 days",
                    "statistics": {
                        "total_scans": 0,
                        "unique_products": 0,
                        "recalls_found": 0,
                        "high_risk_products": 0,
                        "medium_risk_products": 0,
                        "low_risk_products": 0,
                        "safety_score": 100.0,
                    },
                    "products": [],
                },
            )

        # Calculate statistics
        total_scans = len(scan_history)
        unique_products = len(set(s.barcode for s in scan_history if s.barcode))
        recalls_found = sum(s.recalls_found or 0 for s in scan_history)

        # Count risk levels
        risk_counts = {"high": 0, "medium": 0, "low": 0, "critical": 0}

        for scan in scan_history:
            if scan.risk_level:
                risk_level = scan.risk_level.lower()
                if risk_level in risk_counts:
                    risk_counts[risk_level] += 1

        # Calculate safety score (100 = perfect, 0 = all critical)
        safety_score = 100.0
        if total_scans > 0:
            critical_weight = risk_counts["critical"] * 10
            high_weight = risk_counts["high"] * 5
            medium_weight = risk_counts["medium"] * 2
            total_weight = critical_weight + high_weight + medium_weight
            safety_score = max(0, 100 - (total_weight / total_scans * 10))

        # Find most common category and brand
        categories = {}
        brands = {}
        for scan in scan_history:
            if scan.category:
                categories[scan.category] = categories.get(scan.category, 0) + 1
            if scan.brand:
                brands[scan.brand] = brands.get(scan.brand, 0) + 1

        most_scanned_category = (
            max(categories, key=categories.get) if categories else None
        )
        most_scanned_brand = max(brands, key=brands.get) if brands else None

        # Group products and create summaries
        product_groups = {}
        for scan in scan_history:
            key = scan.barcode or scan.product_name or "unknown"
            if key not in product_groups:
                product_groups[key] = {
                    "product_name": scan.product_name or "Unknown Product",
                    "brand": scan.brand,
                    "barcode": scan.barcode,
                    "scans": [],
                    "recalls_found": 0,
                    "risk_levels": [],
                }
            product_groups[key]["scans"].append(scan)
            product_groups[key]["recalls_found"] += scan.recalls_found or 0
            if scan.risk_level:
                product_groups[key]["risk_levels"].append(scan.risk_level)

        # Create product summaries
        product_summaries = []
        for key, group in product_groups.items():
            scans = group["scans"]
            # Determine overall risk level (use highest)
            risk_level = "low"
            if "critical" in group["risk_levels"]:
                risk_level = "critical"
            elif "high" in group["risk_levels"]:
                risk_level = "high"
            elif "medium" in group["risk_levels"]:
                risk_level = "medium"

            product_summaries.append(
                ProductScanSummary(
                    product_name=group["product_name"],
                    brand=group["brand"],
                    barcode=group["barcode"],
                    scan_count=len(scans),
                    first_scanned=min(s.scan_timestamp for s in scans),
                    last_scanned=max(s.scan_timestamp for s in scans),
                    risk_level=risk_level,
                    recalls_found=group["recalls_found"],
                    verdict=scans[-1].verdict or "No Recalls Found",
                )
            )

        # Sort products by risk level and scan count
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        product_summaries.sort(
            key=lambda p: (risk_order.get(p.risk_level, 4), -p.scan_count)
        )

        # Generate report ID
        report_id = f"SR_{uuid.uuid4().hex[:8]}"

        # Prepare statistics
        statistics = SafetySummaryStats(
            total_scans=total_scans,
            unique_products=unique_products,
            recalls_found=recalls_found,
            high_risk_products=risk_counts["high"] + risk_counts["critical"],
            medium_risk_products=risk_counts["medium"],
            low_risk_products=risk_counts["low"],
            most_scanned_category=most_scanned_category,
            most_scanned_brand=most_scanned_brand,
            safety_score=round(safety_score, 1),
        )

        # Generate PDF if requested
        pdf_url = None
        if request.generate_pdf:
            # Use the report builder agent to generate PDF
            try:
                report_agent = ReportBuilderAgentLogic(
                    agent_id=f"report_builder_{report_id}", version="2.1"
                )

                # Prepare data for safety summary report
                report_data = {
                    "report_type": "safety_summary",
                    "report_data": {
                        "user_id": request.user_id,
                        "period_start": start_date.isoformat(),
                        "period_end": end_date.isoformat(),
                        "statistics": statistics.dict(),
                        "products": [
                            p.dict() for p in product_summaries[:20]
                        ],  # Top 20 products
                        "scan_history": [
                            s.to_dict() for s in scan_history[:50]
                        ],  # Recent 50 scans
                    },
                    "workflow_id": report_id,
                }

                result = await report_agent.build_report(report_data)

                if result.get("status") == "success" and result.get("pdf_path"):
                    # In production, upload to S3 and return URL
                    pdf_url = f"/api/v1/reports/download/{report_id}"

                    # Save report record
                    safety_report = SafetyReport(
                        report_id=report_id,
                        user_id=request.user_id,
                        report_type="90_day_summary",
                        period_start=start_date,
                        period_end=end_date,
                        total_scans=total_scans,
                        unique_products=unique_products,
                        recalls_found=recalls_found,
                        high_risk_products=risk_counts["high"]
                        + risk_counts["critical"],
                        report_data={
                            "statistics": statistics.dict(),
                            "products": [p.dict() for p in product_summaries],
                        },
                        pdf_path=result.get("pdf_path"),
                    )
                    db.add(safety_report)
                    db.commit()

            except Exception as e:
                logger.error(f"Failed to generate PDF: {e}")
                # Continue without PDF

        # Return response
        response_data = SafetyReportResponse(
            success=True,
            report_id=report_id,
            report_type="90_day_summary",
            period_start=start_date,
            period_end=end_date,
            statistics=statistics,
            products=product_summaries[:20],  # Return top 20 products
            pdf_url=pdf_url,
            message=f"90-day safety summary generated successfully. {total_scans} scans analyzed.",
        )

        return ApiResponse(success=True, data=response_data.dict())

    except Exception as e:
        logger.error(f"Error generating 90-day report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@safety_reports_router.get("/my-reports-dev", response_model=ApiResponse)
async def get_user_reports_dev(
    user_id: int,
    page: int = 1,
    limit: int = 10,
    sort: str = "created_at",
    order: str = "desc",
) -> ApiResponse:
    """
    Dev override version of my-reports endpoint for testing
    """
    try:
        # Mock report data for testing
        mock_reports = [
            {
                "id": "report_001",
                "user_id": user_id,
                "report_type": "90_day",
                "title": "90-Day Safety Summary",
                "created_at": "2024-01-15T10:00:00Z",
                "status": "completed",
                "pdf_url": "https://example.com/reports/report_001.pdf",
                "summary": "Safety report covering 90 days of product scans",
            },
            {
                "id": "report_002",
                "user_id": user_id,
                "report_type": "quarterly_nursery",
                "title": "Q1 Nursery Safety Report",
                "created_at": "2024-01-01T10:00:00Z",
                "status": "completed",
                "pdf_url": "https://example.com/reports/report_002.pdf",
                "summary": "Quarterly nursery safety analysis",
            },
        ]

        # Sort reports
        if sort == "created_at":
            mock_reports.sort(key=lambda x: x["created_at"], reverse=(order == "desc"))
        elif sort == "title":
            mock_reports.sort(key=lambda x: x["title"], reverse=(order == "desc"))

        # Pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_reports = mock_reports[start_idx:end_idx]

        return ApiResponse(
            success=True,
            data={
                "reports": paginated_reports,
                "page": page,
                "limit": limit,
                "total": len(mock_reports),
                "has_more": end_idx < len(mock_reports),
            },
            message="Reports retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Error fetching user reports: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch reports: {str(e)}"
        )


@safety_reports_router.get("/my-reports", response_model=ApiResponse)
async def get_my_reports(
    user_id: int, limit: int = 10, db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Get list of user's generated safety reports
    """
    try:
        reports = (
            db.query(SafetyReport)
            .filter(SafetyReport.user_id == user_id)
            .order_by(desc(SafetyReport.generated_at))
            .limit(limit)
            .all()
        )

        report_list = []
        for report in reports:
            report_list.append(
                {
                    "report_id": report.report_id,
                    "report_type": report.report_type,
                    "generated_at": report.generated_at.isoformat(),
                    "period_start": report.period_start.isoformat()
                    if report.period_start
                    else None,
                    "period_end": report.period_end.isoformat()
                    if report.period_end
                    else None,
                    "total_scans": report.total_scans,
                    "recalls_found": report.recalls_found,
                    "pdf_available": bool(report.pdf_path or report.s3_url),
                }
            )

        return ApiResponse(
            success=True, data={"reports": report_list, "total": len(report_list)}
        )

    except Exception as e:
        logger.error(f"Error fetching user reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@safety_reports_router.get("/report-dev/{report_id}", response_model=ApiResponse)
async def get_report_details_dev(report_id: str, user_id: int) -> ApiResponse:
    """
    Dev override version of report details endpoint for testing
    """
    try:
        # Mock report details
        mock_report = {
            "id": report_id,
            "user_id": user_id,
            "report_type": "90_day",
            "title": "90-Day Safety Summary",
            "created_at": "2024-01-15T10:00:00Z",
            "status": "completed",
            "pdf_url": "https://example.com/reports/report_001.pdf",
            "summary": "Safety report covering 90 days of product scans",
            "stats": {
                "total_scans": 45,
                "unique_products": 32,
                "recalls_found": 2,
                "high_risk_products": 1,
                "medium_risk_products": 3,
                "low_risk_products": 28,
                "safety_score": 85.5,
            },
            "products": [
                {
                    "product_name": "Baby Formula XYZ",
                    "brand": "SafeBrand",
                    "scan_count": 5,
                    "risk_level": "low",
                    "last_scan": "2024-01-14T15:30:00Z",
                }
            ],
        }

        # Check ownership (simulate 404 for other users' reports)
        if report_id == "999" or user_id != mock_report["user_id"]:
            raise HTTPException(
                status_code=404, detail="Report not found or access denied"
            )

        return ApiResponse(
            success=True,
            data=mock_report,
            message="Report details retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report details: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch report details: {str(e)}"
        )


@safety_reports_router.get("/report/{report_id}", response_model=ApiResponse)
async def get_report_details(
    report_id: str, db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Get detailed information about a specific safety report
    """
    try:
        report = (
            db.query(SafetyReport).filter(SafetyReport.report_id == report_id).first()
        )

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return ApiResponse(
            success=True,
            data={
                "report_id": report.report_id,
                "report_type": report.report_type,
                "generated_at": report.generated_at.isoformat(),
                "period_start": report.period_start.isoformat()
                if report.period_start
                else None,
                "period_end": report.period_end.isoformat()
                if report.period_end
                else None,
                "statistics": {
                    "total_scans": report.total_scans,
                    "unique_products": report.unique_products,
                    "recalls_found": report.recalls_found,
                    "high_risk_products": report.high_risk_products,
                },
                "report_data": report.report_data,
                "pdf_url": f"/api/v1/reports/download/{report_id}"
                if report.pdf_path
                else None,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@safety_reports_router.post("/track-scan", response_model=ApiResponse)
async def track_scan(
    scan_data: Dict[str, Any], db: Session = Depends(get_db)
) -> ApiResponse:
    """
    Track a product scan in user's history
    Called after each scan to build history for reports
    """
    try:
        # Validate required fields
        if not scan_data:
            raise HTTPException(status_code=400, detail="scan_data is required")

        user_id = scan_data.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # Create scan history record with safe defaults
        scan_history = ScanHistory(
            user_id=user_id,
            scan_id=scan_data.get("scan_id", f"scan_{uuid.uuid4().hex[:8]}"),
            product_name=scan_data.get("product_name"),
            brand=scan_data.get("brand"),
            barcode=scan_data.get("barcode"),
            model_number=scan_data.get("model_number"),
            upc_gtin=scan_data.get("upc_gtin"),
            category=scan_data.get("category"),
            scan_type=scan_data.get("scan_type", "barcode"),
            confidence_score=scan_data.get("confidence_score"),
            barcode_format=scan_data.get("barcode_format"),
            verdict=scan_data.get("verdict"),
            risk_level=scan_data.get("risk_level"),
            recalls_found=scan_data.get("recalls_found", 0),
            recall_ids=scan_data.get("recall_ids"),
            agencies_checked=scan_data.get("agencies_checked"),
            allergen_alerts=scan_data.get("allergen_alerts"),
            pregnancy_warnings=scan_data.get("pregnancy_warnings"),
            age_warnings=scan_data.get("age_warnings"),
        )

        db.add(scan_history)
        db.commit()
        db.refresh(scan_history)

        return ApiResponse(
            success=True, data={"scan_id": scan_history.scan_id, "tracked": True}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking scan: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@safety_reports_router.post(
    "/generate-quarterly-nursery-dev", response_model=ApiResponse
)
async def generate_quarterly_nursery_report_dev(
    request: SafetyReportRequest,
) -> ApiResponse:
    """
    Dev override version of quarterly nursery report generation for testing
    """
    try:
        # Check dev override for premium features
        from api.services.dev_override import dev_entitled

        REQUIRED_FEATURE = "safety.comprehensive"

        if not dev_entitled(request.user_id, REQUIRED_FEATURE):
            raise HTTPException(
                status_code=402,
                detail="Subscription required for quarterly nursery report generation",
            )

        # Mock report generation
        report_id = (
            f"report_nursery_{request.user_id}_{int(datetime.now().timestamp())}"
        )

        return ApiResponse(
            success=True,
            data={
                "report_id": report_id,
                "user_id": request.user_id,
                "report_type": "quarterly_nursery",
                "status": "generated",
                "download_url": f"https://example.com/reports/{report_id}.pdf",
                "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
                "message": "Quarterly nursery safety report generated successfully",
            },
            message="Quarterly nursery report generated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating quarterly nursery report: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quarterly nursery report: {str(e)}",
        )


@safety_reports_router.post("/generate-quarterly-nursery", response_model=ApiResponse)
async def generate_quarterly_nursery_report(
    request: SafetyReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """
    Generate a comprehensive quarterly nursery safety audit report

    Provides:
    - Complete inventory of nursery products
    - Category-based safety analysis
    - Critical item assessment (cribs, car seats, etc.)
    - Expiration tracking for consumables
    - Compliance scoring
    - Personalized recommendations
    """
    try:
        # Calculate date range (last 3 months)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)

        # Get user's scan history for nursery products
        scan_history = (
            db.query(ScanHistory)
            .filter(
                and_(
                    ScanHistory.user_id == request.user_id,
                    ScanHistory.scan_timestamp >= start_date,
                    ScanHistory.scan_timestamp <= end_date,
                )
            )
            .order_by(desc(ScanHistory.scan_timestamp))
            .all()
        )

        # Categorize nursery products
        nursery_categories = {
            "Critical Safety": {
                "keywords": ["crib", "car seat", "high chair", "bassinet", "cradle"],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Feeding": {
                "keywords": [
                    "bottle",
                    "formula",
                    "food",
                    "sippy",
                    "breast pump",
                    "sterilizer",
                ],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Toys & Play": {
                "keywords": ["toy", "play", "rattle", "teether", "mobile", "activity"],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Clothing & Textiles": {
                "keywords": [
                    "clothes",
                    "onesie",
                    "blanket",
                    "swaddle",
                    "sheet",
                    "pajama",
                ],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Furniture": {
                "keywords": [
                    "dresser",
                    "changing table",
                    "shelf",
                    "storage",
                    "wardrobe",
                ],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Safety Equipment": {
                "keywords": ["gate", "monitor", "lock", "guard", "protector", "camera"],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Health & Hygiene": {
                "keywords": [
                    "diaper",
                    "wipe",
                    "thermometer",
                    "medicine",
                    "cream",
                    "lotion",
                ],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
            "Transportation": {
                "keywords": ["stroller", "carrier", "wrap", "sling", "wagon"],
                "products": [],
                "high_risk": 0,
                "recalls": 0,
            },
        }

        # Process scan history and categorize products
        product_groups = {}
        for scan in scan_history:
            # Determine category (reserved for future category tracking)
            _ = False  # category_assigned
            product_name_lower = (scan.product_name or "").lower()

            for category, info in nursery_categories.items():
                if any(keyword in product_name_lower for keyword in info["keywords"]):
                    info["products"].append(scan)
                    if scan.risk_level in ["high", "critical"]:
                        info["high_risk"] += 1
                    if scan.recalls_found and scan.recalls_found > 0:
                        info["recalls"] += scan.recalls_found
                    _ = True  # category_assigned
                    break

            # Group by product for summary
            key = scan.barcode or scan.product_name or "unknown"
            if key not in product_groups:
                product_groups[key] = {
                    "product_name": scan.product_name or "Unknown Product",
                    "brand": scan.brand,
                    "barcode": scan.barcode,
                    "category": scan.category,
                    "scans": [],
                    "recalls_found": 0,
                    "risk_levels": [],
                    "recall_ids": [],
                }
            product_groups[key]["scans"].append(scan)
            product_groups[key]["recalls_found"] += scan.recalls_found or 0
            if scan.risk_level:
                product_groups[key]["risk_levels"].append(scan.risk_level)
            if scan.recall_ids:
                product_groups[key]["recall_ids"].extend(scan.recall_ids)

        # Calculate statistics
        total_products = len(product_groups)
        categories_audited = sum(
            1 for cat in nursery_categories.values() if cat["products"]
        )
        critical_items = len(nursery_categories["Critical Safety"]["products"])
        feeding_items = len(nursery_categories["Feeding"]["products"])
        toy_items = len(nursery_categories["Toys & Play"]["products"])
        clothing_items = len(nursery_categories["Clothing & Textiles"]["products"])
        furniture_items = len(nursery_categories["Furniture"]["products"])
        safety_equipment = len(nursery_categories["Safety Equipment"]["products"])

        total_recalls = sum(cat["recalls"] for cat in nursery_categories.values())
        total_high_risk = sum(cat["high_risk"] for cat in nursery_categories.values())

        # Calculate compliance score
        compliance_score = 100.0
        if total_products > 0:
            # Deduct points for recalls and high-risk items
            recall_penalty = (total_recalls / total_products) * 30
            risk_penalty = (total_high_risk / total_products) * 20

            # Bonus points for safety equipment
            safety_bonus = min(10, (safety_equipment / max(1, total_products)) * 20)

            compliance_score = max(
                0, min(100, 100 - recall_penalty - risk_penalty + safety_bonus)
            )

        # Generate recommendations
        recommendations = []

        if nursery_categories["Critical Safety"]["recalls"] > 0:
            recommendations.append(
                "⚠️ URGENT: Replace recalled critical safety items immediately"
            )

        if nursery_categories["Critical Safety"]["high_risk"] > 0:
            recommendations.append(
                "Review and update critical safety items (cribs, car seats)"
            )

        if feeding_items == 0:
            recommendations.append(
                "Consider tracking feeding products for complete safety coverage"
            )

        if safety_equipment < 3:
            recommendations.append("Add more safety equipment (gates, locks, monitors)")

        if total_recalls > 0:
            recommendations.append(
                f"Remove {total_recalls} recalled items from nursery"
            )

        if compliance_score < 70:
            recommendations.append("Schedule a comprehensive nursery safety review")

        if compliance_score >= 90:
            recommendations.append(
                "✅ Excellent nursery safety! Continue regular monitoring"
            )

        # Build category summaries
        category_summaries = []
        for category_name, category_data in nursery_categories.items():
            if category_data["products"]:
                # Create product summaries for this category
                cat_products = []
                for product_key, product_group in product_groups.items():
                    # Check if this product belongs to this category
                    product_in_category = any(
                        scan in category_data["products"]
                        for scan in product_group["scans"]
                    )
                    if product_in_category:
                        scans = product_group["scans"]
                        risk_level = "low"
                        if "critical" in product_group["risk_levels"]:
                            risk_level = "critical"
                        elif "high" in product_group["risk_levels"]:
                            risk_level = "high"
                        elif "medium" in product_group["risk_levels"]:
                            risk_level = "medium"

                        cat_products.append(
                            ProductScanSummary(
                                product_name=product_group["product_name"],
                                brand=product_group["brand"],
                                barcode=product_group["barcode"],
                                scan_count=len(scans),
                                first_scanned=min(s.scan_timestamp for s in scans),
                                last_scanned=max(s.scan_timestamp for s in scans),
                                risk_level=risk_level,
                                recalls_found=product_group["recalls_found"],
                                verdict=scans[-1].verdict or "No Recalls Found",
                            )
                        )

                category_summaries.append(
                    NurseryProductCategory(
                        category=category_name,
                        product_count=len(cat_products),
                        high_risk_count=category_data["high_risk"],
                        recall_count=category_data["recalls"],
                        products=cat_products[:5],  # Top 5 products per category
                    )
                )

        # Generate report ID
        report_id = f"NR_{uuid.uuid4().hex[:8]}"

        # Prepare nursery statistics
        nursery_stats = NurseryReportStats(
            total_products=total_products,
            categories_audited=categories_audited,
            critical_items=critical_items,
            feeding_items=feeding_items,
            toy_items=toy_items,
            clothing_items=clothing_items,
            furniture_items=furniture_items,
            safety_equipment=safety_equipment,
            recalls_found=total_recalls,
            expired_products=0,  # Would need expiration date tracking
            compliance_score=round(compliance_score, 1),
            recommendations=recommendations,
        )

        # Generate PDF if requested
        pdf_url = None
        if request.generate_pdf:
            try:
                report_agent = ReportBuilderAgentLogic(
                    agent_id=f"report_builder_{report_id}", version="2.1"
                )

                # Prepare data for nursery quarterly report
                report_data = {
                    "products": [
                        {
                            "product": {
                                "product_name": p["product_name"],
                                "brand": p["brand"],
                                "barcode": p["barcode"],
                                "category": p["category"],
                            },
                            "recalls": [
                                {"id": r, "agency": "CPSC", "hazard": "Safety concern"}
                                for r in (p.get("recall_ids") or [])
                            ]
                            if p.get("recalls_found")
                            else [],
                            "risk": {
                                "level": p["risk_levels"][0]
                                if p["risk_levels"]
                                else "low",
                                "score": 50 if "high" in p["risk_levels"] else 20,
                            },
                        }
                        for p in list(product_groups.values())[:20]
                    ]
                }

                result = report_agent._build_nursery_quarterly_report(
                    report_data, workflow_id=report_id
                )

                if result.get("status") == "success" and result.get("pdf_path"):
                    pdf_url = f"/api/v1/reports/download/{report_id}"

                    # Save report record
                    safety_report = SafetyReport(
                        report_id=report_id,
                        user_id=request.user_id,
                        report_type="quarterly_nursery",
                        period_start=start_date,
                        period_end=end_date,
                        total_scans=len(scan_history),
                        unique_products=total_products,
                        recalls_found=total_recalls,
                        high_risk_products=total_high_risk,
                        report_data={
                            "statistics": nursery_stats.dict(),
                            "categories": [c.dict() for c in category_summaries],
                        },
                        pdf_path=result.get("pdf_path"),
                    )
                    db.add(safety_report)
                    db.commit()

            except Exception as e:
                logger.error(f"Failed to generate PDF: {e}")

        # Return response
        return ApiResponse(
            success=True,
            data={
                "report_id": report_id,
                "report_type": "quarterly_nursery",
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "statistics": nursery_stats.dict(),
                "categories": [c.dict() for c in category_summaries],
                "pdf_url": pdf_url,
                "message": f"Quarterly nursery audit complete. {total_products} products analyzed across {categories_audited} categories.",
            },
        )

    except Exception as e:
        logger.error(f"Error generating quarterly nursery report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
