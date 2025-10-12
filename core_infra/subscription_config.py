"""
Subscription configuration for mobile IAP
Centralizes all subscription-related settings
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class SubscriptionConfig:
    """Centralized subscription configuration"""

    # Product IDs
    APPLE_PRODUCT_ID_MONTHLY = os.getenv(
        "APPLE_PRODUCT_ID_MONTHLY", "babyshield_monthly"
    )
    APPLE_PRODUCT_ID_ANNUAL = os.getenv("APPLE_PRODUCT_ID_ANNUAL", "babyshield_annual")
    GOOGLE_PRODUCT_ID_MONTHLY = os.getenv(
        "GOOGLE_PRODUCT_ID_MONTHLY", "babyshield_monthly"
    )
    GOOGLE_PRODUCT_ID_ANNUAL = os.getenv(
        "GOOGLE_PRODUCT_ID_ANNUAL", "babyshield_annual"
    )

    # Apple Configuration
    APPLE_SHARED_SECRET = os.getenv("APPLE_SHARED_SECRET", "")
    APPLE_ENVIRONMENT = os.getenv(
        "APPLE_ENVIRONMENT", "sandbox"
    )  # sandbox or production
    APPLE_VERIFY_URL_SANDBOX = "https://sandbox.itunes.apple.com/verifyReceipt"
    APPLE_VERIFY_URL_PRODUCTION = "https://buy.itunes.apple.com/verifyReceipt"

    # Google Configuration
    GOOGLE_SERVICE_ACCOUNT_KEY_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH", "")
    GOOGLE_PACKAGE_NAME = os.getenv("GOOGLE_PACKAGE_NAME", "com.babyshield.app")

    # Pricing
    MONTHLY_PRICE = float(os.getenv("MONTHLY_PRICE", "7.99"))
    ANNUAL_PRICE = float(os.getenv("ANNUAL_PRICE", "79.99"))

    # Product mappings
    PRODUCT_MAPPINGS = {
        # Apple products
        APPLE_PRODUCT_ID_MONTHLY: {
            "plan": "monthly",
            "duration_months": 1,
            "price": MONTHLY_PRICE,
            "provider": "apple",
        },
        APPLE_PRODUCT_ID_ANNUAL: {
            "plan": "annual",
            "duration_months": 12,
            "price": ANNUAL_PRICE,
            "provider": "apple",
        },
        # Google products
        GOOGLE_PRODUCT_ID_MONTHLY: {
            "plan": "monthly",
            "duration_months": 1,
            "price": MONTHLY_PRICE,
            "provider": "google",
        },
        GOOGLE_PRODUCT_ID_ANNUAL: {
            "plan": "annual",
            "duration_months": 12,
            "price": ANNUAL_PRICE,
            "provider": "google",
        },
    }

    @classmethod
    def get_product_info(cls, product_id: str) -> Optional[Dict]:
        """Get product information by ID"""
        return cls.PRODUCT_MAPPINGS.get(product_id)

    @classmethod
    def get_apple_verify_url(cls) -> str:
        """Get appropriate Apple verification URL based on environment"""
        if cls.APPLE_ENVIRONMENT == "production":
            return cls.APPLE_VERIFY_URL_PRODUCTION
        return cls.APPLE_VERIFY_URL_SANDBOX

    @classmethod
    def is_valid_product_id(cls, product_id: str) -> bool:
        """Check if product ID is valid"""
        return product_id in cls.PRODUCT_MAPPINGS

    @classmethod
    def get_duration_months(cls, product_id: str) -> int:
        """Get subscription duration in months"""
        info = cls.get_product_info(product_id)
        return info["duration_months"] if info else 0

    @classmethod
    def get_plan_type(cls, product_id: str) -> Optional[str]:
        """Get plan type (monthly/annual) from product ID"""
        info = cls.get_product_info(product_id)
        return info["plan"] if info else None
