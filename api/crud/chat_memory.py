from __future__ import annotations
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from sqlalchemy import delete, select, func
from datetime import datetime
from api.models.chat_memory import UserProfile, Conversation, ConversationMessage

def get_profile(db: Session, user_id: UUID) -> Optional[UserProfile]:
    return db.get(UserProfile, user_id)

def upsert_profile(db: Session, user_id: UUID, data: Dict[str, Any]) -> UserProfile:
    obj = db.get(UserProfile, user_id)
    if not obj:
        obj = UserProfile(user_id=user_id)
        db.add(obj)
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj

def get_or_create_conversation(db: Session, conv_id: Optional[UUID], user_id: Optional[UUID], scan_id: Optional[str]) -> Conversation:
    if conv_id:
        c = db.get(Conversation, conv_id)
        if c:
            return c
    c = Conversation(id=uuid4(), user_id=user_id, scan_id=scan_id)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

def log_message(db: Session, conversation: Conversation, *, role: str, content: Dict[str, Any], intent: Optional[str], trace_id: Optional[str]):
    m = ConversationMessage(conversation_id=conversation.id, role=role, content=content, intent=intent, trace_id=trace_id)
    conversation.last_activity_at = datetime.utcnow()
    db.add(m)
    db.commit()

def purge_conversations_for_user(db: Session, user_id: Union[UUID, str]) -> int:
    """
    Hard-delete all conversations/messages for user_id.
    Returns number of conversations removed. Messages are cascade-deleted.
    """
    # Convert string to UUID if needed
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    stmt = select(Conversation.id).where(Conversation.user_id == user_id)
    conv_ids = [row[0] for row in db.execute(stmt).all()]
    if not conv_ids:
        return 0
    db.execute(delete(Conversation).where(Conversation.id.in_(conv_ids)))
    db.commit()
    return len(conv_ids)

def mark_erase_requested(db: Session, user_id: Union[UUID, str]) -> None:
    # Convert string to UUID if needed
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    prof = db.get(UserProfile, user_id)
    if not prof:
        prof = UserProfile(user_id=user_id)
        db.add(prof)
    from datetime import datetime, timezone
    prof.erase_requested_at = datetime.now(tz=timezone.utc)
    db.commit()
