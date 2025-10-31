"""Share Token Model for secure result sharing."""

import secrets
from datetime import datetime, UTC

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from core_infra.database import Base


class ShareToken(Base):
    """Model for secure sharing of scan results."""

    __tablename__ = "share_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(100), unique=True, index=True, nullable=False)

    # What is being shared
    share_type = Column(String(50), nullable=False)  # scan_result, report, product_safety
    content_id = Column(String(100), nullable=False)  # scan_id, report_id, etc.

    # Share metadata
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Access control
    max_views = Column(Integer)  # Limit number of views
    view_count = Column(Integer, default=0)
    password_protected = Column(Boolean, default=False)
    password_hash = Column(String(255))  # If password protected

    # Share settings
    allow_download = Column(Boolean, default=True)
    show_personal_info = Column(Boolean, default=False)

    # Shared content snapshot (for permanence even if original is deleted)
    content_snapshot = Column(JSON)

    # Tracking
    last_accessed = Column(DateTime)
    access_log = Column(JSON)  # List of access timestamps and IPs

    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime)

    @classmethod
    def generate_token(cls):
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)

    def is_valid(self) -> bool:
        """Check if the share token is still valid."""
        if not self.is_active:
            return False

        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False

        if self.max_views and self.view_count >= self.max_views:
            return False

        return True

    def increment_view(self) -> None:
        """Increment the view counter."""
        self.view_count += 1
        self.last_accessed = datetime.now(UTC)

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "token": self.token,
            "share_type": self.share_type,
            "content_id": self.content_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "view_count": self.view_count,
            "max_views": self.max_views,
            "is_active": self.is_active,
            "allow_download": self.allow_download,
        }
