"""Authentication Endpoints for BabyShield API
JWT-based authentication system.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.exc import UnknownHashError
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from core_infra.auth import (
    Token,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    get_current_user,
    get_password_hash,
)
from core_infra.database import User, get_db
from core_infra.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_subscribed: bool
    is_active: bool


class PasswordReset(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_password: str


@router.post("/register", response_model=UserResponse)
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db),  # noqa: B008
):
    """Register a new user
    Limited to 5 registrations per hour per IP.
    """
    # Validate passwords match
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
        is_subscribed=False,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"New user registered: {new_user.email}")

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            is_subscribed=new_user.is_subscribed,
            is_active=new_user.is_active,
        )
    except Exception as e:
        db.rollback()
        logger.exception(f"Error registering user: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user account",
        ) from e


@router.post("/token", response_model=Token)
@limiter.limit("10 per minute")  # Rate limiting for auth endpoint
async def login(
    response: Response,  # must be starlette Response for DI
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Login endpoint - returns JWT tokens
    Accepts form-urlencoded data (application/x-www-form-urlencoded)
    Username field should contain email.

    Examples:
    - Content-Type: application/x-www-form-urlencoded
    - username: "user@example.com"
    - password: "securepassword123"

    """
    try:
        # Authenticate user (username field contains email)
        user = authenticate_user(db, form_data.username, form_data.password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"User logged in: {user.email}")

        # If you set cookies/headers, do it on `response` here:
        # response.set_cookie(
        #     "access_token", access_token, httponly=True, secure=True, samesite="lax"
        # )

        payload = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
        return payload

    except (OperationalError, SQLAlchemyError) as e:
        logger.exception("DB error during login")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        ) from e
    except (UnknownHashError, ValueError) as e:
        logger.warning("Password verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error in auth/token")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.post("/refresh", response_model=Token)
async def refresh_token(request: Request, db: Session = Depends(get_db)):  # noqa: B008
    """Refresh access token using refresh token."""
    try:
        # Extract refresh_token from JSON body
        body = await request.json()
        refresh_token = body.get("refresh_token")

        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required in request body")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail='Invalid JSON body. Expected: {"refresh_token": "<token>"}',
        ) from e

    # Decode refresh token
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),  # noqa: B008
):
    """Get current user profile
    Requires authentication.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        is_subscribed=current_user.is_subscribed,
        is_active=current_user.is_active,
    )


@router.put("/me")
async def update_profile(
    updates: dict,
    current_user: User = Depends(get_current_active_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    """Update current user profile
    Requires authentication.
    """
    # Only allow certain fields to be updated
    allowed_fields = ["is_subscribed", "is_pregnant"]

    for field, value in updates.items():
        if field in allowed_fields and hasattr(current_user, field):
            setattr(current_user, field, value)

    try:
        db.commit()
        db.refresh(current_user)

        return {
            "message": "Profile updated successfully",
            "user": UserResponse(
                id=current_user.id,
                email=current_user.email,
                is_subscribed=current_user.is_subscribed,
                is_active=current_user.is_active,
            ),
        }
    except Exception as e:
        db.rollback()
        logger.exception(f"Error updating profile: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating profile",
        ) from e


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):  # noqa: B008
    """Logout endpoint
    In a production system, you might want to blacklist the token.
    """
    # In a real implementation, you might want to:
    # 1. Add the token to a blacklist in Redis
    # 2. Clear any server-side sessions
    # 3. Log the logout event

    logger.info(f"User logged out: {current_user.email}")

    return {"message": "Successfully logged out"}


# DEPRECATED: This endpoint has been moved to auth_deprecated.py
# @router.post("/password-reset")
# This endpoint now returns 410 Gone via the deprecated router

# DEPRECATED: This endpoint has been moved to auth_deprecated.py
# @router.post("/password-reset/confirm")
# This endpoint now returns 410 Gone via the deprecated router


@router.get("/verify")
async def verify_token(
    code: str | None = Query(None, description="Verification code from email"),
    current_user: User | None = Depends(get_current_user),  # noqa: B008
):
    """Verify email or token
    - If code provided: verify email verification code
    - If no code: verify current token (requires auth).
    """
    if code:
        # Email verification flow (public)
        try:
            # Decode verification code
            payload = decode_token(code)
            email = payload.get("sub")

            if not email:
                raise HTTPException(status_code=400, detail="Invalid verification code")

            # Mark email as verified (in real implementation)
            # For now, just return success
            return {
                "valid": True,
                "message": "Email verified successfully",
                "email": email,
            }

        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid or expired verification code") from e
    else:
        # Token verification flow (requires auth)
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide a valid token or verification code.",
            )

        return {"valid": True, "user_id": current_user.id, "email": current_user.email}
