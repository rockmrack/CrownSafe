# scripts/test_metrics_agent.py


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

from agents.business.metrics_agent.agent_logic import MetricsAgentLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
TEST_USER_ID = "user_test_123"
# --------------------------


async def main():
    """Main function to run the MetricsAgent test with a mocked Mixpanel API."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting MetricsAgent Test ---")

    try:
        # 1. Initialize the real MetricsAgentLogic.
        agent_logic = MetricsAgentLogic(agent_id="test_met_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Define the task payload.
        task_inputs = {
            "user_id": TEST_USER_ID,
            "event_name": "Product Scan Completed",
            "properties": {"product_name": "Mock Baby Formula", "risk_level": "High"},
        }
        logger.info(f"Created task: {task_inputs}")

        # 3. Mock the Mixpanel API call.
        # We use @patch to intercept the 'track' call.
        with patch.object(agent_logic.mixpanel_client, "track") as mock_mixpanel_call:
            # 4. Process the task.
            logger.info("Calling agent_logic.process_task (Mixpanel API is mocked)...")
            result = await agent_logic.process_task(task_inputs)
            logger.info("Task processing finished.")

            # 5. Verify the Mixpanel API was called correctly.
            mock_mixpanel_call.assert_called_once_with(
                distinct_id=TEST_USER_ID,
                event_name="Product Scan Completed",
                properties={"product_name": "Mock Baby Formula", "risk_level": "High"},
            )
            logger.info("Verified that the Mixpanel API was called with the correct parameters.")

        # 6. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 7. Validate the result.
        if result.get("status") == "COMPLETED":
            message = result.get("result", {}).get("message")
            if "Event tracked successfully" in message:
                print("\n" + "=" * 50)
                print("✅✅✅ TEST PASSED: Successfully simulated tracking a Mixpanel event.")
            else:
                print("\n" + "=" * 50)
                print("❌ TEST FAILED: The result message was not as expected.")
        else:
            print("\n" + "=" * 50)
            print(f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}")

    except ValueError as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: A configuration error occurred. {e}")
        print("Please ensure you have added your MIXPANEL_PROJECT_TOKEN to the .env file.")
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
