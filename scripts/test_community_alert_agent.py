# scripts/test_community_alert_agent.py

import sys
import os
import asyncio
import logging
import json

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.engagement.community_alert_agent.agent_logic import CommunityAlertAgentLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    """Main function to run the CommunityAlertAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting CommunityAlertAgent Test ---")

    # 1. Load the mock HTML file from our test fixtures.
    fixture_path = os.path.join(project_root, "tests", "fixtures", "mock_forum_page.html")
    try:
        with open(fixture_path, "r") as f:
            mock_html = f.read()
        logger.info("Successfully loaded mock HTML fixture.")
    except FileNotFoundError:
        logger.error(f"Mock HTML file not found at: {fixture_path}")
        return

    try:
        # 2. Initialize the real CommunityAlertAgentLogic.
        agent_logic = CommunityAlertAgentLogic(agent_id="test_ca_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 3. Define the task payload.
        task_inputs = {
            "html_content": mock_html,
            "product_name": "Happy Baby Super-Puffs",
        }
        logger.info(f"Created task with inputs.")

        # 4. Process the task.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(task_inputs)
        logger.info("Task processing finished.")

        # 5. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 6. Validate the result.
        if result.get("status") == "COMPLETED":
            risks_found = result.get("result", {}).get("risks", [])
            # We expect to find "rash", "choking", "hazard", and "safety issue"
            if len(risks_found) >= 4:
                print("\n" + "=" * 50)
                print(
                    f"✅✅✅ TEST PASSED: Agent successfully scraped the page and found {len(risks_found)} risk keywords."
                )
            else:
                print("\n" + "=" * 50)
                print(
                    f"❌ TEST FAILED: The agent only found {len(risks_found)} keywords, but expected at least 4."
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
