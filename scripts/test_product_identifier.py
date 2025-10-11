# scripts/test_product_identifier.py

import sys
import os
import asyncio
import logging
import json

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.product_identifier_agent.agent_logic import ProductIdentifierLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
# We will use a known barcode for a common baby product.
# This is the barcode for "Enfamil NeuroPro Gentlease Infant Formula".
TEST_BARCODE = " 888462079525"
EXPECTED_PRODUCT_NAME_FRAGMENT = "Apple Watch"
# --------------------------


async def main():
    """Main function to run the live ProductIdentifierAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Live ProductIdentifierAgent Test ---")

    try:
        # 1. Initialize the real ProductIdentifierLogic.
        # It will load the API key from your .env file.
        agent_logic = ProductIdentifierLogic(agent_id="test_pi_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Define the task payload.
        task_inputs = {"barcode": TEST_BARCODE}
        logger.info(f"Created task with test barcode: {TEST_BARCODE}")

        # 3. Process the task.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(task_inputs)
        logger.info("Task processing finished.")

        # 4. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 5. Validate the result.
        if result.get("status") == "COMPLETED":
            product_name = result.get("result", {}).get("product_name", "")
            if EXPECTED_PRODUCT_NAME_FRAGMENT.lower() in product_name.lower():
                print("\n" + "=" * 50)
                print(f"✅✅✅ TEST PASSED: Successfully identified '{product_name}' from barcode.")
            else:
                print("\n" + "=" * 50)
                print(
                    f"❌ TEST FAILED: The product name '{product_name}' did not contain the expected fragment '{EXPECTED_PRODUCT_NAME_FRAGMENT}'."
                )
        else:
            print("\n" + "=" * 50)
            print(f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}")

    except ValueError as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: A configuration error occurred. {e}")
        print("Please ensure you have added your UPCITEMDB_API_KEY to the .env file.")
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
