# scripts/test_onboarding_agent.py

import asyncio
import json
import logging
import os
import sys

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.engagement.onboarding_agent.agent_logic import OnboardingAgentLogic  # noqa: E402
from core_infra.database import (  # noqa: E402
    SessionLocal,
    User,
    create_tables,
    drop_tables,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
TEST_USER_ID = 1
# --------------------------


async def main() -> None:
    """Main function to run the OnboardingAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting OnboardingAgent Test ---")

    # 1. Set up a clean database and create a new user.
    drop_tables()
    create_tables()
    with SessionLocal() as db:
        # Create a new user with default values (is_pregnant=False)
        test_user = User(id=TEST_USER_ID, email="new.user@example.com", is_subscribed=True)
        db.add(test_user)
        db.commit()
    logger.info(f"Database seeded with new user ID: {TEST_USER_ID} (is_pregnant=False)")

    try:
        # 2. Initialize the real OnboardingAgentLogic.
        agent_logic = OnboardingAgentLogic(agent_id="test_onboard_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 3. Define the task payload to set the user as pregnant.
        task_inputs = {"user_id": TEST_USER_ID, "is_pregnant": True}
        logger.info(f"Created task with inputs: {task_inputs}")

        # 4. Process the task.
        logger.info("Calling agent_logic.process_task...")
        result = await agent_logic.process_task(task_inputs)
        logger.info("Task processing finished.")

        # 5. Analyze and print the result.
        print("\n" + "=" * 50)
        print("          AGENT TEST RESULT")
        print("=" * 50)
        print(json.dumps(result, indent=2))

        # 6. Verify the database was updated correctly.
        db_was_updated = False
        with SessionLocal() as db:
            updated_user = db.query(User).filter(User.id == TEST_USER_ID).first()
            if updated_user and updated_user.is_pregnant is True:
                db_was_updated = True
                logger.info("Verification successful: User's is_pregnant status is now True in the database.")

        # 7. Validate the final result.
        if result.get("status") == "COMPLETED" and db_was_updated:
            print("\n" + "=" * 50)
            print("✅✅✅ TEST PASSED: Agent successfully updated the user's profile in the database.")
        else:
            print("\n" + "=" * 50)
            if not db_was_updated:
                print(
                    "❌ TEST FAILED: The agent did not correctly update the user's is_pregnant status in the database.",
                )
            else:
                print(f"❌ TEST FAILED: The agent returned a FAILED status. Error: {result.get('error')}")

    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ TEST FAILED: An unexpected error occurred: {e}")

    finally:
        # 8. Clean up the test database.
        drop_tables()
        logger.info("Database tables dropped.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
