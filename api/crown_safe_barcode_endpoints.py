"""Crown Safe Barcode Scanning API Endpoints
Scan hair product barcodes and analyze ingredients for 3C-4C hair safety.
"""

import logging
from datetime import datetime, UTC
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.crown_score_engine import CrownScoreEngine
from core_infra.barcode_scanner import scanner
from core_infra.crown_safe_models import (
    HairProductModel,
    HairProfileModel,
    ProductScanModel,
)
from core_infra.database import get_db_session, get_user_hair_profile

logger = logging.getLogger(__name__)

# Create router
crown_barcode_router = APIRouter(prefix="/api/v1/crown-safe/barcode", tags=["crown-safe-barcode"])


# Request/Response Models
class BarcodeScanRequest(BaseModel):
    """Request model for hair product barcode scanning."""

    user_id: int = Field(..., description="User ID for personalized analysis")
    barcode: str = Field(..., description="UPC/EAN barcode from product")
    scan_method: str = Field(default="barcode", description="Scan method: barcode, image, manual")


class IngredientInfo(BaseModel):
    """Individual ingredient information."""

    name: str
    category: str
    safety_level: str  # safe, caution, harmful
    impact_score: float
    description: str | None = None


class CrownScoreBreakdown(BaseModel):
    """Detailed Crown Score breakdown."""

    total_score: int = Field(..., ge=0, le=100, description="Total Crown Score (0-100)")
    verdict: str = Field(..., description="UNSAFE, USE_WITH_CAUTION, SAFE, EXCELLENT_MATCH")
    harmful_ingredients: list[IngredientInfo] = Field(default_factory=list)
    beneficial_ingredients: list[IngredientInfo] = Field(default_factory=list)
    porosity_match: float = Field(..., description="Porosity compatibility score")
    curl_pattern_match: float = Field(..., description="Curl pattern compatibility")
    hair_goal_alignment: float = Field(..., description="Hair goal alignment score")
    ph_balance_score: float = Field(..., description="pH balance score")
    personalization_used: bool = Field(..., description="Whether user profile was used")


class ProductInfo(BaseModel):
    """Product identification information."""

    product_name: str
    brand: str
    upc_barcode: str
    category: str | None = None
    ingredients_list: list[str]
    product_image_url: str | None = None
    manufacturer: str | None = None


class BarcodeScanResponse(BaseModel):
    """Response model for barcode scan with Crown Score."""

    success: bool
    scan_id: str = Field(..., description="Unique scan identifier")
    product: ProductInfo
    crown_score: CrownScoreBreakdown
    recommendations: list[str] = Field(default_factory=list, description="Personalized recommendations")
    similar_products: list[dict[str, Any]] = Field(
        default_factory=list, description="Better alternatives if score is low",
    )
    scan_timestamp: str


class ApiResponse(BaseModel):
    """Standard API response wrapper."""

    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None


# Helper Functions
def lookup_product_in_database(barcode: str, db: Session) -> HairProductModel | None:
    """Look up hair product by UPC barcode in database.

    Args:
        barcode: UPC/EAN barcode
        db: Database session

    Returns:
        HairProductModel if found, None otherwise

    """
    try:
        # Normalize barcode (remove dashes, leading zeros)
        normalized_barcode = barcode.replace("-", "").lstrip("0")

        # Search for exact match or normalized match
        product = (
            db.query(HairProductModel)
            .filter((HairProductModel.upc_barcode == barcode) | (HairProductModel.upc_barcode == normalized_barcode))
            .first()
        )

        return product
    except Exception as e:
        logger.exception(f"Error looking up product in database: {e}")
        return None


async def extract_ingredients_from_image(image_data: bytes, product_name: str | None = None) -> list[str]:
    """Extract ingredient list from product image using OCR.

    Args:
        image_data: Raw image bytes
        product_name: Optional product name for context

    Returns:
        List of ingredient names

    """
    try:
        # This would integrate with Google Cloud Vision or similar OCR service
        # For now, return empty list - to be implemented
        logger.warning("OCR ingredient extraction not yet implemented")
        return []
    except Exception as e:
        logger.exception(f"Error extracting ingredients from image: {e}")
        return []


def calculate_crown_score_from_product(
    product: HairProductModel, hair_profile: HairProfileModel | None,
) -> dict[str, Any]:
    """Calculate Crown Score for a product using user's hair profile.

    Args:
        product: Hair product model
        hair_profile: User's hair profile (optional)

    Returns:
        Crown Score breakdown dictionary

    """
    try:
        engine = CrownScoreEngine()

        # Build product data for engine
        product_data = {
            "product_name": product.product_name,
            "brand": product.brand,
            "ingredients": product.ingredients_list or [],
            "category": product.category,
            "ph_level": product.ph_level,
        }

        # Build hair profile data
        hair_data = None
        if hair_profile:
            hair_data = {
                "hair_type": hair_profile.hair_type,
                "porosity": hair_profile.porosity,
                "hair_state": hair_profile.hair_state or {},
                "hair_goals": hair_profile.hair_goals or [],
                "sensitivities": hair_profile.sensitivities or [],
            }

        # Calculate score
        result = engine.calculate_crown_score(product_data, hair_data)

        return result
    except Exception as e:
        logger.exception(f"Error calculating Crown Score: {e}")
        raise


def generate_recommendations(crown_score: int, verdict: str, product: HairProductModel) -> list[str]:
    """Generate personalized recommendations based on Crown Score.

    Args:
        crown_score: Total Crown Score (0-100)
        verdict: Crown Score verdict
        product: Hair product model

    Returns:
        List of recommendation strings

    """
    recommendations = []

    if verdict == "UNSAFE":
        recommendations.append(
            f"⚠️ This product scored {crown_score}/100 and contains harmful ingredients for 3C-4C hair.",
        )
        recommendations.append("We strongly recommend avoiding this product and choosing a safer alternative.")
        recommendations.append("Check our 'Excellent Match' products for better options.")
    elif verdict == "USE_WITH_CAUTION":
        recommendations.append(f"⚠️ This product scored {crown_score}/100. Use with caution.")
        recommendations.append("Consider patch testing before full application to check for sensitivities.")
        recommendations.append("Monitor hair health closely after use.")
    elif verdict == "SAFE":
        recommendations.append(f"✅ This product scored {crown_score}/100 and is safe for your hair type.")
        recommendations.append("Follow product instructions for best results with your hair.")
    else:  # EXCELLENT_MATCH
        recommendations.append(f"🌟 Excellent Match! This product scored {crown_score}/100 for your hair profile.")
        recommendations.append("This product is highly compatible with your hair type and goals.")
        recommendations.append("Great choice for maintaining healthy 3C-4C hair!")

    return recommendations


def find_similar_products(product: HairProductModel, crown_score: int, db: Session) -> list[dict[str, Any]]:
    """Find similar products with better Crown Scores.

    Args:
        product: Current product
        crown_score: Current product's Crown Score
        db: Database session

    Returns:
        List of similar products (max 3)

    """
    try:
        # Only suggest alternatives if score is below 70
        if crown_score >= 70:
            return []

        # Find products in same category with better scores
        similar = (
            db.query(HairProductModel)
            .filter(
                HairProductModel.category == product.category,
                HairProductModel.id != product.id,
                HairProductModel.average_crown_score > crown_score,
            )
            .order_by(HairProductModel.average_crown_score.desc())
            .limit(3)
            .all()
        )

        return [
            {
                "product_name": p.product_name,
                "brand": p.brand,
                "upc_barcode": p.upc_barcode,
                "average_crown_score": p.average_crown_score,
                "category": p.category,
            }
            for p in similar
        ]
    except Exception as e:
        logger.exception(f"Error finding similar products: {e}")
        return []


# API Endpoints
@crown_barcode_router.post("/scan", response_model=ApiResponse)
async def scan_hair_product_barcode(request: BarcodeScanRequest, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Scan hair product barcode and analyze ingredients with Crown Score.

    Workflow:
    1. Look up product in Crown Safe database by UPC barcode
    2. If found: Use cached ingredient data
    3. If not found: Return error (product not in database)
    4. Retrieve user's hair profile for personalized analysis
    5. Calculate Crown Score with hair profile
    6. Generate personalized recommendations
    7. Save scan to history
    8. Return detailed analysis

    Args:
        request: Barcode scan request with user_id and barcode

    Returns:
        Crown Score analysis with product information

    Raises:
        404: Product not found in database
        422: Invalid user or missing hair profile

    """
    try:
        scan_id = f"scan_{request.user_id}_{int(datetime.now(UTC).timestamp())}"
        logger.info(f"Crown Safe barcode scan: user={request.user_id}, barcode={request.barcode}, scan_id={scan_id}")

        # 1. Look up product in database
        product = lookup_product_in_database(request.barcode, db)
        if not product:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "product_not_found",
                    "message": f"Product with barcode {request.barcode} not found in Crown Safe database.",
                    "suggestion": "Try scanning the ingredient list with our image analysis feature, or add this product to our database.",  # noqa: E501
                },
            )

        # 2. Retrieve user's hair profile (optional)
        hair_profile = None
        try:
            hair_profile = get_user_hair_profile(request.user_id, db)
        except Exception as profile_error:
            logger.warning(f"Could not retrieve hair profile for user {request.user_id}: {profile_error}")
            # Continue without profile - analysis will be generic

        # 3. Calculate Crown Score
        score_result = calculate_crown_score_from_product(product, hair_profile)

        # 4. Generate recommendations
        recommendations = generate_recommendations(score_result["total_score"], score_result["verdict"], product)

        # 5. Find similar products if score is low
        similar_products = find_similar_products(product, score_result["total_score"], db)

        # 6. Save scan to database
        try:
            scan_record = ProductScanModel(
                user_id=request.user_id,
                product_id=product.id,
                scan_date=datetime.now(UTC),
                crown_score=score_result["total_score"],
                verdict=score_result["verdict"],
                scan_method=request.scan_method,
                analysis_data=score_result,  # Store full breakdown
            )
            db.add(scan_record)
            db.commit()
            db.refresh(scan_record)
            logger.info(
                f"Saved scan record: scan_id={scan_id}, product_id={product.id}, score={score_result['total_score']}",
            )
        except Exception as save_error:
            logger.exception(f"Failed to save scan record: {save_error}")
            db.rollback()
            # Continue - don't fail the request if save fails

        # 7. Build response
        product_info = ProductInfo(
            product_name=product.product_name,
            brand=product.brand,
            upc_barcode=product.upc_barcode,
            category=product.category,
            ingredients_list=product.ingredients_list or [],
            product_image_url=product.product_image_url,
            manufacturer=product.manufacturer,
        )

        crown_score_breakdown = CrownScoreBreakdown(
            total_score=score_result["total_score"],
            verdict=score_result["verdict"],
            harmful_ingredients=[
                IngredientInfo(
                    name=ing["name"],
                    category=ing.get("category", "unknown"),
                    safety_level=ing.get("safety_level", "caution"),
                    impact_score=ing.get("impact_score", 0.0),
                    description=ing.get("description"),
                )
                for ing in score_result.get("harmful_ingredients", [])
            ],
            beneficial_ingredients=[
                IngredientInfo(
                    name=ing["name"],
                    category=ing.get("category", "beneficial"),
                    safety_level="safe",
                    impact_score=ing.get("impact_score", 0.0),
                    description=ing.get("description"),
                )
                for ing in score_result.get("beneficial_ingredients", [])
            ],
            porosity_match=score_result.get("porosity_match", 0.0),
            curl_pattern_match=score_result.get("curl_pattern_match", 0.0),
            hair_goal_alignment=score_result.get("hair_goal_alignment", 0.0),
            ph_balance_score=score_result.get("ph_balance_score", 0.0),
            personalization_used=hair_profile is not None,
        )

        response_data = BarcodeScanResponse(
            success=True,
            scan_id=scan_id,
            product=product_info,
            crown_score=crown_score_breakdown,
            recommendations=recommendations,
            similar_products=similar_products,
            scan_timestamp=datetime.now(UTC).isoformat(),
        )

        return ApiResponse(
            success=True,
            data=response_data.model_dump(),
            message=f"Product analyzed: {product.product_name} scored {score_result['total_score']}/100",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.exception(f"Barcode scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze product: {e!s}")


@crown_barcode_router.post("/scan-image", response_model=ApiResponse)
async def scan_hair_product_image(
    user_id: int,
    file: UploadFile = File(..., description="Product image with barcode"),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    """Scan hair product image to extract barcode and analyze.

    Workflow:
    1. Validate image file
    2. Use barcode scanner to detect barcode in image
    3. If barcode found: Look up product and analyze
    4. If no barcode: Return error with suggestion to use manual entry

    Args:
        user_id: User ID for personalized analysis
        file: Uploaded product image
        db: Database session

    Returns:
        Crown Score analysis if barcode detected

    Raises:
        400: Invalid file type
        413: File too large
        404: No barcode detected in image

    """
    try:
        # Validate file type
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/webp",
        ]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
            )

        # Read and validate file size (10MB limit)
        content = await file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(content)} bytes. Max: 10MB",
            )

        # Scan image for barcodes
        scan_results = await scanner.scan_image(content)

        if not scan_results or not any(r.success for r in scan_results):
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "no_barcode_detected",
                    "message": "Could not detect a barcode in the uploaded image.",
                    "suggestion": "Try taking a clearer photo with better lighting, or enter the barcode manually.",
                },
            )

        # Get first successful scan result
        scan_result = next((r for r in scan_results if r.success), None)
        if not scan_result or not scan_result.gtin:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "invalid_barcode",
                    "message": "Detected barcode is invalid or cannot be read.",
                },
            )

        # Create barcode scan request and process
        barcode_request = BarcodeScanRequest(user_id=user_id, barcode=scan_result.gtin, scan_method="image")

        # Reuse the barcode scan logic
        return await scan_hair_product_barcode(barcode_request, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Image scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to scan image: {e!s}")


@crown_barcode_router.get("/product/{barcode}", response_model=ApiResponse)
async def get_product_by_barcode(barcode: str, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Look up product information by UPC barcode (no analysis).

    Use this endpoint to check if a product exists in the Crown Safe database
    before performing a full scan and analysis.

    Args:
        barcode: UPC/EAN barcode
        db: Database session

    Returns:
        Product information if found

    Raises:
        404: Product not found

    """
    try:
        product = lookup_product_in_database(barcode, db)
        if not product:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "product_not_found",
                    "message": f"Product with barcode {barcode} not found in Crown Safe database.",
                },
            )

        product_data = {
            "product_name": product.product_name,
            "brand": product.brand,
            "upc_barcode": product.upc_barcode,
            "category": product.category,
            "ingredients_count": len(product.ingredients_list or []),
            "average_crown_score": product.average_crown_score,
            "scan_count": product.scan_count,
            "product_image_url": product.product_image_url,
            "manufacturer": product.manufacturer,
        }

        return ApiResponse(
            success=True,
            data=product_data,
            message=f"Product found: {product.product_name}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Product lookup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to lookup product: {e!s}")
