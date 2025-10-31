"""
App Settings Endpoints for BabyShield
Includes Crashlytics toggle and other app preferences
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


# ========================= MODELS =========================


class AppSettings(BaseModel):
    """User app settings"""

    crashlytics_enabled: bool = Field(False, description="Enable crash reporting (default: false)")
    notifications_enabled: bool = Field(True, description="Enable push notifications")
    offline_mode: bool = Field(False, description="Enable offline mode with cached data")
    auto_retry: bool = Field(True, description="Automatically retry failed requests")
    language: str = Field("en", description="App language code")
    theme: str = Field("auto", pattern="^(light|dark|auto)$", description="App theme")


class UpdateSettingsRequest(BaseModel):
    """Request to update specific settings"""

    crashlytics_enabled: Optional[bool] = None
    notifications_enabled: Optional[bool] = None
    offline_mode: Optional[bool] = None
    auto_retry: Optional[bool] = None
    language: Optional[str] = None
    theme: Optional[str] = None


class SettingsResponse(BaseModel):
    """Settings response"""

    ok: bool = True
    settings: AppSettings
    updated_at: Optional[datetime] = None


class CrashlyticsToggleRequest(BaseModel):
    """Specific request for Crashlytics toggle"""

    enabled: bool = Field(..., description="Enable or disable Crashlytics")
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    device_id: Optional[str] = Field(None, description="Device ID for tracking")
    app_version: Optional[str] = Field(None, description="App version")


# ========================= STORAGE =========================

# In-memory storage for demo (use Redis or database in production)
settings_store: Dict[str, AppSettings] = {}


def get_user_settings(user_id: str) -> AppSettings:
    """Get user settings or return defaults"""
    if user_id not in settings_store:
        settings_store[user_id] = AppSettings()
    return settings_store[user_id]


def update_user_settings(user_id: str, updates: dict) -> AppSettings:
    """Update user settings"""
    settings = get_user_settings(user_id)

    for key, value in updates.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)

    settings_store[user_id] = settings
    return settings


# ========================= ENDPOINTS =========================


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    request: Request,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Get current app settings

    Returns all app settings for the user/device.
    If no user_id is provided, uses device_id or returns defaults.
    """
    # Use user_id or device_id as identifier
    identifier = user_id or device_id or "anonymous"

    settings = get_user_settings(identifier)

    logger.info(
        "Settings retrieved",
        extra={
            "identifier": identifier[:8] if len(identifier) > 8 else identifier,
            "crashlytics": settings.crashlytics_enabled,
        },
    )

    return SettingsResponse(ok=True, settings=settings)


@router.patch("/", response_model=SettingsResponse)
async def update_settings(
    request: Request,
    updates: UpdateSettingsRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Update app settings

    Allows partial updates to app settings.
    Only provided fields will be updated.
    """
    identifier = user_id or device_id or "anonymous"
    trace_id = f"settings_{uuid.uuid4().hex[:8]}"

    # Convert to dict and filter None values
    updates_dict = {k: v for k, v in updates.dict().items() if v is not None}

    if not updates_dict:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No settings to update")

    # Update settings
    settings = update_user_settings(identifier, updates_dict)

    logger.info(
        "Settings updated",
        extra={
            "identifier": identifier[:8] if len(identifier) > 8 else identifier,
            "updates": updates_dict,
            "trace_id": trace_id,
        },
    )

    return SettingsResponse(ok=True, settings=settings, updated_at=datetime.utcnow())


@router.post("/crashlytics", response_model=Dict[str, Any])
async def toggle_crashlytics(
    request: Request,
    toggle_request: CrashlyticsToggleRequest,
    user_agent: Optional[str] = Header(None),
):
    """
    Toggle Crashlytics crash reporting

    This endpoint specifically handles enabling/disabling Crashlytics.
    Default is OFF to respect user privacy.

    **Privacy Note**:
    - Crashlytics is OPT-IN only
    - When enabled, only crash logs and performance metrics are collected
    - No personal information is included in crash reports
    - Users can disable at any time
    """
    identifier = toggle_request.user_id or toggle_request.device_id or "anonymous"
    trace_id = f"crash_{uuid.uuid4().hex[:8]}"

    try:
        # Update the crashlytics setting
        settings = get_user_settings(identifier)
        previous_state = settings.crashlytics_enabled
        settings.crashlytics_enabled = toggle_request.enabled
        settings_store[identifier] = settings

        # Log the change
        logger.info(
            "Crashlytics toggled",
            extra={
                "identifier": identifier[:8] if len(identifier) > 8 else identifier,
                "enabled": toggle_request.enabled,
                "previous": previous_state,
                "app_version": toggle_request.app_version,
                "user_agent": user_agent,
                "trace_id": trace_id,
            },
        )

        return {
            "ok": True,
            "crashlytics_enabled": toggle_request.enabled,
            "message": f"Crashlytics {'enabled' if toggle_request.enabled else 'disabled'} successfully",
            "privacy_note": "Crash reports contain no personal information"
            if toggle_request.enabled
            else "No crash data will be collected",
            "trace_id": trace_id,
        }

    except Exception as e:
        logger.error(f"Failed to toggle Crashlytics: {e}", extra={"trace_id": trace_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update Crashlytics setting",
        )


@router.get("/crashlytics/status", response_model=Dict[str, Any])
async def get_crashlytics_status(
    request: Request,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Get current Crashlytics status

    Returns whether Crashlytics is enabled for this user/device.
    """
    identifier = user_id or device_id or "anonymous"
    settings = get_user_settings(identifier)

    return {
        "ok": True,
        "crashlytics_enabled": settings.crashlytics_enabled,
        "privacy_info": {
            "default_state": "disabled",
            "data_collected": [
                "crash stacktraces",
                "device model and OS version",
                "app version",
                "crash timestamp",
            ]
            if settings.crashlytics_enabled
            else [],
            "personal_data": False,
            "can_disable": True,
        },
    }


@router.post("/reset", response_model=SettingsResponse)
async def reset_settings(
    request: Request,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Reset all settings to defaults

    This will reset all app settings to their default values.
    Crashlytics will be disabled by default.
    """
    identifier = user_id or device_id or "anonymous"
    trace_id = f"reset_{uuid.uuid4().hex[:8]}"

    # Reset to defaults
    settings_store[identifier] = AppSettings()

    logger.info(
        "Settings reset to defaults",
        extra={
            "identifier": identifier[:8] if len(identifier) > 8 else identifier,
            "trace_id": trace_id,
        },
    )

    return SettingsResponse(ok=True, settings=settings_store[identifier], updated_at=datetime.utcnow())


# ========================= ERROR RECOVERY =========================


@router.get("/retry-policy")
async def get_retry_policy():
    """
    Get recommended retry policy for failed requests

    This helps the app implement proper retry logic with exponential backoff.
    """
    return {
        "ok": True,
        "retry_policy": {
            "max_retries": 3,
            "initial_delay_ms": 1000,
            "max_delay_ms": 30000,
            "backoff_multiplier": 2,
            "retry_on_status_codes": [408, 429, 500, 502, 503, 504],
            "retry_on_network_error": True,
        },
        "offline_policy": {
            "cache_duration_minutes": 60,
            "allow_stale_data": True,
            "queue_requests": True,
            "sync_on_reconnect": True,
        },
    }
