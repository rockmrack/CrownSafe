import logging
import os
import time
from datetime import datetime, timezone

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_infra.auth import SECRET_KEY, decode_token, get_current_active_user

# Import existing dependencies
from core_infra.database import get_db
from db.models.account_deletion_audit import AccountDeletionAudit

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Reuse your existing delete/export internals if present
try:
    from api.user_data_endpoints import delete_user_data
except Exception:
    delete_user_data = None

logger = logging.getLogger(__name__)


# Rate limiting helper
def _rate_limit_delete(user_id: int, limit=3, window_sec=86400) -> None:
    """Rate limit account deletion attempts to 3 per day per user"""
    try:
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        key = f"acctdel:rl:{user_id}:{time.strftime('%Y%m%d')}"
        v = r.incr(key)
        if v == 1:
            r.expire(key, window_sec)
        if v > limit:
            raise HTTPException(status_code=429, detail="Too many deletion attempts. Limit: 3 per day.")
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Continue without rate limiting if Redis is unavailable


# Audit logging helper
def _audit(db: Session, user_id: int, jti: str, status: str, source="mobile", meta=None) -> None:
    """Log account deletion attempts for audit trail"""
    try:
        # Check if the audit table exists by trying to query it
        db.execute(text("SELECT 1 FROM account_deletion_audit LIMIT 1"))

        audit_entry = AccountDeletionAudit(user_id=user_id, jti=jti, status=status, source=source, meta=meta or {})
        db.add(audit_entry)
        db.commit()
        logger.info(f"Audit logged: user={user_id}, status={status}, jti={jti[:8] if jti else 'None'}...")
    except Exception as e:
        logger.warning(f"Audit logging skipped (table may not exist): {e}")
        # Continue without audit logging if table doesn't exist


# Token blocklist helper
def _blocklist_access_token(raw_token: str) -> None:
    """Blocklist an access token by adding its JTI to Redis"""
    try:
        # Decode token to get JTI and expiration using the same SECRET_KEY as auth.py
        payload = jwt.decode(raw_token, SECRET_KEY, algorithms=["HS256"])
        jti = payload.get("jti")
        exp = int(payload.get("exp", 0))

        if jti and exp:
            ttl = max(1, exp - int(time.time()))
            r = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
            r.setex(f"jwt:block:{jti}", ttl, "1")
            logger.info(f"Blocklisted token with JTI: {jti[:8]}...")
        else:
            logger.warning("Token missing JTI or EXP claims - cannot blocklist")
    except Exception as e:
        logger.error(f"Failed to blocklist token: {e}")
        # Never fail deletion because of blocklist issues


# Token/session revocation helpers (implementations may live elsewhere)
def revoke_tokens_for_user(db: Session, user_id: int) -> None:
    """Revoke refresh/access tokens in your token store/DB/Redis"""
    try:
        # Revoke user's refresh tokens (if stored in database)
        # NOTE: If using JWT-only without database storage, implement token blacklist
        from db.models.auth import RefreshToken

        deleted_count = db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Revoked {deleted_count} tokens for user {user_id}")
    except ImportError:
        # RefreshToken model doesn't exist - using JWT-only approach
        # In this case, tokens should be blacklisted in Redis/cache
        logger.warning(f"Token revocation not fully implemented - consider adding token blacklist for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
        db.rollback()


def invalidate_push_tokens(db: Session, user_id: int) -> None:
    """Remove FCM/APNS tokens tied to the user"""
    try:
        # Import DeviceToken model and delete user's device tokens
        from api.notification_endpoints import DeviceToken

        deleted_count = db.query(DeviceToken).filter(DeviceToken.user_id == user_id).delete(synchronize_session=False)
        db.commit()
        logger.info(f"Invalidated {deleted_count} push tokens for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate push tokens for user {user_id}: {e}")
        db.rollback()


def unlink_devices_and_sessions(db: Session, user_id: int) -> None:
    """Delete device links; wipe server-side sessions"""
    try:
        # Delete device tokens (already covered by invalidate_push_tokens)
        # Clear any server-side session data
        # NOTE: If using Redis for sessions, clear those as well
        from api.notification_endpoints import DeviceToken

        # Mark devices as inactive instead of deleting (for audit trail)
        updated_count = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == user_id)
            .update({"is_active": False}, synchronize_session=False)
        )
        db.commit()

        logger.info(f"Unlinked {updated_count} devices for user {user_id}")

        # TODO: Clear Redis session cache if implemented
        # redis_client.delete(f"session:user:{user_id}:*")
    except Exception as e:
        logger.error(f"Failed to unlink devices/sessions for user {user_id}: {e}")
        db.rollback()


router = APIRouter(prefix="/api/v1", tags=["account"])


@router.delete(
    "/account",
    status_code=204,
    tags=["account"],
    summary="Delete current account",
    description="Deletes the authenticated user's account and personal data. Requires recent authentication.",
    responses={
        204: {"description": "Account deleted"},
        401: {"description": "Unauthorized or re-authentication required"},
        429: {"description": "Too many requests"},
        500: {"description": "Server error"},
    },
)
def delete_account(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
    token: str = Depends(oauth2_scheme),
) -> None:
    """Delete current user account and all associated data.

    This endpoint meets Apple's in-app account deletion requirements.
    Returns 204 No Content on success.
    """
    user_id = current_user.id if hasattr(current_user, "id") else current_user

    # Require recent auth using token claim (≤5 minutes)
    try:
        payload = decode_token(token)
        auth_time = int(payload.get("auth_time", 0))
        if int(time.time()) - auth_time > 300:  # 5 minutes = 300 seconds
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Re-authentication required",
            )
        jti = payload.get("jti")
    except Exception as e:
        logger.error(f"Failed to validate auth time: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Re-authentication required",
        )

    # Rate limiting: 3 attempts per day
    _rate_limit_delete(user_id)

    # Audit log: request started
    _audit(
        db,
        user_id,
        jti,
        "requested",
        source="mobile",
        meta={
            "path": str(request.url.path),
            "user_agent": request.headers.get("user-agent", "")[:100],
        },
    )

    logger.info(f"Account deletion requested for user {user_id}")

    # Prefer your existing deletion pipeline if available
    if delete_user_data:
        try:
            success = delete_user_data(str(user_id), db)
            if not success:
                _audit(
                    db,
                    user_id,
                    jti,
                    "failed",
                    meta={"error": "delete_user_data returned False"},
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to delete user data",
                )
        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            _audit(db, user_id, jti, "failed", meta={"error": str(e)[:200]})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user data",
            )
    else:
        # Minimal fallback: soft-delete + PII scrub (keep legally required data only)
        try:
            # This would need to be adapted to your actual User model
            if hasattr(current_user, "is_active"):
                current_user.is_active = False
            if hasattr(current_user, "deleted_at"):
                current_user.deleted_at = datetime.now(timezone.utc)
            if hasattr(current_user, "email") and current_user.email:
                current_user.email = f"deleted+{user_id}@example.invalid"
            if hasattr(current_user, "full_name"):
                current_user.full_name = None

            db.add(current_user)
            db.commit()
            logger.info(f"Soft-deleted user {user_id}")
        except Exception as e:
            logger.error(f"Failed to soft-delete user {user_id}: {e}")
            _audit(db, user_id, jti, "failed", meta={"error": str(e)[:200]})
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account",
            )

    # Clean up related data (check table existence first)
    cleanup_configs = [
        ("refresh_tokens", "refresh tokens"),
        ("device_push_tokens", "push tokens"),
        ("user_sessions", "sessions"),
    ]

    for table_name, description in cleanup_configs:
        try:
            # Check if table exists first
            check_query = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = :table_name
                )
            """
            table_exists = db.execute(text(check_query), {"table_name": table_name}).scalar()

            if table_exists:
                # Use a separate transaction for each cleanup
                with db.begin():
                    delete_query = f"DELETE FROM {table_name} WHERE user_id = :uid"
                    result = db.execute(text(delete_query), {"uid": user_id})
                    deleted_count = result.rowcount if hasattr(result, "rowcount") else 0
                    logger.info(f"Cleaned up {deleted_count} {description} for user {user_id}")
            else:
                logger.debug(f"Skipping cleanup of {description} - table {table_name} does not exist")
        except Exception as e:
            logger.warning(f"Could not clean up {description}: {e}")
            # Continue with next cleanup - don't let cleanup failures stop account deletion

    # Commit all changes
    try:
        db.commit()
        logger.info(f"Account deletion completed for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to commit changes: {e}")

    # Blocklist the current access token
    _blocklist_access_token(token)

    # Audit log: deletion completed successfully
    _audit(db, user_id, jti, "completed")

    logger.info(f"Account deletion completed for user {user_id}")
    # 204 No Content
    return
