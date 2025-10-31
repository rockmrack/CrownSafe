"""SQLAlchemy model for unit-level serial/lot verification records."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from core_infra.database import Base


class SerialVerification(Base):
    """Stores results of unit-level authenticity/traceability checks.

    A record is created when we parse GS1 data (GTIN, lot, serial, expiry)
    and attempt verification via a manufacturer or registry connector.
    """

    __tablename__ = "serial_verifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Core identifiers
    gtin = Column(String(32), nullable=True, index=True)
    lot_number = Column(String(128), nullable=True, index=True)
    serial_number = Column(String(128), nullable=True, index=True)
    expiry_date = Column(Date, nullable=True)

    # Metadata
    manufacturer = Column(String(256), nullable=True)
    status = Column(String(32), nullable=False, default="unknown")  # verified | invalid | unknown | error
    source = Column(String(64), nullable=True)  # e.g., mock, oem_api, registry_sync
    message = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True)

    # Raw payloads
    verification_payload = Column(JSONB, nullable=True)

    # Timestamps
    checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


# Helpful composite indexes
Index(
    "ix_serial_verifications_gtin_lot",
    SerialVerification.gtin,
    SerialVerification.lot_number,
)
Index(
    "ix_serial_verifications_gtin_serial",
    SerialVerification.gtin,
    SerialVerification.serial_number,
)


__all__ = ["SerialVerification"]
