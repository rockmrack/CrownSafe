# scripts/test_hazard_analysis.py

import sys
import os
import asyncio
import logging
import json

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.hazard_analysis_agent.agent_logic import HazardAnalysisLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
# We will use sample recall data for a fictional baby product.
TEST_RECALL_DATA = {
    "product_details": {"product_name": "Happy Munchkin Organic Puffs"},
    "recall_data": {
        "recalls": [
            {"reason": "Contains undeclared traces of peanuts.", "date": "2025-07-15"},
            {
                "reason": "Small plastic parts found in some batches, posing a choking hazard.",
                "date": "2025-06-01",
            },
        ]
    },
}
# --------------------------


async def main():
    """Main function to run the live HazardAnalysisAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Live HazardAnalysisAgent Test ---")

    try:
        # 1. Initialize the real HazardAnalysisLogic.
        # It will load the API key from your .env file.
        agent_logic = HazardAnalysisLogic(agent_id="test_ha_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Process the task with our sample data.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(TEST_RECALL_DATA)
        logger.info("Task processing finished.")

        # 3. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 4. Validate the result.
        if result.get("status") == "COMPLETED":
            analysis = result.get("result", {})
            if "summary" in analysis and "risk_level" in analysis:
                print("\n" + "=" * 50)
                print("✅✅✅ TEST PASSED: Successfully received a valid analysis from the LLM.")
                print(f"Risk Level: {analysis['risk_level']}")
                print(f"Summary: {analysis['summary']}")
            else:
                print("\n" + "=" * 50)
                print("❌ TEST FAILED: The LLM response was missing required keys ('summary', 'risk_level').")
        else:
            print("\n" + "=" * 50)
            print(f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}")

    except ValueError as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: A configuration error occurred. {e}")
        print("Please ensure you have added your OPENAI_API_KEY to the .env file.")
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
