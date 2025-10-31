"""
SQLAlchemy model for privacy request (DSAR) tracking
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from core_infra.database import Base  # Use existing Base from project


class PrivacyRequest(Base):
    """
    Model for tracking privacy requests (Data Subject Access Requests)
    Compliant with GDPR, CCPA, and other privacy regulations
    """

    __tablename__ = "privacy_requests"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    # Request details
    kind = Column(String(16), nullable=False)  # export, delete, rectify, access, restrict, object
    email = Column(String(320), nullable=False)  # RFC 5321 max email length
    email_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for privacy

    # Status tracking
    status = Column(String(16), nullable=False, default="queued", index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Request metadata
    notes = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True)
    jurisdiction = Column(String(32), nullable=True)  # gdpr, ccpa, etc.
    source = Column(String(32), nullable=True)  # ios, android, web, etc.

    # Audit fields
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)

    # Processing fields
    verification_token = Column(String(128), nullable=True)
    export_url = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "kind IN ('export', 'delete', 'rectify', 'access', 'restrict', 'object')",
            name="check_kind",
        ),
        CheckConstraint(
            "status IN ('queued', 'verifying', 'processing', 'done', 'rejected', 'expired', 'cancelled')",
            name="check_status",
        ),
        CheckConstraint(
            "jurisdiction IS NULL OR jurisdiction IN ('gdpr', 'ccpa', 'pipeda', 'lgpd', 'appi', 'uk_gdpr', 'other')",
            name="check_jurisdiction",
        ),
        CheckConstraint(
            "source IS NULL OR source IN ('ios', 'android', 'web', 'email', 'api', 'admin')",
            name="check_source",
        ),
    )

    def __repr__(self):
        return f"<PrivacyRequest(id={self.id}, kind={self.kind}, email_hash={self.email_hash[:8]}..., status={self.status})>"

    def to_dict(self, include_pii: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization

        Args:
            include_pii: Whether to include personally identifiable information

        Returns:
            Dictionary representation
        """
        data = {
            "id": str(self.id) if self.id else None,
            "kind": self.kind,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "jurisdiction": self.jurisdiction,
            "source": self.source,
            "trace_id": self.trace_id,
            "metadata": self.metadata_json,
            "sla_days": self.sla_days,
            "is_overdue": self.is_overdue,
            "days_elapsed": self.days_elapsed,
        }

        if include_pii:
            data["email"] = self.email
            data["ip_address"] = self.ip_address
            data["user_agent"] = self.user_agent
            data["notes"] = self.notes
            data["rejection_reason"] = self.rejection_reason
        else:
            data["email_hash"] = self.email_hash[:8] + "..."  # Truncated for privacy

        return data

    @property
    def sla_days(self) -> int:
        """Get SLA in days based on jurisdiction"""
        sla_map = {
            "gdpr": 30,
            "uk_gdpr": 30,
            "ccpa": 45,
            "pipeda": 30,
            "lgpd": 15,
            "appi": 30,
            "other": 30,
        }
        return sla_map.get(self.jurisdiction, 30)

    @property
    def is_overdue(self) -> bool:
        """Check if request is overdue based on SLA"""
        if self.status in ("done", "rejected", "cancelled", "expired"):
            return False

        if self.submitted_at:
            deadline = self.submitted_at + timedelta(days=self.sla_days)
            return datetime.now(timezone.utc) > deadline

        return False

    @property
    def days_elapsed(self) -> Optional[int]:
        """Calculate days elapsed since submission"""
        if self.submitted_at:
            elapsed = datetime.now(timezone.utc) - self.submitted_at
            return elapsed.days
        return None

    @property
    def is_pending(self) -> bool:
        """Check if request is still pending"""
        return self.status in ("queued", "verifying", "processing")

    @property
    def is_complete(self) -> bool:
        """Check if request is complete"""
        return self.status in ("done", "rejected", "cancelled", "expired")

    @classmethod
    def hash_email(cls, email: str) -> str:
        """
        Generate SHA-256 hash of normalized email

        Args:
            email: Email address to hash

        Returns:
            Hex digest of SHA-256 hash
        """
        normalized = email.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @classmethod
    def generate_verification_token(cls) -> str:
        """
        Generate secure verification token

        Returns:
            URL-safe token
        """
        return secrets.token_urlsafe(48)  # 64 characters after encoding

    def set_verified(self):
        """Mark request as verified"""
        self.status = "processing"
        self.verified_at = datetime.now(timezone.utc)
        self.verification_token = None  # Clear token after use

    def set_completed(self, export_url: Optional[str] = None, expiry_days: int = 7):
        """
        Mark request as completed

        Args:
            export_url: URL for data export download
            expiry_days: Days until export link expires
        """
        self.status = "done"
        self.completed_at = datetime.now(timezone.utc)

        if export_url:
            self.export_url = export_url
            self.expires_at = datetime.now(timezone.utc) + timedelta(days=expiry_days)

    def set_rejected(self, reason: str):
        """
        Mark request as rejected

        Args:
            reason: Reason for rejection
        """
        self.status = "rejected"
        self.completed_at = datetime.now(timezone.utc)
        self.rejection_reason = reason

    def set_expired(self):
        """Mark request as expired"""
        self.status = "expired"
        self.export_url = None  # Clear expired URL

    @classmethod
    def create_request(
        cls,
        kind: str,
        email: str,
        jurisdiction: Optional[str] = None,
        source: Optional[str] = None,
        trace_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PrivacyRequest":
        """
        Factory method to create a new privacy request

        Args:
            kind: Type of request (export, delete, etc.)
            email: User's email address
            jurisdiction: Legal jurisdiction
            source: Request source (ios, android, web, etc.)
            trace_id: Request trace ID for correlation
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata

        Returns:
            New PrivacyRequest instance
        """
        return cls(
            kind=kind,
            email=email.strip().lower(),
            email_hash=cls.hash_email(email),
            status="queued",
            jurisdiction=jurisdiction,
            source=source,
            trace_id=trace_id,
            ip_address=ip_address,
            user_agent=user_agent,
            verification_token=cls.generate_verification_token(),
            metadata_json=metadata,
        )


# Export
__all__ = ["PrivacyRequest"]
