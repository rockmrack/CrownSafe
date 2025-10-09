"""
Subscription API endpoints for mobile app IAP
Handles receipt validation and entitlement checks
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import logging

from core_infra.database import get_db_session, User
from core_infra.auth import get_current_user
from core_infra.subscription_service import SubscriptionService
from core_infra.receipt_validator import ReceiptValidationService
from core_infra.subscription_config import SubscriptionConfig
from core_infra.rate_limiter import limiter
from api.services.dev_override import dev_entitled

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/subscription", tags=["subscriptions"])


# Pydantic models for requests/responses
class ActivateSubscriptionRequest(BaseModel):
    """Request to activate subscription with receipt"""

    provider: str = Field(..., pattern="^(apple|google)$", description="Payment provider")
    receipt_data: str = Field(
        ..., description="Receipt data (base64 for Apple, purchase token for Google)"
    )
    product_id: Optional[str] = Field(None, description="Product ID (required for Google)")


class SubscriptionStatusResponse(BaseModel):
    """Subscription status response"""

    active: bool
    plan: Optional[str] = None
    provider: Optional[str] = None
    expires_at: Optional[str] = None
    days_remaining: Optional[int] = None
    auto_renew: Optional[bool] = None
    cancelled: Optional[bool] = None
    message: Optional[str] = None


class EntitlementResponse(BaseModel):
    """Entitlement check response"""

    has_access: bool
    subscription: Optional[SubscriptionStatusResponse] = None
    user_id: int


class EntitlementData(BaseModel):
    """Entitlement data for standardized response"""

    feature: str
    entitled: bool
    subscription: Optional[SubscriptionStatusResponse] = None
    user_id: int


class EntitlementEnvelope(BaseModel):
    """Standardized entitlement response envelope"""

    success: bool = True
    data: EntitlementData


class ActivateSubscriptionResponse(BaseModel):
    """Response after activating subscription"""

    success: bool
    subscription: Optional[Dict] = None
    error: Optional[str] = None


# Initialize services
receipt_service = ReceiptValidationService()


@router.post("/activate", response_model=ActivateSubscriptionResponse)
async def activate_subscription(
    request: Request,
    data: ActivateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Activate subscription by validating receipt from Apple/Google

    This endpoint should be called after a successful purchase in the mobile app.
    The app sends the receipt data which we validate with Apple/Google servers.
    """
    logger.info(f"Activating subscription for user {current_user.id} with provider {data.provider}")

    try:
        # Validate and activate subscription
        result = await receipt_service.validate_and_activate(
            user_id=current_user.id,
            provider=data.provider,
            receipt_data=data.receipt_data,
            product_id=data.product_id,
        )

        if result["success"]:
            logger.info(f"Successfully activated subscription for user {current_user.id}")
        else:
            logger.warning(
                f"Failed to activate subscription for user {current_user.id}: {result.get('error')}"
            )

        return ActivateSubscriptionResponse(**result)

    except Exception as e:
        logger.error(f"Error activating subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to activate subscription")


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    request: Request,
    user_id: Optional[int] = Query(None, description="User ID (for testing without auth)"),
    current_user: Optional[User] = Depends(lambda: None),
):
    """
    Get current subscription status for authenticated user or by user_id

    Returns detailed information about the user's subscription including
    plan type, expiry date, and auto-renewal status.
    """
    try:
        # Use user_id parameter if provided (for testing), otherwise use authenticated user
        target_user_id = (
            user_id if user_id is not None else (current_user.id if current_user else None)
        )

        if target_user_id is None:
            return SubscriptionStatusResponse(
                active=False,
                plan=None,
                provider=None,
                expires_at=None,
                days_remaining=None,
                auto_renew=None,
                cancelled=None,
                message="User ID required",
            )

        status = SubscriptionService.get_subscription_status(target_user_id)

        return SubscriptionStatusResponse(
            active=status.get("active", False),
            plan=status.get("plan"),
            provider=status.get("provider"),
            expires_at=status.get("expires_at") or status.get("expired_at"),
            days_remaining=status.get("days_remaining"),
            auto_renew=status.get("auto_renew"),
            cancelled=status.get("cancelled"),
            message=status.get("message"),
        )
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}", exc_info=True)
        # Return safe fallback response
        return SubscriptionStatusResponse(
            active=False,
            plan=None,
            provider=None,
            expires_at=None,
            days_remaining=None,
            auto_renew=None,
            cancelled=None,
            message="Subscription service temporarily unavailable",
        )


@router.get("/entitlement", response_model=EntitlementEnvelope)
async def check_entitlement(
    request: Request,
    user_id: int = Query(..., ge=1, description="User ID to check entitlement for"),
    feature: str = Query(..., min_length=3, description="Feature to check entitlement for"),
    db=Depends(get_db_session),
):
    """
    Quick entitlement check for feature access

    This is a lightweight endpoint for the mobile app to quickly check
    if the user has an active subscription and can access premium features.
    Returns standardized response envelope with 'entitled' field.
    """
    try:
        # Validate feature exists (known features list)
        known_features = {
            "safety.check",
            "safety.comprehensive",
            "premium.pregnancy",
            "premium.allergy",
            "enhanced.scan",
            "basic.scan",
        }

        if feature not in known_features:
            raise HTTPException(status_code=404, detail=f"Unknown feature: {feature}")

        # DEV override first - early return if entitled via dev override
        if dev_entitled(user_id, feature):
            return EntitlementEnvelope(
                success=True,
                data=EntitlementData(
                    feature=feature,
                    entitled=True,
                    user_id=user_id,
                    subscription=SubscriptionStatusResponse(
                        active=True,
                        plan="DEV-OVERRIDE",
                        provider="dev",
                        expires_at=None,
                        auto_renew=False,
                    ),
                ),
            )

        has_access = SubscriptionService.is_active(user_id, feature=feature)
        subscription_data = None

        # Include subscription details if active
        if has_access:
            # Check if this is a dev override first
            override = SubscriptionService._dev_entitlement_override(user_id, feature)
            if override:
                # Use dev override data
                subscription_data = SubscriptionStatusResponse(
                    active=True,
                    plan="DEV-OVERRIDE",
                    provider="dev",
                    expires_at=None,
                    auto_renew=False,
                )
            else:
                # Get real subscription data
                subscription_data = SubscriptionService.get_active_subscription(user_id)
                if subscription_data:
                    subscription_data = SubscriptionStatusResponse(
                        active=True,
                        plan=subscription_data.get("plan"),
                        provider=subscription_data.get("provider"),
                        expires_at=subscription_data.get("expires_at"),
                        auto_renew=subscription_data.get("auto_renew"),
                    )

        # Create standardized response
        payload = EntitlementData(
            feature=feature,
            entitled=bool(has_access),
            subscription=subscription_data,
            user_id=user_id,
        )

        return EntitlementEnvelope(success=True, data=payload)

    except Exception as e:
        logger.error(f"Error checking entitlement: {e}", exc_info=True)
        # Return safe fallback response
        payload = EntitlementData(
            feature=feature, entitled=False, subscription=None, user_id=user_id
        )
        return EntitlementEnvelope(success=True, data=payload)


@router.post("/cancel")
async def cancel_subscription(request: Request, current_user: User = Depends(get_current_user)):
    """
    Cancel subscription (will remain active until expiry)

    This marks the subscription as cancelled but it remains active
    until the current period expires.
    """
    try:
        # Validate user is authenticated
        if not current_user or not hasattr(current_user, "id"):
            raise HTTPException(status_code=401, detail="Authentication required")

        result = SubscriptionService.cancel_subscription(current_user.id)

        if not result["success"]:
            raise HTTPException(
                status_code=400, detail=result.get("error", "Failed to cancel subscription")
            )

        return result

    except HTTPException:
        # Re-raise HTTP exceptions (401, 400) as-is
        raise
    except Exception as e:
        logger.error(
            f"Error cancelling subscription for user {current_user.id if current_user else 'unknown'}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")


@router.get("/history")
async def get_subscription_history(
    request: Request, limit: int = 10, current_user: User = Depends(get_current_user)
):
    """
    Get subscription history for the authenticated user

    Returns a list of past and current subscriptions.
    """
    try:
        # Ensure user is authenticated
        if not current_user or not hasattr(current_user, "id"):
            raise HTTPException(status_code=401, detail="Authentication required")

        history = SubscriptionService.get_subscription_history(current_user.id, limit)

        return {"subscriptions": history or [], "count": len(history) if history else 0}
    except HTTPException:
        # Re-raise HTTP exceptions (like 401)
        raise
    except Exception as e:
        logger.error(
            f"Error getting subscription history for user {current_user.id if current_user else 'unknown'}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription history")


@router.get("/history-dev")
async def get_subscription_history_dev(
    request: Request,
    user_id: int = Query(..., ge=1, description="User ID to get history for"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort: str = Query("date", description="Sort by: date, amount, status"),
    order: str = Query("desc", description="Sort order: asc, desc"),
):
    """
    K-4 History: Dev override version for testing subscription history

    Returns paginated subscription history with date ordering and empty state handling.
    """
    try:
        # Mock subscription history data
        mock_history = [
            {
                "id": "sub_001",
                "plan": "Premium Plan",
                "status": "active",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-12-31T23:59:59Z",
                "amount": 9.99,
                "currency": "USD",
                "provider": "stripe",
            },
            {
                "id": "sub_002",
                "plan": "Basic Plan",
                "status": "expired",
                "start_date": "2023-06-01T00:00:00Z",
                "end_date": "2023-12-31T23:59:59Z",
                "amount": 4.99,
                "currency": "USD",
                "provider": "stripe",
            },
        ]

        # Sort history
        if sort == "date":
            mock_history.sort(key=lambda x: x["start_date"], reverse=(order == "desc"))
        elif sort == "amount":
            mock_history.sort(key=lambda x: x["amount"], reverse=(order == "desc"))
        elif sort == "status":
            mock_history.sort(key=lambda x: x["status"], reverse=(order == "desc"))

        # Pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_history = mock_history[start_idx:end_idx]

        return {
            "success": True,
            "page": page,
            "limit": limit,
            "total": len(mock_history),
            "history": paginated_history,
            "has_more": end_idx < len(mock_history),
        }

    except Exception as e:
        logger.error(f"Error getting subscription history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription history")


@router.get("/products")
async def get_available_products(request: Request):
    """
    Get available subscription products

    Returns the product IDs and pricing for monthly and annual plans.
    This helps the mobile app display the correct products.
    """
    return {
        "products": [
            {
                "id": SubscriptionConfig.APPLE_PRODUCT_ID_MONTHLY,
                "platform": "apple",
                "plan": "monthly",
                "price": SubscriptionConfig.MONTHLY_PRICE,
                "currency": "USD",
                "duration_months": 1,
            },
            {
                "id": SubscriptionConfig.APPLE_PRODUCT_ID_ANNUAL,
                "platform": "apple",
                "plan": "annual",
                "price": SubscriptionConfig.ANNUAL_PRICE,
                "currency": "USD",
                "duration_months": 12,
                "savings": f"${(SubscriptionConfig.MONTHLY_PRICE * 12 - SubscriptionConfig.ANNUAL_PRICE):.2f}",
            },
            {
                "id": SubscriptionConfig.GOOGLE_PRODUCT_ID_MONTHLY,
                "platform": "google",
                "plan": "monthly",
                "price": SubscriptionConfig.MONTHLY_PRICE,
                "currency": "USD",
                "duration_months": 1,
            },
            {
                "id": SubscriptionConfig.GOOGLE_PRODUCT_ID_ANNUAL,
                "platform": "google",
                "plan": "annual",
                "price": SubscriptionConfig.ANNUAL_PRICE,
                "currency": "USD",
                "duration_months": 12,
                "savings": f"${(SubscriptionConfig.MONTHLY_PRICE * 12 - SubscriptionConfig.ANNUAL_PRICE):.2f}",
            },
        ]
    }


# Admin endpoints (protected separately)
@router.get("/admin/metrics", include_in_schema=False)
async def get_subscription_metrics(
    request: Request, current_user: User = Depends(get_current_user)
):
    """
    Get subscription metrics (admin only)

    Returns analytics data about subscriptions.
    """
    # Check if user is admin (you should implement proper admin check)
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    metrics = SubscriptionService.get_subscription_metrics()

    return metrics


@router.post("/admin/cleanup", include_in_schema=False)
async def cleanup_expired_subscriptions(
    request: Request, current_user: User = Depends(get_current_user)
):
    """
    Clean up expired subscriptions (admin only)

    Marks expired subscriptions and updates user statuses.
    """
    # Check if user is admin
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    count = SubscriptionService.cleanup_expired_subscriptions()

    return {"success": True, "subscriptions_cleaned": count}


# ==================== Products/Plans ====================


class PlanFeature(BaseModel):
    """Feature included in a plan"""

    name: str = Field(..., description="Feature name")
    description: str = Field(..., description="Feature description")
    enabled: bool = Field(True, description="Whether feature is enabled")


class SubscriptionPlan(BaseModel):
    """Subscription plan details"""

    id: str = Field(..., description="Plan ID")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    price: float = Field(..., description="Monthly price in USD")
    currency: str = Field("USD", description="Currency code")
    features: List[PlanFeature] = Field(..., description="Included features")
    popular: bool = Field(False, description="Whether this is a popular plan")
    trial_days: int = Field(0, description="Free trial days")


class PlansResponse(BaseModel):
    """Response for plans endpoint"""

    success: bool = Field(True, description="Request success status")
    plans: List[SubscriptionPlan] = Field(..., description="Available subscription plans")
    total: int = Field(..., description="Total number of plans")


@router.get("/plans", response_model=PlansResponse)
async def get_subscription_plans(
    request: Request,
    sort: str = Query("price", description="Sort by: price, name, popularity"),
    order: str = Query("asc", description="Sort order: asc, desc"),
    feature: Optional[str] = Query(None, description="Filter plans by feature"),
):
    """
    K-1 Products/Plans: Get available subscription plans with stable shape

    Returns pricing list with sorting, feature flags, and stable response shape.
    """
    try:
        # Define available plans
        plans = [
            SubscriptionPlan(
                id="basic",
                name="Basic Plan",
                description="Essential safety checking for families",
                price=4.99,
                features=[
                    PlanFeature(
                        name="safety.check",
                        description="Basic product safety checking",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="basic.scan", description="Standard barcode scanning", enabled=True
                    ),
                ],
                popular=False,
                trial_days=7,
            ),
            SubscriptionPlan(
                id="premium",
                name="Premium Plan",
                description="Advanced safety features with premium checks",
                price=9.99,
                features=[
                    PlanFeature(
                        name="safety.check",
                        description="Basic product safety checking",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="safety.comprehensive",
                        description="Comprehensive safety analysis",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="premium.pregnancy",
                        description="Pregnancy safety checks",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="premium.allergy",
                        description="Allergy sensitivity checks",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="enhanced.scan", description="Enhanced barcode scanning", enabled=True
                    ),
                ],
                popular=True,
                trial_days=14,
            ),
            SubscriptionPlan(
                id="family",
                name="Family Plan",
                description="Complete family safety protection",
                price=14.99,
                features=[
                    PlanFeature(
                        name="safety.check",
                        description="Basic product safety checking",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="safety.comprehensive",
                        description="Comprehensive safety analysis",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="premium.pregnancy",
                        description="Pregnancy safety checks",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="premium.allergy",
                        description="Allergy sensitivity checks",
                        enabled=True,
                    ),
                    PlanFeature(
                        name="enhanced.scan", description="Enhanced barcode scanning", enabled=True
                    ),
                    PlanFeature(
                        name="family.profiles",
                        description="Multiple family member profiles",
                        enabled=True,
                    ),
                ],
                popular=False,
                trial_days=30,
            ),
        ]

        # Filter by feature if specified
        if feature:
            plans = [plan for plan in plans if any(f.name == feature for f in plan.features)]

        # Sort plans
        if sort == "price":
            plans.sort(key=lambda p: p.price, reverse=(order == "desc"))
        elif sort == "name":
            plans.sort(key=lambda p: p.name, reverse=(order == "desc"))
        elif sort == "popularity":
            plans.sort(key=lambda p: p.popular, reverse=(order == "desc"))

        return PlansResponse(success=True, plans=plans, total=len(plans))

    except Exception as e:
        logger.error(f"Error getting subscription plans: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve subscription plans")
