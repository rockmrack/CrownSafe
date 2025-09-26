from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class PregnancyCheckIn(BaseModel):
    schema: str = "PregnancyCheck@v1"
    product_name: Optional[str] = None
    category: Optional[str] = None
    ingredients: List[str] = Field(default_factory=list)
    flags: List[str] = Field(default_factory=list)
    jurisdiction: Optional[dict] = None

class RiskItem(BaseModel):
    code: str           # e.g., "soft_cheese_pasteurisation", "unpasteurised_dairy"
    reason: str         # short human reason
    severity: str       # "low"|"moderate"|"high"

class PregnancyCheckOut(BaseModel):
    schema: str = "PregnancyCheckOut@v1"
    risks: List[RiskItem] = Field(default_factory=list)
    notes: Optional[str] = None

class AllergyCheckIn(BaseModel):
    schema: str = "AllergyCheck@v1"
    ingredients: List[str] = Field(default_factory=list)
    profile_allergies: List[str] = Field(default_factory=list)
    product_name: Optional[str] = None

class AllergyHit(BaseModel):
    allergen: str
    present: bool
    evidence: Optional[str] = None  # e.g., "ingredient_list", "may_contains_label"

class AllergyCheckOut(BaseModel):
    schema: str = "AllergyCheckOut@v1"
    hits: List[AllergyHit] = Field(default_factory=list)
    summary: Optional[str] = None


class RecallDetailsIn(BaseModel):
    schema: str = "RecallDetails@v1"
    product_name: Optional[str] = None
    model_number: Optional[str] = None
    brand: Optional[str] = None
    gtin: Optional[str] = None
    jurisdiction: Optional[dict] = None


class RecallRecord(BaseModel):
    id: str
    agency: str        # "CPSC" | "FDA" | "EU Safety Gate" | ...
    date: str          # ISO
    url: Optional[str] = None
    title: Optional[str] = None
    hazard: Optional[str] = None


class RecallDetailsOut(BaseModel):
    schema: str = "RecallDetailsOut@v1"
    recalls: List[RecallRecord] = Field(default_factory=list)
    recalls_found: int = 0
    batch_check: Optional[str] = "Verify batch/lot and date codes on the label."


class IngredientInfoIn(BaseModel):
    schema: str = "IngredientInfo@v1"
    ingredients: List[str] = Field(default_factory=list)
    product_name: Optional[str] = None
    category: Optional[str] = None


class IngredientInfoOut(BaseModel):
    schema: str = "IngredientInfoOut@v1"
    ingredients: List[str] = Field(default_factory=list)
    highlighted: List[str] = Field(default_factory=list)  # e.g., "fragrance", "retinol"
    notes: Optional[str] = None


class AgeCheckIn(BaseModel):
    schema: str = "AgeCheck@v1"
    category: Optional[str] = None
    min_age_months: Optional[int] = None
    flags: List[str] = Field(default_factory=list)


class AgeCheckOut(BaseModel):
    schema: str = "AgeCheckOut@v1"
    age_ok: Optional[bool] = None
    min_age_months: Optional[int] = None
    reasons: List[str] = Field(default_factory=list)
