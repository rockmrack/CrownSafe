"""
Database models for Visual Agent - Phase 2
Includes image processing jobs, HITL review queue, and extraction results
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    JSON,
    Boolean,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid

# Import Base from the main database module
from core_infra.database import Base


class JobStatus(enum.Enum):
    """Status for image processing jobs"""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ReviewStatus(enum.Enum):
    """Status for HITL review queue"""

    QUEUED = "queued"
    CLAIMED = "claimed"
    NEEDS_MORE_INFO = "needs_more_info"
    APPROVED = "approved"
    REJECTED = "rejected"


class ConfidenceLevel(enum.Enum):
    """Confidence level categories"""

    HIGH = "high"  # >= 0.85 - Auto-accept
    MEDIUM = "medium"  # 0.60-0.84 - HITL required
    LOW = "low"  # < 0.60 - Request better image


class ImageJob(Base):
    """Image processing job tracking"""

    __tablename__ = "image_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)

    # S3/Storage info
    s3_bucket = Column(String(255))
    s3_key = Column(String(500))
    s3_presigned_url = Column(Text)  # For temporary access
    file_hash = Column(String(64), unique=True)  # SHA256 for idempotency
    file_size = Column(Integer)
    file_type = Column(String(50))

    # Processing status
    status = Column(SQLEnum(JobStatus), default=JobStatus.QUEUED, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    # Processing steps completed
    virus_scanned = Column(Boolean, default=False)
    normalized = Column(Boolean, default=False)
    barcode_extracted = Column(Boolean, default=False)
    ocr_completed = Column(Boolean, default=False)
    labels_extracted = Column(Boolean, default=False)

    # Overall confidence
    confidence_score = Column(Float, default=0.0)
    confidence_level = Column(SQLEnum(ConfidenceLevel))

    # Relationships
    extractions = relationship(
        "ImageExtraction", back_populates="job", cascade="all, delete-orphan"
    )
    review = relationship("ReviewQueue", back_populates="job", uselist=False)

    def __repr__(self):
        return f"<ImageJob {self.id} status={self.status.value}>"


class ImageExtraction(Base):
    """Extracted data from image analysis"""

    __tablename__ = "image_extractions"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), ForeignKey("image_jobs.id"), nullable=False)

    # Extracted text (OCR)
    ocr_text = Column(Text)
    ocr_confidence = Column(Float)
    ocr_provider = Column(String(50))  # google_vision, aws_rekognition, tesseract

    # Extracted barcodes
    barcodes = Column(JSON)  # [{"type": "QR", "data": "...", "confidence": 0.95}]

    # Extracted product info
    product_name = Column(String(500))
    brand_name = Column(String(200))
    model_number = Column(String(200))
    serial_number = Column(String(200))
    lot_number = Column(String(200))
    upc_code = Column(String(50))

    # Image labels/tags (for classification)
    labels = Column(JSON)  # [{"name": "baby bottle", "confidence": 0.92}]
    dominant_colors = Column(JSON)  # [{"color": "#FF5733", "percent": 0.35}]

    # Safety-related extractions
    warning_labels = Column(JSON)  # ["choking hazard", "small parts"]
    age_recommendations = Column(String(100))  # "3+ years"
    certifications = Column(JSON)  # ["CE", "CPSC", "ASTM"]

    # Metadata
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    extraction_duration_ms = Column(Integer)

    # Relationship
    job = relationship("ImageJob", back_populates="extractions")

    def __repr__(self):
        return f"<ImageExtraction job={self.job_id} product={self.product_name}>"


class ReviewQueue(Base):
    """Human-in-the-loop review queue"""

    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), ForeignKey("image_jobs.id"), nullable=False)

    # Review status
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.QUEUED, index=True)
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest

    # Assignment
    claimed_by = Column(String(100))  # Reviewer email/ID
    claimed_at = Column(DateTime)

    # Review reason
    review_reason = Column(String(500))  # "Low confidence OCR", "Conflicting signals"
    auto_flagged_issues = Column(JSON)  # ["blur_detected", "partial_text", "multiple_products"]

    # Review actions
    reviewed_by = Column(String(100))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)

    # Corrections (what the human fixed)
    corrected_product_name = Column(String(500))
    corrected_brand = Column(String(200))
    corrected_model = Column(String(200))
    corrected_identifiers = Column(JSON)  # {"upc": "...", "lot": "..."}

    # Outcome
    confidence_after_review = Column(Float)
    requires_user_action = Column(Boolean, default=False)
    user_message = Column(Text)  # Message to show user

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    audit_log = Column(JSON, default=list)  # All status changes

    # Relationship
    job = relationship("ImageJob", back_populates="review")

    def __repr__(self):
        return f"<ReviewQueue id={self.id} job={self.job_id} status={self.status.value}>"


class MFVSession(Base):
    """Multi-Factor Verification session tracking"""

    __tablename__ = "mfv_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(36), ForeignKey("image_jobs.id"), nullable=False)
    user_id = Column(Integer, nullable=False)

    # What was extracted from image
    extracted_product = Column(String(500))
    extracted_brand = Column(String(200))
    extracted_model = Column(String(200))

    # What user claimed/confirmed
    user_claimed_product = Column(String(500))
    user_claimed_brand = Column(String(200))
    user_claimed_model = Column(String(200))

    # Verification result
    product_match = Column(Boolean)
    brand_match = Column(Boolean)
    model_match = Column(Boolean)
    overall_match_score = Column(Float)  # 0.0 to 1.0

    # User actions
    user_confirmed = Column(Boolean)
    user_correction = Column(JSON)  # What they corrected

    # Outcome
    verification_passed = Column(Boolean)
    verification_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    def __repr__(self):
        return f"<MFVSession {self.id} passed={self.verification_passed}>"


class ImageAnalysisCache(Base):
    """Cache for expensive image analysis results"""

    __tablename__ = "image_analysis_cache"

    id = Column(Integer, primary_key=True)
    file_hash = Column(String(64), unique=True, index=True)

    # Cached results
    ocr_result = Column(JSON)
    barcode_result = Column(JSON)
    labels_result = Column(JSON)

    # Provider info
    ocr_provider = Column(String(50))
    vision_provider = Column(String(50))

    # Cache metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    hit_count = Column(Integer, default=0)

    def __repr__(self):
        return f"<ImageAnalysisCache hash={self.file_hash[:8]}...>"
