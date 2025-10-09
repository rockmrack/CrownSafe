"""
JWT Authentication for BabyShield API
Production-ready authentication system
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from passlib.exc import UnknownHashError
from core_infra.database import get_db, User
import secrets

logger = logging.getLogger(__name__)

# Configuration (unify secret sources)
SECRET_KEY = (
    os.getenv("JWT_SECRET")
    or os.getenv("SECRET_KEY")
    or os.getenv("JWT_SECRET_KEY")
    or secrets.token_urlsafe(32)
)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing with BCrypt compatibility fix
try:
    # Suppress bcrypt warnings by forcing specific configuration
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*bcrypt.*", category=UserWarning)
        pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12,
            bcrypt__ident="2b",  # Force specific bcrypt variant to avoid version detection
        )
except Exception as e:
    logger.warning(f"BCrypt initialization warning (non-critical): {e}")
    # Final fallback - minimal configuration
    pwd_context = CryptContext(schemes=["bcrypt"])

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        # Log the specific error but don't raise HTTPException here
        # Let the caller handle the response appropriately
        logger.warning(f"Password verification failed: {e}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    import time
    import uuid

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "auth_time": int(time.time()),
            "jti": uuid.uuid4().hex,
        }
    )
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current authenticated user"""
    if not token:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        if not payload:
            raise credentials_exception

        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception

        # Check if token is blocklisted
        jti = payload.get("jti")
        if jti:
            try:
                import redis

                r = redis.from_url(
                    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    decode_responses=True,
                )
                if r.get(f"jwt:block:{jti}"):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token revoked",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            except HTTPException:
                # Re-raise HTTPException (don't catch our own auth errors!)
                raise
            except Exception as e:
                # Log Redis connection issues but continue without blocklist check
                logger.warning(f"Redis blocklist check failed: {e}")
                pass

        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure the current user is active"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active (you can add an 'is_active' field to User model)
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")

    return current_user


async def optional_auth(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - returns user if authenticated, None otherwise"""
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        # Check if user has a password set
        if not hasattr(user, "hashed_password") or not user.hashed_password:
            # For existing users without passwords, you might want to handle this differently
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user
    except SQLAlchemyError as e:
        logger.exception("Database error during authentication")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable",
        )


# Response models
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


class UserLogin(BaseModel):
    email: str
    password: str
