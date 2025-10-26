#!/usr/bin/env python3
# scripts/test_background_alert.py
# Test Scenario 4: Emergency Recall Notification

import os
import sys
import logging
from unittest.mock import patch, AsyncMock, ANY

# ─── 0) Make sure project root is on sys.path ─────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ─── 1) Import the Celery task to test ─────────────────────────────────────────
from core_infra.tasks import check_for_new_recalls_and_alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    logger.info("--- Starting Test Scenario 4: Emergency Recall Notification ---")

    # --- Patch the async process_task methods that the task actually invokes ---
    push_path = "agents.engagement.push_notification_agent.agent_logic.PushNotificationAgentLogic.process_task"
    metrics_path = "agents.business.metrics_agent.agent_logic.MetricsAgentLogic.process_task"

    with (
        patch(push_path, new=AsyncMock(return_value={"status": "COMPLETED"})) as mock_push,
        patch(metrics_path, new=AsyncMock(return_value={"status": "COMPLETED"})) as mock_metrics,
    ):
        # Execute the Celery task synchronously
        logger.info("Executing the Celery task directly (agents are mocked)...")
        result = check_for_new_recalls_and_alert.apply()
        logger.info("Task execution finished.")

        # Print out summary
        print("\n" + "=" * 50)
        print("          SCENARIO 4 TEST RESULT")
        print("=" * 50)
        print(f"Task Status: {'SUCCESS' if result.successful() else 'FAILED'}")
        print(f"Task Return Value: {result.get()}")

        # Verify that our mocked process_task calls ran
        try:
            mock_push.assert_awaited_once()
            logger.info("Verified: PushNotificationAgentLogic.process_task was called once.")
            mock_metrics.assert_awaited_once()
            logger.info("Verified: MetricsAgentLogic.process_task was called once.")

            print("\n✅✅✅ TEST PASSED: The background task correctly invoked both agents.")

        except AssertionError as e:
            print("\n❌ TEST FAILED: An agent was not called as expected.")
            print(f"Details: {e}")

    print("\n--- Test Complete ---")


if __name__ == "__main__":
    main()
