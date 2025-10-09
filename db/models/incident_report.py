"""
Incident Report Model for Crowdsourced Safety Reporting
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    JSON,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core_infra.database import Base


class IncidentType(enum.Enum):
    """Types of safety incidents"""

    INJURY = "injury"
    CHOKING_HAZARD = "choking_hazard"
    SHARP_EDGES = "sharp_edges"
    TOXIC_MATERIAL = "toxic_material"
    STRUCTURAL_FAILURE = "structural_failure"
    BURN_HAZARD = "burn_hazard"
    STRANGULATION = "strangulation"
    SUFFOCATION = "suffocation"
    ALLERGIC_REACTION = "allergic_reaction"
    OTHER = "other"


class SeverityLevel(enum.Enum):
    """Severity levels for incidents"""

    MINOR = "minor"  # No medical attention needed
    MODERATE = "moderate"  # First aid or doctor visit
    SEVERE = "severe"  # Emergency room visit
    CRITICAL = "critical"  # Hospitalization or death


class IncidentStatus(enum.Enum):
    """Status of incident report"""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    FORWARDED_TO_AGENCY = "forwarded_to_agency"
    RESOLVED = "resolved"
    DUPLICATE = "duplicate"


class IncidentReport(Base):
    """User-submitted incident reports for unsafe products"""

    __tablename__ = "incident_reports"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # User information (optional for anonymous reports)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reporter_email = Column(String, nullable=True)  # For anonymous reports
    reporter_phone = Column(String, nullable=True)

    # Product information
    product_name = Column(String, nullable=False, index=True)
    brand_name = Column(String, nullable=True, index=True)
    model_number = Column(String, nullable=True)
    barcode = Column(String, nullable=True, index=True)
    purchase_date = Column(DateTime, nullable=True)
    purchase_location = Column(String, nullable=True)

    # Incident details
    incident_type = Column(Enum(IncidentType), nullable=False, index=True)
    incident_date = Column(DateTime, nullable=False)
    incident_description = Column(Text, nullable=False)
    injury_description = Column(Text, nullable=True)

    # Severity and impact
    severity_level = Column(Enum(SeverityLevel), nullable=False, index=True)
    medical_attention_required = Column(Boolean, default=False)
    hospital_visit = Column(Boolean, default=False)
    child_age_months = Column(Integer, nullable=True)  # Age of affected child

    # Supporting evidence
    photo_urls = Column(JSON, nullable=True)  # List of S3 URLs
    video_url = Column(String, nullable=True)
    receipt_url = Column(String, nullable=True)

    # Reporting details
    reported_to_manufacturer = Column(Boolean, default=False)
    manufacturer_response = Column(Text, nullable=True)
    reported_to_store = Column(Boolean, default=False)
    store_response = Column(Text, nullable=True)

    # Processing status
    status = Column(Enum(IncidentStatus), default=IncidentStatus.SUBMITTED, index=True)
    review_notes = Column(Text, nullable=True)
    reviewer_id = Column(Integer, nullable=True)

    # Agency forwarding
    forwarded_to_cpsc = Column(Boolean, default=False)
    cpsc_case_number = Column(String, nullable=True)
    forwarded_to_fda = Column(Boolean, default=False)
    fda_case_number = Column(String, nullable=True)

    # Clustering and pattern detection
    cluster_id = Column(String, nullable=True, index=True)  # For grouping similar incidents
    similarity_score = Column(Float, nullable=True)  # Confidence in cluster assignment

    # Metadata
    submission_ip = Column(String, nullable=True)
    submission_user_agent = Column(String, nullable=True)
    language = Column(String, default="en")
    country = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    forwarded_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="incident_reports", foreign_keys=[user_id])


class IncidentCluster(Base):
    """Groups of similar incidents for pattern detection"""

    __tablename__ = "incident_clusters"

    id = Column(String, primary_key=True)  # Cluster ID
    product_name = Column(String, nullable=False, index=True)
    brand_name = Column(String, nullable=True)
    incident_type = Column(Enum(IncidentType), nullable=False)

    # Statistics
    incident_count = Column(Integer, default=1)
    severity_distribution = Column(JSON)  # {"minor": 2, "moderate": 3, "severe": 1}
    first_incident_date = Column(DateTime)
    last_incident_date = Column(DateTime)

    # Alert thresholds
    alert_triggered = Column(Boolean, default=False)
    alert_triggered_at = Column(DateTime, nullable=True)
    cpsc_notified = Column(Boolean, default=False)
    cpsc_notified_at = Column(DateTime, nullable=True)

    # Analysis
    risk_score = Column(Float)  # Calculated based on frequency and severity
    trending = Column(Boolean, default=False)  # Rapid increase in reports

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgencyNotification(Base):
    """Track notifications sent to regulatory agencies"""

    __tablename__ = "agency_notifications"

    id = Column(Integer, primary_key=True)
    agency = Column(String, nullable=False)  # CPSC, FDA, etc.
    cluster_id = Column(String, ForeignKey("incident_clusters.id"))

    # Notification details
    notification_type = Column(String)  # "threshold_alert", "trending_alert", "severity_alert"
    incident_count = Column(Integer)
    severity_summary = Column(JSON)

    # Communication
    sent_at = Column(DateTime, default=datetime.utcnow)
    sent_via = Column(String)  # "api", "email", "portal"
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime, nullable=True)
    agency_case_number = Column(String, nullable=True)

    # Metadata
    notification_data = Column(JSON)  # Full notification payload
    created_at = Column(DateTime, default=datetime.utcnow)
