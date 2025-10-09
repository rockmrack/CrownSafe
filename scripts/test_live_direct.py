# scripts/test_live_direct.py

import requests
import json
import logging
import argparse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
API_URL = "http://localhost:8001/api/v1/safety-check"
# -------------------


def main(barcode: str):
    """
    Runs a live, direct API test against the running Docker container with a given barcode.
    """
    logger.info(f"--- Starting Live End-to-End Recall Test for barcode: {barcode} ---")

    # The payload now includes a user_id, as our Commander expects it.
    payload = {"user_id": 1, "barcode": barcode, "image_url": None}  # A sample user ID

    try:
        print(f"> POST {API_URL} with payload: {payload}")
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        print("\n✅ Response JSON:")
        print(json.dumps(result, indent=2))

        if result.get("status") == "COMPLETED" and "data" in result:
            print("\n✅ LIVE TEST PASSED")
        else:
            print(f"\n❌ LIVE TEST FAILED: API returned status '{result.get('status')}'")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ TEST FAILED: Could not connect to the API at {API_URL}.")
        print("Please ensure your Docker containers are running with 'docker-compose up -d'.")
        print(f"Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a direct live test against the BabyShield API."
    )
    parser.add_argument("--barcode", required=True, help="The product barcode to test.")
    args = parser.parse_args()
    main(barcode=args.barcode)
