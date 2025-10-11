from __future__ import annotations
from datetime import datetime, date
from typing import Any, Optional
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    BigInteger,
    SmallInteger,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import os

from core_infra.database import Base  # reuse your existing Base

# Use JSON for SQLite compatibility, JSONB for PostgreSQL
JsonType = JSONB if os.getenv("DATABASE_URL", "").startswith("postgresql") else JSON

# Use String for UUID in SQLite, UUID for PostgreSQL
UuidType = UUID(as_uuid=True) if os.getenv("DATABASE_URL", "").startswith("postgresql") else String(36)


class UserProfile(Base):
    __tablename__ = "user_profile"
    user_id = Column(UuidType, primary_key=True)
    consent_personalization = Column(Boolean, nullable=False, default=False)
    memory_paused = Column(Boolean, nullable=False, default=False)
    allergies = Column(JsonType, nullable=False, default=list)
    pregnancy_trimester = Column(SmallInteger, nullable=True)
    pregnancy_due_date = Column(Date, nullable=True)
    child_birthdate = Column(Date, nullable=True)
    erase_requested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class Conversation(Base):
    __tablename__ = "conversation"
    id = Column(UuidType, primary_key=True)
    user_id = Column(UuidType, nullable=True)
    scan_id = Column(String(64), nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    messages = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_message"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(UuidType, ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    role = Column(String(16), nullable=False)  # 'user' | 'assistant'
    intent = Column(String(64), nullable=True)
    trace_id = Column(String(64), nullable=True)
    content = Column(JsonType, nullable=False)
    conversation = relationship("Conversation", back_populates="messages")
