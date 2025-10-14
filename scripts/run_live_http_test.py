# scripts/run_live_http_test.py

import asyncio
import httpx
import json
import logging
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Set same database URL as seed script
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///babyshield_test.db")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

API_URL = os.getenv("API_URL", "http://127.0.0.1:8001/api/v1/safety-check")
TEST_BARCODE = "037000488786"  # MUST match the one in seed_for_live_test.py!
TEST_USER_ID = 1


async def verify_database_before_test():
    """Verify the database has our test data before making API call"""
    from core_infra.database import SessionLocal, RecallDB, DATABASE_URL

    logger = logging.getLogger(__name__)
    logger.info(f"Verifying database at: {DATABASE_URL}")

    with SessionLocal() as db:
        test_recall = db.query(RecallDB).filter_by(upc=TEST_BARCODE).first()
        if test_recall:
            logger.info(
                f"✅ Pre-test verification: Found recall with UPC {TEST_BARCODE}"
            )
            return True
        else:
            logger.error(
                f"❌ Pre-test verification: No recall found with UPC {TEST_BARCODE}"
            )
            all_recalls = db.query(RecallDB).all()
            logger.info(f"Total recalls in DB: {len(all_recalls)}")
            for r in all_recalls[:5]:  # Show first 5
                logger.info(f"  - Recall: {r.recall_id}, UPC: {r.upc}")
            return False


async def main():
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Live HTTP Test ---")

    # Verify database first
    if not await verify_database_before_test():
        logger.error(
            "Database verification failed! Make sure to run seed_for_live_test.py first."
        )
        return

    payload = {"barcode": TEST_BARCODE, "user_id": TEST_USER_ID}
    logger.info(f"Sending POST request to {API_URL} with payload: {payload}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(API_URL, json=payload)

            print("\n" + "=" * 50)
            print("          LIVE HTTP TEST RESULT")
            print("=" * 50)
            print(f"Status Code: {response.status_code}")
            print(f"Request URL: {API_URL}")
            print(f"Request Payload: {json.dumps(payload, indent=2)}")

            print("\n--- Response Headers ---")
            for key, value in response.headers.items():
                print(f"{key}: {value}")

            print("\n--- Response Body ---")
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))

                if response.status_code == 200:
                    if response_json.get("status") == "COMPLETED":
                        result = response_json.get("result", {})
                        recalls = result.get("recalls", [])
                        if recalls:
                            print("\n" + "=" * 50)
                            print(
                                "✅✅✅ TEST PASSED: The API successfully found recall(s):"
                            )
                            for recall in recalls:
                                print(f"\n  - Recall ID: {recall.get('recall_id')}")
                                print(f"    Product: {recall.get('product_name')}")
                                print(f"    UPC: {recall.get('upc')}")
                                print(f"    Hazard: {recall.get('hazard_description')}")
                        else:
                            print("\n" + "=" * 50)
                            print(
                                "❌ TEST FAILED: API call succeeded, but no recalls found."
                            )
                            print(
                                f"Expected to find recall for barcode: {TEST_BARCODE}"
                            )
                    else:
                        print("\n" + "=" * 50)
                        print(
                            f"❌ TEST FAILED: API returned status: {response_json.get('status')}"
                        )
                        if "error" in response_json:
                            print(f"Error: {response_json['error']}")
                else:
                    print("\n" + "=" * 50)
                    print(f"❌ TEST FAILED: HTTP {response.status_code}")

            except json.JSONDecodeError:
                print("Error: Could not decode JSON from response.")
                print(f"Response Text: {response.text}")
                print("\n" + "=" * 50)
                print("❌ TEST FAILED: The API did not return valid JSON.")

    except httpx.ConnectError:
        print("\n" + "=" * 50)
        print("❌ TEST FAILED: Could not connect to the API server.")
        print(f"Please ensure the API server is running at {API_URL}")
        print("If using Docker: docker-compose up -d")
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()

    print("\n--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
