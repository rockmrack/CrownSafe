"""
Crown Safe - Routine Analysis Endpoints
Batch product analysis and interaction warnings

Endpoints:
- POST /api/v1/cabinet-audit - Analyze entire routine for issues
- POST /api/v1/routine-check - Check product interactions

Key Features:
- Protein overload detection
- Build-up warnings (silicones, heavy oils)
- Stripping/dryness alerts
- Product rotation recommendations
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_endpoints import get_current_user
from core.crown_score_engine import (
    CrownScoreEngine,
    HairGoal,
    HairProfile,
    HairState,
    HairType,
    Porosity,
    ProductType,
)
from core_infra.crown_safe_models import HairProfileModel
from core_infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["routine-analysis"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class ProductInput(BaseModel):
    """Product for analysis (either by product_id or manual input)"""

    product_id: Optional[int] = Field(None, description="Product ID from database")
    product_name: Optional[str] = Field(None, description="Product name (if manual)")
    brand: Optional[str] = Field(None, description="Brand name (if manual)")
    product_type: str = Field(..., description="Shampoo, Conditioner, Leave-In, etc.")
    ingredients: List[str] = Field(..., description="List of ingredients (INCI order)")
    usage_frequency: str = Field(default="daily", description="How often used: daily, weekly, occasionally")


class CabinetAuditRequest(BaseModel):
    """Request for cabinet audit (batch product analysis)"""

    products: List[ProductInput] = Field(..., min_length=1, description="Products to analyze")
    user_id: Optional[int] = Field(None, description="User ID (for fetching hair profile)")

    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {
                        "product_name": "Moisture Shampoo",
                        "brand": "Shea Moisture",
                        "product_type": "Shampoo",
                        "ingredients": [
                            "Water",
                            "Sodium Laureth Sulfate",
                            "Cocamidopropyl Betaine",
                        ],
                        "usage_frequency": "daily",
                    },
                    {
                        "product_name": "Deep Conditioner",
                        "brand": "Mielle",
                        "product_type": "Deep Conditioner",
                        "ingredients": ["Water", "Behentrimonium Chloride", "Shea Butter"],
                        "usage_frequency": "weekly",
                    },
                ],
                "user_id": 1,
            }
        }


class RoutineIssue(BaseModel):
    """Identified issue in routine"""

    issue_type: str  # protein_overload, buildup, stripping, moisture_imbalance
    severity: str  # low, medium, high, critical
    title: str
    description: str
    affected_products: List[str]  # Product names
    recommendation: str


class RotationPlan(BaseModel):
    """Recommended product rotation schedule"""

    frequency: str  # daily, weekly, bi-weekly, monthly
    products: List[str]
    purpose: str


class CabinetAuditResponse(BaseModel):
    """Cabinet audit analysis results"""

    success: bool
    total_products: int
    average_crown_score: float
    issues: List[RoutineIssue]
    rotation_plan: List[RotationPlan]
    summary: str
    red_flag_ingredients: List[str]
    product_scores: dict  # {product_name: crown_score}


class RoutineCheckRequest(BaseModel):
    """Request for product interaction check"""

    product_1_ingredients: List[str] = Field(..., description="First product ingredients")
    product_2_ingredients: List[str] = Field(..., description="Second product ingredients")
    product_1_type: str = Field(..., description="First product type")
    product_2_type: str = Field(..., description="Second product type")
    use_together: bool = Field(default=True, description="Are these used together or sequentially?")


class InteractionWarning(BaseModel):
    """Product interaction warning"""

    warning_type: str  # buildup, stripping, incompatible, neutralizing
    severity: str  # low, medium, high
    description: str
    recommendation: str


class RoutineCheckResponse(BaseModel):
    """Product interaction check results"""

    success: bool
    safe_combination: bool
    warnings: List[InteractionWarning]
    summary: str


class ApiResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool
    message: str
    data: Optional[dict] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def detect_protein_overload(products: List[ProductInput]) -> Optional[RoutineIssue]:
    """Detect if routine has too much protein"""
    protein_keywords = [
        "hydrolyzed",
        "protein",
        "keratin",
        "collagen",
        "amino acid",
        "silk",
        "wheat protein",
        "soy protein",
    ]

    protein_count = 0
    affected = []

    for product in products:
        has_protein = False
        for ingredient in product.ingredients:
            if any(kw in ingredient.lower() for kw in protein_keywords):
                has_protein = True
                break

        if has_protein:
            protein_count += 1
            affected.append(f"{product.product_name or 'Unknown'} ({product.product_type})")

    # Too much protein if 3+ products contain it
    if protein_count >= 3:
        return RoutineIssue(
            issue_type="protein_overload",
            severity="high" if protein_count >= 4 else "medium",
            title="⚠️ Protein Overload Risk",
            description=f"Found protein in {protein_count} products. "
            "Too much protein can cause stiffness, dryness, and breakage in high-porosity 4C hair.",
            affected_products=affected,
            recommendation="Alternate protein-rich products with protein-free moisture treatments. "
            "Use protein products every 2-3 weeks instead of weekly.",
        )
    return None


def detect_buildup(products: List[ProductInput]) -> Optional[RoutineIssue]:
    """Detect silicone/heavy oil build-up risk"""
    buildup_keywords = [
        "dimethicone",
        "cyclomethicone",
        "amodimethicone",
        "silicone",
        "mineral oil",
        "petrolatum",
        "petroleum",
    ]

    buildup_products = []
    has_clarifying = False

    for product in products:
        # Check for clarifying (sulfates in shampoo)
        if product.product_type.lower() == "shampoo":
            if any("sulfate" in ing.lower() for ing in product.ingredients):
                has_clarifying = True

        # Check for build-up ingredients in leave-ins
        if "leave" in product.product_type.lower() or "gel" in product.product_type.lower():
            for ingredient in product.ingredients:
                if any(kw in ingredient.lower() for kw in buildup_keywords):
                    buildup_products.append(f"{product.product_name or 'Unknown'} ({product.product_type})")
                    break

    if buildup_products and not has_clarifying:
        return RoutineIssue(
            issue_type="buildup",
            severity="medium",
            title="⚠️ Build-up Risk (No Clarifying Shampoo)",
            description=f"Found {len(buildup_products)} products with heavy silicones/oils "
            "but no clarifying shampoo to remove build-up.",
            affected_products=buildup_products,
            recommendation="Add a sulfate-based clarifying shampoo for weekly or bi-weekly use. "
            "Without clarification, silicones will coat hair and block moisture.",
        )
    return None


def detect_stripping(products: List[ProductInput]) -> Optional[RoutineIssue]:
    """Detect harsh stripping from too many sulfates"""
    stripping_sulfates = ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"]

    harsh_products = []

    for product in products:
        if product.product_type.lower() == "shampoo":
            for ingredient in product.ingredients:
                if any(sulfate in ingredient.lower() for sulfate in stripping_sulfates):
                    harsh_products.append(f"{product.product_name or 'Unknown'}")
                    break

    if harsh_products and any(p.usage_frequency == "daily" for p in products):
        return RoutineIssue(
            issue_type="stripping",
            severity="medium",
            title="⚠️ Over-Stripping Risk",
            description=f"Using harsh sulfate shampoo ({', '.join(harsh_products)}) daily "
            "can strip natural oils, causing dryness and breakage.",
            affected_products=harsh_products,
            recommendation="Switch to sulfate-free shampoo for daily use. "
            "Use sulfate shampoo only once a week for clarifying.",
        )
    return None


def detect_moisture_imbalance(products: List[ProductInput]) -> Optional[RoutineIssue]:
    """Detect lack of moisturizing products"""
    moisturizing_keywords = [
        "shea butter",
        "coconut oil",
        "jojoba",
        "argan",
        "glycerin",
        "aloe",
        "hyaluronic",
    ]

    has_deep_conditioner = False
    has_leave_in = False
    has_moisturizers = False

    for product in products:
        if "deep conditioner" in product.product_type.lower():
            has_deep_conditioner = True

        if "leave-in" in product.product_type.lower() or "cream" in product.product_type.lower():
            has_leave_in = True

        for ingredient in product.ingredients:
            if any(kw in ingredient.lower() for kw in moisturizing_keywords):
                has_moisturizers = True
                break

    if not has_deep_conditioner or not has_leave_in or not has_moisturizers:
        missing = []
        if not has_deep_conditioner:
            missing.append("deep conditioner")
        if not has_leave_in:
            missing.append("leave-in moisturizer")

        return RoutineIssue(
            issue_type="moisture_imbalance",
            severity="medium",
            title="💧 Moisture Gap Detected",
            description=f"Routine is missing key moisturizing steps: {', '.join(missing)}. "
            "4C hair needs maximum moisture retention.",
            affected_products=[],
            recommendation="Add a weekly deep conditioning treatment and a daily leave-in moisturizer. "
            "Look for ingredients like shea butter, glycerin, and aloe vera.",
        )
    return None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/cabinet-audit", response_model=CabinetAuditResponse)
async def cabinet_audit(
    request: CabinetAuditRequest,
    db: Session = Depends(get_db),  # noqa: B008
    current_user=Depends(get_current_user),  # noqa: B008
):
    """
    Analyze entire hair product routine for issues.

    **Crown Safe Differentiator**: Batch analysis across all products.

    **Detects**:
    - Protein overload (stiffness, breakage)
    - Build-up risk (silicones without clarifying)
    - Over-stripping (harsh sulfates too frequently)
    - Moisture imbalance (missing key products)

    **Returns**:
    - Crown Score for each product
    - Identified issues with severity
    - Product rotation recommendations
    - Summary with actionable advice
    """
    try:
        # Get user's hair profile for personalized analysis
        user_id = request.user_id or current_user.id
        hair_profile_model = db.query(HairProfileModel).filter(HairProfileModel.user_id == user_id).first()

        if not hair_profile_model:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hair profile required for cabinet audit. Create one at POST /profiles",
            )

        # Convert to HairProfile object
        hair_profile = HairProfile(
            hair_type=HairType(hair_profile_model.hair_type),
            porosity=Porosity(hair_profile_model.porosity),
            hair_state=[HairState(s) for s in hair_profile_model.hair_state],
            hair_goals=[HairGoal(g) for g in hair_profile_model.hair_goals],
            sensitivities=hair_profile_model.sensitivities or [],
        )

        # Initialize Crown Score engine
        crown_engine = CrownScoreEngine()

        # Analyze each product
        product_scores = {}
        all_red_flags = []
        total_score = 0

        for product in request.products:
            try:
                product_type_enum = ProductType(product.product_type)
                score, breakdown, verdict = crown_engine.calculate_crown_score(
                    ingredients=product.ingredients,
                    hair_profile=hair_profile,
                    product_type=product_type_enum,
                )

                product_name = product.product_name or f"{product.brand} {product.product_type}"
                product_scores[product_name] = score
                total_score += score

                # Collect red flags
                all_red_flags.extend(breakdown.red_flags)

            except Exception as e:
                logger.warning(f"Error analyzing product: {e}")
                continue

        # Calculate average score
        avg_score = total_score / len(request.products) if request.products else 0

        # Detect routine issues
        issues = []

        protein_issue = detect_protein_overload(request.products)
        if protein_issue:
            issues.append(protein_issue)

        buildup_issue = detect_buildup(request.products)
        if buildup_issue:
            issues.append(buildup_issue)

        stripping_issue = detect_stripping(request.products)
        if stripping_issue:
            issues.append(stripping_issue)

        moisture_issue = detect_moisture_imbalance(request.products)
        if moisture_issue:
            issues.append(moisture_issue)

        # Build rotation plan
        rotation_plan = []

        # Daily: gentle cleanser + leave-in
        daily_products = [
            p.product_name or f"{p.brand} {p.product_type}"
            for p in request.products
            if "leave-in" in p.product_type.lower() or "cream" in p.product_type.lower()
        ]
        if daily_products:
            rotation_plan.append(
                RotationPlan(
                    frequency="daily",
                    products=daily_products[:2],
                    purpose="Daily moisture retention",
                )
            )

        # Weekly: deep conditioner
        weekly_products = [
            p.product_name or f"{p.brand} {p.product_type}"
            for p in request.products
            if "deep" in p.product_type.lower() or "mask" in p.product_type.lower()
        ]
        if weekly_products:
            rotation_plan.append(
                RotationPlan(
                    frequency="weekly",
                    products=weekly_products,
                    purpose="Deep conditioning treatment",
                )
            )

        # Generate summary
        if avg_score >= 80:
            summary = (
                f"✅ Excellent routine! Average Crown Score: {avg_score:.0f}/100. "
                f"Found {len(issues)} minor issue(s) to address."
            )
        elif avg_score >= 60:
            summary = (
                f"⚠️ Good routine with room for improvement. "
                f"Average Crown Score: {avg_score:.0f}/100. "
                f"Address {len(issues)} issue(s) for better results."
            )
        else:
            summary = (
                f"🚨 Routine needs major changes. Average Crown Score: {avg_score:.0f}/100. "
                f"{len(issues)} critical issue(s) found."
            )

        logger.info(
            f"✅ Cabinet audit complete: {len(request.products)} products, "
            f"avg score {avg_score:.0f}, {len(issues)} issues"
        )

        return CabinetAuditResponse(
            success=True,
            total_products=len(request.products),
            average_crown_score=round(avg_score, 1),
            issues=issues,
            rotation_plan=rotation_plan,
            summary=summary,
            red_flag_ingredients=list(set(all_red_flags)),
            product_scores=product_scores,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in cabinet audit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete cabinet audit",
        ) from None


@router.post("/routine-check", response_model=RoutineCheckResponse)
async def routine_check(request: RoutineCheckRequest):
    """
    Check if two products have problematic interactions.

    **Use case**: "Can I use this leave-in with this gel?"

    **Checks for**:
    - Build-up (silicones in both products)
    - Stripping (harsh sulfate + protein)
    - Incompatible (oil-based + water-based gels)
    - Neutralizing effects
    """
    try:
        warnings = []

        # Combine ingredient lists for analysis
        all_ingredients = set(
            [ing.lower() for ing in request.product_1_ingredients]
            + [ing.lower() for ing in request.product_2_ingredients]
        )

        # Check for silicone build-up
        silicones = [ing for ing in all_ingredients if "dimethicone" in ing or "silicone" in ing]
        if len(silicones) >= 2:
            warnings.append(
                InteractionWarning(
                    warning_type="buildup",
                    severity="medium",
                    description="Both products contain silicones, which can layer and cause build-up.",
                    recommendation="Use a clarifying shampoo weekly to prevent coating.",
                )
            )

        # Check for protein + sulfate (over-stripping)
        has_protein = any("protein" in ing or "hydrolyzed" in ing for ing in all_ingredients)
        has_harsh_sulfate = any(
            "sodium lauryl sulfate" in ing or "sodium laureth sulfate" in ing for ing in all_ingredients
        )

        if has_protein and has_harsh_sulfate:
            warnings.append(
                InteractionWarning(
                    warning_type="stripping",
                    severity="high",
                    description="Harsh sulfates strip protein treatments, wasting product and causing dryness.",
                    recommendation="Use sulfate-free shampoo after protein treatments.",
                )
            )

        # Check for incompatible bases (oil + water-based gel)
        product_1_has_oil = any("oil" in ing or "butter" in ing for ing in request.product_1_ingredients)
        product_2_is_water_gel = "gel" in request.product_2_type.lower() and any(
            "water" in ing for ing in request.product_2_ingredients
        )

        if product_1_has_oil and product_2_is_water_gel:
            warnings.append(
                InteractionWarning(
                    warning_type="incompatible",
                    severity="low",
                    description="Oil-based product may repel water-based gel, reducing effectiveness.",
                    recommendation="Apply water-based products first, then seal with oils.",
                )
            )

        # Determine if combination is safe
        safe_combination = len([w for w in warnings if w.severity in ["high", "critical"]]) == 0

        # Generate summary
        if not warnings:
            summary = "✅ Safe combination! No interactions detected."
        elif safe_combination:
            summary = f"⚠️ Mostly safe, but {len(warnings)} minor concern(s) to note."
        else:
            summary = f"🚨 Not recommended - {len(warnings)} interaction(s) found."

        logger.info(f"✅ Routine check: {len(warnings)} warnings, safe={safe_combination}")

        return RoutineCheckResponse(
            success=True,
            safe_combination=safe_combination,
            warnings=warnings,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"❌ Error in routine check: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete routine check",
        ) from None
