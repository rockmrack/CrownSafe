# scripts/test_push_notification_agent.py

import sys
import os
import asyncio
import logging
import json
from unittest.mock import patch

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.engagement.push_notification_agent.agent_logic import PushNotificationAgentLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Test Configuration ---
TEST_DEVICE_TOKEN = "fake_device_token_for_testing_12345"
# --------------------------


async def main():
    """Main function to run the PushNotificationAgent test with mocked Firebase Admin SDK."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting PushNotificationAgent Test ---")

    try:
        # 1. Initialize the real PushNotificationAgentLogic.
        agent_logic = PushNotificationAgentLogic(agent_id="test_pn_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Define the task payload.
        task_inputs = {
            "device_token": TEST_DEVICE_TOKEN,
            "title": "Product Safety Alert",
            "body": "A product you scanned has been recalled.",
            "data": {"mock_recall_id": "1234"},
        }
        logger.info(f"Created task: {task_inputs}")

        # 3. Mock the Firebase Admin SDK send method.
        with patch(
            "firebase_admin.messaging.send", return_value="mock_message_id_123"
        ) as mock_send:
            # 4. Process the task.
            logger.info("Calling agent_logic.process_task (Firebase Admin SDK is mocked)...")
            result = await agent_logic.process_task(task_inputs)
            logger.info("Task processing finished.")

            # 5. Verify the messaging.send call was made.
            mock_send.assert_called_once()
            logger.info("Verified that messaging.send was called once.")

        # 6. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 7. Validate the result.
        if (
            result.get("status") == "COMPLETED"
            and result.get("message_id") == "mock_message_id_123"
        ):
            print("\n" + "=" * 50)
            print("✅✅✅ TEST PASSED: Successfully simulated sending a push notification.")
        else:
            print("\n" + "=" * 50)
            print(f"❌ TEST FAILED: Unexpected result. Result: {result}")

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
