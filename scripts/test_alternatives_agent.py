# scripts/test_alternatives_agent.py

import sys
import os
import asyncio
import logging
import json

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.value_add.alternatives_agent.agent_logic import AlternativesAgentLogic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    """Main function to run the AlternativesAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting AlternativesAgent Test ---")

    try:
        # 1. Initialize the real AlternativesAgentLogic.
        agent_logic = AlternativesAgentLogic(agent_id="test_alt_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Define the task payload for a known category.
        task_inputs = {"product_category": "Infant Formula"}
        logger.info(f"Created task with inputs: {task_inputs}")

        # 3. Process the task.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(task_inputs)
        logger.info("Task processing finished.")

        # 4. Analyze and print the result.
        print("\n" + "="*50)
        print("          AGENT TEST RESULT")
        print("="*50)
        print(json.dumps(result, indent=2))

        # 5. Validate the result.
        if result.get("status") == "COMPLETED":
            alternatives_found = result.get("result", {}).get("alternatives_found", 0)
            if alternatives_found > 0:
                print("\n" + "="*50)
                print(f"✅✅✅ TEST PASSED: Successfully found {alternatives_found} alternatives.")
            else:
                print("\n" + "="*50)
                print(f"❌ TEST FAILED: The agent did not find any alternatives for a known category.")
        else:
            print("\n" + "="*50)
            print(f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}")

    except Exception as e:
        print("\n" + "="*50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())