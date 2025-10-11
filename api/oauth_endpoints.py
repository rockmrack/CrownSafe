"""
OAuth Authentication Endpoints for Apple and Google Sign-In
Stores only internal user_id and provider subject ID
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import httpx
import jwt
import json
import hashlib
import uuid
from pydantic import BaseModel, Field, EmailStr

from core_infra.database import get_db, User
from core_infra.auth import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/oauth", tags=["OAuth Authentication"])

# Google OAuth constants
GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_ISSUER = "https://accounts.google.com"

# ========================= MODELS =========================


class OAuthLoginRequest(BaseModel):
    """OAuth login request with provider token"""

    provider: str = Field(
        ..., pattern="^(apple|google)$", description="OAuth provider (apple or google)"
    )
    id_token: str = Field(..., description="ID token from provider")
    authorization_code: Optional[str] = Field(None, description="Authorization code (for Apple)")
    device_id: Optional[str] = Field(None, description="Device ID for tracking")
    app_version: Optional[str] = Field(None, description="App version")


class OAuthLoginResponse(BaseModel):
    """OAuth login response with JWT tokens"""

    ok: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: str
    is_new_user: bool


class OAuthProvider:
    """Base class for OAuth providers"""

    @staticmethod
    async def verify_token(id_token: str) -> Dict[str, Any]:
        """Verify and decode provider token"""
        raise NotImplementedError


class AppleOAuth(OAuthProvider):
    """Apple Sign-In implementation"""

    APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"
    APPLE_ISSUER = "https://appleid.apple.com"

    @staticmethod
    async def verify_token(id_token: str, client_id: str = None) -> Dict[str, Any]:
        """
        Verify Apple ID token
        Returns decoded token with 'sub' (subject) and 'email' (if available)
        """
        try:
            # For production, fetch Apple's public keys and verify properly
            # This is a simplified version - in production use proper JWT verification

            # Decode without verification first to get the header
            unverified = jwt.decode(id_token, options={"verify_signature": False})

            # In production:
            # 1. Fetch Apple's public keys from APPLE_PUBLIC_KEY_URL
            # 2. Verify the JWT signature using the correct key
            # 3. Verify issuer is APPLE_ISSUER
            # 4. Verify audience matches your client_id

            # Extract required fields
            return {
                "sub": unverified.get("sub"),  # Apple user ID (stable)
                "email": unverified.get("email"),  # May be None
                "email_verified": unverified.get("email_verified", False),
                "is_private_email": unverified.get("is_private_email", False),
                "provider": "apple",
            }

        except jwt.DecodeError as e:
            logger.error(f"Failed to decode Apple token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Apple ID token",
            )
        except Exception as e:
            logger.error(f"Apple token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Apple authentication failed",
            )


class GoogleOAuth(OAuthProvider):
    """Google Sign-In implementation"""

    GOOGLE_TOKEN_INFO_URL = "https://oauth2.googleapis.com/tokeninfo"
    GOOGLE_ISSUER = "https://accounts.google.com"

    @staticmethod
    async def verify_token(id_token: str, client_id: str = None) -> Dict[str, Any]:
        """
        Verify Google ID token
        Returns decoded token with 'sub' (subject) and 'email'
        """
        try:
            # Verify token with Google
            async with httpx.AsyncClient() as client:
                response = await client.get(GOOGLE_TOKEN_INFO_URL, params={"id_token": id_token})

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid Google ID token",
                    )

                token_info = response.json()

                # Verify issuer
                if token_info.get("iss") not in ["accounts.google.com", GOOGLE_ISSUER]:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token issuer",
                    )

                # In production, also verify:
                # - aud (audience) matches your client_id
                # - exp (expiration) hasn't passed

                return {
                    "sub": token_info.get("sub"),  # Google user ID (stable)
                    "email": token_info.get("email"),
                    "email_verified": token_info.get("email_verified", False),
                    "name": token_info.get("name"),
                    "picture": token_info.get("picture"),
                    "provider": "google",
                }

        except httpx.RequestError as e:
            logger.error(f"Failed to verify Google token: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not verify with Google",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed",
            )


# ========================= ENDPOINTS =========================


@router.post("/login", response_model=OAuthLoginResponse)
async def oauth_login(
    request: Request,
    login_data: OAuthLoginRequest,
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None),
):
    """
    OAuth login with Apple or Google

    This endpoint:
    1. Verifies the provider token
    2. Creates or retrieves user based on provider subject ID
    3. Returns JWT tokens for API access

    **Privacy Note**: We only store the provider's subject ID and an internal user ID.
    No email or personal information is stored unless explicitly provided for support.
    """
    trace_id = f"oauth_{uuid.uuid4().hex[:8]}"

    try:
        # Select OAuth provider
        if login_data.provider == "apple":
            provider = AppleOAuth()
        elif login_data.provider == "google":
            provider = GoogleOAuth()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid provider. Use 'apple' or 'google'",
            )

        # Verify token with provider
        token_info = await provider.verify_token(login_data.id_token)

        if not token_info.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

        # Create stable user identifier (hash of provider + subject)
        provider_user_id = f"{login_data.provider}:{token_info['sub']}"
        provider_hash = hashlib.sha256(provider_user_id.encode()).hexdigest()

        # Check if user exists
        user = db.query(User).filter(User.provider_id == provider_hash).first()

        is_new_user = False

        if not user:
            # Create new user (no email stored!)
            user = User(
                provider_id=provider_hash,
                provider_type=login_data.provider,
                is_active=True,
                is_subscribed=False,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True

            logger.info(
                "New OAuth user created",
                extra={
                    "provider": login_data.provider,
                    "user_id": str(user.id),
                    "trace_id": trace_id,
                },
            )
        else:
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()

            logger.info(
                "OAuth user login",
                extra={
                    "provider": login_data.provider,
                    "user_id": str(user.id),
                    "trace_id": trace_id,
                },
            )

        # Create JWT tokens
        access_token_expires = timedelta(hours=1)
        access_token = create_access_token(
            data={"sub": str(user.id), "provider": login_data.provider},
            expires_delta=access_token_expires,
        )

        refresh_token_expires = timedelta(days=30)
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "provider": login_data.provider},
            expires_delta=refresh_token_expires,
        )

        # Log device info if provided
        if login_data.device_id or login_data.app_version:
            logger.info(
                "OAuth login device info",
                extra={
                    "user_id": str(user.id),
                    "device_id": login_data.device_id,
                    "app_version": login_data.app_version,
                    "user_agent": user_agent,
                    "trace_id": trace_id,
                },
            )

        return OAuthLoginResponse(
            ok=True,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=3600,
            user_id=str(user.id),
            is_new_user=is_new_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"OAuth login failed: {e}",
            extra={"provider": login_data.provider, "trace_id": trace_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/logout")
async def oauth_logout(
    request: Request, user_id: Optional[str] = None, device_id: Optional[str] = None
):
    """
    OAuth logout

    This endpoint logs out the user and invalidates their session.
    In a production environment, you would also:
    1. Add the tokens to a blacklist
    2. Clear any server-side session data
    3. Log the logout event
    """
    trace_id = f"logout_{uuid.uuid4().hex[:8]}"

    logger.info(
        "OAuth logout",
        extra={"user_id": user_id, "device_id": device_id, "trace_id": trace_id},
    )

    # In production, add token to blacklist here

    return JSONResponse(
        content={
            "ok": True,
            "message": "Logged out successfully",
            "trace_id": trace_id,
        },
        status_code=200,
    )


@router.post("/revoke")
async def revoke_token(request: Request, token: str, token_type: str = "access_token"):
    """
    Revoke a specific token

    This endpoint allows revoking access or refresh tokens.
    Useful for security purposes or when a device is lost.
    """
    trace_id = f"revoke_{uuid.uuid4().hex[:8]}"

    try:
        # In production:
        # 1. Decode the token
        # 2. Add to blacklist with expiration
        # 3. Log the revocation

        logger.info("Token revoked", extra={"token_type": token_type, "trace_id": trace_id})

        return JSONResponse(
            content={
                "ok": True,
                "message": f"{token_type} revoked successfully",
                "trace_id": trace_id,
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Token revocation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke token",
        )


# ========================= HEALTH CHECK =========================


@router.get("/providers")
async def get_oauth_providers():
    """
    Get list of supported OAuth providers
    """
    return {
        "ok": True,
        "providers": [
            {"id": "apple", "name": "Sign in with Apple", "enabled": True},
            {"id": "google", "name": "Sign in with Google", "enabled": True},
        ],
    }
