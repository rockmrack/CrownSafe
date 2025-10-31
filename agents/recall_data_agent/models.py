# agents/recall_data_agent/models.py
"""
Pydantic models for recall data validation and structure.
Compatible with BabyShield EnhancedRecallDB schema.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Recall(BaseModel):
    """
    Pydantic model for validating and structuring recall data.
    Matches EnhancedRecallDB schema from core_infra/enhanced_database_schema.py
    """

    # Primary identifiers
    recall_id: str = Field(..., description="Unique recall identifier")
    product_name: str = Field(..., description="Product name")

    # Product identifiers
    brand: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None

    # Retail identifiers (barcodes)
    upc: str | None = None
    ean_code: str | None = None
    gtin: str | None = None
    article_number: str | None = None

    # Batch/lot identifiers
    lot_number: str | None = None
    batch_number: str | None = None
    serial_number: str | None = None
    part_number: str | None = None

    # Date identifiers
    recall_date: date = Field(..., description="Date of recall")
    expiry_date: date | None = None
    best_before_date: date | None = None
    production_date: date | None = None

    # Pharmaceutical identifiers
    ndc_number: str | None = None
    din_number: str | None = None

    # Vehicle identifiers
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    model_year: str | None = None
    vin_range: str | None = None

    # Regional/distribution
    country: str | None = None
    regions_affected: list[str] | None = None
    registry_codes: dict[str, str] | None = None

    # Recall metadata
    source_agency: str | None = None
    hazard: str | None = None
    hazard_category: str | None = None
    severity: str | None = None
    risk_category: str | None = None
    recall_reason: str | None = None
    remedy: str | None = None
    recall_class: str | None = None

    # Descriptive fields
    description: str | None = None
    manufacturer_contact: str | None = None
    url: str | None = None

    # Search optimization
    search_keywords: str | None = None
    agency_specific_data: dict[str, Any] | None = None

    # Pydantic v2 configuration
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    def to_db_dict(self) -> dict:
        """Convert to dictionary for database insertion"""
        data = self.model_dump()
        # Ensure date fields are properly formatted
        if isinstance(data.get("recall_date"), date):
            data["recall_date"] = data["recall_date"].isoformat()
        for date_field in ["expiry_date", "best_before_date", "production_date"]:
            if data.get(date_field) and isinstance(data[date_field], date):
                data[date_field] = data[date_field].isoformat()
        return data


class RecallQueryRequest(BaseModel):
    """Request model for recall queries"""

    product_name: str | None = None
    model_number: str | None = None
    upc: str | None = None
    brand: str | None = None
    lot_number: str | None = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RecallQueryResponse(BaseModel):
    """Response model for recall queries"""

    status: str
    recalls_found: int
    recalls: list[Recall]
    error: str | None = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
