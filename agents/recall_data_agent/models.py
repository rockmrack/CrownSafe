# agents/recall_data_agent/models.py
"""
Pydantic models for recall data validation and structure.
Compatible with BabyShield EnhancedRecallDB schema.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import date


class Recall(BaseModel):
    """
    Pydantic model for validating and structuring recall data.
    Matches EnhancedRecallDB schema from core_infra/enhanced_database_schema.py
    """

    # Primary identifiers
    recall_id: str = Field(..., description="Unique recall identifier")
    product_name: str = Field(..., description="Product name")

    # Product identifiers
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None

    # Retail identifiers (barcodes)
    upc: Optional[str] = None
    ean_code: Optional[str] = None
    gtin: Optional[str] = None
    article_number: Optional[str] = None

    # Batch/lot identifiers
    lot_number: Optional[str] = None
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    part_number: Optional[str] = None

    # Date identifiers
    recall_date: date = Field(..., description="Date of recall")
    expiry_date: Optional[date] = None
    best_before_date: Optional[date] = None
    production_date: Optional[date] = None

    # Pharmaceutical identifiers
    ndc_number: Optional[str] = None
    din_number: Optional[str] = None

    # Vehicle identifiers
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    model_year: Optional[str] = None
    vin_range: Optional[str] = None

    # Regional/distribution
    country: Optional[str] = None
    regions_affected: Optional[List[str]] = None
    registry_codes: Optional[Dict[str, str]] = None

    # Recall metadata
    source_agency: Optional[str] = None
    hazard: Optional[str] = None
    hazard_category: Optional[str] = None
    severity: Optional[str] = None
    risk_category: Optional[str] = None
    recall_reason: Optional[str] = None
    remedy: Optional[str] = None
    recall_class: Optional[str] = None

    # Descriptive fields
    description: Optional[str] = None
    manufacturer_contact: Optional[str] = None
    url: Optional[str] = None

    # Search optimization
    search_keywords: Optional[str] = None
    agency_specific_data: Optional[Dict[str, Any]] = None

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

    product_name: Optional[str] = None
    model_number: Optional[str] = None
    upc: Optional[str] = None
    brand: Optional[str] = None
    lot_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class RecallQueryResponse(BaseModel):
    """Response model for recall queries"""

    status: str
    recalls_found: int
    recalls: List[Recall]
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
