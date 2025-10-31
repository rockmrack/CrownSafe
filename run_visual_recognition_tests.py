"""COMPREHENSIVE VISUAL RECOGNITION SYSTEM TEST SUITE
Tests all aspects of the Visual Search Agent and image analysis
"""

import asyncio
import sys
from datetime import datetime


class MockAsyncOpenAI:
    """Mock OpenAI client for testing without API calls"""

    def __init__(self, api_key=None):
        self.chat = self

    @property
    def completions(self):
        return self

    async def create(self, **kwargs):
        """Mock create method that returns appropriate responses based on prompt"""

        class MockChoice:
            def __init__(self, content):
                self.message = MockMessage(content)

        class MockMessage:
            def __init__(self, content):
                self.content = content

        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        # Check if this is a suggestions call or identification call
        messages = kwargs.get("messages", [])
        if messages and messages[0].get("content"):
            content = str(messages[0]["content"])

            # Suggestions mode (Phase 2)
            if "top 3 most likely matches" in content:
                response_json = """{
                    "suggestions": [
                        {
                            "product_name": "Graco SnugRide 35",
                            "brand": "Graco",
                            "model_number": "2166389",
                            "confidence": 0.92
                        },
                        {
                            "product_name": "Graco SnugRide 35 LX",
                            "brand": "Graco",
                            "model_number": "2166391",
                            "confidence": 0.85
                        },
                        {
                            "product_name": "Graco SnugRide 35 Elite",
                            "brand": "Graco",
                            "model_number": "2166393",
                            "confidence": 0.78
                        }
                    ]
                }"""
                return MockResponse(response_json)

            # Identification mode (Phase 3)
            elif "single best guess" in content:
                response_json = """{
                    "product_name": "Graco SnugRide 35",
                    "brand": "Graco",
                    "model_number": "2166389",
                    "confidence": 0.92
                }"""
                return MockResponse(response_json)

        # Default response
        return MockResponse('{"product_name": "Unknown", "brand": "Unknown", "model_number": null, "confidence": 0.5}')


class MockHttpx:
    """Mock httpx module for testing image fetching"""

    class AsyncClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            """Mock GET request"""

            # Simulate successful image fetch
            class MockResponse:
                status_code = 200
                content = b"fake_image_data_for_testing_purposes_only"
                headers = {"content-type": "image/jpeg", "content-length": "42"}

            return MockResponse()


# Don't patch httpx - let the agent use real httpx or handle mock internally


def run_tests():
    """Execute all visual recognition tests"""
    print("=" * 70)
    print("VISUAL RECOGNITION SYSTEM COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    tests_passed = 0
    tests_failed = 0
    test_results = []

    # TEST 1: Import Visual Search Agent
    print("[TEST 1] Visual Search Agent Imports...")
    try:
        from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic

        print("PASS - VisualSearchAgentLogic imported successfully")
        tests_passed += 1
        test_results.append(("Visual Agent Imports", True))
    except Exception as e:
        print(f"FAIL - Import error: {e}")
        tests_failed += 1
        test_results.append(("Visual Agent Imports", False))
        return

    # TEST 2: Agent Initialization
    print("\n[TEST 2] Visual Search Agent Initialization...")
    try:
        # Patch OpenAI before initialization
        import agents.visual.visual_search_agent.agent_logic as agent_module

        _ = getattr(agent_module, "AsyncOpenAI", None)  # original_openai
        agent_module.AsyncOpenAI = MockAsyncOpenAI

        agent = VisualSearchAgentLogic(agent_id="test-visual-agent")
        assert agent.agent_id == "test-visual-agent"
        assert hasattr(agent, "llm_client")
        assert hasattr(agent, "logger")
        print("PASS - Agent initialized with correct attributes")
        tests_passed += 1
        test_results.append(("Agent Initialization", True))
    except Exception as e:
        print(f"FAIL - Initialization error: {e}")
        tests_failed += 1
        test_results.append(("Agent Initialization", False))

    # TEST 3: Image URL Validation (S3 URL Detection)
    print("\n[TEST 3] S3 URL Detection...")
    try:
        from agents.visual.visual_search_agent.agent_logic import _is_s3_url

        # Test S3 URLs
        assert _is_s3_url("s3://bucket/key")
        assert _is_s3_url("https://bucket.s3.amazonaws.com/key")
        assert not _is_s3_url("https://example.com/image.jpg")
        assert not _is_s3_url("http://regular-site.com")

        print("PASS - S3 URL detection working correctly")
        tests_passed += 1
        test_results.append(("S3 URL Detection", True))
    except Exception as e:
        print(f"FAIL - S3 URL detection error: {e}")
        tests_failed += 1
        test_results.append(("S3 URL Detection", False))

    # TEST 4: Suggest Products from Image (Phase 2)
    print("\n[TEST 4] Suggest Products from Image (Top 3 Matches)...")
    try:
        import os

        os.environ["OPENAI_API_KEY"] = "sk-test-key-for-testing"

        agent = VisualSearchAgentLogic(agent_id="test-suggestions")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.suggest_products_from_image("https://example.com/baby-product.jpg"))

        assert result.get("status") == "COMPLETED"
        assert "result" in result
        assert "suggestions" in result["result"]
        suggestions = result["result"]["suggestions"]
        assert len(suggestions) == 3
        assert suggestions[0]["product_name"] == "Graco SnugRide 35"
        assert suggestions[0]["brand"] == "Graco"
        assert suggestions[0]["confidence"] == 0.92

        print(f"PASS - Returned {len(suggestions)} suggestions")
        print(
            f"  Top match: {suggestions[0]['brand']} {suggestions[0]['product_name']} (confidence: {suggestions[0]['confidence']})",  # noqa: E501
        )
        tests_passed += 1
        test_results.append(("Suggest Products", True))
    except Exception as e:
        print(f"FAIL - Suggestions error: {e}")
        tests_failed += 1
        test_results.append(("Suggest Products", False))

    # TEST 5: Identify Product from Image (Phase 3)
    print("\n[TEST 5] Identify Product from Image (Single Best Match)...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-identification")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.identify_product_from_image("https://example.com/baby-product.jpg"))

        assert result.get("status") == "COMPLETED"
        assert "result" in result
        best_match = result["result"]
        assert "product_name" in best_match
        assert "brand" in best_match
        assert "model_number" in best_match
        assert "confidence" in best_match
        assert best_match["product_name"] == "Graco SnugRide 35"
        assert best_match["brand"] == "Graco"
        assert isinstance(best_match["confidence"], float)

        print(f"PASS - Identified: {best_match['brand']} {best_match['product_name']}")
        print(f"  Model: {best_match['model_number']}")
        print(f"  Confidence: {best_match['confidence']}")
        tests_passed += 1
        test_results.append(("Identify Product", True))
    except Exception as e:
        print(f"FAIL - Identification error: {e}")
        tests_failed += 1
        test_results.append(("Identify Product", False))

    # TEST 6: Process Task (Generic Entry Point)
    print("\n[TEST 6] Process Task Entry Point...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-process-task")
        agent.llm_client = MockAsyncOpenAI()

        # Test with identify mode
        result = asyncio.run(agent.process_task({"image_url": "https://example.com/product.jpg", "mode": "identify"}))

        assert result.get("status") == "COMPLETED"
        assert "result" in result

        print("PASS - Process task with identify mode working")
        tests_passed += 1
        test_results.append(("Process Task", True))
    except Exception as e:
        print(f"FAIL - Process task error: {e}")
        tests_failed += 1
        test_results.append(("Process Task", False))

    # TEST 7: Missing Image URL Error Handling
    print("\n[TEST 7] Error Handling - Missing Image URL...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-error-handling")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.process_task({}))

        assert result.get("status") == "FAILED"
        assert "error" in result
        assert "image_url is required" in result["error"]

        print("PASS - Missing image URL error handled correctly")
        tests_passed += 1
        test_results.append(("Missing Image URL", True))
    except Exception as e:
        print(f"FAIL - Error handling test failed: {e}")
        tests_failed += 1
        test_results.append(("Missing Image URL", False))

    # TEST 8: No API Key Handling
    print("\n[TEST 8] Error Handling - No API Key...")
    try:
        os.environ["OPENAI_API_KEY"] = "sk-mock-invalid"

        agent = VisualSearchAgentLogic(agent_id="test-no-api-key")
        # Agent should have None llm_client when API key is mock

        result = asyncio.run(agent.suggest_products_from_image("https://example.com/product.jpg"))

        assert result.get("status") == "FAILED"
        assert "error" in result
        assert "api_key" in result["error"].lower() or "unavailable" in result["error"].lower()

        print("PASS - No API key error handled correctly")
        tests_passed += 1
        test_results.append(("No API Key", True))
    except Exception as e:
        print(f"FAIL - No API key test failed: {e}")
        tests_failed += 1
        test_results.append(("No API Key", False))

    # TEST 9: Response Field Validation
    print("\n[TEST 9] Response Field Validation...")
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test-key"
        agent = VisualSearchAgentLogic(agent_id="test-validation")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.identify_product_from_image("https://example.com/product.jpg"))

        assert result.get("status") == "COMPLETED"
        best_match = result["result"]

        # Check all required fields exist
        required_fields = ["product_name", "brand", "model_number", "confidence"]
        for field in required_fields:
            assert field in best_match, f"Missing required field: {field}"

        # Check confidence is a float
        assert isinstance(best_match["confidence"], float)
        assert 0.0 <= best_match["confidence"] <= 1.0

        print("PASS - All required response fields present and valid")
        print(f"  Fields validated: {', '.join(required_fields)}")
        tests_passed += 1
        test_results.append(("Response Validation", True))
    except Exception as e:
        print(f"FAIL - Response validation error: {e}")
        tests_failed += 1
        test_results.append(("Response Validation", False))

    # TEST 10: Confidence Score Range
    print("\n[TEST 10] Confidence Score Range Validation...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-confidence")
        agent.llm_client = MockAsyncOpenAI()

        # Test identification
        result = asyncio.run(agent.identify_product_from_image("https://example.com/product.jpg"))

        confidence = result["result"]["confidence"]
        assert isinstance(confidence, (int, float))
        assert 0.0 <= confidence <= 1.0

        # Test suggestions
        result = asyncio.run(agent.suggest_products_from_image("https://example.com/product.jpg"))

        for suggestion in result["result"]["suggestions"]:
            conf = suggestion["confidence"]
            assert isinstance(conf, (int, float))
            assert 0.0 <= conf <= 1.0

        print("PASS - Confidence scores in valid range (0.0-1.0)")
        tests_passed += 1
        test_results.append(("Confidence Range", True))
    except Exception as e:
        print(f"FAIL - Confidence validation error: {e}")
        tests_failed += 1
        test_results.append(("Confidence Range", False))

    # TEST 11: Multiple Suggestions Ordering
    print("\n[TEST 11] Multiple Suggestions Confidence Ordering...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-ordering")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.suggest_products_from_image("https://example.com/product.jpg"))

        suggestions = result["result"]["suggestions"]
        assert len(suggestions) >= 2

        # Check confidence scores are in descending order
        confidences = [s["confidence"] for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)

        print("PASS - Suggestions ordered by confidence (highest first)")
        print(f"  Confidence scores: {confidences}")
        tests_passed += 1
        test_results.append(("Suggestions Ordering", True))
    except Exception as e:
        print(f"FAIL - Ordering validation error: {e}")
        tests_failed += 1
        test_results.append(("Suggestions Ordering", False))

    # TEST 12: Image Fetch Function Import
    print("\n[TEST 12] Image Fetch Function Availability...")
    try:
        from agents.visual.visual_search_agent.agent_logic import (
            _fetch_image_bytes,
            _is_s3_url,
        )

        # Verify functions are available
        assert callable(_fetch_image_bytes)
        assert callable(_is_s3_url)

        print("PASS - Image fetch functions available")
        tests_passed += 1
        test_results.append(("Image Fetch Functions", True))
    except Exception as e:
        print(f"FAIL - Image fetch function error: {e}")
        tests_failed += 1
        test_results.append(("Image Fetch Functions", False))

    # TEST 13: Product Name Extraction
    print("\n[TEST 13] Product Name Extraction...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-extraction")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.identify_product_from_image("https://example.com/product.jpg"))

        product_name = result["result"]["product_name"]
        assert isinstance(product_name, str)
        assert len(product_name) > 0
        assert product_name != ""

        print(f"PASS - Product name extracted: '{product_name}'")
        tests_passed += 1
        test_results.append(("Product Name Extraction", True))
    except Exception as e:
        print(f"FAIL - Product name extraction error: {e}")
        tests_failed += 1
        test_results.append(("Product Name Extraction", False))

    # TEST 14: Brand Extraction
    print("\n[TEST 14] Brand Extraction...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-brand")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.identify_product_from_image("https://example.com/product.jpg"))

        brand = result["result"]["brand"]
        assert isinstance(brand, str)
        assert len(brand) > 0

        print(f"PASS - Brand extracted: '{brand}'")
        tests_passed += 1
        test_results.append(("Brand Extraction", True))
    except Exception as e:
        print(f"FAIL - Brand extraction error: {e}")
        tests_failed += 1
        test_results.append(("Brand Extraction", False))

    # TEST 15: Model Number Handling
    print("\n[TEST 15] Model Number Handling...")
    try:
        agent = VisualSearchAgentLogic(agent_id="test-model")
        agent.llm_client = MockAsyncOpenAI()

        result = asyncio.run(agent.identify_product_from_image("https://example.com/product.jpg"))

        model_number = result["result"]["model_number"]
        # Model number can be None if not visible, or a string if detected
        assert model_number is None or isinstance(model_number, str)

        print(f"PASS - Model number handled: '{model_number}'")
        tests_passed += 1
        test_results.append(("Model Number Handling", True))
    except Exception as e:
        print(f"FAIL - Model number handling error: {e}")
        tests_failed += 1
        test_results.append(("Model Number Handling", False))

    # Print Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    total_tests = tests_passed + tests_failed
    success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Success Rate: {success_rate:.1f}%")

    print("\nDetailed Results:")
    for test_name, passed in test_results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {test_name}")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if tests_failed == 0:
        print("\n" + "=" * 70)
        print("ALL VISUAL RECOGNITION TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("\n" + "=" * 70)
        print(f"SOME TESTS FAILED ({tests_failed}/{total_tests})")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
