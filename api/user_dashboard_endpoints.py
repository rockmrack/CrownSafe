"""
User Dashboard & Statistics Endpoints
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from core_infra.database import get_db, RecallDB
from core_infra.auth import get_current_active_user
from core_infra.visual_agent_models import ImageJob, ImageExtraction, JobStatus
from api.schemas.common import ApiResponse, ok, fail
from api.pydantic_base import AppModel
from api.monitoring_scheduler import MonitoredProduct
from api.notification_endpoints import NotificationHistory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


class DashboardStats(AppModel):
    """Dashboard statistics"""

    total_scans: int
    scans_this_month: int
    active_monitors: int
    recalls_detected: int
    notifications_received: int
    safety_score: float
    member_days: int


class ActivitySummary(AppModel):
    """Activity summary"""

    date: str
    scans: int
    recalls_found: int
    notifications: int


class ProductCategory(AppModel):
    """Product category stats"""

    category: str
    count: int
    percentage: float


@router.get("/overview", response_model=ApiResponse)
async def get_dashboard_overview(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get dashboard overview statistics"""
    try:
        now = datetime.utcnow()
        month_ago = now - timedelta(days=30)

        # Get scan statistics
        total_scans = db.query(ImageJob).filter(ImageJob.user_id == current_user.id).count()

        scans_this_month = (
            db.query(ImageJob).filter(ImageJob.user_id == current_user.id, ImageJob.created_at >= month_ago).count()
        )

        # Get monitoring statistics
        active_monitors = (
            db.query(MonitoredProduct)
            .filter(MonitoredProduct.user_id == current_user.id, MonitoredProduct.is_active)
            .count()
        )

        recalls_detected = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == current_user.id,
                MonitoredProduct.recall_status == "recalled",
            )
            .count()
        )

        # Get notification statistics
        notifications_received = (
            db.query(NotificationHistory).filter(NotificationHistory.user_id == current_user.id).count()
        )

        # Calculate safety score (0-100)
        # Based on: products monitored, scan frequency, recall response rate
        safety_score = 85.0  # Base score

        if active_monitors > 0:
            safety_score += min(15, active_monitors * 1.5)  # Up to +15 for monitoring

        if scans_this_month > 10:
            safety_score += 5  # Bonus for active scanning

        # Ensure score is between 0-100
        safety_score = min(100, max(0, safety_score))

        # Calculate member days
        member_since = getattr(current_user, "created_at", now - timedelta(days=30))
        member_days = (now - member_since).days

        stats = DashboardStats(
            total_scans=total_scans,
            scans_this_month=scans_this_month,
            active_monitors=active_monitors,
            recalls_detected=recalls_detected,
            notifications_received=notifications_received,
            safety_score=round(safety_score, 1),
            member_days=member_days,
        )

        return ok(stats.model_dump())

    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        return fail(f"Failed to fetch overview: {str(e)}", status=500)


@router.get("/activity", response_model=ApiResponse)
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=90, description="Number of days to fetch"),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get activity timeline for the last N days"""
    try:
        activities = []
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days - 1)

        # Generate date range
        current_date = start_date
        while current_date <= end_date:
            # Count scans for this day
            day_start = datetime.combine(current_date, datetime.min.time())
            day_end = datetime.combine(current_date, datetime.max.time())

            scans = (
                db.query(ImageJob)
                .filter(
                    ImageJob.user_id == current_user.id,
                    ImageJob.created_at >= day_start,
                    ImageJob.created_at <= day_end,
                )
                .count()
            )

            # Count notifications for this day
            notifications = (
                db.query(NotificationHistory)
                .filter(
                    NotificationHistory.user_id == current_user.id,
                    NotificationHistory.sent_at >= day_start,
                    NotificationHistory.sent_at <= day_end,
                )
                .count()
            )

            # Count recalls found this day
            recalls = (
                db.query(MonitoredProduct)
                .filter(
                    MonitoredProduct.user_id == current_user.id,
                    MonitoredProduct.last_checked >= day_start,
                    MonitoredProduct.last_checked <= day_end,
                    MonitoredProduct.recall_status == "recalled",
                )
                .count()
            )

            activity = ActivitySummary(
                date=current_date.isoformat(),
                scans=scans,
                recalls_found=recalls,
                notifications=notifications,
            )
            activities.append(activity.model_dump())

            current_date += timedelta(days=1)

        return ok(
            {
                "activities": activities,
                "days": days,
                "total_scans": sum(a["scans"] for a in activities),
                "total_recalls": sum(a["recalls_found"] for a in activities),
                "total_notifications": sum(a["notifications"] for a in activities),
            }
        )

    except Exception as e:
        logger.error(f"Error fetching activity timeline: {e}", exc_info=True)
        return fail(f"Failed to fetch activity: {str(e)}", status=500)


@router.get("/product-categories", response_model=ApiResponse)
async def get_product_categories(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get breakdown of scanned products by category"""
    try:
        # Get all extractions for user
        extractions = db.query(ImageExtraction).join(ImageJob).filter(ImageJob.user_id == current_user.id).all()

        # Categorize products
        categories = {}
        for ext in extractions:
            # Simple categorization based on labels or product name
            category = "Other"

            if ext.labels:
                # Use first label as category
                for label in ext.labels:
                    if isinstance(label, dict) and "name" in label:
                        category = label["name"].title()
                        break
            elif ext.product_name:
                # Guess category from product name
                product_lower = ext.product_name.lower()
                if any(word in product_lower for word in ["bottle", "formula", "milk"]):
                    category = "Feeding"
                elif any(word in product_lower for word in ["diaper", "wipe"]):
                    category = "Diapering"
                elif any(word in product_lower for word in ["toy", "play"]):
                    category = "Toys"
                elif any(word in product_lower for word in ["crib", "mattress", "bed"]):
                    category = "Nursery"
                elif any(word in product_lower for word in ["car seat", "stroller"]):
                    category = "Travel"
                elif any(word in product_lower for word in ["bath", "shampoo", "lotion"]):
                    category = "Bath & Body"

            categories[category] = categories.get(category, 0) + 1

        # Calculate percentages
        total = sum(categories.values())
        category_stats = []

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            category_stats.append(
                ProductCategory(category=cat, count=count, percentage=round(percentage, 1)).model_dump()
            )

        return ok({"categories": category_stats[:10], "total_products": total})  # Top 10 categories

    except Exception as e:
        logger.error(f"Error fetching product categories: {e}", exc_info=True)
        return fail(f"Failed to fetch categories: {str(e)}", status=500)


@router.get("/safety-insights", response_model=ApiResponse)
async def get_safety_insights(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get personalized safety insights and recommendations"""
    try:
        insights = []

        # Check monitoring coverage
        total_scans = (
            db.query(ImageJob)
            .filter(
                ImageJob.user_id == current_user.id,
                ImageJob.status == JobStatus.COMPLETED,
            )
            .count()
        )

        monitored = (
            db.query(MonitoredProduct)
            .filter(MonitoredProduct.user_id == current_user.id, MonitoredProduct.is_active)
            .count()
        )

        if total_scans > 0:
            coverage = (monitored / total_scans) * 100
            if coverage < 50:
                insights.append(
                    {
                        "type": "recommendation",
                        "title": "Increase Monitoring Coverage",
                        "message": f"Only {round(coverage)}% of your scanned products are being monitored. Enable monitoring for more products to stay safer.",
                        "priority": "medium",
                    }
                )

        # Check scan frequency
        last_scan = (
            db.query(ImageJob).filter(ImageJob.user_id == current_user.id).order_by(desc(ImageJob.created_at)).first()
        )

        if last_scan:
            days_since = (datetime.utcnow() - last_scan.created_at).days
            if days_since > 14:
                insights.append(
                    {
                        "type": "reminder",
                        "title": "Time for a Safety Check",
                        "message": f"It's been {days_since} days since your last scan. Regular scanning helps identify new products.",
                        "priority": "low",
                    }
                )

        # Check for unread notifications
        unread = (
            db.query(NotificationHistory)
            .filter(
                NotificationHistory.user_id == current_user.id,
                NotificationHistory.read_at.is_(None),
                NotificationHistory.type == "recall",
            )
            .count()
        )

        if unread > 0:
            insights.append(
                {
                    "type": "alert",
                    "title": "Unread Recall Alerts",
                    "message": f"You have {unread} unread recall notifications. Check them immediately for safety.",
                    "priority": "high",
                }
            )

        # Check for recalled products
        recalled = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == current_user.id,
                MonitoredProduct.is_active,
                MonitoredProduct.recall_status == "recalled",
            )
            .count()
        )

        if recalled > 0:
            insights.append(
                {
                    "type": "warning",
                    "title": "Active Recalls",
                    "message": f"{recalled} of your monitored products have active recalls. Review and take action.",
                    "priority": "high",
                }
            )

        # Positive reinforcement
        if monitored >= 5 and recalled == 0:
            insights.append(
                {
                    "type": "success",
                    "title": "Great Job!",
                    "message": "All your monitored products are currently safe. Keep up the good monitoring!",
                    "priority": "low",
                }
            )

        return ok({"insights": insights, "generated_at": datetime.utcnow().isoformat() + "Z"})

    except Exception as e:
        logger.error(f"Error fetching safety insights: {e}", exc_info=True)
        return fail(f"Failed to fetch insights: {str(e)}", status=500)


@router.get("/recent-recalls", response_model=ApiResponse)
async def get_recent_recalls(
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get recent recalls relevant to user's products"""
    try:
        # Get user's product identifiers
        user_upcs = set()
        user_brands = set()

        # From monitored products
        monitored = (
            db.query(MonitoredProduct)
            .filter(MonitoredProduct.user_id == current_user.id, MonitoredProduct.is_active)
            .all()
        )

        for product in monitored:
            if product.upc_code:
                user_upcs.add(product.upc_code)
            if product.brand_name:
                user_brands.add(product.brand_name.lower())

        # From scan history
        extractions = (
            db.query(ImageExtraction).join(ImageJob).filter(ImageJob.user_id == current_user.id).limit(100).all()
        )

        for ext in extractions:
            if ext.upc_code:
                user_upcs.add(ext.upc_code)
            if ext.brand_name:
                user_brands.add(ext.brand_name.lower())

        # Find relevant recalls
        recalls = []

        if user_upcs or user_brands:
            query = db.query(RecallDB).order_by(desc(RecallDB.recall_date))

            # Filter by UPCs or brands
            # Note: This is simplified - you'd want more sophisticated matching
            recent_recalls = query.limit(limit * 2).all()

            for recall in recent_recalls:
                relevant = False

                # Check UPC match
                if hasattr(recall, "upc_codes") and recall.upc_codes:
                    for upc in user_upcs:
                        if upc in recall.upc_codes:
                            relevant = True
                            break

                # Check brand match
                if not relevant and recall.brand:
                    for brand in user_brands:
                        if brand in recall.brand.lower():
                            relevant = True
                            break

                if relevant or len(recalls) < 3:  # Include some general recalls
                    recalls.append(
                        {
                            "id": recall.id,
                            "title": recall.title,
                            "brand": recall.brand,
                            "product": recall.product_name,
                            "hazard": recall.hazard_description,
                            "date": recall.recall_date.isoformat() if recall.recall_date else None,
                            "relevant": relevant,
                        }
                    )

                if len(recalls) >= limit:
                    break

        return ok({"recalls": recalls, "total": len(recalls)})

    except Exception as e:
        logger.error(f"Error fetching recent recalls: {e}", exc_info=True)
        return fail(f"Failed to fetch recalls: {str(e)}", status=500)


@router.get("/achievements", response_model=ApiResponse)
async def get_user_achievements(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get user achievements and milestones"""
    try:
        achievements = []

        # Scan milestones
        total_scans = db.query(ImageJob).filter(ImageJob.user_id == current_user.id).count()

        scan_milestones = [1, 10, 25, 50, 100, 250, 500, 1000]
        for milestone in scan_milestones:
            if total_scans >= milestone:
                achievements.append(
                    {
                        "id": f"scans_{milestone}",
                        "title": f"Scanner Level {scan_milestones.index(milestone) + 1}",
                        "description": f"Completed {milestone} product scans",
                        "icon": "🔍",
                        "unlocked": True,
                        "date": None,  # Would need to track when unlocked
                    }
                )

        # Monitoring achievements
        monitored = (
            db.query(MonitoredProduct)
            .filter(MonitoredProduct.user_id == current_user.id, MonitoredProduct.is_active)
            .count()
        )

        if monitored >= 5:
            achievements.append(
                {
                    "id": "guardian_5",
                    "title": "Safety Guardian",
                    "description": "Monitoring 5+ products",
                    "icon": "🛡️",
                    "unlocked": True,
                }
            )

        if monitored >= 20:
            achievements.append(
                {
                    "id": "guardian_20",
                    "title": "Super Guardian",
                    "description": "Monitoring 20+ products",
                    "icon": "🦸",
                    "unlocked": True,
                }
            )

        # Safety achievements
        recalled_handled = (
            db.query(NotificationHistory)
            .filter(
                NotificationHistory.user_id == current_user.id,
                NotificationHistory.type == "recall",
                NotificationHistory.read_at.isnot(None),
            )
            .count()
        )

        if recalled_handled > 0:
            achievements.append(
                {
                    "id": "first_recall",
                    "title": "Safety First",
                    "description": "Handled your first recall alert",
                    "icon": "⚠️",
                    "unlocked": True,
                }
            )

        # Streak achievements
        # Check for daily scanning streak
        today = datetime.utcnow().date()
        streak = 0
        for i in range(30):
            check_date = today - timedelta(days=i)
            scans = (
                db.query(ImageJob)
                .filter(
                    ImageJob.user_id == current_user.id,
                    func.date(ImageJob.created_at) == check_date,
                )
                .count()
            )

            if scans > 0:
                streak += 1
            else:
                break

        if streak >= 7:
            achievements.append(
                {
                    "id": "streak_7",
                    "title": "Week Warrior",
                    "description": "7-day scanning streak",
                    "icon": "🔥",
                    "unlocked": True,
                }
            )

        if streak >= 30:
            achievements.append(
                {
                    "id": "streak_30",
                    "title": "Safety Champion",
                    "description": "30-day scanning streak",
                    "icon": "🏆",
                    "unlocked": True,
                }
            )

        return ok(
            {
                "achievements": achievements,
                "total_unlocked": len(achievements),
                "current_streak": streak,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching achievements: {e}", exc_info=True)
        return fail(f"Failed to fetch achievements: {str(e)}", status=500)
