# scripts/test_data_governance_agent.py

import asyncio
import json
import logging
import os
import sys

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.governance.datagovernance_agent.agent_logic import DataGovernanceAgentLogic
from core_infra.database import (
    SessionLocal,
    User,
    create_tables,
    drop_tables,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
TEST_USER_ID_TO_DELETE = 99
# --------------------------


async def main():
    """Main function to run the DataGovernanceAgent test."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting DataGovernanceAgent Test ---")

    # 1. Set up a clean database and create a user to be deleted.
    drop_tables()
    create_tables()
    with SessionLocal() as db:
        user_to_delete = User(id=TEST_USER_ID_TO_DELETE, email="delete.me@example.com", is_subscribed=True)
        db.add(user_to_delete)
        db.commit()
    logger.info(f"Database seeded with user to be deleted, ID: {TEST_USER_ID_TO_DELETE}")

    try:
        # 2. Initialize the real DataGovernanceAgentLogic.
        agent_logic = DataGovernanceAgentLogic(agent_id="test_dg_001", logger_instance=logger)
        logger.info("Agent logic initialized.")

        # 3. Define the task payload.
        task_inputs = {
            "action": "delete_user_data",
            "payload": {"user_id": TEST_USER_ID_TO_DELETE},
        }
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

        # 6. Verify the user was deleted from the database.
        user_was_deleted = False
        with SessionLocal() as db:
            deleted_user = db.query(User).filter(User.id == TEST_USER_ID_TO_DELETE).first()
            if deleted_user is None:
                user_was_deleted = True
                logger.info("Verification successful: User is no longer in the database.")

        # 7. Validate the final result.
        if result.get("status") == "COMPLETED" and user_was_deleted:
            print("\n" + "=" * 50)
            print("✅✅✅ TEST PASSED: Agent successfully deleted the user's data from the database.")
        else:
            print("\n" + "=" * 50)
            if not user_was_deleted:
                print("❌ TEST FAILED: The agent did not correctly delete the user from the database.")
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
