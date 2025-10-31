from __future__ import annotations

from pydantic import BaseModel, Field


class PregnancyCheckIn(BaseModel):
    schema: str = "PregnancyCheck@v1"
    product_name: str | None = None
    category: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    jurisdiction: dict | None = None


class RiskItem(BaseModel):
    code: str  # e.g., "soft_cheese_pasteurisation", "unpasteurised_dairy"
    reason: str  # short human reason
    severity: str  # "low"|"moderate"|"high"


class PregnancyCheckOut(BaseModel):
    schema: str = "PregnancyCheckOut@v1"
    risks: list[RiskItem] = Field(default_factory=list)
    notes: str | None = None


class AllergyCheckIn(BaseModel):
    schema: str = "AllergyCheck@v1"
    ingredients: list[str] = Field(default_factory=list)
    profile_allergies: list[str] = Field(default_factory=list)
    product_name: str | None = None


class AllergyHit(BaseModel):
    allergen: str
    present: bool
    evidence: str | None = None  # e.g., "ingredient_list", "may_contains_label"


class AllergyCheckOut(BaseModel):
    schema: str = "AllergyCheckOut@v1"
    hits: list[AllergyHit] = Field(default_factory=list)
    summary: str | None = None


class RecallDetailsIn(BaseModel):
    schema: str = "RecallDetails@v1"
    product_name: str | None = None
    model_number: str | None = None
    brand: str | None = None
    gtin: str | None = None
    jurisdiction: dict | None = None


class RecallRecord(BaseModel):
    id: str
    agency: str  # "CPSC" | "FDA" | "EU Safety Gate" | ...
    date: str  # ISO
    url: str | None = None
    title: str | None = None
    hazard: str | None = None


class RecallDetailsOut(BaseModel):
    schema: str = "RecallDetailsOut@v1"
    recalls: list[RecallRecord] = Field(default_factory=list)
    recalls_found: int = 0
    batch_check: str | None = "Verify batch/lot and date codes on the label."


class IngredientInfoIn(BaseModel):
    schema: str = "IngredientInfo@v1"
    ingredients: list[str] = Field(default_factory=list)
    product_name: str | None = None
    category: str | None = None


class IngredientInfoOut(BaseModel):
    schema: str = "IngredientInfoOut@v1"
    ingredients: list[str] = Field(default_factory=list)
    highlighted: list[str] = Field(default_factory=list)  # e.g., "fragrance", "retinol"
    notes: str | None = None


class AgeCheckIn(BaseModel):
    schema: str = "AgeCheck@v1"
    category: str | None = None
    min_age_months: int | None = None
    flags: list[str] = Field(default_factory=list)


class AgeCheckOut(BaseModel):
    schema: str = "AgeCheckOut@v1"
    age_ok: bool | None = None
    min_age_months: int | None = None
    reasons: list[str] = Field(default_factory=list)
