from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
import logging

# Import existing dependencies
try:
    from core_infra.database import get_db_session
    from core_infra.auth import get_current_active_user
except ImportError:
    # Fallback imports if structure is different
    from api.deps import get_db as get_db_session, get_current_user as get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["devices"])

@router.post("/devices/unregister", status_code=204)
def unregister_device(
    token: Optional[str] = None,
    db: Session = Depends(get_db_session),
    user = Depends(get_current_active_user)
):
    """
    Unregister device push token for the current user.
    
    This endpoint is called before account deletion to clean up
    push notification tokens and device associations.
    """
    user_id = user.id if hasattr(user, 'id') else user
    
    if token:
        try:
            # Delete the specific push token for this user
            result = db.execute(
                text("DELETE FROM device_push_tokens WHERE user_id = :uid AND token = :t"),
                {"uid": user_id, "t": token}
            )
            db.commit()
            
            if result.rowcount > 0:
                logger.info(f"Unregistered push token for user {user_id}")
            else:
                logger.info(f"No push token found for user {user_id} with token {token[:8]}...")
                
        except Exception as e:
            logger.error(f"Failed to unregister push token for user {user_id}: {e}")
            db.rollback()
            # Don't raise exception - this should be idempotent
    else:
        logger.info(f"No push token provided for unregistration by user {user_id}")
    
    return
