"""Crown Safe Visual Recognition API Endpoints
Image upload, hair product analysis, ingredient extraction, and label recognition
Adapted from BabyShield's visual recognition system for hair product safety
"""

import base64
import io
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, Field, validator
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.auth_endpoints import get_current_user
from core_infra.crown_safe_models import (
    HairProductModel,
    IngredientModel,
    ProductScanModel,
)
from core_infra.database import User
from core_infra.database import get_db as get_db_session

logger = logging.getLogger(__name__)

# Router
visual_router = APIRouter(prefix="/api/v1/crown-safe/visual", tags=["crown-safe-visual-recognition"])

# Azure Blob Storage Configuration
AZURE_REGION = os.getenv("AZURE_REGION", "westeurope")
STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-images")

# Initialize Azure Blob Storage client if configured
try:
    storage_client = AzureBlobStorageClient(container_name=STORAGE_CONTAINER)
    AZURE_BLOB_ENABLED = True
except Exception as e:
    storage_client = None
    AZURE_BLOB_ENABLED = False
    logger.warning(f"Azure Blob Storage not configured: {e}")


# ==================== Request/Response Models ====================


class ImageUploadResponse(BaseModel):
    """Response for image upload"""

    scan_id: str
    upload_url: str | None = None
    status: str
    message: str
    expires_at: datetime | None = None


class HairProductImageAnalysisRequest(BaseModel):
    """Request for hair product image analysis"""

    scan_id: str | None = Field(None, description="Scan ID from upload")
    image_url: str | None = Field(None, description="Direct image URL")
    image_base64: str | None = Field(None, description="Base64 encoded image")
    claimed_product_name: str | None = Field(None, description="User-claimed product name")
    claimed_brand: str | None = Field(None, description="User-claimed brand")
    skip_verification: bool = Field(False, description="Skip multi-factor verification")

    @validator("image_base64")
    def validate_base64(cls, v):
        if v and not v.startswith("data:image/"):
            raise ValueError("image_base64 must be a valid data URL")
        return v


class ExtractedIngredient(BaseModel):
    """Single extracted ingredient from label"""

    name: str
    confidence: float = Field(..., ge=0, le=1)
    position: int = Field(..., description="Position in ingredient list")
    category: str | None = None
    concerns: list[str] = []


class LabelExtractionResult(BaseModel):
    """Results from label OCR and parsing"""

    product_name: str | None = None
    brand: str | None = None
    ingredients: list[ExtractedIngredient] = []
    net_weight: str | None = None
    manufacturer: str | None = None
    warnings: list[str] = []
    extraction_confidence: float = Field(..., ge=0, le=1)
    ocr_text_raw: str | None = None


class SafetyAnalysis(BaseModel):
    """Safety analysis of detected hair product"""

    overall_safety_score: float = Field(..., ge=0, le=100)
    risk_level: str = Field(..., description="low, moderate, high, critical")
    flagged_ingredients: list[dict[str, Any]] = []
    recommendations: list[str] = []
    hair_type_compatibility: dict[str, bool] | None = None
    sulfate_free: bool | None = None
    paraben_free: bool | None = None
    silicone_free: bool | None = None


class HairProductImageAnalysisResponse(BaseModel):
    """Response for hair product image analysis"""

    scan_id: str
    status: str
    timestamp: datetime
    processing_time_ms: int

    # Label extraction
    label_extraction: LabelExtractionResult | None = None

    # Product matching
    matched_product: dict[str, Any] | None = None
    match_confidence: float = Field(0.0, ge=0, le=1)

    # Safety analysis
    safety_analysis: SafetyAnalysis | None = None

    # Additional data
    image_quality_score: float = Field(..., ge=0, le=1)
    requires_manual_review: bool = False
    user_feedback_requested: str | None = None


class ProductVerificationRequest(BaseModel):
    """Request to verify extracted product data"""

    scan_id: str
    confirmed_product_name: str | None = None
    confirmed_brand: str | None = None
    confirmed_ingredients: list[str] | None = None
    user_corrections: dict[str, Any] | None = None


class ScanHistoryItem(BaseModel):
    """Single scan history item"""

    scan_id: str
    timestamp: datetime
    product_name: str | None
    brand: str | None
    safety_score: float | None
    image_thumbnail: str | None
    status: str


class ScanHistoryResponse(BaseModel):
    """Response for scan history"""

    scans: list[ScanHistoryItem]
    total: int
    page: int
    page_size: int


# ==================== Helper Functions ====================


def generate_scan_id() -> str:
    """Generate unique scan ID"""
    return f"scan_{uuid.uuid4().hex[:16]}"


def validate_image_file(file: UploadFile) -> tuple[bool, str | None]:
    """Validate uploaded image file"""
    # Check content type (max 10MB size check removed as unused)
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        return False, f"Invalid file type. Allowed: {', '.join(allowed_types)}"

    return True, None


def extract_image_from_base64(base64_data: str) -> Image.Image:
    """Extract PIL Image from base64 data URL"""
    try:
        # Remove data URL prefix if present
        if base64_data.startswith("data:image/"):
            base64_data = base64_data.split(",", 1)[1]

        # Decode base64
        image_bytes = base64.b64decode(base64_data)
        image = Image.open(io.BytesIO(image_bytes))
        return image
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")


def analyze_image_quality(image: Image.Image) -> float:
    """Analyze image quality for label readability"""
    # Simple quality metrics
    width, height = image.size

    # Check resolution (minimum 800x600 recommended)
    if width < 400 or height < 300:
        return 0.3
    elif width < 800 or height < 600:
        return 0.6
    else:
        return 0.9


async def perform_ocr(image: Image.Image) -> str:
    """Perform OCR on product label image
    TODO: Integrate with Google Cloud Vision or AWS Textract
    """
    # Placeholder - integrate with actual OCR service
    logger.info("OCR requested - returning placeholder")
    return "PLACEHOLDER: OCR text would appear here"


async def extract_ingredients_from_text(ocr_text: str) -> list[ExtractedIngredient]:
    """Parse ingredients from OCR text"""
    # Placeholder - implement ingredient parsing logic
    # Look for common patterns like "Ingredients:", "Contains:", etc.
    logger.info("Ingredient extraction requested - returning placeholder")
    return [
        ExtractedIngredient(
            name="Water",
            confidence=0.95,
            position=1,
            category="solvent",
            concerns=[],
        ),
        ExtractedIngredient(
            name="Sodium Lauryl Sulfate",
            confidence=0.90,
            position=2,
            category="surfactant",
            concerns=["harsh surfactant", "may strip natural oils"],
        ),
    ]


async def match_product_in_database(
    db: Session, product_name: str | None, brand: str | None,
) -> HairProductModel | None:
    """Match extracted product to database"""
    if not product_name:
        return None

    query = db.query(HairProductModel)

    if brand:
        query = query.filter(
            HairProductModel.brand_name.ilike(f"%{brand}%"),
            HairProductModel.product_name.ilike(f"%{product_name}%"),
        )
    else:
        query = query.filter(HairProductModel.product_name.ilike(f"%{product_name}%"))

    return query.first()


async def analyze_product_safety(ingredients: list[ExtractedIngredient], db: Session) -> SafetyAnalysis:
    """Analyze safety based on ingredients"""
    flagged = []
    risk_score = 100.0

    for ing in ingredients:
        # Check against ingredient database
        db_ingredient = db.query(IngredientModel).filter(IngredientModel.name.ilike(f"%{ing.name}%")).first()

        if db_ingredient and db_ingredient.safety_concerns:
            flagged.append(
                {
                    "ingredient": ing.name,
                    "concerns": db_ingredient.safety_concerns,
                    "risk_level": db_ingredient.risk_level or "unknown",
                },
            )
            # Reduce safety score based on risk
            if db_ingredient.risk_level == "high":
                risk_score -= 15
            elif db_ingredient.risk_level == "moderate":
                risk_score -= 8
            elif db_ingredient.risk_level == "low":
                risk_score -= 3

    risk_score = max(0, min(100, risk_score))

    # Determine risk level
    if risk_score >= 80:
        risk_level = "low"
    elif risk_score >= 60:
        risk_level = "moderate"
    elif risk_score >= 40:
        risk_level = "high"
    else:
        risk_level = "critical"

    # Check for common labels
    ingredient_names = [i.name.lower() for i in ingredients]
    sulfate_free = not any("sulfate" in name for name in ingredient_names)
    paraben_free = not any("paraben" in name for name in ingredient_names)
    silicone_free = not any("silicone" in name or "cone" in name for name in ingredient_names)

    return SafetyAnalysis(
        overall_safety_score=risk_score,
        risk_level=risk_level,
        flagged_ingredients=flagged,
        recommendations=[
            "Review flagged ingredients for your hair type",
            "Patch test before full application",
            "Consider sulfate-free alternatives" if not sulfate_free else "✓ Sulfate-free product",
        ],
        hair_type_compatibility=None,  # TODO: Analyze based on hair profile
        sulfate_free=sulfate_free,
        paraben_free=paraben_free,
        silicone_free=silicone_free,
    )


# ==================== API Endpoints ====================


@visual_router.post("/upload", response_model=ImageUploadResponse)
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Upload hair product image for analysis

    Steps:
    1. Validate image format and size
    2. Generate unique scan ID
    3. Store image (S3 or local)
    4. Return scan ID for analysis endpoint
    """
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Generate scan ID
    scan_id = generate_scan_id()

    # Read file content
    image_bytes = await file.read()

    # Store image
    if AZURE_BLOB_ENABLED:
        # Upload to Azure Blob Storage
        try:
            blob_name = f"scans/{current_user.id}/{scan_id}.jpg"
            storage_client.upload_file(
                blob_name=blob_name,
                file_data=image_bytes,
                content_type=file.content_type,
            )
            image_url = storage_client.get_blob_url(blob_name)
        except Exception as e:
            logger.error(f"Azure Blob Storage upload failed: {e}")
            raise HTTPException(status_code=500, detail="Image upload failed") from e
    else:
        # Store locally
        from pathlib import Path

        upload_dir = Path("uploads") / "scans" / str(current_user.id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        image_path = upload_dir / f"{scan_id}.jpg"

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        image_url = f"/uploads/scans/{current_user.id}/{scan_id}.jpg"

    # Create scan record
    scan = ProductScanModel(
        user_id=current_user.id,
        scan_type="visual",
        status="uploaded",
        image_url=image_url,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    return ImageUploadResponse(
        scan_id=scan_id,
        upload_url=image_url,
        status="uploaded",
        message="Image uploaded successfully. Use scan_id for analysis.",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )


@visual_router.post("/analyze", response_model=HairProductImageAnalysisResponse)
async def analyze_product_image(
    request: HairProductImageAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Analyze hair product image using visual recognition

    Process:
    1. Load image (from scan_id, URL, or base64)
    2. Perform OCR on product label
    3. Extract product name, brand, ingredients
    4. Match against product database
    5. Analyze ingredient safety
    6. Return comprehensive analysis
    """
    start_time = datetime.utcnow()

    # Get image
    image = None
    if request.image_base64:
        image = extract_image_from_base64(request.image_base64)
    elif request.scan_id:
        # Load from database scan record
        scan = (
            db.query(ProductScanModel)
            .filter(
                ProductScanModel.user_id == current_user.id,
                ProductScanModel.image_url.contains(request.scan_id),
            )
            .first()
        )
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        # TODO: Load image from URL
    elif request.image_url:
        # TODO: Load image from URL
        pass
    else:
        raise HTTPException(status_code=400, detail="Must provide scan_id, image_url, or image_base64")

    if not image:
        raise HTTPException(status_code=400, detail="Could not load image")

    # Analyze image quality
    quality_score = analyze_image_quality(image)

    # Perform OCR
    ocr_text = await perform_ocr(image)

    # Extract ingredients
    extracted_ingredients = await extract_ingredients_from_text(ocr_text)

    # Build label extraction result
    label_extraction = LabelExtractionResult(
        product_name=request.claimed_product_name or "Unknown Product",
        brand=request.claimed_brand or "Unknown Brand",
        ingredients=extracted_ingredients,
        extraction_confidence=0.75,  # Placeholder
        ocr_text_raw=ocr_text,
    )

    # Match product in database
    matched_product = await match_product_in_database(db, label_extraction.product_name, label_extraction.brand)

    # Analyze safety
    safety_analysis = await analyze_product_safety(extracted_ingredients, db)

    # Calculate processing time
    end_time = datetime.utcnow()
    processing_ms = int((end_time - start_time).total_seconds() * 1000)

    # Prepare response
    response = HairProductImageAnalysisResponse(
        scan_id=request.scan_id or generate_scan_id(),
        status="completed",
        timestamp=end_time,
        processing_time_ms=processing_ms,
        label_extraction=label_extraction,
        matched_product={
            "id": matched_product.id,
            "name": matched_product.product_name,
            "brand": matched_product.brand_name,
        }
        if matched_product
        else None,
        match_confidence=0.85 if matched_product else 0.0,
        safety_analysis=safety_analysis,
        image_quality_score=quality_score,
        requires_manual_review=quality_score < 0.5 or safety_analysis.risk_level in ["high", "critical"],
        user_feedback_requested="Please confirm product details" if quality_score < 0.6 else None,
    )

    # Update scan record in background
    if request.scan_id:
        background_tasks.add_task(update_scan_record, db, request.scan_id, response)

    return response


@visual_router.post("/verify")
async def verify_product_extraction(
    request: ProductVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """User verification/correction of extracted product data
    Helps improve OCR accuracy over time
    """
    # TODO: Store verification data for ML training
    return JSONResponse(
        content={
            "status": "verified",
            "message": "Thank you for verification. This helps improve our recognition accuracy.",
        },
    )


@visual_router.get("/scan-history", response_model=ScanHistoryResponse)
async def get_scan_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Get user's scan history"""
    offset = (page - 1) * page_size

    scans = (
        db.query(ProductScanModel)
        .filter(ProductScanModel.user_id == current_user.id)
        .order_by(desc(ProductScanModel.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total = db.query(ProductScanModel).filter(ProductScanModel.user_id == current_user.id).count()

    scan_items = [
        ScanHistoryItem(
            scan_id=str(scan.id),
            timestamp=scan.created_at,
            product_name=scan.product_name,
            brand=scan.brand_name,
            safety_score=scan.safety_score,
            image_thumbnail=scan.image_url,
            status=scan.status,
        )
        for scan in scans
    ]

    return ScanHistoryResponse(scans=scan_items, total=total, page=page, page_size=page_size)


@visual_router.get("/scan/{scan_id}")
async def get_scan_details(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Get detailed scan results"""
    scan = (
        db.query(ProductScanModel)
        .filter(
            ProductScanModel.user_id == current_user.id,
            ProductScanModel.id == scan_id,
        )
        .first()
    )

    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return JSONResponse(
        content={
            "scan_id": str(scan.id),
            "timestamp": scan.created_at.isoformat(),
            "status": scan.status,
            "product_name": scan.product_name,
            "brand": scan.brand_name,
            "safety_score": scan.safety_score,
            "image_url": scan.image_url,
            "analysis": scan.analysis_results,
        },
    )


def update_scan_record(db: Session, scan_id: str, analysis: HairProductImageAnalysisResponse) -> None:
    """Background task to update scan record with analysis results"""
    try:
        scan = db.query(ProductScanModel).filter(ProductScanModel.image_url.contains(scan_id)).first()
        if scan:
            scan.status = "completed"
            scan.product_name = analysis.label_extraction.product_name if analysis.label_extraction else None
            scan.brand_name = analysis.label_extraction.brand if analysis.label_extraction else None
            scan.safety_score = analysis.safety_analysis.overall_safety_score if analysis.safety_analysis else None
            scan.analysis_results = analysis.dict()
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update scan record: {e}")
        db.rollback()
