"""
Pydantic schemas for user report endpoints
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ReportUnsafeProductRequest(BaseModel):
    """Request schema for reporting unsafe products"""

    user_id: int = Field(..., description="ID of the user submitting the report")
    product_name: str = Field(..., min_length=3, max_length=255, description="Name of the unsafe product")
    hazard_description: str = Field(..., min_length=10, description="Detailed description of the hazard")

    # Optional product identifiers
    barcode: Optional[str] = Field(None, max_length=50, description="Product barcode/UPC")
    model_number: Optional[str] = Field(None, max_length=100, description="Model number")
    lot_number: Optional[str] = Field(None, max_length=100, description="Lot/batch number")
    brand: Optional[str] = Field(None, max_length=100, description="Product brand")
    manufacturer: Optional[str] = Field(None, max_length=200, description="Manufacturer name")

    # Classification
    severity: str = Field(
        default="MEDIUM",
        description="Hazard severity level",
        pattern="^(HIGH|MEDIUM|LOW)$",
    )
    category: Optional[str] = Field(None, max_length=100, description="Product category")

    # Reporter information (optional, for follow-up)
    reporter_name: Optional[str] = Field(None, max_length=100, description="Reporter's name")
    reporter_email: Optional[str] = Field(None, max_length=255, description="Reporter's email")
    reporter_phone: Optional[str] = Field(None, max_length=50, description="Reporter's phone")

    # Incident details
    incident_date: Optional[date] = Field(None, description="Date of the incident")
    incident_description: Optional[str] = Field(None, description="Detailed description of what happened")

    # Evidence
    photos: Optional[List[str]] = Field(None, description="Array of photo URLs or base64 encoded images")

    @field_validator("photos")
    @classmethod
    def validate_photos(cls, v):
        """Limit number of photos"""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 photos allowed per report")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 12345,
                "product_name": "Baby Dream Crib Model XL-2000",
                "hazard_description": "Mattress support collapsed causing baby to fall",
                "barcode": "0123456789012",
                "model_number": "XL-2000",
                "brand": "Baby Dream",
                "manufacturer": "Dream Products Inc.",
                "severity": "HIGH",
                "category": "Cribs",
                "incident_date": "2025-10-01",
                "incident_description": "The crib mattress support suddenly collapsed...",
                "reporter_email": "concerned.parent@example.com",
            }
        }


class ReportUnsafeProductResponse(BaseModel):
    """Response schema for successful report submission"""

    report_id: int = Field(..., description="Unique ID of the created report")
    status: str = Field(default="PENDING", description="Current status of the report")
    message: str = Field(..., description="Confirmation message")
    created_at: datetime = Field(..., description="Timestamp when report was created")

    class Config:
        json_schema_extra = {
            "example": {
                "report_id": 1001,
                "status": "PENDING",
                "message": (
                    "Thank you for reporting this unsafe product. "
                    "Our safety team will review your report within 24-48 hours."
                ),
                "created_at": "2025-10-11T14:30:00Z",
            }
        }


class UserReportDetail(BaseModel):
    """Detailed view of a user report (for admin/review)"""

    report_id: int
    user_id: int
    product_name: str
    hazard_description: str
    barcode: Optional[str] = None
    model_number: Optional[str] = None
    lot_number: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    severity: str
    category: Optional[str] = None
    status: str
    reporter_name: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_phone: Optional[str] = None
    incident_date: Optional[date] = None
    incident_description: Optional[str] = None
    photos: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateReportStatusRequest(BaseModel):
    """Request schema for updating report status (admin only)"""

    status: str = Field(
        ...,
        description="New status",
        pattern="^(PENDING|REVIEWING|VERIFIED|REJECTED|DUPLICATE)$",
    )
    review_notes: Optional[str] = Field(None, description="Admin notes about the review")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "VERIFIED",
                "review_notes": "Confirmed with manufacturer. Product added to recall database.",
            }
        }
