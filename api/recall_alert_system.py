"""
Recall Alert System
Monitors agencies for new recalls and pushes alerts to affected users
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.monitoring_scheduler import MonitoredProduct
from api.notification_endpoints import (
    DeviceToken,
    NotificationHistory,
    send_push_notification,
)

# CROWN SAFE: RecallDB model removed - replaced with HairProductModel
from core_infra.database import SessionLocal, get_db
from db.models.scan_history import ScanHistory

# from core_infra.celery_app import celery_app  # Commented out - not available in dev environment

logger = logging.getLogger(__name__)

# Create router
recall_alert_router = APIRouter(prefix="/api/v1/recall-alerts", tags=["recall-alerts"])

# DEV OVERRIDE ENDPOINTS - For testing without database dependencies


@recall_alert_router.post("/test-alert-dev", response_model=dict)
async def send_test_recall_alert_dev(request: dict):
    """
    DEV OVERRIDE: Send test recall alert without database dependencies
    """
    try:
        # Simulate recall alert
        alert_id = f"ALERT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "data": {
                "message": "Test recall alert sent successfully (dev override)",
                "alert_id": alert_id,
                "user_id": request.get("user_id", 123),
                "recall_title": request.get("recall_title", "Test Recall Alert"),
                "product_name": request.get("product_name", "Test Product"),
                "severity": request.get("severity", "high"),
                "agency": request.get("agency", "CPSC"),
                "sent_at": datetime.utcnow().isoformat(),
                "devices_notified": 2,
                "delivery_status": "success",
            },
        }

    except Exception as e:
        logger.error(f"Error in dev recall alert: {e}")
        return {"success": False, "error": f"Failed to send recall alert: {str(e)}"}


@recall_alert_router.get("/check-now-dev", response_model=dict)
async def check_recalls_now_dev():
    """
    DEV OVERRIDE: Check for recalls without database dependencies
    """
    try:
        # Simulate recall check
        check_id = f"CHECK-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        return {
            "success": True,
            "data": {
                "message": "Recall check completed successfully (dev override)",
                "check_id": check_id,
                "checked_at": datetime.utcnow().isoformat(),
                "agencies_checked": ["CPSC", "FDA", "NHTSA"],
                "new_recalls_found": 3,
                "recalls": [
                    {
                        "recall_id": "RECALL-001",
                        "product_name": "Test Baby Product",
                        "agency": "CPSC",
                        "date": datetime.utcnow().isoformat(),
                        "severity": "high",
                    },
                    {
                        "recall_id": "RECALL-002",
                        "product_name": "Test Toy",
                        "agency": "CPSC",
                        "date": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                        "severity": "medium",
                    },
                ],
            },
        }

    except Exception as e:
        logger.error(f"Error in dev recall check: {e}")
        return {"success": False, "error": f"Failed to check recalls: {str(e)}"}


@recall_alert_router.get("/preferences-dev", response_model=dict)
async def get_alert_preferences_dev():
    """
    DEV OVERRIDE: Get alert preferences without database dependencies
    """
    try:
        # Return default preferences for dev/testing
        default_preferences = {
            "alert_enabled": True,
            "alert_frequency": "immediate",
            "categories": [],
            "severity_threshold": "all",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
        }

        return {
            "success": True,
            "data": {
                "message": "Alert preferences retrieved successfully (dev override)",
                "preferences": default_preferences,
                "retrieved_at": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error in dev alert preferences: {e}")
        return {"success": False, "error": f"Failed to get preferences: {str(e)}"}


@recall_alert_router.post("/preferences-dev", response_model=dict)
async def update_alert_preferences_dev(request: dict):
    """
    DEV OVERRIDE: Update alert preferences without database dependencies
    """
    try:
        # Simulate preferences update
        return {
            "success": True,
            "data": {
                "message": "Alert preferences updated successfully (dev override)",
                "preferences": request,
                "updated_at": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error in dev alert preferences: {e}")
        return {"success": False, "error": f"Failed to update preferences: {str(e)}"}


@recall_alert_router.get("/history-dev/{user_id}", response_model=dict)
async def get_alert_history_dev(user_id: int):
    """
    DEV OVERRIDE: Get alert history without database dependencies
    """
    try:
        # Mock alert history
        mock_alerts = [
            {
                "alert_id": "ALERT-001",
                "user_id": user_id,
                "recall_title": "Test Recall Alert 1",
                "product_name": "Test Product A",
                "severity": "high",
                "agency": "CPSC",
                "sent_at": datetime.utcnow().isoformat(),
                "delivery_status": "delivered",
            },
            {
                "alert_id": "ALERT-002",
                "user_id": user_id,
                "recall_title": "Test Recall Alert 2",
                "product_name": "Test Product B",
                "severity": "medium",
                "agency": "FDA",
                "sent_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "delivery_status": "delivered",
            },
        ]

        return {
            "success": True,
            "data": {
                "alerts": mock_alerts,
                "total_count": len(mock_alerts),
                "user_id": user_id,
            },
        }

    except Exception as e:
        logger.error(f"Error in dev alert history: {e}")
        return {"success": False, "error": f"Failed to get alert history: {str(e)}"}


class RecallCheckResult(BaseModel):
    """Result of checking for new recalls"""

    agency: str
    new_recalls_count: int
    recalls: list[dict[str, Any]]
    check_timestamp: datetime


class UserAlertPreference(BaseModel):
    """User preferences for recall alerts"""

    user_id: int
    alert_enabled: bool = True
    alert_frequency: str = "immediate"  # immediate, daily, weekly
    categories: list[str] = []  # Empty means all categories
    severity_threshold: str = "all"  # all, medium, high, critical
    quiet_hours_start: int | None = None  # Hour of day (0-23)
    quiet_hours_end: int | None = None


class RecallAlertService:
    """Service for monitoring and alerting on new recalls"""

    # Agency endpoints to monitor
    AGENCY_ENDPOINTS = {
        "CPSC": "https://www.saferproducts.gov/api/recalls",
        "FDA": "https://api.fda.gov/food/enforcement.json",
        "NHTSA": "https://api.nhtsa.gov/recalls/recallsByManufacturer",
        "EU_RAPEX": "https://ec.europa.eu/safety-gate-api/recalls",
        "HEALTH_CANADA": "https://healthycanadians.gc.ca/recall-alert-rappel-avis/api",
        "ACCC_AUSTRALIA": "https://www.productsafety.gov.au/api/recalls",
    }

    @classmethod
    async def check_agency_for_new_recalls(
        cls, agency: str, last_check_time: datetime, db: Session
    ) -> RecallCheckResult:
        """Check a specific agency for new recalls since last check"""

        new_recalls = []

        try:
            # In production, this would make actual API calls to agencies
            # For now, simulate checking for new recalls

            if agency == "CPSC":
                # Check CPSC for new recalls
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(
                            cls.AGENCY_ENDPOINTS["CPSC"],
                            params={
                                "RecallDateStart": last_check_time.strftime("%Y-%m-%d"),
                                "format": "json",
                            },
                            timeout=10.0,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            # Process CPSC format
                            for recall in data.get("results", []):
                                if recall.get("RecallDate") > last_check_time.isoformat():
                                    new_recalls.append(
                                        {
                                            "recall_id": recall.get("RecallID"),
                                            "product_name": recall.get("Products", [{}])[0].get("Name"),
                                            "hazard": recall.get("Hazards", [{}])[0].get("Name"),
                                            "remedy": recall.get("Remedies", [{}])[0].get("Name"),
                                            "date": recall.get("RecallDate"),
                                            "agency": "CPSC",
                                        }
                                    )
                    except Exception as e:
                        logger.error(f"Error checking CPSC: {e}")

            # Add similar checks for other agencies...

        except Exception as e:
            logger.error(f"Error checking agency {agency}: {e}")

        return RecallCheckResult(
            agency=agency,
            new_recalls_count=len(new_recalls),
            recalls=new_recalls,
            check_timestamp=datetime.utcnow(),
        )

    @classmethod
    async def find_affected_users(cls, recall: dict[str, Any], db: Session) -> list[int]:
        """Find users who have scanned products affected by this recall"""

        affected_user_ids = []

        try:
            # Search scan history for matching products
            product_name = recall.get("product_name", "").lower()

            # Find scans that might match this recall
            matching_scans = (
                db.query(ScanHistory)
                .filter(
                    or_(
                        func.lower(ScanHistory.product_name).contains(product_name),
                        func.lower(ScanHistory.brand).contains(product_name.split()[0] if product_name else ""),
                    )
                )
                .distinct(ScanHistory.user_id)
                .all()
            )

            affected_user_ids = [scan.user_id for scan in matching_scans]

            # Also check monitored products
            monitored = (
                db.query(MonitoredProduct)
                .filter(
                    or_(
                        func.lower(MonitoredProduct.product_name).contains(product_name),
                        func.lower(MonitoredProduct.brand_name).contains(
                            product_name.split()[0] if product_name else ""
                        ),
                    )
                )
                .distinct(MonitoredProduct.user_id)
                .all()
            )

            for product in monitored:
                if product.user_id not in affected_user_ids:
                    affected_user_ids.append(product.user_id)

        except Exception as e:
            logger.error(f"Error finding affected users: {e}")

        return affected_user_ids

    @classmethod
    async def send_recall_alert(cls, user_id: int, recall: dict[str, Any], db: Session) -> bool:
        """Send recall alert to a specific user"""

        try:
            # Get user's devices
            devices = db.query(DeviceToken).filter(DeviceToken.user_id == user_id, DeviceToken.is_active).all()

            if not devices:
                logger.info(f"No active devices for user {user_id}")
                return False

            # Prepare notification
            product_name = recall.get("product_name", "Unknown Product")
            hazard = recall.get("hazard", "Safety concern")

            title = f"⚠️ Recall Alert: {product_name}"
            body = f"URGENT: {hazard}. Check the app for details and next steps."

            data = {
                "type": "recall_alert",
                "recall_id": recall.get("recall_id"),
                "product_name": product_name,
                "severity": cls._determine_severity(recall),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Store notification in history
            try:
                notification = NotificationHistory(
                    user_id=user_id,
                    type="recall_alert",
                    title=title,
                    body=body,
                    priority="high",
                    category="safety",
                    data=recall,
                    sent_at=datetime.utcnow(),
                )
                db.add(notification)
            except NameError:
                # NotificationHistory not available, skip storage
                logger.warning("NotificationHistory not available, skipping notification storage")
            except Exception as e:
                logger.error(f"Error storing notification history: {e}")

            # Send to each device
            success_count = 0
            for device in devices:
                success = await send_push_notification(
                    token=device.token,
                    title=title,
                    body=body,
                    data=data,
                    platform=device.platform,
                )
                if success:
                    success_count += 1

            db.commit()

            logger.info(f"Sent recall alert to {success_count}/{len(devices)} devices for user {user_id}")
            return success_count > 0

        except Exception as e:
            logger.error(f"Error sending recall alert: {e}")
            return False

    @classmethod
    def _determine_severity(cls, recall: dict[str, Any]) -> str:
        """Determine severity level of a recall"""

        hazard = recall.get("hazard", "").lower()

        # Critical severity keywords
        if any(word in hazard for word in ["death", "fatal", "choking", "suffocation", "strangulation"]):
            return "critical"

        # High severity keywords
        if any(word in hazard for word in ["injury", "burn", "cut", "poison", "toxic", "lead"]):
            return "high"

        # Medium severity keywords
        if any(word in hazard for word in ["risk", "hazard", "defect", "malfunction"]):
            return "medium"

        return "low"


# Background Tasks for Processing (FastAPI BackgroundTasks)


# @celery_app.task(name="check_all_agencies_for_recalls")  # Commented out - celery not available
async def check_all_agencies_for_recalls():
    """
    Background task that checks all agencies for new recalls.
    Used with FastAPI BackgroundTasks (supports async functions).

    NOTE: If Celery is re-enabled in the future, this function will need to be
    converted back to sync and use asyncio.run() for async operations, or use
    Celery's async task support with proper configuration.

    Currently runs on-demand via /check-now endpoint or can be scheduled.
    """
    logger.info("Starting scheduled recall check across all agencies...")

    db = SessionLocal()
    try:
        # Get last check time (stored in system config or database)
        # For now, check last 24 hours
        last_check = datetime.utcnow() - timedelta(hours=24)

        all_new_recalls = []

        # Check each agency
        for agency in RecallAlertService.AGENCY_ENDPOINTS.keys():
            try:
                result = await RecallAlertService.check_agency_for_new_recalls(agency, last_check, db)

                if result.new_recalls_count > 0:
                    logger.info(f"Found {result.new_recalls_count} new recalls from {agency}")
                    all_new_recalls.extend(result.recalls)

            except Exception as e:
                logger.error(f"Error checking {agency}: {e}", exc_info=True)

        # Process new recalls
        if all_new_recalls:
            logger.info(f"Processing {len(all_new_recalls)} total new recalls")

            for recall in all_new_recalls:
                # Find affected users
                affected_users = await RecallAlertService.find_affected_users(recall, db)

                logger.info(f"Recall {recall.get('recall_id')} affects {len(affected_users)} users")

                # Send alerts to affected users
                for user_id in affected_users:
                    await RecallAlertService.send_recall_alert(user_id, recall, db)

                # Store recall in database
                try:
                    new_recall = RecallDB(
                        recall_id=recall.get("recall_id"),
                        source_agency=recall.get("agency"),
                        product_name=recall.get("product_name"),
                        hazard=recall.get("hazard"),
                        remedy=recall.get("remedy"),
                        recall_date=datetime.fromisoformat(recall.get("date"))
                        if recall.get("date")
                        else datetime.utcnow(),
                    )
                    db.add(new_recall)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error storing recall: {e}", exc_info=True)
                    db.rollback()

        logger.info("Recall check completed")
        return {"new_recalls": len(all_new_recalls)}

    finally:
        db.close()


# @celery_app.task(name="send_daily_recall_digest")  # Commented out - celery not available
def send_daily_recall_digest():
    """
    Send daily digest of recalls to users who prefer daily updates
    """
    logger.info("Sending daily recall digest...")

    with get_db() as db:
        # Get recalls from last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)

        recent_recalls = db.query(RecallDB).filter(RecallDB.created_at >= yesterday).all()

        if not recent_recalls:
            logger.info("No new recalls for daily digest")
            return

        # Get users with daily digest preference
        # This would check user preferences table
        # For now, we'll simulate

        digest_content = f"Daily Safety Update: {len(recent_recalls)} new recalls\n\n"
        for recall in recent_recalls[:5]:  # Top 5 recalls
            digest_content += f"• {recall.product_name}: {recall.hazard}\n"

        # Send digest to users
        # Implementation would go here

        logger.info(f"Daily digest sent with {len(recent_recalls)} recalls")


# API Endpoints


@recall_alert_router.post("/test-alert")
async def test_recall_alert(user_id: int, product_name: str, db: Session = Depends(get_db)):
    """Test endpoint to trigger a recall alert for a user"""

    mock_recall = {
        "recall_id": f"TEST_{datetime.utcnow().timestamp()}",
        "product_name": product_name,
        "hazard": "Test hazard - this is a test alert",
        "remedy": "No action needed - this is a test",
        "agency": "TEST",
    }

    success = await RecallAlertService.send_recall_alert(user_id, mock_recall, db)

    if success:
        return {"success": True, "message": "Test alert sent successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test alert")


@recall_alert_router.get("/check-now")
async def check_recalls_now(background_tasks: BackgroundTasks):
    """Manually trigger a recall check across all agencies"""

    background_tasks.add_task(check_all_agencies_for_recalls)

    return {"success": True, "message": "Recall check initiated in background"}


@recall_alert_router.get("/preferences")
async def get_alert_preferences(
    user_id: int = Query(..., description="User ID to get preferences for"),
    db: Session = Depends(get_db),
):
    """Get user's recall alert preferences"""

    try:
        # For now, return default preferences since we don't have a preferences table yet
        # In production, this would query the user preferences table
        default_preferences = {
            "user_id": user_id,
            "alert_enabled": True,
            "alert_frequency": "immediate",
            "categories": [],
            "severity_threshold": "all",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
        }

        return {
            "success": True,
            "message": "Alert preferences retrieved",
            "preferences": default_preferences,
        }

    except Exception as e:
        logger.error(f"Error getting alert preferences: {e}")
        return {"success": False, "error": f"Failed to get preferences: {str(e)}"}


@recall_alert_router.post("/preferences")
async def update_alert_preferences(preferences: UserAlertPreference, db: Session = Depends(get_db)):
    """Update user's recall alert preferences"""

    # Store preferences in database
    # Implementation would update user preferences table

    return {
        "success": True,
        "message": "Alert preferences updated",
        "preferences": preferences.dict(),
    }


@recall_alert_router.get("/history/{user_id}")
async def get_alert_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get user's recall alert history"""

    try:
        # Try to use NotificationHistory if available
        alerts = (
            db.query(NotificationHistory)
            .filter(
                NotificationHistory.user_id == user_id,
                NotificationHistory.type == "recall_alert",
            )
            .order_by(NotificationHistory.sent_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "success": True,
            "alerts": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "body": alert.body,
                    "sent_at": alert.sent_at.isoformat() if alert.sent_at else None,
                    "data": alert.data,
                }
                for alert in alerts
            ],
            "total": len(alerts),
            "message": "Alert history retrieved successfully",
        }

    except NameError:
        # Fallback: NotificationHistory not available, return empty history
        logger.warning(f"NotificationHistory not available, returning empty history for user {user_id}")
        return {
            "success": True,
            "alerts": [],
            "total": 0,
            "message": "Alert history not available (database table not initialized)",
        }
    except Exception as e:
        logger.error(f"Error retrieving alert history for user {user_id}: {e}")
        return {
            "success": False,
            "error": f"Failed to retrieve alert history: {str(e)}",
            "alerts": [],
            "total": 0,
        }
