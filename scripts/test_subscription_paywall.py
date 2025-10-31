# scripts/test_subscription_paywall.py
# Test Scenario 5 (Corrected): Subscription Paywall

import asyncio
import json
import logging
import os
import sys

import httpx

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from core_infra.database import (  # noqa: E402
    SessionLocal,
    User,
    create_tables,
    drop_tables,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
API_BASE_URL = "http://127.0.0.1:8001"
SUBSCRIBER_ID = 1
NON_SUBSCRIBER_ID = 2
TEST_BARCODE = "381370037248"
# --------------------------


async def main():
    """Main function to test the subscription paywall."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Test Scenario 5: Subscription Paywall ---")

    # 1. Set up a clean database with our test users.
    drop_tables()
    create_tables()
    with SessionLocal() as db:
        # --- THIS IS THE FIX ---
        subscriber = User(id=SUBSCRIBER_ID, email="subscriber@test.com", is_subscribed=True)
        non_subscriber = User(id=NON_SUBSCRIBER_ID, email="nonsubscriber@test.com", is_subscribed=False)
        db.add_all([subscriber, non_subscriber])
        db.commit()
    logger.info("Database seeded with a subscriber and a non-subscriber.")

    # We assume the server is already running in a separate terminal.

    try:
        async with httpx.AsyncClient() as client:
            # --- Test 1: Non-Subscriber (Should be Blocked) ---
            logger.info("--- Testing Non-Subscriber (expect 403 Forbidden) ---")
            non_subscriber_payload = {
                "barcode": TEST_BARCODE,
                "user_id": NON_SUBSCRIBER_ID,
            }
            response_non_subscriber = await client.post(
                f"{API_BASE_URL}/api/v1/safety-check", json=non_subscriber_payload,
            )

            print("\n" + "=" * 50)
            print("          TEST RESULT for Non-Subscriber")
            print("=" * 50)
            print(f"Status Code: {response_non_subscriber.status_code}")
            print(f"Response Body: {response_non_subscriber.json()}")

            if response_non_subscriber.status_code == 403:
                print("\n✅✅✅ NON-SUBSCRIBER TEST PASSED: API correctly blocked access with a 403 Forbidden error.")
            else:
                print(
                    f"\n❌❌❌ NON-SUBSCRIBER TEST FAILED: Expected status code 403, but got {response_non_subscriber.status_code}.",  # noqa: E501
                )

            print("\n" + "#" * 60 + "\n")

            # --- Test 2: Subscriber (Should Succeed) ---
            logger.info("--- Testing Subscriber (expect 200 OK) ---")
            subscriber_payload = {"barcode": TEST_BARCODE, "user_id": SUBSCRIBER_ID}
            response_subscriber = await client.post(f"{API_BASE_URL}/api/v1/safety-check", json=subscriber_payload)

            print("\n" + "=" * 50)
            print("          TEST RESULT for Subscriber")
            print("=" * 50)
            print(f"Status Code: {response_subscriber.status_code}")
            print(f"Response Body: {json.dumps(response_subscriber.json(), indent=2)}")

            if response_subscriber.status_code == 200 and response_subscriber.json().get("status") == "COMPLETED":
                print("\n✅✅✅ SUBSCRIBER TEST PASSED: API correctly allowed access and the workflow completed.")
            else:
                print(
                    f"\n❌❌❌ SUBSCRIBER TEST FAILED: Expected status code 200, but got {response_subscriber.status_code}.",  # noqa: E501
                )

    except httpx.ConnectError:
        print("\n" + "=" * 50)
        print("❌ TEST FAILED: Could not connect to the API server.")
        print("Please ensure the FastAPI server is running in a separate terminal on port 8001.")
        print("Command: uvicorn api.main_crownsafe:app --port 8001")
    finally:
        # 3. Clean up the test database.
        drop_tables()
        logger.info("Database tables dropped.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
