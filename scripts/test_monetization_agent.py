# scripts/test_monetization_agent.py

import sys
import os
import asyncio
import logging
import json
from unittest.mock import patch, MagicMock

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

# We need to set up a test database BEFORE we import the agent logic
from core_infra.database import Base, engine, SessionLocal, User
from agents.business.monetization_agent.agent_logic import MonetizationAgentLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Test Configuration ---
TEST_USER_ID = 1
TEST_USER_EMAIL = "test.user@example.com"
# --------------------------


async def main():
    """Main function to run the MonetizationAgent test with a mocked Stripe API and a live test database."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting MonetizationAgent Test ---")

    # 1. Set up a clean, in-memory test database for this test run.
    logger.info("Setting up in-memory test database...")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Create a fake user for the test with required fields
        test_user = User(
            id=TEST_USER_ID, email=TEST_USER_EMAIL, hashed_password="fakehashedpassword"
        )
        db.add(test_user)
        db.commit()
    logger.info(f"Database seeded with test user ID: {TEST_USER_ID}")

    try:
        # 2. Initialize the real MonetizationAgentLogic.
        agent_logic = MonetizationAgentLogic(agent_id="test_mon_001")
        logger.info("Agent logic initialized.")

        # 3. Mock the Stripe API calls.
        mock_customer = MagicMock()
        mock_customer.id = "cus_test_12345"

        mock_session = MagicMock()
        mock_session.id = "cs_test_12345"
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_12345"

        with (
            patch("stripe.Customer.create", return_value=mock_customer) as mock_customer_create,
            patch(
                "stripe.checkout.Session.create", return_value=mock_session
            ) as mock_session_create,
        ):
            # 4. Call the agent's primary logic function.
            logger.info(
                "Calling agent_logic.create_subscription_checkout_session (Stripe API is mocked)..."
            )
            result = agent_logic.create_subscription_checkout_session(
                user_id=TEST_USER_ID, tier="family_tier"
            )
            logger.info("Task processing finished.")

            # 5. Verify the Stripe API was called correctly.
            mock_customer_create.assert_called_once()
            mock_session_create.assert_called_once()
            logger.info("Verified that Stripe Customer.create and Session.create were both called.")

        # 6. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 7. Validate the result.
        if result.get("status") == "success":
            checkout_url = result.get("checkout_url", "")
            if "https://checkout.stripe.com" in checkout_url:
                print("\n" + "=" * 50)
                print("✅✅✅ TEST PASSED: Successfully created a mock checkout session.")
            else:
                print("\n" + "=" * 50)
                print("❌ TEST FAILED: The checkout URL was not in the expected format.")
        else:
            print("\n" + "=" * 50)
            print(
                f"❌ TEST FAILED: The agent returned an error status. Message: {result.get('message')}"
            )

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}", exc_info=True)

    finally:
        # 8. Clean up the test database.
        logger.info("Tearing down in-memory test database...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    # This agent's logic is synchronous, so we don't need asyncio.run
    asyncio.run(main())
