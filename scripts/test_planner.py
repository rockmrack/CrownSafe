# test_planner.py

import asyncio
import json
import logging
import os
import sys

# --- FIX: Add project root to Python's path ---
# This allows the script to find the 'agents' module.
# It gets the current file's path, goes up one directory (to 'scripts'), then up one more (to the project root).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# ---------------------------------------------

from agents.planning.planner_agent.agent_logic import BabyShieldPlannerLogic  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main():
    """Main function to run the test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting BabyShield Planner Agent Test (v3.1) ---")

    # 1. Initialize the Planner Agent Logic
    planner = BabyShieldPlannerLogic(agent_id="test_planner_001", logger_instance=logger)
    logger.info("Planner initialized.")

    # 2. Define a sample task payload that matches your template's needs
    sample_task = {
        "goal": "Check the safety of a baby product with a barcode.",
        "barcode": "0123456789123",
        "image_url": None,  # Simulating a barcode-only scan
    }
    logger.info(f"Created sample task: {sample_task}")

    # 3. Process the task to generate a plan
    logger.info("Calling planner.process_task...")
    result = planner.process_task(sample_task)
    logger.info("Planner task processing finished.")

    # 4. Analyze and print the result
    print("\n" + "=" * 50)
    print("          PLANNER AGENT TEST RESULT")
    print("=" * 50)

    if result.get("status") == "COMPLETED":
        print("✅ Status: COMPLETED")
        plan = result.get("plan", {})
        print(f"   Plan ID: {plan.get('plan_id')}")
        print(f"   Workflow Goal: {plan.get('workflow_goal')}")

        print("\n--- Generated Plan Steps ---")
        print(json.dumps(plan, indent=2))

        # Verification check
        step1_inputs = plan.get("steps", [{}])[0].get("inputs", {})
        if step1_inputs.get("barcode") == "0123456789123":
            print("\n" + "=" * 50)
            print("✅ TEST PASSED: The plan was generated successfully and the barcode was correctly substituted.")
        else:
            print("\n" + "=" * 50)
            print("❌ TEST FAILED: The barcode was not substituted correctly in the plan.")

    else:
        print("❌ Status: FAILED")
        print(f"   Error: {result.get('error')}")
        print("\n" + "=" * 50)
        print("❌ TEST FAILED: The planner could not generate a plan.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
