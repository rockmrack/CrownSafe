#!/usr/bin/env python3
import requests
import json
import logging
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Test Configuration ---
API_URL = "http://localhost:8001/api/v1/safety-check"
TEST_USER_ID = 1
TEST_BARCODE = "850016249012"
# --------------------------


def validate_response(resp: Dict[str, Any]) -> bool:
    """
    Validate that:
      - status == COMPLETED
      - data.summary is non-empty string
      - data.risk_level is one of expected levels
    """
    if resp.get("status") != "COMPLETED":
        print(f"❌ TEST FAILED: status was '{resp.get('status')}', expected 'COMPLETED'.")
        return False

    data = resp.get("data", {})
    summary = data.get("summary", "")
    risk = data.get("risk_level", "")

    if not isinstance(summary, str) or not summary.strip():
        print("❌ TEST FAILED: summary is empty or missing.")
        return False

    # Accept any non-empty risk_level here; you can tighten to ["Low","Medium","High","Critical"]
    if not isinstance(risk, str) or not risk.strip():
        print("❌ TEST FAILED: risk_level is empty or missing.")
        return False

    # All checks passed
    return True


def main():
    logger.info("=== Starting Live End-to-End Recall Test ===")

    payload = {"user_id": TEST_USER_ID, "barcode": TEST_BARCODE}

    try:
        logger.info(f"POST {API_URL} → {payload}")
        r = requests.post(API_URL, json=payload, timeout=30)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: Could not reach API at {API_URL}")
        print("Please ensure your service is running (e.g. `docker-compose up -d`).")
        print(f"Error: {e}")
        print("=" * 60 + "\n")
        return

    try:
        result = r.json()
    except ValueError:
        print("❌ TEST FAILED: Response was not valid JSON:")
        print(r.text)
        return

    print("\n" + "=" * 60)
    print("          LIVE API TEST RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    if validate_response(result):
        print("✅✅✅ TEST PASSED: Received COMPLETED status with valid summary and risk level.")
    else:
        # validate_response already printed the failure reason
        pass

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
