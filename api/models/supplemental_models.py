"""
Pydantic models for supplemental data and enhanced safety reports
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class NutritionalInfo(BaseModel):
    """Nutritional information model"""
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    cholesterol: Optional[float] = None
    vitamins: Dict[str, float] = Field(default_factory=dict)
    minerals: Dict[str, float] = Field(default_factory=dict)

class FoodDataResponse(BaseModel):
    """Food data response model"""
    fdc_id: Optional[str] = None
    name: Optional[str] = None
    ingredients: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)
    nutritional_info: Optional[NutritionalInfo] = None
    safety_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class CosmeticIngredient(BaseModel):
    """Cosmetic ingredient model"""
    name: str
    cas_number: Optional[str] = None
    functions: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)
    safety_assessment: Optional[str] = None

class CosmeticDataResponse(BaseModel):
    """Cosmetic data response model"""
    product_name: Optional[str] = None
    ingredients: List[CosmeticIngredient] = Field(default_factory=list)
    regulatory_status: Dict[str, str] = Field(default_factory=dict)
    safety_concerns: List[str] = Field(default_factory=list)
    safety_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class ChemicalSafetyLimits(BaseModel):
    """Chemical safety limits model"""
    osha_pel: Optional[str] = None  # Permissible Exposure Limit
    acgih_tlv: Optional[str] = None  # Threshold Limit Value
    niosh_rel: Optional[str] = None  # Recommended Exposure Limit
    idlh: Optional[str] = None  # Immediately Dangerous to Life or Health

class ChemicalDataResponse(BaseModel):
    """Chemical data response model"""
    chemical_name: Optional[str] = None
    cas_number: Optional[str] = None
    safety_limits: Optional[ChemicalSafetyLimits] = None
    health_effects: List[str] = Field(default_factory=list)
    exposure_guidelines: Dict[str, str] = Field(default_factory=dict)
    safety_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source: str = "unknown"
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class EnhancedSafetyReport(BaseModel):
    """Enhanced safety report combining recall and supplemental data"""
    product_identifier: str
    product_name: Optional[str] = None
    product_type: str  # "food", "cosmetic", "chemical", "unknown"
    
    # Recall data
    recall_status: str = "no_recalls"
    recall_count: int = 0
    recent_recalls: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Supplemental data
    food_data: Optional[FoodDataResponse] = None
    cosmetic_data: Optional[CosmeticDataResponse] = None
    chemical_data: Optional[ChemicalDataResponse] = None
    
    # Overall assessment
    overall_safety_score: float = Field(0.5, ge=0.0, le=1.0)
    safety_recommendations: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    
    # Metadata
    data_sources: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    confidence_level: float = Field(0.5, ge=0.0, le=1.0)

class SupplementalDataRequest(BaseModel):
    """Request model for supplemental data"""
    product_identifier: str
    product_name: Optional[str] = None
    product_type: Optional[str] = None  # "food", "cosmetic", "chemical"
    include_food_data: bool = True
    include_cosmetic_data: bool = True
    include_chemical_data: bool = True

class SupplementalDataResponse(BaseModel):
    """Response model for supplemental data"""
    success: bool
    data: Optional[EnhancedSafetyReport] = None
    message: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: Optional[int] = None
