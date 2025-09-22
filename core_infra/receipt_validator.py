"""
Receipt validation for Apple App Store and Google Play
Validates receipts and creates/updates subscriptions
"""

import json
import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import httpx

from core_infra.subscription_config import SubscriptionConfig
from core_infra.subscription_models import (
    Subscription, SubscriptionPlan, SubscriptionStatus, 
    PaymentProvider, ReceiptValidation
)
from core_infra.database import get_db_session, User

logger = logging.getLogger(__name__)

# Feature flag for receipt validation (disabled by default - requires Google service account key)
ENABLE_RECEIPT_VALIDATION = os.getenv("ENABLE_RECEIPT_VALIDATION", "false").lower() == "true"

# Google imports - optional
GOOGLE_API_AVAILABLE = False
if ENABLE_RECEIPT_VALIDATION:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        GOOGLE_API_AVAILABLE = True
        logger.info("Receipt validation enabled - Google API libraries available")
    except ImportError:
        logger.error("Receipt validation enabled but Google API libraries not available")
        if os.getenv("ENVIRONMENT") == "production":
            raise RuntimeError("Receipt validation enabled in production but Google API libraries missing")
else:
    logger.info("Receipt validation disabled by config")


class AppleReceiptValidator:
    """Validates Apple App Store receipts"""
    
    def __init__(self):
        self.shared_secret = SubscriptionConfig.APPLE_SHARED_SECRET
        self.verify_url = SubscriptionConfig.get_apple_verify_url()
    
    async def validate(self, receipt_data: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate Apple receipt
        Returns: (is_valid, receipt_info)
        """
        try:
            # Prepare request
            payload = {
                "receipt-data": receipt_data,
                "password": self.shared_secret,
                "exclude-old-transactions": True
            }
            
            # Send validation request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.verify_url,
                    json=payload,
                    timeout=10.0
                )
                result = response.json()
            
            # Check status
            status = result.get("status", -1)
            
            # Status 0 means valid
            if status == 0:
                return True, self._parse_receipt(result)
            
            # Status 21007 means wrong environment (sandbox receipt in production)
            # Try the other environment
            if status == 21007:
                other_url = (
                    SubscriptionConfig.APPLE_VERIFY_URL_PRODUCTION 
                    if self.verify_url == SubscriptionConfig.APPLE_VERIFY_URL_SANDBOX
                    else SubscriptionConfig.APPLE_VERIFY_URL_SANDBOX
                )
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        other_url,
                        json=payload,
                        timeout=10.0
                    )
                    result = response.json()
                
                if result.get("status") == 0:
                    return True, self._parse_receipt(result)
            
            # Log error status
            logger.warning(f"Apple receipt validation failed with status: {status}")
            return False, None
            
        except Exception as e:
            logger.error(f"Apple receipt validation error: {e}")
            return False, None
    
    def _parse_receipt(self, receipt_data: Dict) -> Dict:
        """Parse Apple receipt response"""
        latest_receipt_info = receipt_data.get("latest_receipt_info", [])
        
        if not latest_receipt_info:
            return {}
        
        # Get the most recent transaction
        latest = latest_receipt_info[-1]
        
        # Parse dates (Apple uses milliseconds)
        def parse_date(ms_string):
            if ms_string:
                return datetime.fromtimestamp(int(ms_string) / 1000)
            return None
        
        return {
            "product_id": latest.get("product_id"),
            "transaction_id": latest.get("transaction_id"),
            "original_transaction_id": latest.get("original_transaction_id"),
            "purchase_date": parse_date(latest.get("purchase_date_ms")),
            "expires_date": parse_date(latest.get("expires_date_ms")),
            "is_trial": latest.get("is_trial_period") == "true",
            "auto_renew": receipt_data.get("pending_renewal_info", [{}])[0].get(
                "auto_renew_status"
            ) == "1"
        }


class GoogleReceiptValidator:
    """Validates Google Play receipts"""
    
    def __init__(self):
        self.package_name = SubscriptionConfig.GOOGLE_PACKAGE_NAME
        self.service = self._init_service()
    
    def _init_service(self):
        """Initialize Google Play API service"""
        try:
            if not ENABLE_RECEIPT_VALIDATION:
                logger.info("Receipt validation disabled - skipping Google service initialization")
                return None
                
            if not GOOGLE_API_AVAILABLE:
                logger.error("Receipt validation enabled but Google API libraries not available")
                return None
            
            # Try to get service account key from environment variable (ECS Secrets Manager)
            key_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
            if key_json:
                try:
                    key_data = json.loads(key_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        key_data,
                        scopes=["https://www.googleapis.com/auth/androidpublisher"]
                    )
                    return build("androidpublisher", "v3", credentials=credentials)
                except Exception as e:
                    logger.error(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
                    return None
            
            # Fallback to file path
            key_path = SubscriptionConfig.GOOGLE_SERVICE_ACCOUNT_KEY_PATH
            if not key_path or not os.path.exists(key_path):
                logger.error("Receipt validation enabled but Google service account key not configured")
                if os.getenv("ENVIRONMENT") == "production":
                    raise RuntimeError("Receipt validation enabled in production but Google service account key missing")
                return None
            
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/androidpublisher"]
            )
            
            return build("androidpublisher", "v3", credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to initialize Google Play service: {e}")
            return None
    
    async def validate(self, purchase_token: str, product_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate Google Play receipt
        Returns: (is_valid, receipt_info)
        """
        try:
            if not self.service:
                logger.error("Google Play service not initialized")
                return False, None
            
            # Get subscription purchase details
            purchase = self.service.purchases().subscriptions().get(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            
            # Check if purchase is valid
            if purchase.get("purchaseState") == 0:  # 0 = Purchased
                return True, self._parse_purchase(purchase, product_id)
            
            logger.warning(f"Google purchase invalid state: {purchase.get('purchaseState')}")
            return False, None
            
        except Exception as e:
            logger.error(f"Google receipt validation error: {e}")
            return False, None
    
    def _parse_purchase(self, purchase: Dict, product_id: str) -> Dict:
        """Parse Google Play purchase response"""
        # Parse dates (Google uses milliseconds)
        def parse_date(ms_string):
            if ms_string:
                return datetime.fromtimestamp(int(ms_string) / 1000)
            return None
        
        return {
            "product_id": product_id,
            "transaction_id": purchase.get("orderId"),
            "original_transaction_id": purchase.get("linkedPurchaseToken", purchase.get("orderId")),
            "purchase_date": parse_date(purchase.get("startTimeMillis")),
            "expires_date": parse_date(purchase.get("expiryTimeMillis")),
            "is_trial": purchase.get("paymentState") == 2,  # 2 = Free trial
            "auto_renew": purchase.get("autoRenewing", False)
        }


class ReceiptValidationService:
    """Main service for validating receipts and managing subscriptions"""
    
    def __init__(self):
        self.apple_validator = AppleReceiptValidator()
        self.google_validator = GoogleReceiptValidator()
    
    async def validate_and_activate(
        self, 
        user_id: int,
        provider: str,
        receipt_data: str,
        product_id: Optional[str] = None
    ) -> Dict:
        """
        Validate receipt and activate subscription
        
        Args:
            user_id: User ID
            provider: "apple" or "google"
            receipt_data: Receipt data (base64 for Apple, purchase token for Google)
            product_id: Product ID (required for Google)
        
        Returns:
            Dict with status and subscription info
        """
        try:
            # Validate based on provider
            if provider.lower() == "apple":
                is_valid, receipt_info = await self.apple_validator.validate(receipt_data)
                provider_enum = PaymentProvider.APPLE
            elif provider.lower() == "google":
                if not product_id:
                    return {
                        "success": False,
                        "error": "Product ID required for Google receipts"
                    }
                is_valid, receipt_info = await self.google_validator.validate(
                    receipt_data, product_id
                )
                provider_enum = PaymentProvider.GOOGLE
            else:
                return {
                    "success": False,
                    "error": f"Invalid provider: {provider}"
                }
            
            if not is_valid or not receipt_info:
                # Log failed validation
                self._log_validation(
                    user_id=user_id,
                    provider=provider_enum,
                    product_id=product_id or receipt_info.get("product_id", "unknown"),
                    receipt_hash=self._hash_receipt(receipt_data),
                    is_valid=False,
                    error="Receipt validation failed"
                )
                
                return {
                    "success": False,
                    "error": "Invalid receipt"
                }
            
            # Extract product ID from receipt if not provided
            if not product_id:
                product_id = receipt_info.get("product_id")
            
            # Get product configuration
            product_info = SubscriptionConfig.get_product_info(product_id)
            if not product_info:
                return {
                    "success": False,
                    "error": f"Unknown product ID: {product_id}"
                }
            
            # Create or update subscription
            subscription = await self._create_or_update_subscription(
                user_id=user_id,
                provider=provider_enum,
                receipt_info=receipt_info,
                product_info=product_info,
                receipt_data=receipt_data
            )
            
            # Log successful validation
            self._log_validation(
                user_id=user_id,
                provider=provider_enum,
                product_id=product_id,
                receipt_hash=self._hash_receipt(receipt_data),
                is_valid=True,
                subscription_id=subscription.id,
                transaction_id=receipt_info.get("original_transaction_id")
            )
            
            return {
                "success": True,
                "subscription": subscription.to_dict()
            }
            
        except Exception as e:
            logger.error(f"Receipt validation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_or_update_subscription(
        self,
        user_id: int,
        provider: PaymentProvider,
        receipt_info: Dict,
        product_info: Dict,
        receipt_data: str
    ) -> Subscription:
        """Create or update subscription in database"""
        with get_db_session() as db:
            # Use optimized UPSERT for subscription
            from core_infra.upsert_handler import upsert_handler
            
            subscription_data = {
                "user_id": user_id,
                "plan": product_info["plan"],
                "status": "active",
                "provider": provider.value,
                "product_id": receipt_info["product_id"],
                "started_at": receipt_info["purchase_date"],
                "expires_at": receipt_info["expires_date"],
                "original_transaction_id": receipt_info["original_transaction_id"],
                "latest_receipt": receipt_data[:5000],  # Store truncated receipt
                "price": product_info["price"],
                "currency": "USD",
                "auto_renew": receipt_info.get("auto_renew", True),
                "cancelled_at": None,
                "trial_end_date": receipt_info.get("trial_end_date")
            }
            
            # Perform UPSERT (will update if exists, insert if new)
            success = upsert_handler.upsert_subscription(db, subscription_data)
            
            if not success:
                raise ValueError("Failed to create/update subscription")
            
            # Fetch the subscription to return it
            subscription = db.query(Subscription).filter(
                Subscription.user_id == user_id,
                Subscription.original_transaction_id == receipt_info["original_transaction_id"]
            ).first()
            
            # Update user's subscription status
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_subscribed = True
            
            db.commit()
            db.refresh(subscription)
            return subscription
    
    def _hash_receipt(self, receipt_data: str) -> str:
        """Generate hash of receipt for deduplication"""
        return hashlib.sha256(receipt_data.encode()).hexdigest()
    
    def _log_validation(
        self,
        user_id: int,
        provider: PaymentProvider,
        product_id: str,
        receipt_hash: str,
        is_valid: bool,
        subscription_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Log receipt validation attempt"""
        try:
            with get_db_session() as db:
                validation = ReceiptValidation(
                    subscription_id=subscription_id,
                    user_id=user_id,
                    provider=provider,
                    product_id=product_id,
                    receipt_hash=receipt_hash,
                    transaction_id=transaction_id,
                    is_valid=is_valid,
                    error_message=error
                )
                db.add(validation)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to log validation: {e}")
