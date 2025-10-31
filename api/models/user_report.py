"""SQLAlchemy model for user_reports table"""

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from core_infra.database import Base


class UserReport(Base):
    """Model for community-reported unsafe products

    Allows users to report dangerous products that may not yet be in
    the official recall database, helping to keep the community safe.
    """

    __tablename__ = "user_reports"

    report_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    # Product Information
    product_name = Column(String(255), nullable=False)
    hazard_description = Column(Text, nullable=False)
    barcode = Column(String(50), nullable=True, index=True)
    model_number = Column(String(100), nullable=True, index=True)
    lot_number = Column(String(100), nullable=True)
    brand = Column(String(100), nullable=True)
    manufacturer = Column(String(200), nullable=True)

    # Classification
    severity = Column(String(20), nullable=False, default="MEDIUM", index=True)  # HIGH, MEDIUM, LOW
    category = Column(String(100), nullable=True)  # Crib, Toy, Bottle, etc.
    # PENDING, REVIEWING, VERIFIED, REJECTED, DUPLICATE
    status = Column(String(50), nullable=False, default="PENDING", index=True)

    # Reporter Information (optional)
    reporter_name = Column(String(100), nullable=True)
    reporter_email = Column(String(255), nullable=True)
    reporter_phone = Column(String(50), nullable=True)

    # Incident Details
    incident_date = Column(Date, nullable=True)
    incident_description = Column(Text, nullable=True)

    # Evidence
    photos = Column(JSON, nullable=True)  # Array of photo URLs
    # Additional data (renamed from 'metadata' to avoid SQLAlchemy reserved attribute)
    report_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Review Information
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, nullable=True)  # Admin user ID
    review_notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UserReport(report_id={self.report_id}, "
            f"product='{self.product_name}', "
            f"severity='{self.severity}', status='{self.status}')>"
        )

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "report_id": self.report_id,
            "user_id": self.user_id,
            "product_name": self.product_name,
            "hazard_description": self.hazard_description,
            "barcode": self.barcode,
            "model_number": self.model_number,
            "lot_number": self.lot_number,
            "brand": self.brand,
            "manufacturer": self.manufacturer,
            "severity": self.severity,
            "category": self.category,
            "status": self.status,
            "incident_date": (self.incident_date.isoformat() if self.incident_date is not None else None),
            "incident_description": self.incident_description,
            "photos": self.photos,
            "created_at": (self.created_at.isoformat() if self.created_at is not None else None),
            "updated_at": (self.updated_at.isoformat() if self.updated_at is not None else None),
            "reviewed_at": (self.reviewed_at.isoformat() if self.reviewed_at is not None else None),
        }
