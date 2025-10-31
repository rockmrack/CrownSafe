from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core_infra.database import Base


class ExplainFeedback(Base):
    __tablename__ = "explain_feedback"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), nullable=True)
    scan_id = Column(String(64), nullable=False)
    trace_id = Column(String(64), nullable=True)
    helpful = Column(Boolean, nullable=False)
    reason = Column(String(256), nullable=True)
    comment = Column(Text, nullable=True)
    platform = Column(String(32), nullable=True)
    app_version = Column(String(32), nullable=True)
    locale = Column(String(16), nullable=True)
    jurisdiction_code = Column(String(8), nullable=True)
