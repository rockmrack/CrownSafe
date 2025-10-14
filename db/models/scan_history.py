"""
Scan History Model for tracking user product scans
Used for generating 90-day safety summaries
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from core_infra.database import Base


class ScanHistory(Base):
    """Track user scan history for safety reports"""

    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scan_id = Column(String(100), unique=True, index=True)
    scan_timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Product information
    product_name = Column(String(255))
    brand = Column(String(255))
    barcode = Column(String(100), index=True)
    model_number = Column(String(100))
    upc_gtin = Column(String(100))
    category = Column(String(100))

    # Scan details
    scan_type = Column(String(50))  # barcode, image, text, visual
    confidence_score = Column(Float)
    barcode_format = Column(String(50))

    # Safety results
    verdict = Column(String(100))  # No Recalls Found, Recall Alert, etc.
    risk_level = Column(String(50))  # low, medium, high, critical
    recalls_found = Column(Integer, default=0)
    recall_ids = Column(JSON)  # List of recall IDs if any
    agencies_checked = Column(String(100))

    # Additional safety info
    allergen_alerts = Column(JSON)
    pregnancy_warnings = Column(JSON)
    age_warnings = Column(JSON)

    # Report generation
    included_in_reports = Column(JSON)  # List of report IDs this scan is included in

    # Relationships (User model defined in core_infra.database)
    # user = relationship("User", back_populates="scan_history")

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            "scan_id": self.scan_id,
            "scan_timestamp": self.scan_timestamp.isoformat() if self.scan_timestamp else None,
            "product": {
                "name": self.product_name,
                "brand": self.brand,
                "barcode": self.barcode,
                "model_number": self.model_number,
                "category": self.category,
            },
            "safety": {
                "verdict": self.verdict,
                "risk_level": self.risk_level,
                "recalls_found": self.recalls_found,
                "recall_ids": self.recall_ids or [],
            },
            "scan_details": {
                "type": self.scan_type,
                "confidence": self.confidence_score,
                "format": self.barcode_format,
            },
        }


class SafetyReport(Base):
    """Track generated safety reports"""

    __tablename__ = "safety_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(100), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Report details
    report_type = Column(String(50))  # 90_day_summary, monthly, weekly
    generated_at = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime)
    period_end = Column(DateTime)

    # Summary statistics
    total_scans = Column(Integer, default=0)
    unique_products = Column(Integer, default=0)
    recalls_found = Column(Integer, default=0)
    high_risk_products = Column(Integer, default=0)

    # Report content
    report_data = Column(JSON)  # Detailed report data
    pdf_path = Column(String(500))
    s3_url = Column(String(500))

    # Relationships (User model defined in core_infra.database)
    # user = relationship("User", back_populates="safety_reports")
