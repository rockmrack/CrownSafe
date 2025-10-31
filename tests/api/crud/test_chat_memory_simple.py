import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# Create test-specific models for SQLite compatibility
TestBase = declarative_base()


class UserProfileModel(TestBase):
    __tablename__ = "user_profile"
    user_id = Column(String(36), primary_key=True)
    consent_personalization = Column(Boolean, nullable=False, default=False)
    memory_paused = Column(Boolean, nullable=False, default=False)
    allergies = Column(Text, nullable=False, default="[]")  # JSON as text for SQLite
    pregnancy_trimester = Column(SmallInteger, nullable=True)
    pregnancy_due_date = Column(Date, nullable=True)
    child_birthdate = Column(Date, nullable=True)
    erase_requested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ConversationModel(TestBase):
    __tablename__ = "conversation"
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True)
    scan_id = Column(String(64), nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    messages = relationship(
        "ConversationMessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class ConversationMessageModel(TestBase):
    __tablename__ = "conversation_message"
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversation.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    role = Column(String(16), nullable=False)  # 'user' | 'assistant'
    intent = Column(String(64), nullable=True)
    trace_id = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)  # JSON as text for SQLite
    conversation = relationship("ConversationModel", back_populates="messages")


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    TestBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_create_user_profile(db_session):
    """Test creating a user profile"""
    user_id = str(uuid4())

    profile = UserProfileModel(
        user_id=user_id,
        consent_personalization=True,
        allergies=json.dumps(["peanuts", "milk"]),
        pregnancy_trimester=2,
        pregnancy_due_date=date(2025, 6, 15),
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    assert profile.user_id == user_id
    assert profile.consent_personalization
    assert json.loads(profile.allergies) == ["peanuts", "milk"]
    assert profile.pregnancy_trimester == 2
    assert profile.pregnancy_due_date == date(2025, 6, 15)


def test_create_conversation(db_session):
    """Test creating a conversation"""
    conv_id = str(uuid4())
    user_id = str(uuid4())
    scan_id = "test_scan_123"

    conv = ConversationModel(id=conv_id, user_id=user_id, scan_id=scan_id)
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    assert conv.id == conv_id
    assert conv.user_id == user_id
    assert conv.scan_id == scan_id


def test_create_conversation_message(db_session):
    """Test creating a conversation message"""
    conv_id = str(uuid4())

    # Create conversation first
    conv = ConversationModel(id=conv_id, scan_id="test_scan_123")
    db_session.add(conv)
    db_session.commit()

    # Create message
    message_content = {"text": "Is this safe during pregnancy?"}
    message = ConversationMessageModel(
        conversation_id=conv_id,
        role="user",
        content=json.dumps(message_content),
        trace_id="trace-123",
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)

    assert message.conversation_id == conv_id
    assert message.role == "user"
    assert json.loads(message.content) == message_content
    assert message.trace_id == "trace-123"
