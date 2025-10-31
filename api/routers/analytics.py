from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from api.crud.analytics import create_explain_feedback
from core.metrics import inc_alternative_clicked
from core_infra.database import get_db

router = APIRouter()


class ExplainFeedbackPayload(BaseModel):
    scan_id: str = Field(..., min_length=1, max_length=64)
    helpful: bool
    trace_id: str | None = Field(None, max_length=64)
    reason: str | None = Field(None, max_length=256)  # e.g., "unclear","incorrect","irrelevant"
    comment: str | None = Field(None, max_length=500)
    platform: str | None = Field(None, max_length=32)
    app_version: str | None = Field(None, max_length=32)
    locale: str | None = Field(None, max_length=16)
    jurisdiction_code: str | None = Field(None, max_length=8)

    @field_validator("helpful", mode="before")
    @classmethod
    def validate_helpful_is_bool(cls, v):
        """Ensure helpful field is a strict boolean, not coerced from string/int"""
        if not isinstance(v, bool):
            raise ValueError("helpful field must be a boolean (true/false), not a string or number")
        return v


class ExplainFeedbackResponse(BaseModel):
    ok: bool
    id: int


@router.post("/explain-feedback", response_model=ExplainFeedbackResponse)
def explain_feedback(payload: ExplainFeedbackPayload, request: Request, db: Session = Depends(get_db)):
    """
    Record user feedback on explain-result responses.
    Captures thumbs up/down from the mobile UI.
    """
    # Resolve user (optional)
    user_id: UUID | None = None
    try:
        from core.auth import current_user

        user_id = getattr(current_user, "id", None)
    except Exception:
        # No auth required for feedback - anonymous is fine
        pass

    try:
        row_id = create_explain_feedback(
            db,
            scan_id=payload.scan_id,
            helpful=payload.helpful,
            user_id=user_id,
            trace_id=payload.trace_id,
            reason=payload.reason,
            comment=payload.comment,
            platform=payload.platform or request.headers.get("X-Platform"),
            app_version=payload.app_version or request.headers.get("X-App-Version"),
            locale=payload.locale or request.headers.get("X-Locale"),
            jurisdiction_code=payload.jurisdiction_code,
        )

        # Record metrics (if available)
        try:
            from core.metrics import inc_explain_feedback

            inc_explain_feedback(payload.helpful, payload.reason)
        except ImportError:
            # Metrics not available, continue
            pass

        return ExplainFeedbackResponse(ok=True, id=row_id)

    except Exception as e:
        # Log error but don't expose internal details
        import logging

        logging.error(f"Failed to record explain feedback: {e}")
        raise HTTPException(status_code=500, detail="failed_to_record_feedback")


class AltClickPayload(BaseModel):
    scan_id: str = Field(..., min_length=1, max_length=64)
    alt_id: str = Field(..., min_length=1, max_length=64)


class AltClickResponse(BaseModel):
    ok: bool


@router.post("/alt-click", response_model=AltClickResponse)
def alt_click(payload: AltClickPayload, request: Request):
    """
    Record when a user clicks on an alternative product suggestion.
    Lightweight endpoint for usage analytics.
    """
    try:
        # Record metrics (primary purpose)
        inc_alternative_clicked(payload.alt_id)

        # Could store lightweight row in future if needed for detailed analytics
        # For now, just metrics is sufficient

        return AltClickResponse(ok=True)

    except Exception as e:
        # Non-blocking error: log but don't fail
        import logging

        logging.warning(f"Failed to record alternative click: {e}")
        return AltClickResponse(ok=True)  # Always return success for UX


class EmergencyOpenResponse(BaseModel):
    ok: bool


@router.post("/emergency-open", response_model=EmergencyOpenResponse)
def emergency_open(request: Request):
    """
    Record when a user opens the Emergency Guidance screen.
    Lightweight endpoint for usage analytics.
    """
    try:
        # Could add metrics here if needed
        # For now, just log the event
        import logging

        logging.info("Emergency Guidance screen opened")

        # Could store lightweight row in future if needed for detailed analytics
        # For now, just return success

        return EmergencyOpenResponse(ok=True)

    except Exception as e:
        # Non-blocking error: log but don't fail
        import logging

        logging.warning(f"Failed to record emergency open: {e}")
        return EmergencyOpenResponse(ok=True)  # Always return success for UX
