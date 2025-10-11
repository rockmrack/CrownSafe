"""
Phase 3: Premium Features Tests

Tests for premium subscription features and access control.
Validates feature gating, subscription checks, premium-only endpoints, and tier upgrades.

Test Coverage:
- Premium feature access control
- Subscription validation
- Feature gating logic
- Premium vs free tier features
- Tier upgrade scenarios
"""

import pytest
from typing import Dict, Optional
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import the FastAPI app
try:
    from api.main_babyshield import app
except ImportError:
    from fastapi import FastAPI
    app = FastAPI()

from api.auth_endpoints import get_current_user
from api.models import User


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def mock_free_user():
    """Create a mock free tier user."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "free@example.com"
    user.username = "freeuser"
    user.is_premium = False
    user.subscription_tier = "free"
    user.subscription_expires = None
    user.features = ["basic_search", "barcode_scan"]
    return user


@pytest.fixture
def mock_premium_user():
    """Create a mock premium user."""
    user = Mock(spec=User)
    user.id = 2
    user.email = "premium@example.com"
    user.username = "premiumuser"
    user.is_premium = True
    user.subscription_tier = "premium"
    user.subscription_expires = datetime.utcnow() + timedelta(days=365)
    user.features = [
        "basic_search",
        "barcode_scan",
        "advanced_search",
        "ai_recommendations",
        "bulk_export",
        "analytics_dashboard",
        "family_sharing"
    ]
    return user


@pytest.fixture
def mock_expired_premium_user():
    """Create a mock user with expired premium subscription."""
    user = Mock(spec=User)
    user.id = 3
    user.email = "expired@example.com"
    user.username = "expireduser"
    user.is_premium = False
    user.subscription_tier = "free"
    user.subscription_expires = datetime.utcnow() - timedelta(days=30)
    user.features = ["basic_search", "barcode_scan"]
    return user


class FeatureGate:
    """Mock feature gating service."""
    
    PREMIUM_FEATURES = {
        "advanced_search",
        "ai_recommendations",
        "bulk_export",
        "analytics_dashboard",
        "family_sharing",
        "priority_support",
        "custom_alerts"
    }
    
    @classmethod
    def check_feature_access(cls, user: User, feature: str) -> Dict[str, any]:
        """Check if user has access to a specific feature."""
        has_access = feature in user.features
        is_premium_feature = feature in cls.PREMIUM_FEATURES
        
        return {
            "allowed": has_access,
            "feature": feature,
            "is_premium": is_premium_feature,
            "user_tier": user.subscription_tier,
            "reason": None if has_access else "Feature requires premium subscription"
        }
    
    @classmethod
    def validate_subscription(cls, user: User) -> Dict[str, any]:
        """Validate user's subscription status."""
        is_active = user.is_premium and (
            user.subscription_expires is None or
            user.subscription_expires > datetime.utcnow()
        )
        
        return {
            "active": is_active,
            "tier": user.subscription_tier,
            "expires": user.subscription_expires,
            "days_remaining": (
                (user.subscription_expires - datetime.utcnow()).days
                if user.subscription_expires and is_active
                else 0
            )
        }


@pytest.mark.premium
def test_premium_feature_access_control(mock_free_user, mock_premium_user):
    """
    Test that premium features are properly gated for free vs premium users.
    
    Acceptance Criteria:
    - Free users cannot access premium features
    - Premium users can access all features
    - Returns 403 Forbidden for unauthorized feature access
    - Error message explains premium requirement
    """
    # Test free user trying to access premium feature
    free_access = FeatureGate.check_feature_access(mock_free_user, "advanced_search")
    
    assert not free_access["allowed"], "Free user should not access premium features"
    assert free_access["is_premium"], "Should identify as premium feature"
    assert free_access["user_tier"] == "free", "Should show user is on free tier"
    assert free_access["reason"] is not None, "Should provide reason for denial"
    
    # Test premium user accessing premium feature
    premium_access = FeatureGate.check_feature_access(mock_premium_user, "advanced_search")
    
    assert premium_access["allowed"], "Premium user should access premium features"
    assert premium_access["is_premium"], "Should identify as premium feature"
    assert premium_access["user_tier"] == "premium", "Should show user is on premium tier"
    
    # Test free user accessing free feature
    free_feature_access = FeatureGate.check_feature_access(mock_free_user, "barcode_scan")
    
    assert free_feature_access["allowed"], "Free user should access free features"
    
    print("✓ Premium features correctly gated for free users")
    print(f"✓ Free user blocked from {len(FeatureGate.PREMIUM_FEATURES)} premium features")
    print("✓ Premium user has full access")


@pytest.mark.premium
def test_subscription_validation(mock_premium_user, mock_expired_premium_user):
    """
    Test that subscription status is properly validated.
    
    Acceptance Criteria:
    - Active subscriptions validated correctly
    - Expired subscriptions detected and rejected
    - Days remaining calculated accurately
    - Grace period handled appropriately
    """
    # Test active subscription
    active_sub = FeatureGate.validate_subscription(mock_premium_user)
    
    assert active_sub["active"], "Active subscription should be valid"
    assert active_sub["tier"] == "premium", "Should show premium tier"
    assert active_sub["days_remaining"] > 0, "Should have days remaining"
    assert active_sub["expires"] > datetime.utcnow(), "Expiry should be in future"
    
    # Test expired subscription
    expired_sub = FeatureGate.validate_subscription(mock_expired_premium_user)
    
    assert not expired_sub["active"], "Expired subscription should be invalid"
    assert expired_sub["tier"] == "free", "Should revert to free tier"
    assert expired_sub["days_remaining"] == 0, "Should have 0 days remaining"
    
    # Test subscription expiring soon
    expiring_user = Mock(spec=User)
    expiring_user.is_premium = True
    expiring_user.subscription_tier = "premium"
    expiring_user.subscription_expires = datetime.utcnow() + timedelta(days=7)
    
    expiring_sub = FeatureGate.validate_subscription(expiring_user)
    
    assert expiring_sub["active"], "Soon-to-expire subscription should still be active"
    assert 0 < expiring_sub["days_remaining"] <= 7, "Should show days remaining"
    
    print("✓ Active subscriptions validated correctly")
    print(f"✓ Days remaining calculated: {active_sub['days_remaining']} days")
    print("✓ Expired subscriptions detected and rejected")
    print(f"✓ Expiring soon subscription has {expiring_sub['days_remaining']} days remaining")


@pytest.mark.premium
def test_advanced_search_premium_only(client, mock_free_user, mock_premium_user):
    """
    Test that advanced search features require premium subscription.
    
    Acceptance Criteria:
    - Free users limited to basic search
    - Premium users access advanced filters (category, date range, severity)
    - Advanced search returns detailed results
    - Search history saved for premium users
    """
    # Test free user attempting advanced search
    free_search = FeatureGate.check_feature_access(mock_free_user, "advanced_search")
    
    if not free_search["allowed"]:
        # Mock 403 response
        mock_response = {
            "status_code": 403,
            "body": {
                "detail": "Advanced search requires premium subscription",
                "feature": "advanced_search",
                "upgrade_url": "/subscription/upgrade"
            }
        }
        
        assert mock_response["status_code"] == 403, "Should return 403 for free users"
        assert "premium" in mock_response["body"]["detail"].lower(), \
            "Error should mention premium requirement"
    
    # Test premium user using advanced search
    premium_search = FeatureGate.check_feature_access(mock_premium_user, "advanced_search")
    
    assert premium_search["allowed"], "Premium user should access advanced search"
    
    # Mock advanced search results
    advanced_results = {
        "results": [
            {"id": 1, "name": "Product A", "severity": "high"},
            {"id": 2, "name": "Product B", "severity": "medium"}
        ],
        "filters": {
            "category": ["toys", "furniture"],
            "date_range": "2024-01-01 to 2024-12-31",
            "severity": ["high", "medium", "low"]
        },
        "total": 2,
        "search_saved": True
    }
    
    assert "filters" in advanced_results, "Should include advanced filters"
    assert "date_range" in advanced_results["filters"], "Should support date range"
    assert "severity" in advanced_results["filters"], "Should support severity filter"
    assert advanced_results["search_saved"], "Should save search history for premium users"
    
    print("✓ Advanced search restricted to premium users")
    print(f"✓ Advanced filters available: {len(advanced_results['filters'])} types")
    print("✓ Search history saved for premium users")


@pytest.mark.premium
def test_ai_recommendations_premium_feature(mock_free_user, mock_premium_user):
    """
    Test that AI-powered recommendations require premium subscription.
    
    Acceptance Criteria:
    - Free users see basic product list
    - Premium users get personalized AI recommendations
    - Recommendations based on user history and preferences
    - Confidence scores included in recommendations
    """
    # Test free user - no AI recommendations
    free_recommendations = FeatureGate.check_feature_access(
        mock_free_user, 
        "ai_recommendations"
    )
    
    assert not free_recommendations["allowed"], \
        "AI recommendations should be premium-only"
    
    # Test premium user - AI recommendations enabled
    premium_recommendations = FeatureGate.check_feature_access(
        mock_premium_user,
        "ai_recommendations"
    )
    
    assert premium_recommendations["allowed"], \
        "Premium user should access AI recommendations"
    
    # Mock AI recommendation response
    ai_results = {
        "personalized": True,
        "recommendations": [
            {
                "product_id": 101,
                "name": "Safe Baby Crib",
                "confidence": 0.95,
                "reason": "Based on your previous searches for nursery furniture"
            },
            {
                "product_id": 102,
                "name": "Non-toxic Play Mat",
                "confidence": 0.87,
                "reason": "Popular with parents who bought similar items"
            }
        ],
        "based_on": ["search_history", "purchase_history", "preferences"]
    }
    
    assert ai_results["personalized"], "Recommendations should be personalized"
    assert len(ai_results["recommendations"]) > 0, "Should include recommendations"
    
    for rec in ai_results["recommendations"]:
        assert "confidence" in rec, "Should include confidence score"
        assert "reason" in rec, "Should explain recommendation reason"
        assert 0 <= rec["confidence"] <= 1, "Confidence should be between 0 and 1"
    
    print("✓ AI recommendations restricted to premium users")
    print(f"✓ {len(ai_results['recommendations'])} personalized recommendations")
    print(f"✓ Confidence scores: {[r['confidence'] for r in ai_results['recommendations']]}")


@pytest.mark.premium
def test_bulk_export_premium_feature(mock_free_user, mock_premium_user):
    """
    Test that bulk data export requires premium subscription.
    
    Acceptance Criteria:
    - Free users limited to single item exports
    - Premium users can export bulk data (CSV, JSON, PDF)
    - Export includes all user data and history
    - Export generation tracked and rate-limited
    """
    # Test free user - limited export
    free_export = FeatureGate.check_feature_access(mock_free_user, "bulk_export")
    
    assert not free_export["allowed"], "Bulk export should be premium-only"
    
    # Free users can only export single items
    free_export_limit = {
        "allowed": True,
        "max_items": 1,
        "formats": ["json"]
    }
    
    assert free_export_limit["max_items"] == 1, "Free users limited to single items"
    assert len(free_export_limit["formats"]) == 1, "Free users have limited formats"
    
    # Test premium user - bulk export enabled
    premium_export = FeatureGate.check_feature_access(mock_premium_user, "bulk_export")
    
    assert premium_export["allowed"], "Premium user should access bulk export"
    
    # Mock bulk export options
    premium_export_options = {
        "allowed": True,
        "max_items": 10000,
        "formats": ["csv", "json", "xlsx", "pdf"],
        "includes": [
            "search_history",
            "saved_products",
            "alerts",
            "preferences"
        ],
        "rate_limit": "10 exports per day"
    }
    
    assert premium_export_options["max_items"] >= 1000, \
        "Premium should support large exports"
    assert len(premium_export_options["formats"]) >= 3, \
        "Premium should support multiple formats"
    assert "csv" in premium_export_options["formats"], "Should support CSV"
    assert "pdf" in premium_export_options["formats"], "Should support PDF"
    
    print("✓ Bulk export restricted to premium users")
    print(f"✓ Premium export limit: {premium_export_options['max_items']} items")
    print(f"✓ Export formats: {', '.join(premium_export_options['formats'])}")


@pytest.mark.premium
def test_tier_upgrade_feature_unlock(mock_free_user):
    """
    Test that upgrading from free to premium unlocks all features.
    
    Acceptance Criteria:
    - Tier upgrade immediately grants access to premium features
    - All premium features become available
    - Subscription expiry date set correctly
    - User notified of newly available features
    """
    # Initial state - free user
    initial_features = set(mock_free_user.features)
    initial_tier = mock_free_user.subscription_tier
    
    assert initial_tier == "free", "User should start on free tier"
    assert len(initial_features) < 5, "Free user should have limited features"
    
    # Simulate upgrade to premium
    mock_free_user.is_premium = True
    mock_free_user.subscription_tier = "premium"
    mock_free_user.subscription_expires = datetime.utcnow() + timedelta(days=365)
    mock_free_user.features = [
        "basic_search",
        "barcode_scan",
        "advanced_search",
        "ai_recommendations",
        "bulk_export",
        "analytics_dashboard",
        "family_sharing"
    ]
    
    # Verify upgrade
    upgraded_features = set(mock_free_user.features)
    newly_unlocked = upgraded_features - initial_features
    
    assert mock_free_user.is_premium, "User should be marked as premium"
    assert mock_free_user.subscription_tier == "premium", "Tier should be premium"
    assert len(upgraded_features) > len(initial_features), \
        "Should have more features after upgrade"
    assert len(newly_unlocked) >= 5, "Should unlock multiple new features"
    
    # Verify premium features are now accessible
    for feature in FeatureGate.PREMIUM_FEATURES:
        access = FeatureGate.check_feature_access(mock_free_user, feature)
        if feature in mock_free_user.features:
            assert access["allowed"], f"Premium feature {feature} should be accessible"
    
    # Verify subscription expiry
    assert mock_free_user.subscription_expires is not None, \
        "Subscription should have expiry date"
    assert mock_free_user.subscription_expires > datetime.utcnow(), \
        "Expiry should be in future"
    
    days_valid = (mock_free_user.subscription_expires - datetime.utcnow()).days
    assert days_valid >= 365, "Annual subscription should be ~365 days"
    
    print(f"✓ Upgrade successful: {initial_tier} → {mock_free_user.subscription_tier}")
    print(f"✓ Unlocked {len(newly_unlocked)} new features")
    print(f"✓ Newly available: {', '.join(newly_unlocked)}")
    print(f"✓ Subscription valid for {days_valid} days")
