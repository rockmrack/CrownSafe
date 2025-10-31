"""Legal Compliance API Endpoints
Provides endpoints for COPPA, Children's Code, GDPR, and legal content management
Critical for app store approval and regulatory compliance.
"""

import logging
import secrets
import uuid
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from core_infra.auth import get_current_active_user
from core_infra.database import User, get_db

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(prefix="/api/v1/compliance", tags=["Legal Compliance"])

# ==================== Enums ====================


class ConsentType(str, Enum):
    COPPA_PARENTAL = "coppa_parental"
    DATA_PROCESSING = "data_processing"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    THIRD_PARTY = "third_party"


class PrivacyRight(str, Enum):
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class AgeVerificationMethod(str, Enum):
    BIRTHDATE = "birthdate"
    CREDIT_CARD = "credit_card"
    ID_VERIFICATION = "id_verification"
    PARENTAL_EMAIL = "parental_email"
    PHONE_VERIFICATION = "phone_verification"


class DataCategory(str, Enum):
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    HEALTH = "health"
    LOCATION = "location"
    BEHAVIORAL = "behavioral"
    BIOMETRIC = "biometric"


# ==================== Request/Response Models ====================


# COPPA Compliance Models
class AgeVerificationRequest(BaseModel):
    """Request model for age verification."""

    user_id: int | None = Field(None, description="Existing user ID if available")
    email: EmailStr = Field(..., description="User email")
    birthdate: date = Field(..., description="User's birthdate")
    parent_email: EmailStr | None = Field(None, description="Parent email if under 13")
    verification_method: AgeVerificationMethod = Field(AgeVerificationMethod.BIRTHDATE)
    country: str = Field("US", description="User's country for compliance rules")


class AgeVerificationResponse(BaseModel):
    """Response model for age verification."""

    verified: bool
    age: int
    requires_parental_consent: bool
    coppa_applies: bool
    gdpr_child: bool  # Under 16 in EU
    verification_token: str | None = None
    parent_consent_url: str | None = None
    restrictions: list[str]
    timestamp: datetime


class ParentalConsentRequest(BaseModel):
    """Request model for parental consent."""

    child_email: EmailStr
    parent_email: EmailStr
    parent_name: str
    consent_types: list[ConsentType]
    verification_token: str = Field(..., description="Token from age verification")
    verification_method: AgeVerificationMethod = Field(AgeVerificationMethod.PARENTAL_EMAIL)
    credit_card_last4: str | None = Field(None, min_length=4, max_length=4)


class ParentalConsentResponse(BaseModel):
    """Response model for parental consent."""

    consent_id: str
    status: str  # "pending", "verified", "rejected"
    child_email: str
    parent_email: str
    consents_granted: list[ConsentType]
    verification_method: str
    expires_at: datetime | None = None
    timestamp: datetime


# Children's Code Compliance Models
class ChildrenCodeAssessmentRequest(BaseModel):
    """Request for Children's Code compliance assessment."""

    user_id: int
    age: int
    country: str
    features_used: list[str] = Field(..., description="App features the child uses")
    data_collected: list[DataCategory] = Field(..., description="Types of data collected")
    third_party_sharing: bool = Field(False, description="Whether data is shared")


class ChildrenCodeAssessmentResponse(BaseModel):
    """Response for Children's Code assessment."""

    compliant: bool
    age_appropriate: bool
    required_safeguards: list[str]
    prohibited_features: list[str]
    design_recommendations: list[str]
    privacy_settings: dict[str, Any]
    parental_controls_required: bool
    timestamp: datetime


# Data Governance Models
class DataRequestModel(BaseModel):
    """Request model for data governance operations."""

    user_id: int
    request_type: PrivacyRight
    email: EmailStr
    reason: str | None = None
    data_categories: list[DataCategory] | None = None
    verification_code: str | None = None


class DataRequestResponse(BaseModel):
    """Response model for data requests."""

    request_id: str
    status: str  # "pending", "processing", "completed", "rejected"
    request_type: PrivacyRight
    estimated_completion: datetime
    download_url: str | None = None
    message: str
    timestamp: datetime


class DataRetentionPolicyRequest(BaseModel):
    """Request model for data retention settings."""

    user_id: int
    data_category: DataCategory
    retention_days: int | None = Field(None, ge=0, le=3650)
    auto_delete: bool = Field(True)
    anonymize_instead: bool = Field(False)


class DataRetentionPolicyResponse(BaseModel):
    """Response model for retention policy."""

    policy_id: str
    user_id: int
    policies: dict[DataCategory, dict[str, Any]]
    compliance_status: str
    next_deletion_date: datetime | None
    timestamp: datetime


# Legal Content Models
class LegalDocumentRequest(BaseModel):
    """Request model for legal documents."""

    document_type: str = Field(..., description="tos, privacy, cookie, child_privacy")
    language: str = Field("en", description="Language code")
    country: str = Field("US", description="Country code")
    user_age: int | None = Field(None, description="For age-appropriate content")
    format: str = Field("html", description="html, plain, json")


class LegalDocumentResponse(BaseModel):
    """Response model for legal documents."""

    document_type: str
    version: str
    language: str
    country: str
    content: str
    last_updated: datetime
    age_appropriate: bool
    requires_acceptance: bool
    summary_points: list[str]


class ConsentUpdateRequest(BaseModel):
    """Request model for updating consent."""

    user_id: int
    consent_types: dict[ConsentType, bool]
    ip_address: str | None = None
    user_agent: str | None = None


class ConsentUpdateResponse(BaseModel):
    """Response model for consent update."""

    user_id: int
    consents_updated: dict[ConsentType, bool]
    timestamp: datetime
    ip_logged: bool
    next_review_date: datetime


# ==================== COPPA Compliance Endpoints ====================


@router.post("/coppa/verify-age", response_model=AgeVerificationResponse)
async def verify_user_age(request: AgeVerificationRequest, db: Session = Depends(get_db)):
    """Verify user age for COPPA compliance.

    This endpoint:
    1. Calculates user age from birthdate
    2. Determines if COPPA applies (under 13 in US)
    3. Checks GDPR child status (under 16 in EU)
    4. Generates parental consent flow if needed
    """
    try:
        logger.info(f"Age verification for {request.email}")

        # Calculate age
        today = date.today()
        age = (
            today.year
            - request.birthdate.year
            - ((today.month, today.day) < (request.birthdate.month, request.birthdate.day))
        )

        # Determine compliance requirements
        coppa_applies = age < 13 and request.country == "US"
        gdpr_child = age < 16 and request.country in [
            "GB",
            "EU",
            "DE",
            "FR",
            "IT",
            "ES",
        ]
        requires_consent = coppa_applies or (gdpr_child and age < 13)

        # Generate verification token if consent needed
        verification_token = None
        parent_consent_url = None
        if requires_consent:
            verification_token = secrets.token_urlsafe(32)
            parent_consent_url = f"/compliance/parental-consent?token={verification_token}"

            # Store verification token (in production, save to database)
            logger.info(f"Generated consent token for {request.email}: {verification_token}")

        # Determine restrictions
        restrictions = []
        if coppa_applies:
            restrictions.extend(
                [
                    "Cannot collect personal information without parental consent",
                    "Cannot enable social features",
                    "Cannot share data with third parties",
                    "Must use age-appropriate content",
                    "Cannot use behavioral advertising",
                ],
            )

        if gdpr_child:
            restrictions.extend(
                [
                    "Enhanced privacy protections required",
                    "Clear and child-friendly privacy notices",
                    "Parental controls must be available",
                    "Data minimization enforced",
                ],
            )

        return AgeVerificationResponse(
            verified=not requires_consent or request.parent_email is not None,
            age=age,
            requires_parental_consent=requires_consent,
            coppa_applies=coppa_applies,
            gdpr_child=gdpr_child,
            verification_token=verification_token,
            parent_consent_url=parent_consent_url,
            restrictions=restrictions,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Age verification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Age verification failed: {e!s}")


@router.post("/coppa/parental-consent", response_model=ParentalConsentResponse)
async def submit_parental_consent(
    request: ParentalConsentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Submit and verify parental consent for COPPA.

    Verification methods:
    1. Credit card verification ($0.50 charge)
    2. Government ID upload
    3. Phone verification
    4. Signed consent form
    5. Video conference verification
    """
    try:
        logger.info(f"Parental consent submission for child {request.child_email}")

        # Verify the token matches
        # In production, check against stored tokens

        # Perform verification based on method
        verified = False
        if request.verification_method == AgeVerificationMethod.CREDIT_CARD:
            # Verify credit card (mock)
            if request.credit_card_last4:
                verified = True
                logger.info(f"Credit card verification successful for {request.parent_email}")

        elif request.verification_method == AgeVerificationMethod.PARENTAL_EMAIL:
            # Send verification email (mock)
            verified = False  # Pending email confirmation
            logger.info(f"Verification email sent to {request.parent_email}")

            # Schedule email sending in background
            background_tasks.add_task(logger.info, f"Sending consent email to {request.parent_email}")

        # Generate consent ID
        consent_id = f"consent_{uuid.uuid4().hex[:12]}"

        # Set expiration (consent expires after 1 year)
        expires_at = datetime.now() + timedelta(days=365) if verified else None

        return ParentalConsentResponse(
            consent_id=consent_id,
            status="verified" if verified else "pending",
            child_email=request.child_email,
            parent_email=request.parent_email,
            consents_granted=request.consent_types if verified else [],
            verification_method=request.verification_method.value,
            expires_at=expires_at,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Parental consent failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parental consent failed: {e!s}")


@router.get("/coppa/consent-status/{user_id}")
async def get_consent_status(user_id: int, db: Session = Depends(get_db)):
    """Check COPPA consent status for a user."""
    try:
        # In production, fetch from database
        # Mock response for now
        return {
            "user_id": user_id,
            "has_parental_consent": True,
            "consent_date": datetime.now() - timedelta(days=30),
            "expires_at": datetime.now() + timedelta(days=335),
            "verification_method": "credit_card",
            "restrictions": [],
            "allowed_features": [
                "barcode_scanning",
                "recall_checking",
                "safety_reports",
            ],
            "blocked_features": [
                "social_sharing",
                "location_tracking",
                "behavioral_analytics",
            ],
        }

    except Exception as e:
        logger.error(f"Consent status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Consent status check failed: {e!s}")


# ==================== Children's Code Compliance Endpoints ====================


@router.post("/childrens-code/assess", response_model=ChildrenCodeAssessmentResponse)
async def assess_childrens_code_compliance(request: ChildrenCodeAssessmentRequest, db: Session = Depends(get_db)):
    """Assess compliance with Age Appropriate Design Code (Children's Code).

    Checks against 15 standards including:
    1. Best interests of the child
    2. Age-appropriate application
    3. Transparency
    4. Detrimental use of data
    5. Policies and standards
    6. Default settings
    7. Data minimization
    8. Data sharing
    9. Geolocation
    10. Parental controls
    11. Profiling
    12. Nudge techniques
    13. Connected toys
    14. Online tools
    15. Data protection impact assessments
    """
    try:
        logger.info(f"Children's Code assessment for user {request.user_id}, age {request.age}")

        compliant = True
        required_safeguards = []
        prohibited_features = []
        design_recommendations = []

        # Age-based assessment
        if request.age < 13:
            required_safeguards.extend(
                [
                    "Privacy settings must default to maximum",
                    "No behavioral advertising allowed",
                    "Parental controls must be enabled",
                    "Data collection must be minimized",
                    "Clear, child-friendly privacy information required",
                ],
            )

            if request.third_party_sharing:
                compliant = False
                prohibited_features.append("Third-party data sharing")

            if DataCategory.LOCATION in request.data_collected:
                prohibited_features.append("Location tracking")
                required_safeguards.append("Location services must be off by default")

            if DataCategory.BEHAVIORAL in request.data_collected:
                compliant = False
                prohibited_features.append("Behavioral profiling")

            design_recommendations.extend(
                [
                    "Use icons and graphics instead of text",
                    "Provide audio options for important information",
                    "Implement time limits and break reminders",
                    "Avoid dark patterns and manipulative design",
                    "Provide easy account deletion options",
                ],
            )

        elif request.age < 16:
            required_safeguards.extend(
                [
                    "Age-appropriate privacy settings",
                    "Limited data sharing options",
                    "Parental visibility into account activity",
                    "Regular privacy reminders",
                ],
            )

            if DataCategory.BIOMETRIC in request.data_collected:
                required_safeguards.append("Explicit consent required for biometric data")

            design_recommendations.extend(
                [
                    "Progressive disclosure of features based on age",
                    "Educational content about privacy",
                    "Easy-to-use privacy controls",
                    "Regular consent renewals",
                ],
            )

        # Determine privacy settings
        privacy_settings = {
            "profile_visibility": "private" if request.age < 16 else "friends_only",
            "data_collection": "minimal" if request.age < 13 else "limited",
            "advertising": "disabled" if request.age < 13 else "non_targeted",
            "analytics": "essential_only" if request.age < 13 else "limited",
            "social_features": "disabled" if request.age < 13 else "restricted",
            "notifications": "parent_controlled" if request.age < 13 else "limited",
            "location_services": "disabled" if request.age < 13 else "ask_each_time",
        }

        return ChildrenCodeAssessmentResponse(
            compliant=compliant,
            age_appropriate=len(prohibited_features) == 0,
            required_safeguards=required_safeguards,
            prohibited_features=prohibited_features,
            design_recommendations=design_recommendations,
            privacy_settings=privacy_settings,
            parental_controls_required=request.age < 16,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Children's Code assessment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Assessment failed: {e!s}")


# ==================== Data Governance Endpoints ====================


@router.post("/gdpr/data-request", response_model=DataRequestResponse)
async def submit_data_request(
    request: DataRequestModel,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Submit GDPR data request (access, deletion, portability, etc.).

    Handles:
    - Right to access (Article 15)
    - Right to rectification (Article 16)
    - Right to erasure/be forgotten (Article 17)
    - Right to data portability (Article 20)
    - Right to restriction (Article 18)
    - Right to object (Article 21)
    """
    try:
        logger.info(f"GDPR {request.request_type} request for user {request.user_id}")

        # Generate request ID
        request_id = f"gdpr_{request.request_type.value}_{uuid.uuid4().hex[:8]}"

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Determine processing time based on request type
        if request.request_type == PrivacyRight.ACCESS:
            estimated_completion = datetime.now() + timedelta(hours=24)
            message = "Your data access request has been received. You will receive your data within 24 hours."

        elif request.request_type == PrivacyRight.ERASURE:
            estimated_completion = datetime.now() + timedelta(hours=72)
            message = "Your deletion request has been received. Your data will be permanently deleted within 72 hours."

            # Schedule deletion in background
            background_tasks.add_task(logger.info, f"Scheduling deletion for user {request.user_id}")

        elif request.request_type == PrivacyRight.PORTABILITY:
            estimated_completion = datetime.now() + timedelta(hours=48)
            message = "Your data portability request has been received. You will receive your data in a portable format within 48 hours."  # noqa: E501

        else:
            estimated_completion = datetime.now() + timedelta(hours=72)
            message = (
                f"Your {request.request_type.value} request has been received and will be processed within 72 hours."
            )

        # In production, store request in database

        return DataRequestResponse(
            request_id=request_id,
            status="pending",
            request_type=request.request_type,
            estimated_completion=estimated_completion,
            download_url=None,
            message=message,
            timestamp=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data request failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data request failed: {e!s}")


@router.get("/gdpr/request-status/{request_id}")
async def get_request_status(
    request_id: str,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db),
):
    """Check status of a GDPR data request."""
    try:
        # In production, fetch from database
        # Mock response
        return {
            "request_id": request_id,
            "status": "processing",
            "request_type": "access",
            "submitted_at": datetime.now() - timedelta(hours=12),
            "estimated_completion": datetime.now() + timedelta(hours=12),
            "progress_percentage": 50,
            "download_url": None,
            "message": "Your request is being processed. 50% complete.",
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Status check failed: {e!s}")


@router.post("/gdpr/retention-policy", response_model=DataRetentionPolicyResponse)
async def set_retention_policy(request: DataRetentionPolicyRequest, db: Session = Depends(get_db)):
    """Set data retention policies for user data.

    Allows users to control how long their data is retained.
    """
    try:
        logger.info(f"Setting retention policy for user {request.user_id}")

        # Generate policy ID
        policy_id = f"retention_{uuid.uuid4().hex[:12]}"

        # Create retention policies
        policies = {
            DataCategory.PERSONAL: {
                "retention_days": 365,
                "auto_delete": True,
                "anonymize": False,
            },
            DataCategory.SENSITIVE: {
                "retention_days": 90,
                "auto_delete": True,
                "anonymize": False,
            },
            DataCategory.HEALTH: {
                "retention_days": 730,  # 2 years for health data
                "auto_delete": False,
                "anonymize": True,
            },
            DataCategory.LOCATION: {
                "retention_days": 30,
                "auto_delete": True,
                "anonymize": False,
            },
            DataCategory.BEHAVIORAL: {
                "retention_days": 180,
                "auto_delete": True,
                "anonymize": True,
            },
        }

        # Override with user preferences
        if request.data_category in policies:
            policies[request.data_category] = {
                "retention_days": request.retention_days,
                "auto_delete": request.auto_delete,
                "anonymize": request.anonymize_instead,
            }

        # Calculate next deletion date
        next_deletion = datetime.now() + timedelta(days=30)  # Check monthly

        return DataRetentionPolicyResponse(
            policy_id=policy_id,
            user_id=request.user_id,
            policies=policies,
            compliance_status="compliant",
            next_deletion_date=next_deletion,
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Retention policy update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Policy update failed: {e!s}")


# ==================== Legal Content Management Endpoints ====================


@router.post("/legal/document", response_model=LegalDocumentResponse)
async def get_legal_document(request: LegalDocumentRequest, db: Session = Depends(get_db)):
    """Get legal documents (ToS, Privacy Policy, etc.) with age-appropriate versions."""
    try:
        logger.info(f"Fetching {request.document_type} document")

        # Determine age-appropriate content
        age_appropriate = True
        content = ""
        summary_points = []

        if request.document_type == "privacy":
            if request.user_age and request.user_age < 13:
                # Child-friendly privacy policy
                content = """
                <h1>How We Keep You Safe 🛡️</h1>
                <p>We care about keeping your information safe!</p>
                <h2>What We Know About You 📝</h2>
                <ul>
                    <li>Your name (if your parent tells us)</li>
                    <li>Products you scan to check if they're safe</li>
                    <li>Nothing else without your parent's permission!</li>
                </ul>
                <h2>Who Can See Your Information 👀</h2>
                <ul>
                    <li>Only your parents</li>
                    <li>Our safety helpers (but only to keep you safe)</li>
                    <li>Never strangers or other companies</li>
                </ul>
                <h2>Your Parent is in Charge 👨‍👩‍👧</h2>
                <p>Your parent can always see what you're doing and delete anything they want.</p>
                """
                summary_points = [
                    "We only collect what we need to keep you safe",
                    "Your parent controls everything",
                    "We never share your information",
                    "You can ask us to delete everything",
                ]
            else:
                # Standard privacy policy
                content = """
                <h1>Privacy Policy</h1>
                <p>Last updated: {date}</p>
                <h2>Information We Collect</h2>
                <p>We collect information you provide directly, including...</p>
                <h2>How We Use Your Information</h2>
                <p>We use your information to provide safety services...</p>
                <h2>Data Sharing</h2>
                <p>We do not sell your personal information...</p>
                <h2>Your Rights</h2>
                <p>You have the right to access, correct, and delete your data...</p>
                """.format(date=datetime.now().strftime("%B %d, %Y"))

                summary_points = [
                    "We collect minimal data necessary for safety services",
                    "Your data is never sold",
                    "You control your data",
                    "We comply with GDPR and CCPA",
                ]

        elif request.document_type == "tos":
            content = "<h1>Terms of Service</h1><p>By using BabyShield...</p>"
            summary_points = [
                "Service provided as-is for safety information",
                "Not a substitute for professional advice",
                "User responsible for product decisions",
                "We reserve the right to modify services",
            ]

        return LegalDocumentResponse(
            document_type=request.document_type,
            version="2.0.0",
            language=request.language,
            country=request.country,
            content=content,
            last_updated=datetime.now() - timedelta(days=30),
            age_appropriate=age_appropriate,
            requires_acceptance=request.document_type == "tos",
            summary_points=summary_points,
        )

    except Exception as e:
        logger.error(f"Document fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Document fetch failed: {e!s}")


@router.post("/legal/consent/update", response_model=ConsentUpdateResponse)
async def update_user_consent(request: ConsentUpdateRequest, db: Session = Depends(get_db)):
    """Update user consent preferences."""
    try:
        logger.info(f"Updating consent for user {request.user_id}")

        # Validate user
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Log consent changes with IP for compliance
        if request.ip_address:
            logger.info(f"Consent updated from IP {request.ip_address}")

        # In production, store consent audit trail

        # Calculate next review date (annual review)
        next_review = datetime.now() + timedelta(days=365)

        return ConsentUpdateResponse(
            user_id=request.user_id,
            consents_updated=request.consent_types,
            timestamp=datetime.now(),
            ip_logged=bool(request.ip_address),
            next_review_date=next_review,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consent update failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Consent update failed: {e!s}")


# ==================== Privacy Dashboard Endpoint ====================


@router.get("/privacy/dashboard/{user_id}")
async def get_privacy_dashboard(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get comprehensive privacy dashboard for a user.

    Shows all privacy settings, consents, and compliance status.
    """
    try:
        # Derive actual subject from JWT; ignore path param for IDOR safety
        subject_id = current_user.id
        user = db.query(User).filter(User.id == subject_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Mock comprehensive privacy dashboard
        return {
            "user_id": subject_id,
            "compliance_status": {
                "coppa": "compliant",
                "gdpr": "compliant",
                "ccpa": "compliant",
                "childrens_code": "compliant",
            },
            "age_verification": {
                "verified": True,
                "age_group": "13-15",
                "parental_consent": True,
                "verification_date": datetime.now() - timedelta(days=90),
            },
            "consents": {
                "data_processing": True,
                "marketing": False,
                "analytics": True,
                "third_party": False,
                "last_updated": datetime.now() - timedelta(days=30),
            },
            "data_collected": {
                "personal": ["email", "age"],
                "usage": ["scan_history", "search_queries"],
                "device": ["device_id", "app_version"],
                "location": "disabled",
            },
            "privacy_settings": {
                "profile_visibility": "private",
                "data_sharing": "disabled",
                "advertising": "disabled",
                "analytics": "essential_only",
            },
            "data_requests": [
                {
                    "type": "access",
                    "date": datetime.now() - timedelta(days=60),
                    "status": "completed",
                },
            ],
            "retention_policies": {
                "personal_data": "1 year",
                "usage_data": "6 months",
                "scan_history": "2 years",
            },
            "rights_available": [
                "Access your data",
                "Delete your account",
                "Export your data",
                "Correct inaccuracies",
                "Restrict processing",
                "Object to processing",
            ],
            "next_review_date": datetime.now() + timedelta(days=30),
            "last_activity": datetime.now() - timedelta(hours=2),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Privacy dashboard failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dashboard failed: {e!s}")
