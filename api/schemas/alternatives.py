from pydantic import BaseModel, Field
from typing import List, Optional


class AlternativeItem(BaseModel):
    id: str
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    reason: str  # why safer/better (plain language)
    tags: List[str] = Field(
        default_factory=list
    )  # e.g. ["pasteurised","peanut-free","flat-sleep"]
    pregnancy_safe: Optional[bool] = None
    allergy_safe_for: List[str] = Field(
        default_factory=list
    )  # subset of user allergies
    age_min_months: Optional[int] = None
    link_url: Optional[str] = None  # product page or gov list (optional)
    evidence: List[dict] = Field(default_factory=list)  # EvidenceItem dicts


class AlternativesOut(BaseModel):
    schema: str = "AlternativesOut@v1"
    items: List[AlternativeItem] = Field(default_factory=list)
