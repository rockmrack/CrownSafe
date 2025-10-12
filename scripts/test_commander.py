# scripts/test_commander.py
# Version: 7.3 - Golden Master (Live End-to-End Validation for Baby Product)

import sys
import os
import asyncio
import logging
import json
from datetime import date

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic
from core_infra.database import Base, engine, SessionLocal, RecallDB

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Test Configuration ---
# Use a baby product UPC that the trial endpoint recognizes
# Johnson's Baby Shampoo 15oz: UPC 381370037248
TEST_BARCODE = "381370037248"
# --------------------------


async def main():
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Golden Master (Live End-to-End) Test for Baby Product ---")

    # 1. Set up in-memory test database and seed with matching recall
    logger.info("Setting up in-memory test database...")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Seed a recall entry matching the product name returned by the identify agent
        test_recall = RecallDB(
            recall_id="LIVE-TEST-001",
            source_agency="TEST_DB",
            recall_date=date(2025, 7, 22),
            description="Integration test recall for Johnson's Baby Shampoo 15oz.",
            hazard="Integration test hazard",
            remedy="Integration test remedy",
            product_name="Johnson and Johnson Baby Shampoo, 15 Ounce",
            url="http://example.com/recall",
        )
        db.add(test_recall)
        db.commit()
    logger.info("Database seeded with one recall record for baby shampoo.")

    try:
        # 2. Initialize the live Commander (with real sub-agents)
        commander = BabyShieldCommanderLogic(agent_id="golden_master_commander", logger_instance=logger)
        logger.info("Commander initialized with live sub-agents.")

        # 3. Create the user request with our baby product barcode
        user_request = {"barcode": TEST_BARCODE, "image_url": None}
        logger.info(f"User request: {user_request}")

        # 4. Execute the end-to-end safety check workflow
        logger.info("Calling commander.start_safety_check_workflow...")
        final_result = await commander.start_safety_check_workflow(user_request)
        logger.info("Commander workflow completed.")

        # 5. Print and validate the golden master output
        print("\n" + "=" * 60)
        print("          GOLDEN MASTER TEST RESULT")
        print("=" * 60)
        print(json.dumps(final_result, indent=2))

        status = final_result.get("status")
        if status == "COMPLETED":
            risk_level = final_result.get("data", {}).get("risk_level")
            if risk_level and risk_level != "None":
                print("\n" + "=" * 60)
                print("✅✅✅ GOLDEN MASTER TEST PASSED: Live end-to-end baby product workflow succeeded.")
            else:
                print("\n" + "=" * 60)
                print(f"❌ TEST FAILED: Workflow completed but risk_level was '{risk_level}'.")
        else:
            print("\n" + "=" * 60)
            print(f"❌ TEST FAILED: Workflow failed with status '{status}'.")
            print(f"Error: {final_result.get('error')}")

    finally:
        # 6. Clean up the test database
        logger.info("Tearing down in-memory test database...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
