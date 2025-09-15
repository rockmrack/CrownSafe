"""
Subscription service for entitlement checks and management
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from core_infra.database import get_db_session, User
from core_infra.subscription_models import (
    Subscription, SubscriptionStatus, SubscriptionPlan
)

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscription entitlements"""
    
    @staticmethod
    def _dev_entitlement_override(user_id: int, feature: str = None) -> Optional[Dict]:
        """
        DEV/QA only: allow entitlements via env without touching DB.
        ENTITLEMENTS_ALLOW_ALL: "1|true|yes" -> grant everything
        ENTITLEMENTS_ALLOWLIST: "67,123"      -> user_id allow-list
        ENTITLEMENTS_FEATURES:  "safety.check,safety.comprehensive" -> feature scope (empty = all)
        """
        val = os.getenv("ENTITLEMENTS_ALLOW_ALL", "").strip().lower()
        if val in ("1", "true", "yes"):
            return {"has_access": True, "subscription": {"plan": "DEV-OVERRIDE"}, "user_id": user_id}

        allow_users = {s.strip() for s in os.getenv("ENTITLEMENTS_ALLOWLIST", "").split(",") if s.strip()}
        if str(user_id) in allow_users:
            feats = {s.strip() for s in os.getenv("ENTITLEMENTS_FEATURES", "").split(",") if s.strip()}
            if not feats or (feature and feature in feats):
                return {"has_access": True, "subscription": {"plan": "DEV-OVERRIDE"}, "user_id": user_id}
        return None
    
    @staticmethod
    def is_active(user_id: int, db: Optional[Session] = None, feature: str = None) -> bool:
        """
        Check if user has an active subscription
        
        Args:
            user_id: User ID to check
            db: Optional database session
            feature: Optional feature name for dev override
        
        Returns:
            True if user has active subscription, False otherwise
        """
        # Check dev override first
        override = SubscriptionService._dev_entitlement_override(user_id, feature)
        if override:
            logger.info(f"DEV OVERRIDE: Granting access to user {user_id} for feature {feature}")
            return True
        
        if db:
            return SubscriptionService._check_active_with_session(user_id, db)
        
        with get_db_session() as session:
            return SubscriptionService._check_active_with_session(user_id, session)
    
    @staticmethod
    def _check_active_with_session(user_id: int, db: Session) -> bool:
        """Check active subscription with provided session"""
        # Get most recent active subscription
        subscription = db.query(Subscription).filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at > datetime.utcnow()
            )
        ).order_by(Subscription.expires_at.desc()).first()
        
        if subscription:
            return True
        
        # Check if we need to update expired subscriptions
        expired = db.query(Subscription).filter(
            and_(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at <= datetime.utcnow()
            )
        ).all()
        
        # Mark expired subscriptions
        for sub in expired:
            sub.status = SubscriptionStatus.EXPIRED
            logger.info(f"Marked subscription {sub.id} as expired for user {user_id}")
        
        if expired:
            # Update user's subscription status
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_subscribed = False
            db.commit()
        
        return False
    
    @staticmethod
    def get_active_subscription(user_id: int) -> Optional[Dict]:
        """
        Get user's active subscription details
        
        Args:
            user_id: User ID
        
        Returns:
            Subscription dict or None
        """
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > datetime.utcnow()
                )
            ).order_by(Subscription.expires_at.desc()).first()
            
            if subscription:
                return subscription.to_dict()
            
            return None
    
    @staticmethod
    def get_subscription_status(user_id: int) -> Dict:
        """
        Get detailed subscription status for user
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with subscription status details
        """
        with get_db_session() as db:
            # Get active subscription
            active = db.query(Subscription).filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > datetime.utcnow()
                )
            ).order_by(Subscription.expires_at.desc()).first()
            
            if active:
                days_remaining = (active.expires_at - datetime.utcnow()).days
                
                return {
                    "active": True,
                    "plan": active.plan.value,
                    "provider": active.provider.value,
                    "expires_at": active.expires_at.isoformat(),
                    "days_remaining": days_remaining,
                    "auto_renew": active.auto_renew,
                    "cancelled": active.cancelled_at is not None
                }
            
            # Check for expired subscription
            expired = db.query(Subscription).filter(
                and_(
                    Subscription.user_id == user_id,
                    or_(
                        Subscription.status == SubscriptionStatus.EXPIRED,
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            Subscription.expires_at <= datetime.utcnow()
                        )
                    )
                )
            ).order_by(Subscription.expires_at.desc()).first()
            
            if expired:
                return {
                    "active": False,
                    "plan": expired.plan.value,
                    "provider": expired.provider.value,
                    "expired_at": expired.expires_at.isoformat(),
                    "days_since_expiry": (datetime.utcnow() - expired.expires_at).days
                }
            
            # No subscription found
            return {
                "active": False,
                "plan": None,
                "message": "No subscription found"
            }
    
    @staticmethod
    def cancel_subscription(user_id: int) -> Dict:
        """
        Cancel user's subscription (will remain active until expiry)
        
        Args:
            user_id: User ID
        
        Returns:
            Result dict
        """
        with get_db_session() as db:
            subscription = db.query(Subscription).filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > datetime.utcnow()
                )
            ).first()
            
            if not subscription:
                return {
                    "success": False,
                    "error": "No active subscription found"
                }
            
            # Mark as cancelled but keep active until expiry
            subscription.auto_renew = False
            subscription.cancelled_at = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "message": "Subscription cancelled",
                "expires_at": subscription.expires_at.isoformat()
            }
    
    @staticmethod
    def get_subscription_history(user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get user's subscription history
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
        
        Returns:
            List of subscription dicts
        """
        with get_db_session() as db:
            subscriptions = db.query(Subscription).filter(
                Subscription.user_id == user_id
            ).order_by(Subscription.created_at.desc()).limit(limit).all()
            
            return [sub.to_dict() for sub in subscriptions]
    
    @staticmethod
    def check_expiring_soon(days_threshold: int = 3) -> List[Dict]:
        """
        Find subscriptions expiring soon
        
        Args:
            days_threshold: Days before expiry to check
        
        Returns:
            List of expiring subscriptions
        """
        with get_db_session() as db:
            threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
            
            expiring = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > datetime.utcnow(),
                    Subscription.expires_at <= threshold_date,
                    Subscription.auto_renew == False  # Only non-auto-renewing
                )
            ).all()
            
            return [
                {
                    "user_id": sub.user_id,
                    "subscription_id": sub.id,
                    "plan": sub.plan.value,
                    "expires_at": sub.expires_at.isoformat(),
                    "days_remaining": (sub.expires_at - datetime.utcnow()).days
                }
                for sub in expiring
            ]
    
    @staticmethod
    def cleanup_expired_subscriptions() -> int:
        """
        Clean up expired subscriptions (mark as expired and update users)
        
        Returns:
            Number of subscriptions cleaned up
        """
        with get_db_session() as db:
            # Find expired active subscriptions
            expired = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at <= datetime.utcnow()
                )
            ).all()
            
            count = 0
            user_ids = set()
            
            for sub in expired:
                sub.status = SubscriptionStatus.EXPIRED
                user_ids.add(sub.user_id)
                count += 1
                logger.info(f"Marked subscription {sub.id} as expired")
            
            # Update affected users
            if user_ids:
                for user_id in user_ids:
                    # Check if user has any other active subscriptions
                    has_active = db.query(Subscription).filter(
                        and_(
                            Subscription.user_id == user_id,
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            Subscription.expires_at > datetime.utcnow()
                        )
                    ).first() is not None
                    
                    if not has_active:
                        user = db.query(User).filter(User.id == user_id).first()
                        if user:
                            user.is_subscribed = False
                            logger.info(f"Updated user {user_id} subscription status to False")
            
            db.commit()
            
            return count
    
    @staticmethod
    def get_subscription_metrics() -> Dict:
        """
        Get subscription metrics for analytics
        
        Returns:
            Dict with subscription metrics
        """
        with get_db_session() as db:
            now = datetime.utcnow()
            
            # Total active subscriptions
            active_count = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now
                )
            ).count()
            
            # Active by plan
            monthly_count = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now,
                    Subscription.plan == SubscriptionPlan.MONTHLY
                )
            ).count()
            
            annual_count = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now,
                    Subscription.plan == SubscriptionPlan.ANNUAL
                )
            ).count()
            
            # Cancelled but still active
            cancelled_count = db.query(Subscription).filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > now,
                    Subscription.cancelled_at.isnot(None)
                )
            ).count()
            
            # Total expired
            expired_count = db.query(Subscription).filter(
                Subscription.status == SubscriptionStatus.EXPIRED
            ).count()
            
            return {
                "active_total": active_count,
                "active_monthly": monthly_count,
                "active_annual": annual_count,
                "cancelled_active": cancelled_count,
                "expired_total": expired_count,
                "monthly_percentage": (monthly_count / active_count * 100) if active_count > 0 else 0,
                "annual_percentage": (annual_count / active_count * 100) if active_count > 0 else 0
            }
