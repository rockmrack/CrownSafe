"""
Shared Pydantic Models
Reduces duplication of model definitions across endpoint files
"""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator

from utils.security.input_validator import (
    InputValidator,
)

# ============================================================================
# ENUMS
# ============================================================================


class RiskLevel(str, Enum):
    """Product risk level"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RecallStatus(str, Enum):
    """Recall status"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    MONITORING = "monitoring"
    UNDER_INVESTIGATION = "under_investigation"


class SubscriptionTier(str, Enum):
    """Subscription tier"""

    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"
    ENTERPRISE = "enterprise"


class NotificationChannel(str, Enum):
    """Notification delivery channel"""

    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"


class ScanType(str, Enum):
    """Type of barcode scan"""

    BARCODE = "barcode"
    QR_CODE = "qr_code"
    DATAMATRIX = "datamatrix"
    IMAGE = "image"
    MANUAL = "manual"


# ============================================================================
# REQUEST MODELS
# ============================================================================


class UserIdRequest(BaseModel):
    """Base request with user ID"""

    user_id: int = Field(..., gt=0, description="User ID")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        return InputValidator.validate_user_id(v)


class PaginationRequest(BaseModel):
    """Standard pagination request"""

    limit: int = Field(20, ge=1, le=100, description="Items per page")
    offset: int = Field(0, ge=0, le=10000, description="Number of items to skip")

    # Validation is now in Field constraints above


class DateRangeRequest(BaseModel):
    """Date range filter"""

    date_from: date | None = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: date | None = Field(None, description="End date (YYYY-MM-DD)")

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v, info):
        date_from = info.data.get("date_from")
        if v and date_from:
            if v < date_from:
                raise ValueError("date_to must be after date_from")
        return v


class BarcodeScanRequest(BaseModel):
    """Request to scan a barcode"""

    model_config = {"protected_namespaces": ()}

    barcode: str = Field(..., min_length=1, max_length=50, description="Barcode data")
    user_id: int = Field(..., gt=0, description="User ID")
    barcode_type: ScanType | None = Field(None, description="Type of barcode")

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, v):
        return InputValidator.validate_barcode(v)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        return InputValidator.validate_user_id(v)


class ProductSearchRequest(BaseModel):
    """Request to search for products/recalls"""

    query: str | None = Field(None, max_length=200, description="Search query")
    product_name: str | None = Field(None, max_length=500, description="Product name")
    brand: str | None = Field(None, max_length=200, description="Brand name")
    model_number: str | None = Field(None, max_length=100, description="Model number")
    barcode: str | None = Field(None, max_length=50, description="Barcode")

    # Filters
    risk_level: RiskLevel | None = Field(None, description="Risk level filter")
    agencies: list[str] | None = Field(None, description="Agency filter")
    date_from: date | None = Field(None, description="Start date")
    date_to: date | None = Field(None, description="End date")

    # Pagination
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v):
        if v:
            return InputValidator.validate_search_query(v)
        return v

    @field_validator("barcode")
    @classmethod
    def validate_barcode(cls, v):
        if v:
            return InputValidator.validate_barcode(v)
        return v


class EmailRequest(BaseModel):
    """Request with email address"""

    email: EmailStr = Field(..., description="Email address")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        return InputValidator.validate_email(v)


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class ApiResponse(BaseModel):
    """Standard API response"""

    success: bool = Field(..., description="Whether request was successful")
    data: Any | None = Field(None, description="Response data")
    error: str | None = Field(None, description="Error message if failed")
    message: str | None = Field(None, description="Additional message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    trace_id: str | None = Field(None, description="Trace ID for debugging")


class PaginatedResponse(BaseModel):
    """Paginated API response"""

    success: bool = True
    data: list[Any] = Field(default_factory=list, description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more items exist")
    next_cursor: str | None = Field(None, description="Cursor for next page")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserResponse(BaseModel):
    """User data response"""

    id: int
    email: str
    created_at: datetime
    is_subscribed: bool = False
    subscription_tier: SubscriptionTier | None = None
    email_verified: bool = False


class ProductInfo(BaseModel):
    """Product information"""

    model_config = {"protected_namespaces": ()}

    product_name: str
    brand: str | None = None
    model_number: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    upc: str | None = None
    description: str | None = None


class RecallInfo(BaseModel):
    """Recall information"""

    recall_id: str
    product_name: str
    brand: str | None = None
    hazard: str
    description: str
    recall_date: date
    source_agency: str
    country: str
    risk_level: RiskLevel
    status: RecallStatus = RecallStatus.ACTIVE
    url: str | None = None
    image_url: str | None = None


class ScanResult(BaseModel):
    """Barcode scan result"""

    model_config = {"protected_namespaces": ()}

    scan_id: str = Field(..., description="Unique scan ID")
    barcode: str
    scan_type: ScanType
    timestamp: datetime

    # Extracted data
    product_info: ProductInfo | None = None

    # Recall check results
    recall_found: bool = False
    recall_count: int = 0
    recalls: list[RecallInfo] = Field(default_factory=list)

    # Risk assessment
    overall_risk: RiskLevel = RiskLevel.UNKNOWN
    safety_score: float | None = Field(None, ge=0, le=100, description="Safety score (0-100)")

    # Additional metadata
    verification_status: str | None = None
    trace_id: str | None = None


class NotificationResponse(BaseModel):
    """Notification data"""

    notification_id: str
    user_id: int
    title: str
    message: str
    channel: NotificationChannel
    sent_at: datetime
    read_at: datetime | None = None
    data: dict[str, Any] | None = None


class SubscriptionResponse(BaseModel):
    """Subscription information"""

    user_id: int
    tier: SubscriptionTier
    is_active: bool
    start_date: date
    end_date: date | None = None
    auto_renew: bool = False
    features: list[str] = Field(default_factory=list)


# ============================================================================
# ANALYTICS & REPORTING
# ============================================================================


class AnalyticsData(BaseModel):
    """Analytics data point"""

    metric_name: str
    value: float
    timestamp: datetime
    dimensions: dict[str, str] | None = None


class ReportMetadata(BaseModel):
    """Report metadata"""

    report_id: str
    report_type: str
    created_at: datetime
    user_id: int
    file_url: str | None = None
    status: str = "completed"


# ============================================================================
# ERROR MODELS
# ============================================================================


class ErrorDetail(BaseModel):
    """Detailed error information"""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: str | None = Field(None, description="Field that caused error")
    details: dict[str, Any] | None = Field(None, description="Additional details")


class ValidationError(BaseModel):
    """Validation error response"""

    success: bool = False
    error: str = "Validation failed"
    errors: list[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# HEALTH CHECK
# ============================================================================


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, str] = Field(
        default_factory=lambda: {
            "database": "unknown",
            "cache": "unknown",
            "external_apis": "unknown",
        }
    )
