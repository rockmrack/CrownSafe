
from pydantic import BaseModel, Field


class AlternativeItem(BaseModel):
    id: str
    name: str
    brand: str | None = None
    category: str | None = None
    reason: str  # why safer/better (plain language)
    tags: list[str] = Field(default_factory=list)  # e.g. ["pasteurised","peanut-free","flat-sleep"]
    pregnancy_safe: bool | None = None
    allergy_safe_for: list[str] = Field(default_factory=list)  # subset of user allergies
    age_min_months: int | None = None
    link_url: str | None = None  # product page or gov list (optional)
    evidence: list[dict] = Field(default_factory=list)  # EvidenceItem dicts


class AlternativesOut(BaseModel):
    schema: str = "AlternativesOut@v1"
    items: list[AlternativeItem] = Field(default_factory=list)
