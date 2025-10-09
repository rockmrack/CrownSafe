"""
Product Monitoring Scheduler - 24/7 automated product monitoring
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Text,
    and_,
)
from sqlalchemy.orm import relationship

from core_infra.database import get_db_session, Base, RecallDB
from core_infra.visual_agent_models import ImageExtraction, ImageJob
from api.notification_endpoints import (
    NotificationHistory,
    send_push_notification,
    DeviceToken,
)

logger = logging.getLogger(__name__)


class MonitoredProduct(Base):
    """Products being monitored for users"""

    __tablename__ = "monitored_products"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Product identification
    product_name = Column(String(500))
    brand_name = Column(String(200))
    model_number = Column(String(200))
    upc_code = Column(String(50), index=True)
    category = Column(String(100))

    # Source
    source_job_id = Column(String(36))  # Original scan job
    added_via = Column(String(50))  # scan, manual, import

    # Monitoring settings
    is_active = Column(Boolean, default=True)
    check_frequency_hours = Column(Integer, default=24)  # How often to check
    last_checked = Column(DateTime)
    next_check = Column(DateTime, default=datetime.utcnow)

    # Status
    recall_status = Column(String(50), default="safe")  # safe, recalled, warning
    last_recall_id = Column(String(200))
    recalls_found = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    extra_metadata = Column("metadata", JSON)  # Renamed to avoid SQLAlchemy reserved attribute


class MonitoringRun(Base):
    """History of monitoring runs"""

    __tablename__ = "monitoring_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Statistics
    products_checked = Column(Integer, default=0)
    new_recalls_found = Column(Integer, default=0)
    notifications_sent = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Status
    status = Column(String(20), default="running")  # running, completed, failed
    error_message = Column(Text)

    # Details
    run_details = Column(JSON)


class ProductMonitoringScheduler:
    """Scheduler for 24/7 product monitoring"""

    @classmethod
    async def add_product_to_monitoring(
        cls,
        user_id: int,
        product_name: str,
        brand_name: Optional[str] = None,
        model_number: Optional[str] = None,
        upc_code: Optional[str] = None,
        source_job_id: Optional[str] = None,
        check_frequency_hours: int = 24,
    ) -> MonitoredProduct:
        """Add a product to monitoring"""
        with get_db_session() as db:
            # Check if already monitoring
            existing = (
                db.query(MonitoredProduct)
                .filter(
                    and_(
                        MonitoredProduct.user_id == user_id,
                        MonitoredProduct.upc_code == upc_code
                        if upc_code
                        else MonitoredProduct.product_name == product_name,
                        MonitoredProduct.is_active,
                    )
                )
                .first()
            )

            if existing:
                # Update existing
                existing.check_frequency_hours = check_frequency_hours
                existing.updated_at = datetime.utcnow()
                db.commit()
                return existing

            # Create new monitoring
            monitored = MonitoredProduct(
                user_id=user_id,
                product_name=product_name,
                brand_name=brand_name,
                model_number=model_number,
                upc_code=upc_code,
                source_job_id=source_job_id,
                check_frequency_hours=check_frequency_hours,
                next_check=datetime.utcnow() + timedelta(hours=check_frequency_hours),
                added_via="scan" if source_job_id else "manual",
            )

            db.add(monitored)
            db.commit()
            db.refresh(monitored)

            logger.info(f"Added product to monitoring: {product_name} for user {user_id}")
            return monitored

    @classmethod
    async def check_product_for_recalls(
        cls, product: MonitoredProduct, db: Session
    ) -> Dict[str, Any]:
        """Check a single product for recalls"""
        try:
            recalls_found = []

            # Search by UPC if available
            if product.upc_code:
                recalls = (
                    db.query(RecallDB).filter(RecallDB.upc_codes.contains([product.upc_code])).all()
                )
                recalls_found.extend(recalls)

            # Search by product name and brand
            if product.product_name:
                from sqlalchemy import func

                # Case-insensitive search
                query = db.query(RecallDB)

                if product.brand_name:
                    query = query.filter(
                        func.lower(RecallDB.brand).contains(product.brand_name.lower())
                    )

                query = query.filter(
                    func.lower(RecallDB.product_name).contains(product.product_name.lower())
                )

                recalls = query.limit(10).all()

                # Deduplicate
                existing_ids = {r.id for r in recalls_found}
                for recall in recalls:
                    if recall.id not in existing_ids:
                        recalls_found.append(recall)

            # Search by model number
            if product.model_number and not recalls_found:
                recalls = (
                    db.query(RecallDB)
                    .filter(
                        func.lower(RecallDB.model_numbers).contains(product.model_number.lower())
                    )
                    .limit(5)
                    .all()
                )
                recalls_found.extend(recalls)

            return {
                "product_id": product.id,
                "recalls_found": len(recalls_found),
                "recalls": [
                    {
                        "id": r.id,
                        "title": r.title,
                        "hazard": r.hazard_description,
                        "remedy": r.remedy_description,
                        "date": r.recall_date.isoformat() if r.recall_date else None,
                        "severity": getattr(r, "severity", "medium"),
                    }
                    for r in recalls_found[:5]  # Limit to 5 most relevant
                ],
            }

        except Exception as e:
            logger.error(f"Error checking product {product.id}: {e}")
            return {"product_id": product.id, "error": str(e), "recalls_found": 0}

    @classmethod
    async def send_recall_notification(
        cls, user_id: int, product: MonitoredProduct, recalls: List[Dict], db: Session
    ):
        """Send notification about new recalls"""
        try:
            # Get user's devices
            devices = (
                db.query(DeviceToken)
                .filter(DeviceToken.user_id == user_id, DeviceToken.is_active)
                .all()
            )

            if not devices:
                logger.info(f"No devices found for user {user_id}")
                return

            # Prepare notification
            recall_count = len(recalls)
            title = f"⚠️ Recall Alert: {product.product_name}"

            if recall_count == 1:
                body = f"A recall has been issued for {product.product_name}. Tap for details."
            else:
                body = (
                    f"{recall_count} recalls found for {product.product_name}. Check immediately."
                )

            # Store in history
            notification = NotificationHistory(
                user_id=user_id,
                type="recall",
                title=title,
                body=body,
                priority="high",
                category="safety",
                related_product_id=str(product.id),
                data={
                    "product_name": product.product_name,
                    "brand": product.brand_name,
                    "recalls": recalls,
                },
            )
            db.add(notification)
            db.commit()

            # Send to each device
            for device in devices:
                # Check quiet hours
                if cls._is_quiet_hours(device):
                    logger.info(f"Skipping notification for device {device.id} (quiet hours)")
                    continue

                # Check if recalls are enabled
                if not device.notification_types.get("recalls", True):
                    continue

                await send_push_notification(
                    token=device.token,
                    title=title,
                    body=body,
                    data={
                        "type": "recall",
                        "product_id": str(product.id),
                        "notification_id": str(notification.id),
                        "recall_count": str(recall_count),
                    },
                    platform=device.platform,
                )

            logger.info(f"Sent recall notification to user {user_id} for product {product.id}")

        except Exception as e:
            logger.error(f"Error sending notification: {e}")

    @classmethod
    def _is_quiet_hours(cls, device: DeviceToken) -> bool:
        """Check if current time is in quiet hours for device"""
        if not device.quiet_hours_start or not device.quiet_hours_end:
            return False

        try:
            now = datetime.now().time()
            start = datetime.strptime(device.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(device.quiet_hours_end, "%H:%M").time()

            if start <= end:
                return start <= now <= end
            else:
                # Overnight quiet hours
                return now >= start or now <= end

        except Exception:
            return False

    @classmethod
    async def run_monitoring_cycle(cls) -> Dict[str, Any]:
        """Run a complete monitoring cycle"""
        run = None

        try:
            with get_db_session() as db:
                # Create run record
                run = MonitoringRun()
                db.add(run)
                db.commit()
                db.refresh(run)
                run_id = run.id

            logger.info(f"Starting monitoring run {run_id}")

            products_checked = 0
            new_recalls_found = 0
            notifications_sent = 0
            errors = []

            with get_db_session() as db:
                # Get products due for checking
                due_products = (
                    db.query(MonitoredProduct)
                    .filter(
                        MonitoredProduct.is_active,
                        MonitoredProduct.next_check <= datetime.utcnow(),
                    )
                    .limit(1000)
                    .all()
                )  # Process in batches

                logger.info(f"Found {len(due_products)} products to check")

                for product in due_products:
                    try:
                        # Check for recalls
                        result = await cls.check_product_for_recalls(product, db)
                        products_checked += 1

                        if result.get("recalls_found", 0) > 0:
                            # Check if these are new recalls
                            if product.recalls_found < result["recalls_found"]:
                                new_recalls_found += result["recalls_found"] - product.recalls_found

                                # Send notification
                                await cls.send_recall_notification(
                                    product.user_id, product, result["recalls"], db
                                )
                                notifications_sent += 1

                            # Update product status
                            product.recall_status = "recalled"
                            product.recalls_found = result["recalls_found"]
                            product.last_recall_id = (
                                result["recalls"][0]["id"] if result["recalls"] else None
                            )
                        else:
                            product.recall_status = "safe"

                        # Update check time
                        product.last_checked = datetime.utcnow()
                        product.next_check = datetime.utcnow() + timedelta(
                            hours=product.check_frequency_hours
                        )

                    except Exception as e:
                        logger.error(f"Error checking product {product.id}: {e}")
                        errors.append(str(e))

                # Commit all updates
                db.commit()

                # Update run record
                run = db.query(MonitoringRun).filter_by(id=run_id).first()
                if run:
                    run.completed_at = datetime.utcnow()
                    run.products_checked = products_checked
                    run.new_recalls_found = new_recalls_found
                    run.notifications_sent = notifications_sent
                    run.errors_count = len(errors)
                    run.status = "completed"
                    run.run_details = {
                        "errors": errors[:10],  # Store first 10 errors
                        "duration_seconds": (run.completed_at - run.started_at).total_seconds(),
                    }
                    db.commit()

            logger.info(
                f"Monitoring run {run_id} completed: {products_checked} checked, {new_recalls_found} new recalls, {notifications_sent} notifications"
            )

            return {
                "run_id": run_id,
                "products_checked": products_checked,
                "new_recalls_found": new_recalls_found,
                "notifications_sent": notifications_sent,
                "errors": len(errors),
            }

        except Exception as e:
            logger.error(f"Monitoring cycle failed: {e}")

            if run:
                with get_db_session() as db:
                    run = db.query(MonitoringRun).filter_by(id=run.id).first()
                    if run:
                        run.status = "failed"
                        run.error_message = str(e)
                        run.completed_at = datetime.utcnow()
                        db.commit()

            raise

    @classmethod
    async def auto_add_from_scans(cls):
        """Automatically add products from recent scans to monitoring"""
        try:
            with get_db_session() as db:
                # Get recent completed scans not yet monitored
                recent_scans = (
                    db.query(ImageJob)
                    .join(ImageExtraction)
                    .filter(
                        ImageJob.status == "completed",
                        ImageJob.created_at >= datetime.utcnow() - timedelta(days=7),
                    )
                    .all()
                )

                added_count = 0
                for job in recent_scans:
                    extraction = db.query(ImageExtraction).filter_by(job_id=job.id).first()
                    if extraction and extraction.product_name:
                        # Check if already monitoring
                        existing = (
                            db.query(MonitoredProduct)
                            .filter(
                                MonitoredProduct.user_id == job.user_id,
                                MonitoredProduct.source_job_id == job.id,
                            )
                            .first()
                        )

                        if not existing:
                            await cls.add_product_to_monitoring(
                                user_id=job.user_id,
                                product_name=extraction.product_name,
                                brand_name=extraction.brand_name,
                                model_number=extraction.model_number,
                                upc_code=extraction.upc_code,
                                source_job_id=job.id,
                            )
                            added_count += 1

                logger.info(f"Auto-added {added_count} products to monitoring")

        except Exception as e:
            logger.error(f"Error auto-adding products: {e}")


# Celery task for scheduled monitoring
from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("monitoring", broker=REDIS_URL, backend=REDIS_URL)


@celery_app.task(name="run_product_monitoring")
def run_product_monitoring():
    """Celery task to run product monitoring"""
    import asyncio

    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(ProductMonitoringScheduler.run_monitoring_cycle())
    return result


@celery_app.task(name="auto_add_products")
def auto_add_products():
    """Celery task to auto-add products from scans"""
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(ProductMonitoringScheduler.auto_add_from_scans())
    return {"status": "completed"}
