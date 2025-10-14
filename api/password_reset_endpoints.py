"""
Password Reset Endpoints - Email-based password reset flow
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from pydantic import EmailStr

from core_infra.database import get_db, Base
from core_infra.auth import get_password_hash
from api.schemas.common import ApiResponse, ok, fail
from api.pydantic_base import AppModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Password Reset Token Model
class PasswordResetToken(Base):
    """Password reset tokens table"""

    __tablename__ = "password_reset_tokens"

    id = Column(String(64), primary_key=True)  # SHA256 of token
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Fixed: Integer not String
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


# Request/Response Models
class PasswordResetRequest(AppModel):
    """Request password reset"""

    email: EmailStr


class PasswordResetConfirm(AppModel):
    """Confirm password reset with token"""

    token: str
    new_password: str
    confirm_password: str


class PasswordResetComplete(AppModel):
    """Complete password reset with new password"""

    new_password: str
    confirm_password: str


class PasswordResetResponse(AppModel):
    """Password reset response"""

    message: str
    expires_in_minutes: Optional[int] = None


async def send_reset_email(email: str, token: str, user_name: Optional[str] = None):
    """
    Send password reset email
    This is a placeholder - integrate with your email service
    """
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import os

        # Email configuration from environment
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        from_email = os.getenv("FROM_EMAIL", "noreply@babyshield.ai")
        app_url = os.getenv("APP_URL", "https://babyshield.cureviax.ai")

        if not smtp_user or not smtp_pass:
            logger.warning("SMTP not configured, logging reset link instead")
            logger.info(f"Password reset link for {email}: {app_url}/reset-password?token={token}")
            return

        # Create reset URL
        reset_url = f"{app_url}/reset-password?token={token}"

        # Create email message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Reset Your BabyShield Password"
        message["From"] = from_email
        message["To"] = email

        # Email body
        text = f"""
        Hello {user_name or "User"},
        
        You requested to reset your password for your BabyShield account.
        
        Click the link below to reset your password:
        {reset_url}
        
        This link will expire in 1 hour.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        The BabyShield Team
        """

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h2 style="color: #2c3e50;">Reset Your Password</h2>
              <p>Hello {user_name or "User"},</p>
              <p>You requested to reset your password for your BabyShield account.</p>
              <p style="margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #3498db; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                  Reset Password
                </a>
              </p>
              <p style="color: #7f8c8d; font-size: 14px;">
                This link will expire in 1 hour.
              </p>
              <p style="color: #7f8c8d; font-size: 14px;">
                If you didn't request this, please ignore this email.
              </p>
              <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 30px 0;">
              <p style="color: #95a5a6; font-size: 12px;">
                Best regards,<br>
                The BabyShield Team
              </p>
            </div>
          </body>
        </html>
        """

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            start_tls=True,
            username=smtp_user,
            password=smtp_pass,
        )

        logger.info(f"Password reset email sent to {email}")

    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")
        # Don't fail the request if email fails - log the token for manual recovery
        logger.info(f"Password reset token for {email}: {token}")


@router.post("/password-reset/request", response_model=ApiResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email

    Always returns success to prevent email enumeration
    """
    try:
        from core_infra.database import User

        # Find user by email
        user = db.query(User).filter(User.email == request.email.lower()).first()

        if user:
            # Generate secure token
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

            # Delete any existing tokens for this user
            db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).delete()

            # Create new token
            reset_token = PasswordResetToken(
                id=token_hash,
                user_id=user.id,  # Fixed: Use integer directly
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            db.add(reset_token)
            db.commit()

            # Send email in background
            user_name = getattr(user, "name", None) or getattr(user, "username", None)
            background_tasks.add_task(send_reset_email, request.email, raw_token, user_name)

            logger.info(f"Password reset requested for user {user.id}")
        else:
            # Log attempt but don't reveal user doesn't exist
            logger.info(f"Password reset requested for non-existent email: {request.email}")

        # Always return success
        response = PasswordResetResponse(
            message="If an account exists with this email, you will receive a password reset link.",
            expires_in_minutes=60,
        )

        return ok(response.model_dump())

    except Exception as e:
        logger.error(f"Error processing password reset request: {e}", exc_info=True)
        return fail("Failed to process request", status=500)


@router.post("/password-reset/confirm", response_model=ApiResponse)
async def confirm_password_reset(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    """
    Confirm password reset with token and new password
    """
    try:
        from core_infra.database import User

        # Validate password match
        if request.new_password != request.confirm_password:
            return fail("Passwords do not match", code="PASSWORD_MISMATCH", status=400)

        # Validate password strength
        if len(request.new_password) < 8:
            return fail("Password must be at least 8 characters", code="WEAK_PASSWORD")

        # Hash the provided token to find it in DB
        token_hash = hashlib.sha256(request.token.encode()).hexdigest()

        # Find valid token
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.id == token_hash,
                PasswordResetToken.expires_at > datetime.utcnow(),
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )

        if not reset_token:
            return fail("Invalid or expired reset token", code="INVALID_TOKEN", status=400)

        # Find user
        user = db.query(User).filter(User.id == reset_token.user_id).first()

        if not user:
            return fail("User not found", code="USER_NOT_FOUND", status=404)

        # Update password
        user.hashed_password = get_password_hash(request.new_password)

        # Mark token as used
        reset_token.used_at = datetime.utcnow()

        db.commit()

        logger.info(f"Password reset completed for user {user.id}")

        return ok({"message": "Password reset successfully"})

    except Exception as e:
        logger.error(f"Error confirming password reset: {e}", exc_info=True)
        return fail("Failed to reset password", status=500)


@router.post("/password-reset/validate", response_model=ApiResponse)
async def validate_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Validate if a reset token is still valid
    """
    try:
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Check if token exists and is valid
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.id == token_hash,
                PasswordResetToken.expires_at > datetime.utcnow(),
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )

        if reset_token:
            # Calculate remaining time
            remaining = reset_token.expires_at - datetime.utcnow()
            remaining_minutes = int(remaining.total_seconds() / 60)

            return ok({"valid": True, "expires_in_minutes": remaining_minutes})
        else:
            return ok({"valid": False, "message": "Token is invalid or expired"})

    except Exception as e:
        logger.error(f"Error validating reset token: {e}", exc_info=True)
        return fail("Failed to validate token", status=500)


@router.post("/password-reset/complete", response_model=ApiResponse)
async def complete_password_reset(
    token: str = Query(..., description="Password reset token"),
    request: PasswordResetComplete = Body(...),
    db: Session = Depends(get_db),
):
    """
    Complete password reset with token and new password
    """
    try:
        from core_infra.database import User

        # Validate password match
        if request.new_password != request.confirm_password:
            return fail("Passwords do not match", code="PASSWORD_MISMATCH", status=400)

        # Validate password strength
        if len(request.new_password) < 8:
            return fail("Password must be at least 8 characters", code="WEAK_PASSWORD")

        # Hash the provided token to find it in DB
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find valid token
        reset_token = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.id == token_hash,
                PasswordResetToken.expires_at > datetime.utcnow(),
                PasswordResetToken.used_at.is_(None),
            )
            .first()
        )

        if not reset_token:
            return fail("Invalid or expired reset token", code="INVALID_TOKEN", status=400)

        # Find user
        user = db.query(User).filter(User.id == reset_token.user_id).first()

        if not user:
            return fail("User not found", code="USER_NOT_FOUND", status=404)

        # Update password
        user.hashed_password = get_password_hash(request.new_password)

        # Mark token as used (one-time use)
        reset_token.used_at = datetime.utcnow()

        db.commit()

        logger.info(f"Password reset completed for user {user.id}")

        return ok({"message": "Password updated successfully"})

    except Exception as e:
        logger.error(f"Error completing password reset: {e}", exc_info=True)
        return fail("Failed to reset password", status=500)
