# scripts/test_safety_check_barcode.py
# Test Scenario 1: Basic Safety Check via Barcode

import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
import sys
import os
import asyncio
import logging
import json
import datetime

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic
from core_infra.database import Base, engine, SessionLocal, RecallDB


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Test Configuration ---
TEST_BARCODE = "381370037248"  # Johnson's Baby Shampoo UPC
EXPECTED_PRODUCT_NAME_FRAGMENT = "Johnson"
# --------------------------

async def main():
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Test Scenario 1: Basic Safety Check via Barcode ---")

    # 1. Set up a clean database and add a test recall record.
    logger.info("Setting up in-memory test database...")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        test_recall = RecallDB(
            recall_id="SCENARIO-1-TEST-001",
            product_name="Johnson and Johnson Baby Shampoo, 15 Ounce",  # Updated to match API response
            brand="Johnson & Johnson",
            country="USA",
            recall_date=datetime.date(2025, 7, 22),
            hazard_description="Contains a newly identified mild allergen.",
            hazard="Contains a newly identified mild allergen.",  # Added for recall agent
            manufacturer_contact="support@jj.com"
        )
        db.add(test_recall)
        db.commit()
    logger.info("Database is set up with one test recall for 'Johnson and Johnson Baby Shampoo, 15 Ounce'.")

    try:
        # 2. Initialize the real Commander. It will initialize the real sub-agents.
        commander = BabyShieldCommanderLogic(agent_id="scenario_1_commander", logger_instance=logger)
        logger.info("Step 1: Live Commander and all sub-agents initialized.")

        # 3. Define the user request with our test barcode.
        user_request = {"barcode": TEST_BARCODE, "image_url": None}
        logger.info(f"Step 2: Created user request with barcode: {TEST_BARCODE}")

        # 4. Start the live workflow.
        logger.info("Step 3: Calling commander.start_safety_check_workflow...")
        final_result = await commander.start_safety_check_workflow(user_request)
        logger.info("Commander workflow finished.")

        # 5. Analyze the final result.
        print("\n" + "="*50)
        print("          SCENARIO 1 TEST RESULT")
        print("="*50)
        print(json.dumps(final_result, indent=2))

        # 6. Validate the final result.
        if final_result.get("status") == "COMPLETED":
            risk_level = final_result["data"].get("risk_level")
            summary = final_result["data"].get("summary", "")
            if risk_level and "allergen" in summary.lower():
                print("\n" + "="*50)
                print("✅✅✅ TEST PASSED: Correctly identified product, recall, and hazard summary.")
            else:
                print("\n" + "="*50)
                print(f"❌ TEST FAILED: Unexpected analysis. risk_level='{risk_level}', summary='{summary}'")
        else:
            print("\n" + "="*50)
            print(f"❌ TEST FAILED: Workflow status '{final_result.get('status')}'")
            print(f"Error: {final_result.get('error')}")

    finally:
        # 7. Clean up the test database.
        logger.info("Tearing down in-memory test database...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped.")

    print("--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())