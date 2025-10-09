"""
Chat memory CRUD operations - stub implementation for chat router
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session


def get_profile(db: Session, user_id: Optional[UUID]):
    """Get user profile for chat personalization"""
    return None


def get_or_create_conversation(
    db: Session, conversation_id: Optional[UUID], user_id: Optional[UUID], scan_id: str
):
    """Get or create conversation record"""

    # Return a simple object with an id
    class MockConversation:
        def __init__(self):
            self.id = conversation_id or UUID("00000000-0000-0000-0000-000000000000")

    return MockConversation()


def log_message(
    db: Session,
    conversation,
    role: str,
    content: Dict[str, Any],
    intent: str = None,
    trace_id: str = None,
):
    """Log chat message"""
    pass


def upsert_profile(db: Session, user_id: UUID, profile_data: Dict[str, Any]):
    """Update or insert user profile"""
    pass


def mark_erase_requested(db: Session, user_id: UUID):
    """Mark user data for erasure"""
    pass


def purge_conversations_for_user(db: Session, user_id: UUID):
    """Purge all conversations for user"""
    pass
