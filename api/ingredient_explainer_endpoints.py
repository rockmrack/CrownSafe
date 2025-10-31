"""Crown Safe - Ingredient Explainer Endpoints
Plain-English ingredient explanations for user education

Endpoint:
- GET /api/v1/ingredients/{ingredient_name} - Get ingredient details

Core UX Feature: "Tap any ingredient for explanation"
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core_infra.crown_safe_models import IngredientModel
from core_infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingredients", tags=["ingredients"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class IngredientExplanation(BaseModel):
    """Plain-English ingredient explanation"""

    # Basic info
    name: str = Field(..., description="Common ingredient name")
    inci_name: str | None = Field(None, description="INCI (scientific) name")
    common_names: list[str] = Field(default=[], description="Alternative names for this ingredient")

    # Quick verdict
    category: str = Field(..., description="Ingredient category (Alcohol, Sulfate, etc.)")
    safety_level: str = Field(..., description="Safety level: Safe, Caution, Avoid")
    base_score: int = Field(..., description="Base score (-50 to +20)")

    # Plain English explanation
    description: str = Field(..., description="What this ingredient is and does")
    why_good: str | None = Field(None, description="Benefits (if any)")
    why_bad: str | None = Field(None, description="Concerns (if any)")

    # Hair type guidance
    best_for: list[str] = Field(default=[], description="Hair types that benefit most (3C, 4A, 4B, 4C)")
    avoid_if: list[str] = Field(default=[], description="When to avoid this ingredient")

    # Porosity notes
    porosity_notes: dict[str, str] = Field(
        default={},
        description="Guidance by porosity level (Low, Medium, High)",
    )

    # Usage context
    function: str | None = Field(None, description="Technical function (humectant, etc.)")
    rinse_off_vs_leave_in: str | None = Field(None, description="Is it safer in rinse-off or leave-in products?")

    # Regulatory
    fda_status: str | None = Field(None, description="FDA status")
    eu_status: str | None = Field(None, description="EU status")

    # Additional info
    research_links: list[str] = Field(default=[], description="Scientific references")

    class Config:
        from_attributes = True


class IngredientSearchResult(BaseModel):
    """Search result for ingredient lookup"""

    name: str
    category: str
    safety_level: str
    base_score: int
    description_preview: str  # First 150 characters


class ApiResponse(BaseModel):
    """Standard API response wrapper"""

    success: bool
    message: str
    data: dict | None = None


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/{ingredient_name}", response_model=IngredientExplanation)
async def get_ingredient_explainer(
    ingredient_name: str,
    hair_type: str | None = Query(None, description="User's hair type for personalized advice"),
    porosity: str | None = Query(None, description="User's porosity for tailored notes"),
):
    """Get plain-English explanation for an ingredient.

    **Core UX Feature**: Tap any ingredient in a product scan to see this.

    **Example:**
    ```
    GET /api/v1/ingredients/Cetyl Alcohol?hair_type=4C&porosity=High
    ```

    **Returns:**
    - What the ingredient is and does (plain English)
    - Whether it's good or bad for your hair type
    - Porosity-specific notes (if applicable)
    - Safety information and warnings
    """
    try:
        # Get database session using context manager
        db_gen = get_db()
        db: Session = next(db_gen)

        try:
            # Normalize ingredient name (case-insensitive, trim whitespace)
            normalized_name = ingredient_name.strip()

            # Try exact match first
            ingredient = (
                db.query(IngredientModel)
                .filter(func.lower(IngredientModel.name) == func.lower(normalized_name))
                .first()
            )

            # If not found, try INCI name
            if not ingredient:
                ingredient = (
                    db.query(IngredientModel)
                    .filter(func.lower(IngredientModel.inci_name) == func.lower(normalized_name))
                    .first()
                )

            # If still not found, check common names (JSON search)
            if not ingredient:
                # PostgreSQL JSON contains search
                ingredient = (
                    db.query(IngredientModel)
                    .filter(func.lower(IngredientModel.common_names.cast(str)).contains(normalized_name.lower()))
                    .first()
                )

            if not ingredient:
                logger.warning(f"Ingredient not found: {ingredient_name}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Ingredient '{ingredient_name}' not found in database. Try searching or check spelling.",
                )

            # Build porosity-specific notes
            porosity_notes = {}
            if ingredient.porosity_adjustments:
                for poro_level, adjustment in ingredient.porosity_adjustments.items():
                    if adjustment > 5:
                        porosity_notes[poro_level] = (
                            f"Excellent for {poro_level.lower()} porosity (+{adjustment} score bonus)"
                        )
                    elif adjustment > 0:
                        porosity_notes[poro_level] = f"Good for {poro_level.lower()} porosity (+{adjustment} bonus)"
                    elif adjustment < -5:
                        porosity_notes[poro_level] = (
                            f"Not recommended for {poro_level.lower()} porosity ({adjustment} penalty)"
                        )
                    elif adjustment < 0:
                        porosity_notes[poro_level] = f"Use caution with {poro_level.lower()} porosity ({adjustment})"
                    else:
                        porosity_notes[poro_level] = f"Neutral for {poro_level.lower()} porosity"

            # Build "best for" list based on curl pattern adjustments
            best_for = []
            if ingredient.curl_pattern_adjustments:
                for curl_type, adjustment in ingredient.curl_pattern_adjustments.items():
                    if adjustment > 5:
                        best_for.append(curl_type)

            # Build "avoid if" list
            avoid_if = []
            if ingredient.base_score < -20:
                avoid_if.append("Generally avoid - high risk")
            if ingredient.safety_level in ["Avoid", "Dangerous"]:
                avoid_if.append(f"Safety concern: {ingredient.safety_level}")

            # Add specific warnings based on effects
            if ingredient.effects:
                if "Drying" in ingredient.effects:
                    avoid_if.append("High porosity hair (very drying)")
                if "Protein" in ingredient.effects:
                    avoid_if.append("Protein sensitivity")
                if "Build-up" in ingredient.effects:
                    avoid_if.append("Fine hair or low-porosity (causes build-up)")

            # Determine rinse-off vs leave-in guidance
            rinse_off_guidance = None
            if ingredient.category in ["Sulfate", "Surfactant"]:
                rinse_off_guidance = "Best in rinse-off products (shampoos). Avoid in leave-ins."
            elif ingredient.category == "Silicone" and "Non-volatile" in str(ingredient.subcategory):
                rinse_off_guidance = "Can cause build-up in leave-ins. Use clarifying shampoo periodically."
            elif ingredient.category == "Alcohol" and "Drying" in str(ingredient.subcategory):
                rinse_off_guidance = "Acceptable in rinse-off products. Avoid in leave-ins."

            logger.info(f"✅ Ingredient explainer: {ingredient.name} (score: {ingredient.base_score})")

            return IngredientExplanation(
                name=ingredient.name,
                inci_name=ingredient.inci_name,
                common_names=ingredient.common_names or [],
                category=ingredient.category,
                safety_level=ingredient.safety_level,
                base_score=ingredient.base_score,
                description=ingredient.description or "No description available.",
                why_good=ingredient.why_good,
                why_bad=ingredient.why_bad,
                best_for=best_for,
                avoid_if=avoid_if,
                porosity_notes=porosity_notes,
                function=ingredient.function,
                rinse_off_vs_leave_in=rinse_off_guidance,
                fda_status=ingredient.fda_status,
                eu_status=ingredient.eu_status,
                research_links=ingredient.research_links or [],
            )

        finally:
            # Close database session
            try:
                next(db_gen)
            except StopIteration:
                pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting ingredient explainer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve ingredient information",
        ) from None


@router.get("", response_model=list[IngredientSearchResult])
async def search_ingredients(
    query: str = Query(..., min_length=2, description="Search query (ingredient name)"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
):
    """Search for ingredients by name.

    **Use case:** Autocomplete/search when user types ingredient name.

    **Example:**
    ```
    GET /api/v1/ingredients?query=alcohol&limit=10
    ```
    """
    try:
        db_gen = get_db()
        db: Session = next(db_gen)

        try:
            # Case-insensitive search across name, INCI name, and common names
            search_pattern = f"%{query.lower()}%"

            results = (
                db.query(IngredientModel)
                .filter(
                    (func.lower(IngredientModel.name).like(search_pattern))
                    | (func.lower(IngredientModel.inci_name).like(search_pattern)),
                )
                .order_by(IngredientModel.name)
                .limit(limit)
                .all()
            )

            if not results:
                logger.info(f"No ingredients found for query: {query}")
                return []

            logger.info(f"✅ Found {len(results)} ingredients for query: {query}")

            return [
                IngredientSearchResult(
                    name=ing.name,
                    category=ing.category,
                    safety_level=ing.safety_level,
                    base_score=ing.base_score,
                    description_preview=(
                        ing.description[:150] + "..."
                        if ing.description and len(ing.description) > 150
                        else (ing.description or "No description")
                    ),
                )
                for ing in results
            ]

        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f"❌ Error searching ingredients: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search ingredients",
        ) from None
