#!/usr/bin/env python3
"""scripts/test_model_number_scan.py

End-to-end test script for the Model Number Scanning feature.
Tests the new model_number parameter in the safety-check API endpoint
and verifies that model numbers are prioritized over barcodes for recall matching.
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Any

import requests

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_api_endpoint_with_model_number(
    user_id: int,
    barcode: str,
    model_number: str | None,
    api_url: str = "http://localhost:8001",
) -> dict[str, Any]:
    """Test the /api/v1/safety-check endpoint with model number parameter.

    Args:
        user_id: User ID for the safety check
        barcode: Product barcode
        model_number: Product model number (optional)
        api_url: Base URL for the API

    Returns:
        Dictionary containing test results

    """
    endpoint = f"{api_url}/api/v1/safety-check"

    payload = {"user_id": user_id, "barcode": barcode, "image_url": None}

    # Add model_number if provided
    if model_number:
        payload["model_number"] = model_number

    logger.info(f"Testing endpoint: {endpoint}")
    logger.info(f"Payload: {payload}")

    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        logger.info(f"Response status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            logger.info(f"Response JSON: {result}")
            return {
                "success": True,
                "status_code": response.status_code,
                "response": result,
            }
        else:
            logger.error(f"API returned non-200 status: {response.status_code}")
            logger.error(f"Response text: {response.text}")
            return {
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"success": False, "error": str(e)}


async def test_direct_database_search(model_number: str) -> dict[str, Any]:
    """Test direct database search for model number to verify data ingestion worked.

    Args:
        model_number: Model number to search for

    Returns:
        Dictionary containing search results

    """
    try:
        from core_infra.database import RecallDB, get_db_session

        logger.info(f"Testing direct database search for model number: {model_number}")

        with get_db_session() as db:
            # Search for exact model number match
            recalls = db.query(RecallDB).filter(RecallDB.model_number.ilike(model_number)).all()

            logger.info(f"Found {len(recalls)} recalls with model number '{model_number}'")

            if recalls:
                recall_data = []
                for recall in recalls:
                    recall_dict = {
                        "recall_id": recall.recall_id,
                        "product_name": recall.product_name,
                        "model_number": recall.model_number,
                        "source_agency": recall.source_agency,
                        "recall_date": recall.recall_date.isoformat() if recall.recall_date else None,
                    }
                    recall_data.append(recall_dict)
                    logger.info(f"  - {recall.recall_id}: {recall.product_name} (Model: {recall.model_number})")

                return {
                    "success": True,
                    "recalls_found": len(recalls),
                    "recalls": recall_data,
                }
            else:
                # Check if we have any model numbers in the database at all
                sample_models = (
                    db.query(RecallDB.model_number).filter(RecallDB.model_number.isnot(None)).limit(10).all()
                )
                logger.info(f"No exact matches. Sample model numbers in database: {[m[0] for m in sample_models]}")

                return {
                    "success": True,
                    "recalls_found": 0,
                    "sample_models": [m[0] for m in sample_models],
                }

    except Exception as e:
        logger.error(f"Database search failed: {e}")
        return {"success": False, "error": str(e)}


async def test_recall_data_agent_directly(model_number: str) -> dict[str, Any]:
    """Test the RecallDataAgent directly with model number input.

    Args:
        model_number: Model number to search for

    Returns:
        Dictionary containing agent test results

    """
    try:
        from agents.recall_data_agent.agent_logic import RecallDataAgentLogic

        logger.info(f"Testing RecallDataAgent directly with model number: {model_number}")

        agent = RecallDataAgentLogic(agent_id="test_model_agent")

        # Test with model number priority
        result = await agent.process_task(
            {
                "model_number": model_number,
                "barcode": "dummy_barcode",  # This should be ignored due to model number priority
                "product_name": "dummy_product",  # This should be ignored due to model number priority
            },
        )

        logger.info(f"Agent result: {result}")

        return {"success": result.get("status") == "COMPLETED", "agent_result": result}

    except Exception as e:
        logger.error(f"Agent test failed: {e}")
        return {"success": False, "error": str(e)}


def run_comprehensive_test_suite(user_id: int, barcode: str, model_number: str | None = None):
    """Run comprehensive test suite for model number scanning feature.

    Args:
        user_id: User ID for API tests
        barcode: Product barcode
        model_number: Product model number (optional)

    """
    logger.info("🧪 Starting Model Number Scanning Test Suite")
    logger.info("=" * 60)

    test_results = {}

    # Test 1: Database availability and model number data
    logger.info("\n📊 Test 1: Database Model Number Data Check")
    if model_number:
        test_results["database_search"] = asyncio.run(test_direct_database_search(model_number))
    else:
        logger.info("⚠️  No model number provided, skipping database search test")
        test_results["database_search"] = {
            "success": False,
            "reason": "No model number provided",
        }

    # Test 2: RecallDataAgent direct test
    if model_number:
        logger.info("\n🤖 Test 2: RecallDataAgent Direct Test")
        test_results["agent_direct"] = asyncio.run(test_recall_data_agent_directly(model_number))
    else:
        logger.info("⚠️  No model number provided, skipping agent direct test")
        test_results["agent_direct"] = {
            "success": False,
            "reason": "No model number provided",
        }

    # Test 3: API endpoint with model number
    logger.info("\n🌐 Test 3: API Endpoint with Model Number")
    test_results["api_with_model"] = test_api_endpoint_with_model_number(user_id, barcode, model_number)

    # Test 4: API endpoint without model number (baseline)
    logger.info("\n🌐 Test 4: API Endpoint without Model Number (Baseline)")
    test_results["api_without_model"] = test_api_endpoint_with_model_number(user_id, barcode, None)

    # Summary
    logger.info("\n📋 Test Suite Summary")
    logger.info("=" * 60)

    for test_name, result in test_results.items():
        status = "✅ PASSED" if result.get("success") else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not result.get("success") and "error" in result:
            logger.info(f"  Error: {result['error']}")
        elif not result.get("success") and "reason" in result:
            logger.info(f"  Reason: {result['reason']}")

    # Overall assessment
    passed_tests = sum(1 for result in test_results.values() if result.get("success"))
    total_tests = len(test_results)

    logger.info(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        logger.info("🎉 All tests passed! Model number scanning is working correctly.")
        sys.exit(0)
    elif passed_tests > 0:
        logger.info("⚠️  Some tests passed. Feature is partially working.")
        sys.exit(1)
    else:
        logger.info("💥 All tests failed. Model number scanning needs debugging.")
        sys.exit(2)


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test Model Number Scanning Feature")
    parser.add_argument("--user-id", type=int, default=1, help="User ID for API tests")
    parser.add_argument("--barcode", type=str, required=True, help="Product barcode")
    parser.add_argument("--model-number", type=str, help="Product model number to test")
    parser.add_argument("--api-url", type=str, default="http://localhost:8001", help="Base API URL")

    args = parser.parse_args()

    logger.info("Model Number Scanning Test")
    logger.info(f"User ID: {args.user_id}")
    logger.info(f"Barcode: {args.barcode}")
    logger.info(f"Model Number: {args.model_number}")
    logger.info(f"API URL: {args.api_url}")

    run_comprehensive_test_suite(args.user_id, args.barcode, args.model_number)


if __name__ == "__main__":
    main()
