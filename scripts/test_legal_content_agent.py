# scripts/test_legal_content_agent.py

import sys
import os
import asyncio
import logging
import json

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.governance.legalcontent_agent.agent_logic import LegalContentAgentLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Test Configuration ---
# We will test by fetching one of the files you have in data/legal/
TEST_DOCUMENT_NAME = "tos_en_us_v1.2.txt"
# --------------------------


async def main():
    """Main function to run the LegalContentAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting LegalContentAgent Test ---")

    try:
        # 1. Initialize the real LegalContentAgentLogic.
        agent_logic = LegalContentAgentLogic(agent_id="test_lc_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 2. Define the task payload.
        task_inputs = {"document_name": TEST_DOCUMENT_NAME}
        logger.info(f"Created task to fetch document: {TEST_DOCUMENT_NAME}")

        # 3. Process the task.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(task_inputs)
        logger.info("Task processing finished.")

        # 4. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        # We print the first 200 characters of the content for brevity
        if result.get("status") == "COMPLETED":
            result_copy = result.copy()
            result_copy["result"]["content"] = result_copy["result"]["content"][:200] + "..."
            print(json.dumps(result_copy, indent=2))
        else:
            print(json.dumps(result, indent=2))

        # 5. Validate the result.
        if result.get("status") == "COMPLETED":
            content = result.get("result", {}).get("content", "")
            if len(content) > 50:  # Check that we got a reasonable amount of text
                print("\n" + "=" * 50)
                print(
                    f"✅✅✅ TEST PASSED: Successfully read the legal document '{TEST_DOCUMENT_NAME}'."
                )
            else:
                print("\n" + "=" * 50)
                print(
                    "❌ TEST FAILED: The agent returned empty or very short content for the document."
                )
        else:
            print("\n" + "=" * 50)
            print(
                f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}"
            )

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
