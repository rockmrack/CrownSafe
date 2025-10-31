# agents/business/monetization_agent/agent_logic.py

import logging
import os
from typing import Any

import stripe

from core_infra.database import User, get_db_session

logger = logging.getLogger(__name__)

# Load the Stripe secret key from environment variables
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
FAMILY_TIER_PRICE_ID = "price_1RmzVqGvt4HMLy3kEwtI8AtZ"  # Replace with your actual price


class MonetizationAgentLogic:
    """Manages user monetization, Stripe integration, and subscription state.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.logger = logger
        if not stripe.api_key:
            self.logger.error("Stripe API key not configured. MonetizationAgent will not function.")
        self.logger.info("MonetizationAgentLogic initialized.")

    def create_stripe_customer(self, user_id: int) -> dict[str, Any]:
        """Ensure the user is a Stripe customer; if not, create and persist the Stripe customer_id.
        """
        self.logger.info(f"Creating Stripe customer for user_id: {user_id}")
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"status": "error", "message": "User not found."}
                # Already linked to Stripe
                if getattr(user, "stripe_customer_id", None):
                    return {
                        "status": "success",
                        "stripe_customer_id": user.stripe_customer_id,
                    }

                # Create customer on Stripe
                customer = stripe.Customer.create(email=user.email, metadata={"babyshield_user_id": user.id})
                user.stripe_customer_id = customer.id
                db.commit()
                db.refresh(user)
                self.logger.info(f"Linked user {user.id} to Stripe customer {customer.id}")
                return {"status": "success", "stripe_customer_id": customer.id}
        except Exception as e:
            self.logger.error(f"Stripe customer creation failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Stripe customer creation failed: {e}",
            }

    def create_subscription_checkout_session(self, user_id: int, tier: str) -> dict[str, Any]:
        """Creates a Stripe Checkout session for the user's subscription tier.
        """
        self.logger.info(f"Creating checkout session for user_id: {user_id}, tier: {tier}")
        price_id = None
        if tier == "family_tier":
            price_id = FAMILY_TIER_PRICE_ID
        # Extend with more tiers if needed

        if not price_id:
            return {
                "status": "error",
                "message": f"Invalid or missing subscription tier: {tier}",
            }

        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"status": "error", "message": "User not found."}

                # Ensure Stripe customer exists (may create if missing)
                if not getattr(user, "stripe_customer_id", None):
                    cust_res = self.create_stripe_customer(user_id)
                    if cust_res.get("status") != "success":
                        return cust_res
                    db.refresh(user)

                # Now create the Checkout Session
                checkout_session = stripe.checkout.Session.create(
                    customer=user.stripe_customer_id,
                    payment_method_types=["card"],
                    line_items=[{"price": price_id, "quantity": 1}],
                    mode="subscription",
                    success_url="https://babyshield.com/subscribe/success?session_id={CHECKOUT_SESSION_ID}",
                    cancel_url="https://babyshield.com/subscribe/cancel",
                )
                self.logger.info(f"Created Stripe checkout session for user {user.id}: {checkout_session.url}")
                return {"status": "success", "checkout_url": checkout_session.url}

        except Exception as e:
            self.logger.error(f"Failed to create Stripe checkout session: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Checkout session creation failed: {e}",
            }

    def get_user_subscription_status(self, user_id: int) -> dict[str, Any]:
        """Return the subscription status for the user.
        """
        self.logger.info(f"Checking subscription status for user_id: {user_id}")
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not getattr(user, "stripe_customer_id", None):
                    return {"status": "success", "tier": "free", "is_active": False}

            subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
            for sub in subscriptions.data:
                if sub.status == "active":
                    sub_tier = "family_tier" if sub.items.data[0].price.id == FAMILY_TIER_PRICE_ID else "standard"
                    self.logger.info(f"User {user.id} has an active '{sub_tier}' subscription.")
                    return {
                        "status": "success",
                        "tier": sub_tier,
                        "is_active": True,
                        "stripe_subscription_id": sub.id,
                    }

            self.logger.info(f"User {user.id} has no active subscriptions.")
            return {"status": "success", "tier": "free", "is_active": False}
        except Exception as e:
            self.logger.error(f"Failed to get Stripe subscription status: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to check subscription status: {e}",
            }

    def cancel_user_subscription(self, user_id: int) -> dict[str, Any]:
        """Cancels the user's active Stripe subscription.
        """
        self.logger.info(f"Attempting to cancel subscription for user_id: {user_id}")
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not getattr(user, "stripe_customer_id", None):
                    return {"status": "error", "message": "No Stripe customer linked."}

            subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)
            for sub in subscriptions.data:
                if sub.status == "active":
                    stripe.Subscription.delete(sub.id)
                    self.logger.info(f"Cancelled Stripe subscription {sub.id} for user {user.id}")
                    return {"status": "success", "cancelled_subscription_id": sub.id}
            return {"status": "error", "message": "No active subscription found."}
        except Exception as e:
            self.logger.error(f"Failed to cancel subscription: {e}", exc_info=True)
            return {"status": "error", "message": f"Failed to cancel subscription: {e}"}

    # Helper for onboarding/UX flows (optional)
    def get_or_create_customer_and_checkout(self, user_id: int, tier: str) -> dict[str, Any]:
        """Ensure Stripe customer exists, then create a checkout session (one call UX).
        """
        cust = self.create_stripe_customer(user_id)
        if cust.get("status") != "success":
            return cust
        return self.create_subscription_checkout_session(user_id, tier)
