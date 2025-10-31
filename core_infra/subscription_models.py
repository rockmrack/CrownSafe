"""Subscription models for mobile app IAP (Apple/Google)
Supports monthly ($7.99) and annual ($79.99) plans
"""

import enum
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship

# Import Base from the main database module
from core_infra.database import Base


class SubscriptionPlan(enum.Enum):
    """Subscription plan types"""

    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(enum.Enum):
    """Subscription status"""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"  # Waiting for receipt validation
    FAILED = "failed"  # Payment failed


class PaymentProvider(enum.Enum):
    """Payment provider"""

    APPLE = "apple"
    GOOGLE = "google"


class Subscription(Base):
    """Subscription model for mobile app IAP
    Tracks user subscriptions from Apple App Store and Google Play
    """

    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user = relationship("User", backref="subscriptions")

    # Subscription details
    plan = Column(SQLEnum(SubscriptionPlan), nullable=False)  # monthly or annual
    status = Column(SQLEnum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.PENDING)
    provider = Column(SQLEnum(PaymentProvider), nullable=False)  # apple or google

    # Product IDs from app stores
    product_id = Column(String(100), nullable=False)  # e.g., "babyshield_monthly" or "babyshield_annual"

    # Subscription periods
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)  # When user cancelled (may still be active until expires_at)

    # Receipt data
    original_transaction_id = Column(String(200), index=True)  # Apple's original_transaction_id or Google's orderId
    latest_receipt = Column(String(5000))  # Store latest receipt for revalidation
    receipt_data = Column(String(10000))  # Full receipt JSON for debugging

    # Pricing (store for analytics)
    price = Column(Float)  # 7.99 or 79.99
    currency = Column(String(3), default="USD")

    # Auto-renewal
    auto_renew = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_active", "user_id", "status"),
        Index("idx_expires_at", "expires_at"),
        Index("idx_transaction_id", "original_transaction_id"),
    )

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return self.status == SubscriptionStatus.ACTIVE and self.expires_at > datetime.now(timezone.utc)

    def calculate_expiry(self) -> DateTime:
        """Calculate expiry date based on plan"""
        if self.plan == SubscriptionPlan.MONTHLY:
            return self.started_at + timedelta(days=30)
        elif self.plan == SubscriptionPlan.ANNUAL:
            return self.started_at + timedelta(days=365)
        return self.started_at

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan": self.plan.value,
            "status": self.status.value,
            "provider": self.provider.value,
            "product_id": self.product_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "auto_renew": self.auto_renew,
            "is_active": self.is_active(),
        }

    def __repr__(self) -> str:
        return (
            f"<Subscription(id={self.id}, user_id={self.user_id}, "
            f"plan={self.plan.value}, status={self.status.value}, "
            f"expires_at={self.expires_at})>"
        )


class ReceiptValidation(Base):
    """Track receipt validation attempts for audit and debugging
    """

    __tablename__ = "receipt_validations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Subscription relationship
    subscription_id = Column(String(36), ForeignKey("subscriptions.id"), nullable=True)
    subscription = relationship("Subscription", backref="validations")

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Validation details
    provider = Column(SQLEnum(PaymentProvider), nullable=False)
    product_id = Column(String(100), nullable=False)

    # Receipt info
    receipt_hash = Column(String(64))  # SHA256 hash of receipt for deduplication
    transaction_id = Column(String(200))

    # Validation result
    is_valid = Column(Boolean, nullable=False)
    validation_response = Column(String(5000))  # Store provider response
    error_message = Column(String(500))

    # Timestamps
    validated_at = Column(DateTime, default=datetime.utcnow)

    # Index for quick lookups
    __table_args__ = (
        Index("idx_receipt_hash", "receipt_hash"),
        Index("idx_user_validations", "user_id", "validated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReceiptValidation(id={self.id}, user_id={self.user_id}, "
            f"provider={self.provider.value}, is_valid={self.is_valid})>"
        )
