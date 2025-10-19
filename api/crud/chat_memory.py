"""
Chat memory CRUD operations - stub implementation for chat router
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from api.models.chat_memory import Conversation, ConversationMessage, UserProfile


def _get_column_python_type(column) -> Optional[type]:
    """Safely retrieve a column's python_type attribute."""

    try:
        return column.property.columns[0].type.python_type
    except (AttributeError, IndexError, NotImplementedError):
        return None


def _normalize_uuid_for_column(
    column,
    uuid_value: Optional[Union[UUID, str]],
) -> Optional[Union[UUID, str]]:
    """Normalize UUID values according to the target column type."""

    if uuid_value is None:
        return None

    if isinstance(uuid_value, UUID):
        normalized_uuid = uuid_value
    elif isinstance(uuid_value, str):
        try:
            normalized_uuid = UUID(uuid_value)
        except ValueError as exc:
            raise ValueError(f"Invalid UUID string provided: {uuid_value!r}") from exc
    else:
        raise TypeError(
            f"uuid_value must be a UUID, string, or None. Got {type(uuid_value).__name__}: {uuid_value!r}"
        )

    column_python_type = _get_column_python_type(column)
    if column_python_type is UUID:
        return normalized_uuid

    return str(normalized_uuid)


def get_profile(db: Session, user_id: Optional[UUID]):
    """Get user profile for chat personalization"""
    if user_id is None:
        return None
    normalized_user_id = _normalize_uuid_for_column(UserProfile.user_id, user_id)
    return (
        db.query(UserProfile).filter(UserProfile.user_id == normalized_user_id).first()
    )


def get_or_create_conversation(
    db: Session,
    conversation_id: Optional[UUID],
    user_id: Optional[UUID],
    scan_id: str,
):
    """Get or create conversation record.

    Note: Uses _uuid_to_str() helper for cross-database compatibility.
    """
    # If conversation_id provided, try to get existing
    if conversation_id:
        normalized_conv_id = _normalize_uuid_for_column(
            Conversation.id, conversation_id
        )
        conv = (
            db.query(Conversation).filter(Conversation.id == normalized_conv_id).first()
        )
        if conv:
            return conv

    # Create new conversation
    conv = Conversation(
        id=_normalize_uuid_for_column(Conversation.id, uuid4()),
        user_id=_normalize_uuid_for_column(Conversation.user_id, user_id),
        scan_id=scan_id,
        started_at=datetime.utcnow(),
        last_activity_at=datetime.utcnow(),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def log_message(
    db: Session,
    conversation: Conversation,
    role: str,
    content: Dict[str, Any],
    intent: Optional[str] = None,
    trace_id: Optional[str] = None,
):
    """Log chat message to conversation.

    Note: Content is serialized to JSON string for database compatibility across
    different schema versions (Text vs JSON column types). When retrieving messages,
    deserialize using json.loads(message.content).

    Args:
        db: Database session
        conversation: Conversation object
        role: Message role (currently 'user' and 'assistant' are supported upstream)
        content: Message content dictionary (must be JSON-serializable)
        intent: Optional intent classification
        trace_id: Optional trace ID for debugging

    Raises:
        ValueError: If content is not a valid dictionary or not JSON-serializable
    """
    # Validate content structure before serialization
    if not isinstance(content, dict):
        raise ValueError("Content must be a dictionary.")

    # Validate that content is JSON-serializable to prevent injection
    try:
        serialized_content = json.dumps(content)
    except (TypeError, ValueError) as e:
        raise ValueError("Content must be JSON-serializable.") from e

    message = ConversationMessage(
        conversation_id=conversation.id,
        role=role,
        content=serialized_content,
        intent=intent,
        trace_id=trace_id,
        created_at=datetime.utcnow(),
    )
    db.add(message)

    # Update conversation last_activity_at
    conversation.last_activity_at = datetime.utcnow()
    db.commit()
    db.refresh(message)
    return message


def upsert_profile(db: Session, user_id: UUID, profile_data: Dict[str, Any]):
    """Update or insert user profile

    Note: Converts UUID to appropriate type based on database.
    SQLite uses String(36), PostgreSQL uses UUID type.
    """
    # Define allowed profile fields (allowlist for security)
    ALLOWED_FIELDS = {
        "consent_personalization",
        "memory_paused",
        "allergies",
        "pregnancy_trimester",
        "pregnancy_due_date",
        "child_birthdate",
        "erase_requested_at",
    }

    user_id_value = _normalize_uuid_for_column(UserProfile.user_id, user_id)

    # Try to get existing profile
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id_value).first()

    if profile:
        # Update existing - only allowed fields
        for key, value in profile_data.items():
            if key in ALLOWED_FIELDS:
                setattr(profile, key, value)
        profile.updated_at = datetime.utcnow()
    else:
        # Create new - filter to allowed fields only
        filtered_data = {k: v for k, v in profile_data.items() if k in ALLOWED_FIELDS}
        profile = UserProfile(
            user_id=user_id_value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **filtered_data,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile


def mark_erase_requested(db: Session, user_id: Union[UUID, str]):
    """Mark user data for erasure

    Creates profile if it doesn't exist.

    Args:
        db: Database session
        user_id: UUID or string representation of the user to mark for erasure
    """
    # Normalize UUID based on the actual column type in the database
    user_id_value = _normalize_uuid_for_column(UserProfile.user_id, user_id)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id_value).first()

    if not profile:
        # Create new profile with erase request
        profile = UserProfile(
            user_id=user_id_value,
            erase_requested_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
    else:
        profile.erase_requested_at = datetime.utcnow()

    db.commit()


def purge_conversations_for_user(db: Session, user_id: Union[UUID, str]):
    """Purge all conversations for user

    Deletes all conversations and their associated messages (via cascade).
    Uses synchronize_session='fetch' to ensure ORM tracks the deletion properly.

    Args:
        db: Database session
        user_id: UUID or string UUID of the user whose conversations to purge

    Returns:
        int: Number of conversations deleted
    """
    # Normalize user_id to handle both UUID and string types
    # Try UUID first (for PostgreSQL), then string (for SQLite compatibility)
    if isinstance(user_id, str):
        user_id_uuid = UUID(user_id)
        user_id_str = user_id
    else:
        user_id_uuid = user_id
        user_id_str = str(user_id)

    # Try querying with both formats to handle different column types
    # PostgreSQL uses UUID type, SQLite tests use String type
    # First try UUID (for PostgreSQL)
    conversation_ids = [
        row[0]
        for row in db.query(Conversation.id)
        .filter(Conversation.user_id == user_id_uuid)
        .all()
    ]

    # If UUID query found nothing, try string query (for SQLite)
    if not conversation_ids:
        conversation_ids = [
            row[0]
            for row in db.query(Conversation.id)
            .filter(Conversation.user_id == user_id_str)
            .all()
        ]

    if not conversation_ids:
        return 0

    # Delete messages first (explicit delete for test compatibility)
    db.query(ConversationMessage).filter(
        ConversationMessage.conversation_id.in_(conversation_ids)
    ).delete(synchronize_session=False)

    # Delete conversations with same UUID/String fallback logic
    # First try UUID (for PostgreSQL)
    deleted_count = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id_uuid)
        .delete(synchronize_session=False)
    )

    # If UUID delete didn't work, try string (for SQLite)
    if deleted_count == 0:
        deleted_count = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id_str)
            .delete(synchronize_session=False)
        )

    db.commit()

    # Return the actual count if database reported it
    if deleted_count:
        return deleted_count

    # Some database backends (notably older SQLite builds) return 0 for bulk deletes
    # even when rows were removed. Fall back to the number of conversations we
    # targeted minus any that still remain.
    remaining = (
        db.query(Conversation).filter(Conversation.id.in_(conversation_ids)).count()
    )
    return max(len(conversation_ids) - remaining, 0)
