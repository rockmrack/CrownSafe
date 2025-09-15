"""
Tests for subscription system (monthly and annual plans)
Tests receipt validation, entitlement checks, and subscription management
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import base64

from core_infra.subscription_models import (
    Subscription, SubscriptionPlan, SubscriptionStatus, PaymentProvider
)
from core_infra.subscription_service import SubscriptionService
from core_infra.receipt_validator import (
    AppleReceiptValidator, GoogleReceiptValidator, ReceiptValidationService
)
from core_infra.subscription_config import SubscriptionConfig
from core_infra.database import get_db_session, User


# Test fixtures
@pytest.fixture
def test_user():
    """Create a test user"""
    with get_db_session() as db:
        user = User(
            email="test@example.com",
            hashed_password="hashed_password",
            is_subscribed=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        yield user
        # Cleanup
        db.delete(user)
        db.commit()


@pytest.fixture
def monthly_subscription(test_user):
    """Create a monthly subscription"""
    with get_db_session() as db:
        sub = Subscription(
            user_id=test_user.id,
            plan=SubscriptionPlan.MONTHLY,
            status=SubscriptionStatus.ACTIVE,
            provider=PaymentProvider.APPLE,
            product_id=SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            original_transaction_id="test_monthly_123",
            price=7.99,
            currency="USD"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        yield sub
        # Cleanup
        db.delete(sub)
        db.commit()


@pytest.fixture
def annual_subscription(test_user):
    """Create an annual subscription"""
    with get_db_session() as db:
        sub = Subscription(
            user_id=test_user.id,
            plan=SubscriptionPlan.ANNUAL,
            status=SubscriptionStatus.ACTIVE,
            provider=PaymentProvider.GOOGLE,
            product_id=SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            original_transaction_id="test_annual_456",
            price=79.99,
            currency="USD"
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        yield sub
        # Cleanup
        db.delete(sub)
        db.commit()


class TestSubscriptionConfig:
    """Test subscription configuration"""
    
    def test_product_mappings(self):
        """Test product ID mappings"""
        # Monthly products
        monthly_apple = SubscriptionConfig.get_product_info(
            SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY
        )
        assert monthly_apple["plan"] == "monthly"
        assert monthly_apple["duration_months"] == 1
        assert monthly_apple["price"] == 7.99
        assert monthly_apple["provider"] == "apple"
        
        # Annual products
        annual_google = SubscriptionConfig.get_product_info(
            SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL
        )
        assert annual_google["plan"] == "annual"
        assert annual_google["duration_months"] == 12
        assert annual_google["price"] == 79.99
        assert annual_google["provider"] == "google"
    
    def test_valid_product_ids(self):
        """Test product ID validation"""
        assert SubscriptionConfig.is_valid_product_id(
            SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY
        )
        assert SubscriptionConfig.is_valid_product_id(
            SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL
        )
        assert not SubscriptionConfig.is_valid_product_id("invalid_product")
    
    def test_get_duration_months(self):
        """Test getting subscription duration"""
        assert SubscriptionConfig.get_duration_months(
            SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY
        ) == 1
        assert SubscriptionConfig.get_duration_months(
            SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL
        ) == 12
        assert SubscriptionConfig.get_duration_months("invalid") == 0


class TestSubscriptionService:
    """Test subscription service"""
    
    def test_is_active_with_valid_subscription(self, monthly_subscription):
        """Test checking active subscription"""
        assert SubscriptionService.is_active(monthly_subscription.user_id)
    
    def test_is_active_with_expired_subscription(self, test_user):
        """Test checking expired subscription"""
        with get_db_session() as db:
            # Create expired subscription
            sub = Subscription(
                user_id=test_user.id,
                plan=SubscriptionPlan.MONTHLY,
                status=SubscriptionStatus.ACTIVE,
                provider=PaymentProvider.APPLE,
                product_id=SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
                started_at=datetime.utcnow() - timedelta(days=60),
                expires_at=datetime.utcnow() - timedelta(days=30),
                original_transaction_id="expired_123"
            )
            db.add(sub)
            db.commit()
        
        # Should return False and mark as expired
        assert not SubscriptionService.is_active(test_user.id)
        
        # Check that subscription was marked as expired
        with get_db_session() as db:
            sub = db.query(Subscription).filter(
                Subscription.original_transaction_id == "expired_123"
            ).first()
            assert sub.status == SubscriptionStatus.EXPIRED
    
    def test_get_active_subscription(self, monthly_subscription):
        """Test getting active subscription details"""
        sub_data = SubscriptionService.get_active_subscription(
            monthly_subscription.user_id
        )
        
        assert sub_data is not None
        assert sub_data["plan"] == "monthly"
        assert sub_data["is_active"] is True
        assert sub_data["provider"] == "apple"
    
    def test_get_subscription_status_active(self, annual_subscription):
        """Test getting subscription status for active subscription"""
        status = SubscriptionService.get_subscription_status(
            annual_subscription.user_id
        )
        
        assert status["active"] is True
        assert status["plan"] == "annual"
        assert status["provider"] == "google"
        assert status["days_remaining"] >= 364
        assert status["auto_renew"] is True
    
    def test_cancel_subscription(self, monthly_subscription):
        """Test cancelling subscription"""
        result = SubscriptionService.cancel_subscription(
            monthly_subscription.user_id
        )
        
        assert result["success"] is True
        assert "expires_at" in result
        
        # Check subscription is marked as cancelled but still active
        with get_db_session() as db:
            sub = db.query(Subscription).filter(
                Subscription.id == monthly_subscription.id
            ).first()
            assert sub.cancelled_at is not None
            assert sub.auto_renew is False
            assert sub.status == SubscriptionStatus.ACTIVE
    
    def test_get_subscription_history(self, test_user):
        """Test getting subscription history"""
        # Create multiple subscriptions
        with get_db_session() as db:
            for i in range(3):
                sub = Subscription(
                    user_id=test_user.id,
                    plan=SubscriptionPlan.MONTHLY,
                    status=SubscriptionStatus.EXPIRED,
                    provider=PaymentProvider.APPLE,
                    product_id=SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
                    started_at=datetime.utcnow() - timedelta(days=90 + i*30),
                    expires_at=datetime.utcnow() - timedelta(days=60 + i*30),
                    original_transaction_id=f"history_{i}"
                )
                db.add(sub)
            db.commit()
        
        history = SubscriptionService.get_subscription_history(test_user.id, limit=5)
        assert len(history) == 3
        # Most recent first
        assert history[0]["original_transaction_id"] == "history_0"
    
    def test_check_expiring_soon(self, test_user):
        """Test finding subscriptions expiring soon"""
        with get_db_session() as db:
            # Create subscription expiring in 2 days
            sub = Subscription(
                user_id=test_user.id,
                plan=SubscriptionPlan.MONTHLY,
                status=SubscriptionStatus.ACTIVE,
                provider=PaymentProvider.APPLE,
                product_id=SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
                started_at=datetime.utcnow() - timedelta(days=28),
                expires_at=datetime.utcnow() + timedelta(days=2),
                original_transaction_id="expiring_soon",
                auto_renew=False  # Not auto-renewing
            )
            db.add(sub)
            db.commit()
        
        expiring = SubscriptionService.check_expiring_soon(days_threshold=3)
        assert len(expiring) == 1
        assert expiring[0]["user_id"] == test_user.id
        assert expiring[0]["days_remaining"] <= 2
    
    def test_subscription_metrics(self, monthly_subscription, annual_subscription):
        """Test getting subscription metrics"""
        metrics = SubscriptionService.get_subscription_metrics()
        
        assert metrics["active_total"] >= 2
        assert metrics["active_monthly"] >= 1
        assert metrics["active_annual"] >= 1


class TestAppleReceiptValidator:
    """Test Apple receipt validation"""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_valid_monthly_receipt(self, mock_post):
        """Test validating valid monthly Apple receipt"""
        # Mock Apple's response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": 0,
            "latest_receipt_info": [{
                "product_id": SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
                "transaction_id": "apple_txn_123",
                "original_transaction_id": "apple_original_123",
                "purchase_date_ms": "1700000000000",
                "expires_date_ms": str(int((datetime.utcnow() + timedelta(days=30)).timestamp() * 1000)),
                "is_trial_period": "false"
            }],
            "pending_renewal_info": [{
                "auto_renew_status": "1"
            }]
        }
        mock_post.return_value = mock_response
        
        validator = AppleReceiptValidator()
        is_valid, receipt_info = await validator.validate("fake_receipt_data")
        
        assert is_valid is True
        assert receipt_info["product_id"] == SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY
        assert receipt_info["original_transaction_id"] == "apple_original_123"
        assert receipt_info["auto_renew"] is True
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_valid_annual_receipt(self, mock_post):
        """Test validating valid annual Apple receipt"""
        # Mock Apple's response
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": 0,
            "latest_receipt_info": [{
                "product_id": SubscriptionConfig.APPLE_PRODUCT_ID_ANNUAL,
                "transaction_id": "apple_txn_456",
                "original_transaction_id": "apple_original_456",
                "purchase_date_ms": "1700000000000",
                "expires_date_ms": str(int((datetime.utcnow() + timedelta(days=365)).timestamp() * 1000)),
                "is_trial_period": "false"
            }],
            "pending_renewal_info": [{
                "auto_renew_status": "1"
            }]
        }
        mock_post.return_value = mock_response
        
        validator = AppleReceiptValidator()
        is_valid, receipt_info = await validator.validate("fake_annual_receipt")
        
        assert is_valid is True
        assert receipt_info["product_id"] == SubscriptionConfig.APPLE_PRODUCT_ID_ANNUAL
        assert receipt_info["expires_date"] > datetime.utcnow() + timedelta(days=360)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_invalid_receipt(self, mock_post):
        """Test invalid Apple receipt"""
        mock_response = Mock()
        mock_response.json.return_value = {"status": 21002}  # Invalid receipt
        mock_post.return_value = mock_response
        
        validator = AppleReceiptValidator()
        is_valid, receipt_info = await validator.validate("invalid_receipt")
        
        assert is_valid is False
        assert receipt_info is None


class TestReceiptValidationService:
    """Test complete receipt validation service"""
    
    @pytest.mark.asyncio
    @patch.object(AppleReceiptValidator, 'validate')
    async def test_validate_and_activate_monthly(self, mock_validate, test_user):
        """Test validating and activating monthly subscription"""
        # Mock successful validation
        mock_validate.return_value = (True, {
            "product_id": SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
            "transaction_id": "test_txn",
            "original_transaction_id": "test_original",
            "purchase_date": datetime.utcnow(),
            "expires_date": datetime.utcnow() + timedelta(days=30),
            "is_trial": False,
            "auto_renew": True
        })
        
        service = ReceiptValidationService()
        result = await service.validate_and_activate(
            user_id=test_user.id,
            provider="apple",
            receipt_data="fake_monthly_receipt"
        )
        
        assert result["success"] is True
        assert result["subscription"]["plan"] == "monthly"
        assert result["subscription"]["is_active"] is True
        
        # Check database
        with get_db_session() as db:
            sub = db.query(Subscription).filter(
                Subscription.user_id == test_user.id
            ).first()
            assert sub is not None
            assert sub.plan == SubscriptionPlan.MONTHLY
            assert sub.status == SubscriptionStatus.ACTIVE
            
            # Check user is marked as subscribed
            user = db.query(User).filter(User.id == test_user.id).first()
            assert user.is_subscribed is True
    
    @pytest.mark.asyncio
    @patch.object(GoogleReceiptValidator, 'validate')
    async def test_validate_and_activate_annual(self, mock_validate, test_user):
        """Test validating and activating annual subscription"""
        # Mock successful validation
        mock_validate.return_value = (True, {
            "product_id": SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL,
            "transaction_id": "google_order_123",
            "original_transaction_id": "google_original_123",
            "purchase_date": datetime.utcnow(),
            "expires_date": datetime.utcnow() + timedelta(days=365),
            "is_trial": False,
            "auto_renew": True
        })
        
        service = ReceiptValidationService()
        result = await service.validate_and_activate(
            user_id=test_user.id,
            provider="google",
            receipt_data="fake_purchase_token",
            product_id=SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL
        )
        
        assert result["success"] is True
        assert result["subscription"]["plan"] == "annual"
        
        # Check database
        with get_db_session() as db:
            sub = db.query(Subscription).filter(
                Subscription.user_id == test_user.id
            ).first()
            assert sub is not None
            assert sub.plan == SubscriptionPlan.ANNUAL
            assert sub.price == 79.99
    
    @pytest.mark.asyncio
    @patch.object(AppleReceiptValidator, 'validate')
    async def test_invalid_receipt_handling(self, mock_validate, test_user):
        """Test handling invalid receipt"""
        # Mock failed validation
        mock_validate.return_value = (False, None)
        
        service = ReceiptValidationService()
        result = await service.validate_and_activate(
            user_id=test_user.id,
            provider="apple",
            receipt_data="invalid_receipt"
        )
        
        assert result["success"] is False
        assert "error" in result
        
        # Check no subscription was created
        with get_db_session() as db:
            sub = db.query(Subscription).filter(
                Subscription.user_id == test_user.id
            ).first()
            assert sub is None
    
    @pytest.mark.asyncio
    async def test_unknown_product_id(self, test_user):
        """Test handling unknown product ID"""
        service = ReceiptValidationService()
        
        # Mock the validators to return a receipt with unknown product
        with patch.object(AppleReceiptValidator, 'validate') as mock_validate:
            mock_validate.return_value = (True, {
                "product_id": "unknown_product",
                "transaction_id": "test",
                "original_transaction_id": "test",
                "purchase_date": datetime.utcnow(),
                "expires_date": datetime.utcnow() + timedelta(days=30),
                "is_trial": False,
                "auto_renew": True
            })
            
            result = await service.validate_and_activate(
                user_id=test_user.id,
                provider="apple",
                receipt_data="receipt_with_unknown_product"
            )
            
            assert result["success"] is False
            assert "Unknown product ID" in result["error"]


class TestSubscriptionModels:
    """Test subscription model methods"""
    
    def test_subscription_is_active(self):
        """Test subscription is_active method"""
        # Active subscription
        active_sub = Subscription(
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.utcnow() + timedelta(days=10)
        )
        assert active_sub.is_active() is True
        
        # Expired subscription
        expired_sub = Subscription(
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.utcnow() - timedelta(days=10)
        )
        assert expired_sub.is_active() is False
        
        # Cancelled subscription
        cancelled_sub = Subscription(
            status=SubscriptionStatus.CANCELLED,
            expires_at=datetime.utcnow() + timedelta(days=10)
        )
        assert cancelled_sub.is_active() is False
    
    def test_calculate_expiry(self):
        """Test expiry date calculation"""
        start_date = datetime(2024, 1, 1)
        
        # Monthly subscription
        monthly_sub = Subscription(
            plan=SubscriptionPlan.MONTHLY,
            started_at=start_date
        )
        expiry = monthly_sub.calculate_expiry()
        assert expiry == start_date + timedelta(days=30)
        
        # Annual subscription
        annual_sub = Subscription(
            plan=SubscriptionPlan.ANNUAL,
            started_at=start_date
        )
        expiry = annual_sub.calculate_expiry()
        assert expiry == start_date + timedelta(days=365)
    
    def test_subscription_to_dict(self):
        """Test subscription serialization"""
        sub = Subscription(
            id="test_id",
            user_id=1,
            plan=SubscriptionPlan.ANNUAL,
            status=SubscriptionStatus.ACTIVE,
            provider=PaymentProvider.APPLE,
            product_id=SubscriptionConfig.APPLE_PRODUCT_ID_ANNUAL,
            started_at=datetime(2024, 1, 1),
            expires_at=datetime(2025, 1, 1),
            auto_renew=True
        )
        
        data = sub.to_dict()
        
        assert data["id"] == "test_id"
        assert data["user_id"] == 1
        assert data["plan"] == "annual"
        assert data["status"] == "active"
        assert data["provider"] == "apple"
        assert data["auto_renew"] is True
        assert data["is_active"] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
