# data_models/api.py

from pydantic import BaseModel

from .recall import RecallRecord


class CheckProductRequest(BaseModel):
    upc: str | None = None
    image_url: str | None = None
    country: str


class CheckProductResponse(BaseModel):
    product_name: str
    recalls: list[RecallRecord]
    risk_summary: str | None = None
