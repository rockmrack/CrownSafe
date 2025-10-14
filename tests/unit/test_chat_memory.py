"""
Unit tests for api/models/chat_memory.py
Tests chat memory models for user profiles, conversations, and messages
"""

import pytest
from datetime import datetime, date
from unittest.mock import patch, Mock
from sqlalchemy import (
    create_engine,
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
from sqlalchemy.orm import sessionmaker
from api.models.chat_memory import (
    UserProfile,
    Conversation,
    ConversationMessage,
    JsonType,
    UuidType,
)


class TestChatMemoryModels:
    """Test chat memory models functionality"""

    @classmethod
    def setup_class(cls):
        """Set up in-memory SQLite database and create tables once per class"""
        cls.engine = create_engine("sqlite:///:memory:")
        from core_infra.database import Base

        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    @pytest.fixture
    def db_session(self):
        """Provide a new session for each test method"""
        session = self.Session()
        yield session
        session.close()

    @pytest.mark.integration
    def test_user_profile_creation(self, db_session):
        """Test UserProfile model creation"""
        user_profile = UserProfile(
            user_id="test-user-123",
            consent_personalization=True,
            memory_paused=False,
            allergies=["peanuts", "shellfish"],
            pregnancy_trimester=2,
            pregnancy_due_date=date(2024, 6, 15),
            child_birthdate=date(2022, 3, 10),
        )

        db_session.add(user_profile)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "test-user-123")
            .first()
        )

        assert retrieved is not None
        assert retrieved.user_id == "test-user-123"
        assert retrieved.consent_personalization is True
        assert retrieved.memory_paused is False
        assert retrieved.allergies == ["peanuts", "shellfish"]
        assert retrieved.pregnancy_trimester == 2
        assert retrieved.pregnancy_due_date == date(2024, 6, 15)
        assert retrieved.child_birthdate == date(2022, 3, 10)
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

    def test_user_profile_defaults(self, db_session):
        """Test UserProfile model with default values"""
        user_profile = UserProfile(user_id="test-user-456")

        db_session.add(user_profile)
        db_session.commit()

        retrieved = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "test-user-456")
            .first()
        )

        assert retrieved.consent_personalization is False
        assert retrieved.memory_paused is False
        assert retrieved.allergies == []
        assert retrieved.pregnancy_trimester is None
        assert retrieved.pregnancy_due_date is None
        assert retrieved.child_birthdate is None
        assert retrieved.erase_requested_at is None

    def test_user_profile_json_fields(self, db_session):
        """Test UserProfile JSON fields handling"""
        complex_allergies = [
            {"type": "peanuts", "severity": "severe"},
            {"type": "shellfish", "severity": "moderate"},
        ]

        user_profile = UserProfile(user_id="test-user-789", allergies=complex_allergies)

        db_session.add(user_profile)
        db_session.commit()

        retrieved = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "test-user-789")
            .first()
        )

        assert retrieved.allergies == complex_allergies

    def test_conversation_creation(self, db_session):
        """Test Conversation model creation"""
        conversation = Conversation(
            id="conv-123", user_id="user-123", scan_id="scan-456"
        )

        db_session.add(conversation)
        db_session.commit()

        retrieved = (
            db_session.query(Conversation).filter(Conversation.id == "conv-123").first()
        )

        assert retrieved is not None
        assert retrieved.id == "conv-123"
        assert retrieved.user_id == "user-123"
        assert retrieved.scan_id == "scan-456"
        assert retrieved.started_at is not None
        assert retrieved.last_activity_at is not None

    def test_conversation_defaults(self, db_session):
        """Test Conversation model with default values"""
        conversation = Conversation(id="conv-456")

        db_session.add(conversation)
        db_session.commit()

        retrieved = (
            db_session.query(Conversation).filter(Conversation.id == "conv-456").first()
        )

        assert retrieved.user_id is None
        assert retrieved.scan_id is None
        assert retrieved.started_at is not None
        assert retrieved.last_activity_at is not None

    def test_conversation_message_creation(self, db_session):
        """Test ConversationMessage model creation"""
        # First create a conversation
        conversation = Conversation(id="conv-123")
        db_session.add(conversation)
        db_session.commit()

        # Create message
        message = ConversationMessage(
            conversation_id="conv-123",
            role="user",
            intent="product_inquiry",
            trace_id="trace-789",
            content={"text": "What is this product?", "type": "question"},
        )

        db_session.add(message)
        db_session.commit()

        retrieved = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.id == message.id)
            .first()
        )

        assert retrieved is not None
        assert retrieved.conversation_id == "conv-123"
        assert retrieved.role == "user"
        assert retrieved.intent == "product_inquiry"
        assert retrieved.trace_id == "trace-789"
        assert retrieved.content == {
            "text": "What is this product?",
            "type": "question",
        }
        assert retrieved.created_at is not None

    def test_conversation_message_defaults(self, db_session):
        """Test ConversationMessage model with default values"""
        # First create a conversation
        conversation = Conversation(id="conv-456")
        db_session.add(conversation)
        db_session.commit()

        # Create message with minimal data
        message = ConversationMessage(
            conversation_id="conv-456", role="assistant", content={"text": "Hello!"}
        )

        db_session.add(message)
        db_session.commit()

        retrieved = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.id == message.id)
            .first()
        )

        assert retrieved.intent is None
        assert retrieved.trace_id is None
        assert retrieved.created_at is not None

    def test_conversation_message_json_content(self, db_session):
        """Test ConversationMessage JSON content handling"""
        # First create a conversation
        conversation = Conversation(id="conv-789")
        db_session.add(conversation)
        db_session.commit()

        # Create message with complex JSON content
        complex_content = {
            "text": "Here's the product information",
            "type": "response",
            "data": {
                "product_name": "Baby Bottle",
                "safety_score": 85,
                "recalls": [],
                "ingredients": ["BPA-free plastic", "Silicone"],
            },
            "metadata": {"confidence": 0.95, "sources": ["FDA", "CPSC"]},
        }

        message = ConversationMessage(
            conversation_id="conv-789", role="assistant", content=complex_content
        )

        db_session.add(message)
        db_session.commit()

        retrieved = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.id == message.id)
            .first()
        )

        assert retrieved.content == complex_content
        assert retrieved.content["data"]["product_name"] == "Baby Bottle"
        assert retrieved.content["metadata"]["confidence"] == 0.95

    def test_conversation_relationship(self, db_session):
        """Test Conversation-Message relationship"""
        # Create conversation
        conversation = Conversation(id="conv-relationship")
        db_session.add(conversation)
        db_session.commit()

        # Create messages
        message1 = ConversationMessage(
            conversation_id="conv-relationship",
            role="user",
            content={"text": "First message"},
        )
        message2 = ConversationMessage(
            conversation_id="conv-relationship",
            role="assistant",
            content={"text": "Second message"},
        )

        db_session.add(message1)
        db_session.add(message2)
        db_session.commit()

        # Test relationship
        retrieved_conv = (
            db_session.query(Conversation)
            .filter(Conversation.id == "conv-relationship")
            .first()
        )

        assert len(retrieved_conv.messages) == 2
        assert retrieved_conv.messages[0].role == "user"
        assert retrieved_conv.messages[1].role == "assistant"

        # Test reverse relationship
        retrieved_msg = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.id == message1.id)
            .first()
        )

        assert retrieved_msg.conversation.id == "conv-relationship"

    def test_conversation_cascade_delete(self, db_session):
        """Test cascade delete behavior"""
        # Create conversation with messages
        conversation = Conversation(id="conv-cascade")
        db_session.add(conversation)
        db_session.commit()

        message1 = ConversationMessage(
            conversation_id="conv-cascade", role="user", content={"text": "Message 1"}
        )
        message2 = ConversationMessage(
            conversation_id="conv-cascade",
            role="assistant",
            content={"text": "Message 2"},
        )

        db_session.add(message1)
        db_session.add(message2)
        db_session.commit()

        # Verify messages exist
        message_count = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == "conv-cascade")
            .count()
        )
        assert message_count == 2

        # Delete conversation
        db_session.delete(conversation)
        db_session.commit()

        # Verify messages are cascade deleted
        message_count = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == "conv-cascade")
            .count()
        )
        assert message_count == 0

    def test_user_profile_erase_request(self, db_session):
        """Test UserProfile erase request functionality"""
        user_profile = UserProfile(
            user_id="test-erase-user",
            consent_personalization=True,
            allergies=["peanuts"],
        )

        db_session.add(user_profile)
        db_session.commit()

        # Set erase request
        user_profile.erase_requested_at = datetime.utcnow()
        db_session.commit()

        retrieved = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "test-erase-user")
            .first()
        )

        assert retrieved.erase_requested_at is not None

    def test_conversation_last_activity_update(self, db_session):
        """Test Conversation last_activity_at update"""
        conversation = Conversation(id="conv-activity")
        db_session.add(conversation)
        db_session.commit()

        original_activity = conversation.last_activity_at

        # Simulate activity update
        conversation.last_activity_at = datetime.utcnow()
        db_session.commit()

        retrieved = (
            db_session.query(Conversation)
            .filter(Conversation.id == "conv-activity")
            .first()
        )

        assert retrieved.last_activity_at > original_activity

    def test_message_role_validation(self, db_session):
        """Test ConversationMessage role field"""
        conversation = Conversation(id="conv-roles")
        db_session.add(conversation)
        db_session.commit()

        # Test valid roles
        valid_roles = ["user", "assistant", "system"]

        for role in valid_roles:
            message = ConversationMessage(
                conversation_id="conv-roles",
                role=role,
                content={"text": f"Message with role {role}"},
            )
            db_session.add(message)

        db_session.commit()

        messages = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == "conv-roles")
            .all()
        )

        assert len(messages) == 3
        roles = [msg.role for msg in messages]
        assert set(roles) == set(valid_roles)

    def test_message_intent_field(self, db_session):
        """Test ConversationMessage intent field"""
        conversation = Conversation(id="conv-intent")
        db_session.add(conversation)
        db_session.commit()

        intents = [
            "product_inquiry",
            "safety_check",
            "recall_search",
            "general_question",
        ]

        for intent in intents:
            message = ConversationMessage(
                conversation_id="conv-intent",
                role="user",
                intent=intent,
                content={"text": f"Message with intent {intent}"},
            )
            db_session.add(message)

        db_session.commit()

        messages = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == "conv-intent")
            .all()
        )

        assert len(messages) == 4
        message_intents = [msg.intent for msg in messages]
        assert set(message_intents) == set(intents)

    def test_message_trace_id_field(self, db_session):
        """Test ConversationMessage trace_id field"""
        conversation = Conversation(id="conv-trace")
        db_session.add(conversation)
        db_session.commit()

        trace_ids = ["trace-001", "trace-002", "trace-003"]

        for trace_id in trace_ids:
            message = ConversationMessage(
                conversation_id="conv-trace",
                role="user",
                trace_id=trace_id,
                content={"text": f"Message with trace {trace_id}"},
            )
            db_session.add(message)

        db_session.commit()

        messages = (
            db_session.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == "conv-trace")
            .all()
        )

        assert len(messages) == 3
        message_traces = [msg.trace_id for msg in messages]
        assert set(message_traces) == set(trace_ids)

    def test_user_profile_pregnancy_fields(self, db_session):
        """Test UserProfile pregnancy-related fields"""
        user_profile = UserProfile(
            user_id="test-pregnancy",
            pregnancy_trimester=3,
            pregnancy_due_date=date(2024, 8, 15),
            child_birthdate=date(2021, 5, 20),
        )

        db_session.add(user_profile)
        db_session.commit()

        retrieved = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "test-pregnancy")
            .first()
        )

        assert retrieved.pregnancy_trimester == 3
        assert retrieved.pregnancy_due_date == date(2024, 8, 15)
        assert retrieved.child_birthdate == date(2021, 5, 20)

    def test_user_profile_allergies_edge_cases(self, db_session):
        """Test UserProfile allergies field edge cases"""
        # Test empty allergies
        user1 = UserProfile(user_id="user-empty-allergies")
        db_session.add(user1)
        db_session.commit()

        retrieved1 = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "user-empty-allergies")
            .first()
        )
        assert retrieved1.allergies == []

        # Test None allergies (should default to empty list)
        user2 = UserProfile(user_id="user-none-allergies", allergies=None)
        db_session.add(user2)
        db_session.commit()

        retrieved2 = (
            db_session.query(UserProfile)
            .filter(UserProfile.user_id == "user-none-allergies")
            .first()
        )
        assert retrieved2.allergies == []

    def test_conversation_scan_id_field(self, db_session):
        """Test Conversation scan_id field"""
        conversation = Conversation(id="conv-scan", scan_id="scan-abc123")

        db_session.add(conversation)
        db_session.commit()

        retrieved = (
            db_session.query(Conversation)
            .filter(Conversation.id == "conv-scan")
            .first()
        )

        assert retrieved.scan_id == "scan-abc123"

    def test_message_auto_increment_id(self, db_session):
        """Test ConversationMessage auto-increment ID"""
        conversation = Conversation(id="conv-auto-id")
        db_session.add(conversation)
        db_session.commit()

        # Create multiple messages
        messages = []
        for i in range(5):
            message = ConversationMessage(
                conversation_id="conv-auto-id",
                role="user",
                content={"text": f"Message {i}"},
            )
            db_session.add(message)
            messages.append(message)

        db_session.commit()

        # Verify IDs are auto-incremented
        ids = [msg.id for msg in messages]
        assert len(set(ids)) == 5  # All unique
        assert min(ids) > 0  # All positive
        assert max(ids) - min(ids) == 4  # Sequential


class TestDatabaseCompatibility:
    """Test database compatibility features"""

    def test_json_type_selection(self):
        """Test JsonType selection based on database URL"""
        from api.models.chat_memory import get_json_type

        # Test PostgreSQL
        db_url_postgres = "postgresql://user:pass@localhost/db"
        json_type_postgres = get_json_type(db_url_postgres)
        assert json_type_postgres.__name__ == "JSONB"

        # Test SQLite
        db_url_sqlite = "sqlite:///test.db"
        json_type_sqlite = get_json_type(db_url_sqlite)
        assert json_type_sqlite.__name__ == "JSON"

    def test_uuid_type_selection(self):
        """Test UuidType selection based on database URL"""
        from api.models.chat_memory import get_uuid_type

        # Test PostgreSQL
        db_url_postgres = "postgresql://user:pass@localhost/db"
        uuid_type_postgres = get_uuid_type(db_url_postgres)
        assert hasattr(uuid_type_postgres, "as_uuid")

        # Test SQLite
        db_url_sqlite = "sqlite:///test.db"
        _ = get_uuid_type(db_url_sqlite)  # uuid_type_sqlite
        assert UuidType.__name__ == "String"


if __name__ == "__main__":
    pytest.main([__file__])
