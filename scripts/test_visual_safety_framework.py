#!/usr/bin/env python3
"""
Test script for the Visual Safety Framework implementation
Tests both Phase 1 (liability mitigation) and Phase 2 (visual suggestions)
"""

import asyncio
import json
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_phase1_liability_mitigation():
    """Test Phase 1: INCONCLUSIVE status for unidentified products"""
    logger.info("=" * 60)
    logger.info("TESTING PHASE 1: LIABILITY MITIGATION")
    logger.info("=" * 60)

    try:
        from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic

        # Create commander instance
        commander = BabyShieldCommanderLogic(agent_id="test_commander")

        # Test with a product that won't be found (should return INCONCLUSIVE)
        test_request = {
            "barcode": "9999999999999",  # Non-existent barcode
            "model_number": None,
            "image_url": None,
        }

        logger.info(f"Testing with non-existent product: {test_request}")

        # Mock the router to return a completed but empty result
        class MockRouter:
            async def execute_plan(self, plan):
                return {
                    "status": "COMPLETED",
                    "final_result": {},
                }  # Empty result (no risk_level)

        # Replace router with mock
        commander.router = MockRouter()

        result = await commander.start_safety_check_workflow(test_request)

        # Verify INCONCLUSIVE status
        assert result["status"] == "INCONCLUSIVE", f"Expected INCONCLUSIVE status, got {result['status']}"
        assert result["data"]["risk_level"] == "Unknown", (
            f"Expected Unknown risk level, got {result['data'].get('risk_level')}"
        )
        assert "not mean the product is safe" in result["data"]["note"], "Missing safety disclaimer"

        logger.info("✅ Phase 1 Test PASSED: INCONCLUSIVE status returned correctly")
        logger.info(f"Result: {json.dumps(result, indent=2)}")

    except Exception as e:
        logger.error(f"❌ Phase 1 Test FAILED: {e}", exc_info=True)
        return False

    return True


async def test_phase2_visual_suggestions():
    """Test Phase 2: Visual product suggestions (mock mode)"""
    logger.info("=" * 60)
    logger.info("TESTING PHASE 2: VISUAL PRODUCT SUGGESTIONS")
    logger.info("=" * 60)

    try:
        from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic

        # Create visual search agent instance
        visual_agent = VisualSearchAgentLogic(agent_id="test_visual")

        # Mock the OpenAI client response
        class MockMessage:
            content = json.dumps(
                [
                    {
                        "product_name": "Baby Monitor Pro 2000",
                        "brand": "SafeGuard",
                        "model_number": "SG-2000",
                        "confidence": 0.85,
                    },
                    {
                        "product_name": "Baby Monitor Plus",
                        "brand": "SafeGuard",
                        "model_number": "SG-1500",
                        "confidence": 0.65,
                    },
                    {
                        "product_name": "Smart Baby Monitor",
                        "brand": "TechBaby",
                        "model_number": "TB-3000",
                        "confidence": 0.45,
                    },
                ]
            )

        class MockChoice:
            message = MockMessage()

        class MockResponse:
            choices = [MockChoice()]

        class MockOpenAI:
            class Chat:
                class Completions:
                    async def create(self, **kwargs):
                        return MockResponse()

                completions = Completions()

            chat = Chat()

        # Replace OpenAI client with mock
        visual_agent.llm_client = MockOpenAI()

        # Test with a mock image URL
        test_image_url = "https://example.com/baby-monitor.jpg"
        logger.info(f"Testing with image URL: {test_image_url}")

        result = await visual_agent.process_task({"image_url": test_image_url})

        # Verify successful completion
        assert result["status"] == "COMPLETED", f"Expected COMPLETED status, got {result['status']}"
        assert "suggestions" in result["result"], "Missing suggestions in result"

        suggestions = result["result"]["suggestions"]
        assert len(suggestions) == 3, f"Expected 3 suggestions, got {len(suggestions)}"
        assert suggestions[0]["confidence"] == 0.85, "First suggestion should have highest confidence"

        logger.info("✅ Phase 2 Test PASSED: Visual suggestions returned correctly")
        logger.info(f"Suggestions: {json.dumps(suggestions, indent=2)}")

    except Exception as e:
        logger.error(f"❌ Phase 2 Test FAILED: {e}", exc_info=True)
        return False

    return True


async def test_api_endpoint_integration():
    """Test the API endpoint integration (requires running server)"""
    logger.info("=" * 60)
    logger.info("TESTING API ENDPOINT INTEGRATION")
    logger.info("=" * 60)

    try:
        import httpx

        # Note: This test requires the API server to be running
        base_url = "http://localhost:8000"

        # Test the visual suggestion endpoint
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/visual/suggest-product",
                json={"image_url": "https://example.com/test-product.jpg"},
                timeout=10.0,
            )

            if response.status_code == 503:
                logger.warning("⚠️ Visual search service not ready (expected if OpenAI key not configured)")
            elif response.status_code == 200:
                data = response.json()
                assert data.get("success"), "Expected success=true in response"
                logger.info("✅ API Endpoint Test PASSED")
                logger.info(f"Response: {json.dumps(data, indent=2)}")
            else:
                logger.error(f"❌ Unexpected status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

    except httpx.ConnectError:
        logger.warning("⚠️ API server not running - skipping endpoint test")
    except Exception as e:
        logger.error(f"❌ API Endpoint Test FAILED: {e}", exc_info=True)
        return False

    return True


async def main():
    """Run all tests"""
    logger.info("Starting Visual Safety Framework Tests")
    logger.info("=" * 60)

    results = []

    # Run Phase 1 test
    results.append(("Phase 1: Liability Mitigation", await test_phase1_liability_mitigation()))

    # Run Phase 2 test
    results.append(("Phase 2: Visual Suggestions", await test_phase2_visual_suggestions()))

    # Run API endpoint test (optional - requires running server)
    # results.append(("API Endpoint Integration", await test_api_endpoint_integration()))

    # Summary
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        logger.info("\n🎉 All tests PASSED! Visual Safety Framework is ready.")
    else:
        logger.error("\n⚠️ Some tests FAILED. Please review the errors above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
