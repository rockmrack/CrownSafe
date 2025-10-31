# data_models/api.py
from typing import List, Optional

from pydantic import BaseModel

from .recall import RecallRecord


class CheckProductRequest(BaseModel):
    upc: Optional[str] = None
    image_url: Optional[str] = None
    country: str


class CheckProductResponse(BaseModel):
    product_name: str
    recalls: List[RecallRecord]
    risk_summary: Optional[str] = None
