"""
Database models for Proactive Consumer Product Safety Risk Assessment Framework
Implements golden records, risk profiles, and data source tracking
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

# Import Base from the main database module to maintain a single declarative base
from core_infra.database import Base


class DataSource(Enum):
    """Data source types"""

    CPSC_RECALL = "cpsc_recall"
    CPSC_NEISS = "cpsc_neiss"
    CPSC_VIOLATION = "cpsc_violation"
    CPSC_PENALTY = "cpsc_penalty"
    EU_SAFETY_GATE = "eu_safety_gate"
    COMMERCIAL_DB = "commercial_db"
    INTERNAL_PIM = "internal_pim"
    USER_REPORT = "user_report"
    AI_EXTRACTION = "ai_extraction"


class RiskSeverity(Enum):
    """Risk severity levels aligned with FDA/CPSC classifications"""

    CLASS_I = "class_i"  # Serious health hazard or death
    CLASS_II = "class_ii"  # Temporary health problem or slight threat
    CLASS_III = "class_iii"  # Unlikely to cause adverse health consequences
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProductGoldenRecord(Base):
    """
    Unified product record - the single source of truth
    Consolidates data from all sources through entity resolution
    """

    __tablename__ = "product_golden_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Primary identifiers
    gtin = Column(String(14), index=True)  # Global Trade Item Number
    upc = Column(String(12), index=True)
    ean = Column(String(13), index=True)
    asin = Column(String(10))  # Amazon Standard Identification Number

    # Product details
    product_name = Column(String(500), nullable=False)
    brand = Column(String(200), index=True)
    manufacturer = Column(String(200), index=True)
    model_number = Column(String(200))
    product_category = Column(String(200))
    product_subcategory = Column(String(200))

    # Additional identifiers
    serial_numbers = Column(JSON)  # Array of known serial numbers
    lot_numbers = Column(JSON)  # Array of known lot numbers
    batch_codes = Column(JSON)  # Array of batch codes

    # Product attributes
    description = Column(Text)
    country_of_origin = Column(String(100))
    manufacturing_date_range = Column(JSON)  # {"start": "2020-01-01", "end": "2023-12-31"}

    # Digital assets
    primary_image_url = Column(String(500))
    additional_images = Column(JSON)  # Array of image URLs
    qr_code_data = Column(JSON)

    # Compliance and certification
    certifications = Column(JSON)  # ["CE", "CPSC", "ASTM"]
    safety_standards = Column(JSON)  # Standards this product should meet
    age_grading = Column(String(50))  # "3+ years", "0-12 months"

    # Entity resolution metadata
    confidence_score = Column(Float, default=0.0)  # How confident we are this is accurate
    source_records = Column(JSON)  # Array of source record IDs that were merged
    resolution_method = Column(String(50))  # "exact_match", "fuzzy_match", "ml_model"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_verified = Column(DateTime)

    # Relationships
    risk_profile = relationship("ProductRiskProfile", back_populates="product", uselist=False)
    data_sources = relationship("ProductDataSource", back_populates="product")
    incidents = relationship("SafetyIncident", back_populates="product")

    # Indexes for performance
    __table_args__ = (
        Index("idx_product_identifiers", "gtin", "upc", "ean"),
        Index("idx_product_search", "product_name", "brand", "manufacturer"),
    )


class ProductRiskProfile(Base):
    """
    Dynamic risk assessment profile for each product
    Continuously updated based on new data
    """

    __tablename__ = "product_risk_profiles"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(36), ForeignKey("product_golden_records.id"), unique=True)

    # Overall risk score (0-100)
    risk_score = Column(Float, default=0.0, index=True)
    risk_level = Column(String(20))  # "low", "medium", "high", "critical"

    # Component scores (weighted factors)
    severity_score = Column(Float, default=0.0)  # Weight: 35%
    recency_score = Column(Float, default=0.0)  # Weight: 20%
    volume_score = Column(Float, default=0.0)  # Weight: 15%
    violation_score = Column(Float, default=0.0)  # Weight: 15%
    compliance_score = Column(Float, default=0.0)  # Weight: 15%

    # Detailed metrics
    total_recalls = Column(Integer, default=0)
    total_incidents = Column(Integer, default=0)
    total_injuries = Column(Integer, default=0)
    total_deaths = Column(Integer, default=0)
    units_affected = Column(Integer, default=0)

    # Recent activity (last 12 months)
    recent_recalls = Column(Integer, default=0)
    recent_incidents = Column(Integer, default=0)
    recent_violations = Column(Integer, default=0)

    # Risk factors
    active_recalls = Column(JSON)  # Current active recalls
    hazard_types = Column(JSON)  # ["choking", "fire", "chemical"]
    affected_demographics = Column(JSON)  # ["infants", "toddlers"]

    # Trend analysis
    risk_trend = Column(String(20))  # "increasing", "stable", "decreasing"
    trend_data = Column(JSON)  # Historical risk scores

    # Calculation metadata
    last_calculated = Column(DateTime)
    calculation_version = Column(String(20))
    calculation_details = Column(JSON)  # Detailed breakdown of score calculation

    # Alerts and flags
    requires_review = Column(Boolean, default=False)
    review_reason = Column(Text)
    alert_level = Column(String(20))  # "none", "low", "medium", "high", "critical"

    # Relationship
    product = relationship("ProductGoldenRecord", back_populates="risk_profile")


class ProductDataSource(Base):
    """
    Tracks all data sources for a product
    Maintains provenance and update history
    """

    __tablename__ = "product_data_sources"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(36), ForeignKey("product_golden_records.id"))

    # Source information
    source_type = Column(String(50))  # DataSource enum value
    source_name = Column(String(200))
    source_id = Column(String(200))  # ID in the source system
    source_url = Column(String(500))

    # Data snapshot
    raw_data = Column(JSON)  # Original data from source
    processed_data = Column(JSON)  # Normalized data

    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    data_version = Column(String(50))

    # Quality metrics
    data_quality_score = Column(Float)
    completeness_score = Column(Float)

    # Relationship
    product = relationship("ProductGoldenRecord", back_populates="data_sources")

    # Unique constraint to prevent duplicates
    __table_args__ = (UniqueConstraint("product_id", "source_type", "source_id", name="uq_product_source"),)


class SafetyIncident(Base):
    """
    Individual safety incidents linked to products
    From CPSC NEISS, Clearinghouse, EU Safety Gate, etc.
    """

    __tablename__ = "safety_incidents"

    id = Column(Integer, primary_key=True)
    product_id = Column(String(36), ForeignKey("product_golden_records.id"))

    # Incident details
    incident_date = Column(DateTime)
    report_date = Column(DateTime)
    source = Column(String(50))  # "NEISS", "Clearinghouse", "EU_Safety_Gate"
    source_id = Column(String(100))

    # Incident type and severity
    incident_type = Column(String(100))  # "injury", "death", "near_miss"
    hazard_type = Column(String(100))  # "choking", "burn", "laceration"
    severity = Column(String(50))  # RiskSeverity enum

    # Victim information (anonymized)
    victim_age = Column(Integer)
    victim_age_unit = Column(String(20))  # "years", "months"
    victim_gender = Column(String(10))

    # Incident description
    narrative = Column(Text)
    injury_description = Column(Text)
    body_part_affected = Column(String(100))
    disposition = Column(String(100))  # "treated_released", "hospitalized", "death"

    # Medical details
    diagnosis = Column(String(200))
    treatment = Column(Text)
    hospital_ed = Column(String(200))

    # Investigation
    investigation_status = Column(String(50))
    root_cause = Column(Text)
    corrective_action = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)

    # Relationship
    product = relationship("ProductGoldenRecord", back_populates="incidents")

    # Index for queries
    __table_args__ = (
        Index("idx_incident_date", "incident_date", "severity"),
        Index("idx_incident_type", "incident_type", "hazard_type"),
    )


class CompanyComplianceProfile(Base):
    """
    Company/manufacturer compliance history
    Used for risk scoring based on company track record
    """

    __tablename__ = "company_compliance_profiles"

    id = Column(Integer, primary_key=True)
    company_name = Column(String(200), unique=True, nullable=False)

    # Company identifiers
    alternate_names = Column(JSON)  # Array of aliases/DBAs
    ein = Column(String(20))  # Employer Identification Number
    duns = Column(String(20))  # D&B number

    # Compliance metrics
    total_recalls = Column(Integer, default=0)
    total_violations = Column(Integer, default=0)
    total_penalties = Column(Integer, default=0)
    total_penalty_amount = Column(Float, default=0.0)

    # Recent activity (12 months)
    recent_recalls = Column(Integer, default=0)
    recent_violations = Column(Integer, default=0)

    # Compliance score (0-100, higher is better)
    compliance_score = Column(Float, default=100.0)
    compliance_trend = Column(String(20))  # "improving", "stable", "declining"

    # Risk factors
    repeat_offender = Column(Boolean, default=False)
    high_risk_categories = Column(JSON)  # Product categories with issues
    common_violations = Column(JSON)  # Types of violations

    # Timestamps
    first_violation_date = Column(DateTime)
    last_violation_date = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow)


class RiskAssessmentReport(Base):
    """
    Generated risk assessment reports
    Includes all analysis, scores, and disclaimers
    """

    __tablename__ = "risk_assessment_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("product_golden_records.id"))

    # Report metadata
    report_type = Column(String(50))  # "full", "summary", "alert"
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(String(100))  # User or system that triggered
    report_version = Column(String(20))

    # Report content
    executive_summary = Column(Text)
    risk_score = Column(Float)
    risk_level = Column(String(20))

    # Detailed sections
    risk_factors = Column(JSON)  # Breakdown of all risk factors
    data_sources_summary = Column(JSON)  # Summary of data sources used
    incident_analysis = Column(JSON)  # Analysis of incidents
    compliance_analysis = Column(JSON)  # Company compliance analysis
    recommendations = Column(JSON)  # Actionable recommendations

    # Legal and compliance
    disclaimers = Column(Text)  # Legal disclaimers
    limitations = Column(Text)  # Known limitations
    data_freshness = Column(JSON)  # Age of various data sources

    # Report status
    status = Column(String(50))  # "draft", "pending_review", "approved", "published"
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    approval_notes = Column(Text)

    # Distribution
    recipients = Column(JSON)  # Who received this report
    access_log = Column(JSON)  # Who accessed and when

    # Storage
    report_url = Column(String(500))  # S3 URL for full report
    report_format = Column(String(20))  # "pdf", "html", "json"

    # Audit
    audit_trail = Column(JSON)  # All changes to the report


class DataIngestionJob(Base):
    """
    Tracks data ingestion jobs from various sources
    """

    __tablename__ = "data_ingestion_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Job details
    source_type = Column(String(50))  # DataSource enum
    job_type = Column(String(50))  # "full", "incremental", "real_time"
    status = Column(String(50))  # "queued", "running", "completed", "failed"

    # Timing
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Results
    records_fetched = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_matched = Column(Integer, default=0)
    records_created = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)

    # Error handling
    errors = Column(JSON)  # Array of errors encountered
    retry_count = Column(Integer, default=0)

    # Metadata
    configuration = Column(JSON)  # Job configuration
    checkpoint = Column(JSON)  # For resumable jobs

    # Performance
    processing_time_seconds = Column(Integer)

    # Index for queries
    __table_args__ = (Index("idx_ingestion_status", "source_type", "status", "scheduled_at"),)
