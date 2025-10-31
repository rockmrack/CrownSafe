import json
from datetime import datetime
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

# Import the CRUD functions we want to test
from api.crud import chat_memory

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

    # Monkey-patch the production models with test models
    # This allows the CRUD functions to work with the test database schema
    chat_memory.Conversation = ConversationModel
    chat_memory.ConversationMessage = ConversationMessageModel
    chat_memory.UserProfile = UserProfileModel

    yield session
    session.close()


# Helper functions to call the CRUD functions
def purge_conversations_for_user(db_session, user_id):
    return chat_memory.purge_conversations_for_user(db_session, user_id)


def mark_erase_requested(db_session, user_id):
    return chat_memory.mark_erase_requested(db_session, user_id)


def test_purge_conversations_for_user_no_conversations(db_session):
    """Test purging when user has no conversations"""
    user_id = str(uuid4())

    # Should return 0 when no conversations exist
    deleted_count = purge_conversations_for_user(db_session, user_id)
    assert deleted_count == 0


def test_purge_conversations_for_user_with_conversations(db_session):
    """Test purging when user has conversations"""
    user_id = str(uuid4())
    other_user_id = str(uuid4())

    # Create conversations for the target user
    conv1 = ConversationModel(id=str(uuid4()), user_id=user_id, scan_id="scan1")
    conv2 = ConversationModel(id=str(uuid4()), user_id=user_id, scan_id="scan2")

    # Create conversation for another user (should not be deleted)
    conv3 = ConversationModel(id=str(uuid4()), user_id=other_user_id, scan_id="scan3")

    db_session.add_all([conv1, conv2, conv3])
    db_session.commit()

    # Add messages to the conversations
    msg1 = ConversationMessageModel(conversation_id=conv1.id, role="user", content=json.dumps({"text": "Hello"}))
    msg2 = ConversationMessageModel(
        conversation_id=conv1.id,
        role="assistant",
        content=json.dumps({"summary": "Hi there"}),
    )
    msg3 = ConversationMessageModel(conversation_id=conv2.id, role="user", content=json.dumps({"text": "Question"}))
    msg4 = ConversationMessageModel(
        conversation_id=conv3.id,
        role="user",
        content=json.dumps({"text": "Other user"}),
    )

    db_session.add_all([msg1, msg2, msg3, msg4])
    db_session.commit()

    # Verify initial state
    assert db_session.query(ConversationModel).count() == 3
    assert db_session.query(ConversationMessageModel).count() == 4

    # Purge conversations for target user
    deleted_count = purge_conversations_for_user(db_session, user_id)

    # Should have deleted 2 conversations
    assert deleted_count == 2

    # Verify only the other user's conversation remains
    remaining_convs = db_session.query(ConversationModel).all()
    assert len(remaining_convs) == 1
    assert remaining_convs[0].user_id == other_user_id

    # Messages should be cascade-deleted for target user, but remain for other user
    remaining_msgs = db_session.query(ConversationMessageModel).all()
    assert len(remaining_msgs) == 1
    assert remaining_msgs[0].conversation_id == conv3.id


def test_mark_erase_requested_new_profile(db_session):
    """Test marking erase requested for user without existing profile"""
    user_id = str(uuid4())

    # Should create new profile with erase timestamp
    mark_erase_requested(db_session, user_id)

    profile = db_session.get(UserProfileModel, user_id)
    assert profile is not None
    assert profile.user_id == user_id
    assert profile.erase_requested_at is not None
    assert isinstance(profile.erase_requested_at, datetime)


def test_mark_erase_requested_existing_profile(db_session):
    """Test marking erase requested for user with existing profile"""
    user_id = str(uuid4())

    # Create existing profile
    existing_profile = UserProfileModel(
        user_id=user_id, consent_personalization=True, allergies=json.dumps(["peanuts"]),
    )
    db_session.add(existing_profile)
    db_session.commit()

    # Mark erase requested
    mark_erase_requested(db_session, user_id)

    # Refresh and check
    db_session.refresh(existing_profile)
    assert existing_profile.erase_requested_at is not None
    assert existing_profile.consent_personalization  # Other fields preserved
    assert json.loads(existing_profile.allergies) == ["peanuts"]


def test_purge_conversations_cascade_delete(db_session):
    """Test that messages are properly cascade-deleted when conversations are purged"""
    user_id = str(uuid4())

    # Create conversation with multiple messages
    conv = ConversationModel(id=str(uuid4()), user_id=user_id, scan_id="test_scan")
    db_session.add(conv)
    db_session.commit()

    # Add many messages
    messages = []
    for i in range(10):
        msg = ConversationMessageModel(
            conversation_id=conv.id,
            role="user" if i % 2 == 0 else "assistant",
            content=json.dumps({"text": f"Message {i}"}),
            trace_id=f"trace-{i}",
        )
        messages.append(msg)

    db_session.add_all(messages)
    db_session.commit()

    # Verify initial state
    assert db_session.query(ConversationModel).count() == 1
    assert db_session.query(ConversationMessageModel).count() == 10

    # Purge conversations
    deleted_count = purge_conversations_for_user(db_session, user_id)

    # Verify everything is deleted
    assert deleted_count == 1
    assert db_session.query(ConversationModel).count() == 0
    assert db_session.query(ConversationMessageModel).count() == 0


def test_purge_conversations_multiple_users(db_session):
    """Test that purging only affects the specified user"""
    user1_id = str(uuid4())
    user2_id = str(uuid4())
    user3_id = str(uuid4())

    # Create conversations for multiple users
    convs = [
        ConversationModel(id=str(uuid4()), user_id=user1_id, scan_id="scan1"),
        ConversationModel(id=str(uuid4()), user_id=user1_id, scan_id="scan2"),
        ConversationModel(id=str(uuid4()), user_id=user2_id, scan_id="scan3"),
        ConversationModel(id=str(uuid4()), user_id=user2_id, scan_id="scan4"),
        ConversationModel(id=str(uuid4()), user_id=user3_id, scan_id="scan5"),
    ]

    db_session.add_all(convs)
    db_session.commit()

    # Purge conversations for user2 only
    deleted_count = purge_conversations_for_user(db_session, user2_id)

    # Should have deleted 2 conversations
    assert deleted_count == 2

    # Verify correct conversations remain
    remaining_convs = db_session.query(ConversationModel).all()
    assert len(remaining_convs) == 3

    remaining_user_ids = {conv.user_id for conv in remaining_convs}
    assert user1_id in remaining_user_ids
    assert user3_id in remaining_user_ids
    assert user2_id not in remaining_user_ids
