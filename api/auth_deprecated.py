"""Deprecated Auth Endpoints
Handles deprecated authentication endpoints with proper 410 Gone responses.
"""

from typing import Never

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/auth", tags=["auth-deprecated"])


@router.post("/password-reset", deprecated=True)
def password_reset_deprecated() -> Never:
    """Old password reset endpoint - deprecated
    Replaced by /api/v1/auth/password-reset/request.
    """
    raise HTTPException(
        status_code=410,
        detail="Deprecated endpoint. Use /api/v1/auth/password-reset/request instead.",
    )


@router.post("/password-reset/confirm", deprecated=True)
def password_reset_confirm_deprecated() -> Never:
    """Old password reset confirmation endpoint - deprecated
    Replaced by the new password reset flow.
    """
    raise HTTPException(
        status_code=410,
        detail="Deprecated endpoint. Use the new password reset flow instead.",
    )
