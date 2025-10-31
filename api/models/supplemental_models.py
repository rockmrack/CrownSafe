"""
Pydantic models for supplemental data and enhanced safety reports
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class NutritionalInfo(BaseModel):
    """Nutritional information model"""

    calories: float | None = None
    protein: float | None = None
    carbohydrates: float | None = None
    fat: float | None = None
    fiber: float | None = None
    sugar: float | None = None
    sodium: float | None = None
    cholesterol: float | None = None
    vitamins: dict[str, float] = Field(default_factory=dict)
    minerals: dict[str, float] = Field(default_factory=dict)


class FoodDataResponse(BaseModel):
    """Food data response model"""

    fdc_id: str | None = None
    name: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    nutritional_info: NutritionalInfo | None = None
    safety_score: float | None = None
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CosmeticIngredient(BaseModel):
    """Cosmetic ingredient model"""

    name: str
    cas_number: str | None = None
    functions: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    safety_assessment: str | None = None


class CosmeticDataResponse(BaseModel):
    """Cosmetic data response model"""

    product_name: str | None = None
    ingredients: list[CosmeticIngredient] = Field(default_factory=list)
    regulatory_status: dict[str, str] = Field(default_factory=dict)
    safety_concerns: list[str] = Field(default_factory=list)
    safety_score: float | None = None
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChemicalSafetyLimits(BaseModel):
    """Chemical safety limits model"""

    osha_pel: str | None = None  # Permissible Exposure Limit
    acgih_tlv: str | None = None  # Threshold Limit Value
    niosh_rel: str | None = None  # Recommended Exposure Limit
    idlh: str | None = None  # Immediately Dangerous to Life or Health


class ChemicalDataResponse(BaseModel):
    """Chemical data response model"""

    chemical_name: str | None = None
    cas_number: str | None = None
    safety_limits: ChemicalSafetyLimits | None = None
    health_effects: list[str] = Field(default_factory=list)
    exposure_guidelines: dict[str, str] = Field(default_factory=dict)
    safety_score: float | None = None
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnhancedSafetyReport(BaseModel):
    """Enhanced safety report combining recall and supplemental data"""

    product_identifier: str
    product_name: str | None = None
    product_type: str = "unknown"  # "food", "cosmetic", "chemical", "unknown"

    # Recall data
    recall_status: str = "no_recalls"
    recall_count: int = 0
    recent_recalls: list[dict[str, Any]] = Field(default_factory=list)

    # Supplemental data
    food_data: FoodDataResponse | None = None
    cosmetic_data: CosmeticDataResponse | None = None
    chemical_data: ChemicalDataResponse | None = None

    # Overall assessment
    overall_safety_score: float = 0.5
    safety_recommendations: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)

    # Metadata
    data_sources: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_level: float = 0.5


class SupplementalDataRequest(BaseModel):
    """Request model for supplemental data"""

    product_identifier: str
    product_name: str | None = None
    product_type: str | None = None  # "food", "cosmetic", "chemical"
    include_food_data: bool = True
    include_cosmetic_data: bool = True
    include_chemical_data: bool = True


class SupplementalDataResponse(BaseModel):
    """Response model for supplemental data"""

    success: bool
    data: EnhancedSafetyReport | None = None
    message: str | None = None
    error: str | None = None
    processing_time_ms: int | None = None
