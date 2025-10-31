"""
SQLAlchemy model for ingestion run tracking
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from core_infra.database import Base  # Use existing Base from project


class IngestionRun(Base):
    """
    Model for tracking data ingestion runs
    """

    __tablename__ = "ingestion_runs"

    # Primary key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        nullable=False,
    )

    # Core fields
    agency = Column(String(64), nullable=False, index=True)
    mode = Column(String(16), nullable=False)  # delta, full, incremental
    status = Column(String(16), nullable=False, index=True)  # queued, running, success, failed, cancelled, partial

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False)

    # Metrics
    items_inserted = Column(Integer, default=0, nullable=False)
    items_updated = Column(Integer, default=0, nullable=False)
    items_skipped = Column(Integer, default=0, nullable=False)
    items_failed = Column(Integer, default=0, nullable=False)

    # Error tracking
    error_text = Column(Text, nullable=True)

    # Audit fields
    initiated_by = Column(String(128), nullable=True)
    trace_id = Column(String(64), nullable=True)

    # Flexible metadata storage
    metadata_json = Column(JSONB, nullable=True)

    # Table constraints
    __table_args__ = (
        CheckConstraint("mode IN ('delta', 'full', 'incremental')", name="check_mode"),
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'cancelled', 'partial')",
            name="check_status",
        ),
    )

    def __repr__(self):
        return f"<IngestionRun(id={self.id}, agency={self.agency}, status={self.status})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": str(self.id) if self.id else None,
            "agency": self.agency,
            "mode": self.mode,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "items_inserted": self.items_inserted,
            "items_updated": self.items_updated,
            "items_skipped": self.items_skipped,
            "items_failed": self.items_failed,
            "error_text": self.error_text,
            "initiated_by": self.initiated_by,
            "trace_id": self.trace_id,
            "metadata": self.metadata_json,
            "duration_seconds": self.duration_seconds,
            "is_running": self.is_running,
            "is_success": self.is_success,
        }

    @property
    def duration_seconds(self) -> float | None:
        """Calculate run duration in seconds"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        elif self.started_at:
            # Still running
            return (datetime.utcnow().replace(tzinfo=self.started_at.tzinfo) - self.started_at).total_seconds()
        return None

    @property
    def is_running(self) -> bool:
        """Check if ingestion is currently running"""
        return self.status == "running"

    @property
    def is_success(self) -> bool:
        """Check if ingestion completed successfully"""
        return self.status in ("success", "partial")

    @property
    def is_failed(self) -> bool:
        """Check if ingestion failed"""
        return self.status in ("failed", "cancelled")

    @property
    def total_items_processed(self) -> int:
        """Total number of items processed"""
        return self.items_inserted + self.items_updated + self.items_skipped

    def set_running(self, trace_id: str | None = None):
        """Mark ingestion as running"""
        self.status = "running"
        self.started_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        if trace_id:
            self.trace_id = trace_id

    def set_success(
        self,
        items_inserted: int = 0,
        items_updated: int = 0,
        items_skipped: int = 0,
        items_failed: int = 0,
    ):
        """Mark ingestion as successful"""
        self.status = "success" if items_failed == 0 else "partial"
        self.finished_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.items_inserted = items_inserted
        self.items_updated = items_updated
        self.items_skipped = items_skipped
        self.items_failed = items_failed

    def set_failed(self, error: str):
        """Mark ingestion as failed"""
        self.status = "failed"
        self.finished_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.error_text = error[:5000] if error else None  # Truncate to 5000 chars

    def set_cancelled(self):
        """Mark ingestion as cancelled"""
        self.status = "cancelled"
        self.finished_at = datetime.utcnow().replace(tzinfo=timezone.utc)
        self.error_text = "Ingestion cancelled by user"


# Export
__all__ = ["IngestionRun"]
