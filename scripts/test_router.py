# scripts/test_router.py

import asyncio
import json
import logging
import os
import sys
from unittest.mock import AsyncMock

# --- FIX: Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# ----------------------------------------------

from agents.routing.router_agent.agent_logic import BabyShieldRouterLogic


# --- Mock Agent Logic ---
# We create a fake version of the RecallDataAgentLogic.
# This is necessary because we don't have its real logic yet.
class MockRecallDataAgentLogic:
    def __init__(self, *args, **kwargs):
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"recalls_found": 1, "summary": "Found one recall."},
            }
        )


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def convert_sets_to_lists(obj):
    """
    Recursively convert all sets in a dict or list to lists for JSON serialization.
    """
    if isinstance(obj, dict):
        return {k: convert_sets_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, list):
        return [convert_sets_to_lists(i) for i in obj]
    else:
        return obj


async def main():
    """Main function to run the simplified Router test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Simplified Router Test ---")

    # 1. --- Create a simplified, one-step plan manually ---
    simplified_plan = {
        "plan_id": "test_plan_123",
        "steps": [
            {
                "step_id": "step1_check_recalls",
                "task_description": "Check for recalls.",
                "agent_capability_required": "query_recalls_by_product",
                "inputs": {"product_name": "Test Product", "upc": "123"},
                "dependencies": [],
            }
        ],
    }
    logger.info("Step 1: Created a simplified one-step plan.")
    print(json.dumps(simplified_plan, indent=2))

    # 2. --- Initialize Router and MOCK the RecallDataAgent ---
    router = BabyShieldRouterLogic(agent_id="test_router_001", logger_instance=logger)

    # IMPORTANT: Replace the real agent logic with our mock.
    if "query_recalls_by_product" in router.agent_registry:
        router.agent_registry["query_recalls_by_product"] = MockRecallDataAgentLogic()
        logger.info("Step 2: Router initialized and RecallDataAgent has been mocked.")
    else:
        logger.error("Router could not register the RecallDataAgent. Check import paths.")
        return

    # 3. --- Execute the simplified plan ---
    logger.info("Step 3: Calling router.execute_plan...")
    router_result = await router.execute_plan(simplified_plan)
    logger.info("Router execution finished.")

    # 4. --- Analyze the final result ---
    print("\n" + "=" * 50)
    print("          ROUTER AGENT TEST RESULT")
    print("=" * 50)
    print(json.dumps(convert_sets_to_lists(router_result), indent=2))  # <-- Fix applied here

    if router_result.get("status") == "COMPLETED":
        final_result = router_result.get("final_result", {})
        if final_result.get("recalls_found") == 1:
            print("\n" + "=" * 50)
            print("✅ TEST PASSED: The router successfully executed the one-step plan.")
        else:
            print("\n" + "=" * 50)
            print("❌ TEST FAILED: The final result was not as expected.")
    else:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: The router did not complete the plan. Status: {router_result.get('status')}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
