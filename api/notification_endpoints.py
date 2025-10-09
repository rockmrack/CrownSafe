"""
Enhanced Notification Endpoints - Push notifications, history, and device management
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Text, desc
from sqlalchemy.orm import relationship

from core_infra.database import get_db, Base
from core_infra.auth import get_current_active_user
from api.schemas.common import ApiResponse, ok, fail
from api.pydantic_base import AppModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


# Database Models
class DeviceToken(Base):
    """User device tokens for push notifications"""

    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(500), nullable=False, unique=True)
    platform = Column(String(20), nullable=False)  # ios, android, web
    device_name = Column(String(200))
    device_model = Column(String(100))
    app_version = Column(String(20))

    # Status
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Push settings
    quiet_hours_start = Column(String(5))  # HH:MM format
    quiet_hours_end = Column(String(5))  # HH:MM format
    notification_types = Column(
        JSON,
        default=lambda: {
            "recalls": True,
            "safety_alerts": True,
            "product_updates": True,
            "promotions": False,
            "weekly_summary": True,
        },
    )


class NotificationHistory(Base):
    """History of all notifications sent to users"""

    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Notification details
    type = Column(String(50), nullable=False)  # recall, alert, update, promotion
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON)  # Additional payload data

    # Delivery status
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime)
    read_at = Column(DateTime)
    clicked_at = Column(DateTime)
    dismissed_at = Column(DateTime)

    # Platform info
    platform = Column(String(20))
    device_token_id = Column(Integer, ForeignKey("device_tokens.id"))

    # Status
    status = Column(String(20), default="sent")  # sent, delivered, failed, read, clicked
    error_message = Column(Text)

    # Priority and categorization
    priority = Column(String(10), default="normal")  # high, normal, low
    category = Column(String(50))
    related_product_id = Column(String(200))
    related_recall_id = Column(String(200))


# Request/Response Models
class RegisterDeviceRequest(AppModel):
    """Register a device for push notifications"""

    token: str
    platform: str  # ios, android, web
    device_name: Optional[str] = None
    device_model: Optional[str] = None
    app_version: Optional[str] = None


class NotificationPreferences(AppModel):
    """User notification preferences"""

    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # HH:MM
    quiet_hours_end: Optional[str] = None  # HH:MM
    notification_types: Dict[str, bool] = {
        "recalls": True,
        "safety_alerts": True,
        "product_updates": True,
        "promotions": False,
        "weekly_summary": True,
    }


class NotificationItem(AppModel):
    """Single notification in history"""

    id: int
    type: str
    title: str
    body: str
    sent_at: datetime
    read_at: Optional[datetime] = None
    status: str
    priority: str
    data: Optional[Dict[str, Any]] = None


class SendNotificationRequest(AppModel):
    """Send a notification to user"""

    title: str
    body: str
    type: str = "alert"
    priority: str = "normal"
    data: Optional[Dict[str, Any]] = None


# Firebase integration
def get_firebase_app():
    """Get or initialize Firebase app"""
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        import os

        # Check if already initialized
        try:
            app = firebase_admin.get_app()
            return app
        except ValueError:
            pass

        # Initialize Firebase
        cred_path = os.getenv("FIREBASE_CREDENTIALS", "secrets/serviceAccountKey.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")
            return app
        else:
            logger.warning(f"Firebase credentials not found at {cred_path}")
            return None

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None


async def send_push_notification(
    token: str, title: str, body: str, data: Optional[Dict] = None, platform: str = "android"
) -> bool:
    """Send push notification via Firebase"""
    try:
        from firebase_admin import messaging

        app = get_firebase_app()
        if not app:
            logger.warning("Firebase not available, skipping push notification")
            return False

        # Build message
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )

        # Platform-specific config
        if platform == "ios":
            message.apns = messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(badge=1, sound="default"))
            )
        elif platform == "android":
            message.android = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default", click_action="FLUTTER_NOTIFICATION_CLICK"
                ),
            )

        # Send message
        response = messaging.send(message)
        logger.info(f"Push notification sent: {response}")
        return True

    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


@router.post("/device/register", response_model=ApiResponse)
async def register_device(
    request: RegisterDeviceRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Register a device for push notifications"""
    try:
        # Check if token already exists
        existing = db.query(DeviceToken).filter(DeviceToken.token == request.token).first()

        if existing:
            # Update existing token
            existing.user_id = current_user.id
            existing.platform = request.platform
            existing.device_name = request.device_name
            existing.device_model = request.device_model
            existing.app_version = request.app_version
            existing.last_used = datetime.utcnow()
            existing.is_active = True
        else:
            # Create new token
            device_token = DeviceToken(
                user_id=current_user.id,
                token=request.token,
                platform=request.platform,
                device_name=request.device_name,
                device_model=request.device_model,
                app_version=request.app_version,
            )
            db.add(device_token)

        db.commit()

        return ok({"message": "Device registered successfully"})

    except Exception as e:
        logger.error(f"Error registering device: {e}", exc_info=True)
        return fail(f"Failed to register device: {str(e)}", status=500)


# DEV OVERRIDE ENDPOINTS - For testing without authentication/database dependencies


@router.post("/device/register-dev", response_model=ApiResponse)
async def register_device_dev(request: RegisterDeviceRequest):
    """
    DEV OVERRIDE: Register device without authentication/database dependencies
    """
    try:
        # Simulate device registration
        device_id = f"DEV-{request.token[:8].upper()}"

        return ok(
            {
                "message": "Device registered successfully (dev override)",
                "device_id": device_id,
                "token": request.token,
                "platform": request.platform,
                "registered_at": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error in dev device registration: {e}")
        return fail(f"Failed to register device: {str(e)}", status=500)


@router.get("/devices-dev", response_model=ApiResponse)
async def get_devices_dev():
    """
    DEV OVERRIDE: Get devices without authentication/database dependencies
    """
    try:
        # Mock device data
        mock_devices = [
            {
                "device_id": "DEV-12345678",
                "token": "test_token_12345678",
                "platform": "android",
                "device_name": "Test Android Device",
                "device_model": "Pixel 7",
                "app_version": "1.0.0",
                "is_active": True,
                "last_used": datetime.utcnow().isoformat(),
                "created_at": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            },
            {
                "device_id": "DEV-87654321",
                "token": "test_token_87654321",
                "platform": "ios",
                "device_name": "Test iOS Device",
                "device_model": "iPhone 14",
                "app_version": "1.0.0",
                "is_active": True,
                "last_used": datetime.utcnow().isoformat(),
                "created_at": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            },
        ]

        return ok({"devices": mock_devices, "total_count": len(mock_devices)})

    except Exception as e:
        logger.error(f"Error in dev devices list: {e}")
        return fail(f"Failed to get devices: {str(e)}", status=500)


@router.delete("/device-dev/{token}", response_model=ApiResponse)
async def unregister_device_dev(token: str):
    """
    DEV OVERRIDE: Unregister device without authentication/database dependencies
    """
    try:
        # Simulate device unregistration
        return ok(
            {
                "message": f"Device with token {token[:8]}... unregistered successfully (dev override)",
                "unregistered_at": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error in dev device unregistration: {e}")
        return fail(f"Failed to unregister device: {str(e)}", status=500)


@router.get("/history-dev", response_model=ApiResponse)
async def get_notification_history_dev():
    """
    DEV OVERRIDE: Get notification history without authentication/database dependencies
    """
    try:
        # Mock notification history
        mock_notifications = [
            {
                "notification_id": "NOTIF-001",
                "title": "Test Recall Alert",
                "body": "This is a test recall notification",
                "type": "recall",
                "sent_at": datetime.utcnow().isoformat(),
                "read": False,
                "data": {"recall_id": "RECALL-123"},
            },
            {
                "notification_id": "NOTIF-002",
                "title": "Safety Update",
                "body": "New safety information available",
                "type": "safety_alert",
                "sent_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "read": True,
                "data": {"product_id": "PROD-456"},
            },
        ]

        return ok(
            {
                "notifications": mock_notifications,
                "total_count": len(mock_notifications),
                "unread_count": len([n for n in mock_notifications if not n["read"]]),
            }
        )

    except Exception as e:
        logger.error(f"Error in dev notification history: {e}")
        return fail(f"Failed to get notification history: {str(e)}", status=500)


@router.put("/preferences-dev", response_model=ApiResponse)
async def update_preferences_dev(request: dict):
    """
    DEV OVERRIDE: Update notification preferences without authentication/database dependencies
    """
    try:
        # Simulate preferences update
        return ok(
            {
                "message": "Notification preferences updated successfully (dev override)",
                "preferences": request,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Error in dev preferences update: {e}")
        return fail(f"Failed to update preferences: {str(e)}", status=500)


@router.post("/test-dev", response_model=ApiResponse)
async def send_test_notification_dev(request: dict):
    """
    DEV OVERRIDE: Send test notification without authentication/database dependencies
    """
    try:
        # Simulate test notification
        notification_id = f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        return ok(
            {
                "message": "Test notification sent successfully (dev override)",
                "notification_id": notification_id,
                "title": request.get("title", "Test Notification"),
                "body": request.get("body", "This is a test notification"),
                "sent_at": datetime.utcnow().isoformat(),
                "devices_targeted": 2,
                "delivery_status": "success",
            }
        )

    except Exception as e:
        logger.error(f"Error in dev test notification: {e}")
        return fail(f"Failed to send test notification: {str(e)}", status=500)


@router.delete("/device/{token}", response_model=ApiResponse)
async def unregister_device(
    token: str, current_user=Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Unregister a device from push notifications"""
    try:
        device = (
            db.query(DeviceToken)
            .filter(DeviceToken.token == token, DeviceToken.user_id == current_user.id)
            .first()
        )

        if device:
            device.is_active = False
            db.commit()
            return ok({"message": "Device unregistered successfully"})
        else:
            return fail("Device not found", code="NOT_FOUND", status=404)

    except Exception as e:
        logger.error(f"Error unregistering device: {e}", exc_info=True)
        return fail(f"Failed to unregister device: {str(e)}", status=500)


@router.get("/devices", response_model=ApiResponse)
async def get_registered_devices(
    current_user=Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Get all registered devices for current user"""
    try:
        devices = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == current_user.id, DeviceToken.is_active)
            .all()
        )

        device_list = [
            {
                "token": d.token[:10] + "...",  # Partial token for security
                "platform": d.platform,
                "device_name": d.device_name,
                "device_model": d.device_model,
                "app_version": d.app_version,
                "last_used": d.last_used.isoformat() + "Z",
                "registered_at": d.created_at.isoformat() + "Z",
            }
            for d in devices
        ]

        return ok({"devices": device_list, "count": len(device_list)})

    except Exception as e:
        logger.error(f"Error fetching devices: {e}", exc_info=True)
        return fail(f"Failed to fetch devices: {str(e)}", status=500)


@router.get("/history", response_model=ApiResponse)
async def get_notification_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = None,
    unread_only: bool = False,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get notification history with pagination"""
    try:
        query = db.query(NotificationHistory).filter(NotificationHistory.user_id == current_user.id)

        # Apply filters
        if type:
            query = query.filter(NotificationHistory.type == type)

        if unread_only:
            query = query.filter(NotificationHistory.read_at.is_(None))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        notifications = (
            query.order_by(desc(NotificationHistory.sent_at)).offset(offset).limit(page_size).all()
        )

        # Build response
        items = []
        for n in notifications:
            item = NotificationItem(
                id=n.id,
                type=n.type,
                title=n.title,
                body=n.body,
                sent_at=n.sent_at,
                read_at=n.read_at,
                status=n.status,
                priority=n.priority,
                data=n.data,
            )
            items.append(item.model_dump())

        # Count unread
        unread_count = (
            db.query(NotificationHistory)
            .filter(
                NotificationHistory.user_id == current_user.id,
                NotificationHistory.read_at.is_(None),
            )
            .count()
        )

        return ok(
            {
                "notifications": items,
                "total": total,
                "unread_count": unread_count,
                "page": page,
                "page_size": page_size,
                "has_more": (offset + page_size) < total,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching notification history: {e}", exc_info=True)
        return fail(f"Failed to fetch history: {str(e)}", status=500)


@router.post("/mark-read/{notification_id}", response_model=ApiResponse)
async def mark_notification_read(
    notification_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read"""
    try:
        notification = (
            db.query(NotificationHistory)
            .filter(
                NotificationHistory.id == notification_id,
                NotificationHistory.user_id == current_user.id,
            )
            .first()
        )

        if not notification:
            return fail("Notification not found", code="NOT_FOUND", status=404)

        notification.read_at = datetime.utcnow()
        notification.status = "read"
        db.commit()

        return ok({"message": "Notification marked as read"})

    except Exception as e:
        logger.error(f"Error marking notification read: {e}", exc_info=True)
        return fail(f"Failed to mark as read: {str(e)}", status=500)


@router.post("/mark-all-read", response_model=ApiResponse)
async def mark_all_notifications_read(
    current_user=Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    try:
        db.query(NotificationHistory).filter(
            NotificationHistory.user_id == current_user.id, NotificationHistory.read_at.is_(None)
        ).update({"read_at": datetime.utcnow(), "status": "read"})
        db.commit()

        return ok({"message": "All notifications marked as read"})

    except Exception as e:
        logger.error(f"Error marking all as read: {e}", exc_info=True)
        return fail(f"Failed to mark all as read: {str(e)}", status=500)


@router.put("/preferences", response_model=ApiResponse)
async def update_notification_preferences(
    preferences: NotificationPreferences,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update notification preferences for all user devices"""
    try:
        devices = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == current_user.id, DeviceToken.is_active)
            .all()
        )

        for device in devices:
            if preferences.quiet_hours_enabled:
                device.quiet_hours_start = preferences.quiet_hours_start
                device.quiet_hours_end = preferences.quiet_hours_end
            else:
                device.quiet_hours_start = None
                device.quiet_hours_end = None

            device.notification_types = preferences.notification_types

        db.commit()

        return ok({"message": "Preferences updated successfully", "devices_updated": len(devices)})

    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        return fail(f"Failed to update preferences: {str(e)}", status=500)


@router.post("/test", response_model=ApiResponse)
async def send_test_notification(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Send a test notification to all user devices"""
    try:
        devices = (
            db.query(DeviceToken)
            .filter(DeviceToken.user_id == current_user.id, DeviceToken.is_active)
            .all()
        )

        if not devices:
            return fail("No registered devices found", code="NO_DEVICES")

        # Create notification record
        notification = NotificationHistory(
            user_id=current_user.id,
            type="test",
            title="Test Notification",
            body="This is a test notification from BabyShield",
            priority="normal",
            data={"test": True, "timestamp": datetime.utcnow().isoformat()},
        )
        db.add(notification)
        db.commit()

        # Send to each device in background
        sent_count = 0
        for device in devices:
            success = await send_push_notification(
                token=device.token,
                title="Test Notification",
                body="This is a test notification from BabyShield",
                data={"notification_id": str(notification.id)},
                platform=device.platform,
            )
            if success:
                sent_count += 1

        return ok(
            {
                "message": f"Test notification sent to {sent_count}/{len(devices)} devices",
                "devices_count": len(devices),
                "sent_count": sent_count,
            }
        )

    except Exception as e:
        logger.error(f"Error sending test notification: {e}", exc_info=True)
        return fail(f"Failed to send test: {str(e)}", status=500)
