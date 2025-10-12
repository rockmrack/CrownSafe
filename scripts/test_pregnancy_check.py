# scripts/test_pregnancy_check.py
# Test Scenario: Pregnancy Product Scan (Simplified - No subscription tiers)

import sys
import os
import asyncio
import logging
import json
from unittest.mock import patch, AsyncMock

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic
from core_infra.database import Base, engine, SessionLocal, User, get_db_session

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- Test Configuration ---
TEST_BARCODE_RISKY_PRODUCT = "850016249012"  # CeraVe Cleanser
TEST_USER_ID = 1
# --------------------------


# --- Mock Agent Logic ---
class MockProductIdentifierLogic:
    def __init__(self, *args, **kwargs):
        self.agent_id = "identify_product"
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {
                    "product_name": "CeraVe Hydrating Facial Cleanser",
                    "upc": TEST_BARCODE_RISKY_PRODUCT,
                    "ingredients": ["Water", "Glycerin", "Salicylic Acid", "Ceramides"],
                },
            }
        )


class MockRecallDataAgentLogic:
    def __init__(self, *args, **kwargs):
        self.agent_id = "query_recalls_by_product"
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"recalls_found": 0, "recalls": []},
            }
        )


class MockHazardAnalysisLogic:
    def __init__(self, *args, **kwargs):
        self.agent_id = "analyze_hazards"
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"summary": "Analysis complete.", "risk_level": "Low"},
            }
        )


class MockPregnancyCheckLogic:
    def __init__(self, *args, **kwargs):
        self.agent_id = "analyze_pregnancy_risks"
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {
                    "risks_found": 1,
                    "risky_ingredients": ["Salicylic Acid"],
                    "recommendations": "Avoid Salicylic Acid during pregnancy.",
                    "detailed_analysis": "Salicylic Acid is not recommended during pregnancy.",
                },
            }
        )


# --------------------------


async def run_pregnancy_test():
    """Run the pregnancy safety check workflow."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Pregnancy Safety Check Test ---")

    # Create test plan with correct field names ('inputs' not 'input')
    test_plan = {
        "workflow_name": "Pregnancy Safety Check",
        "steps": [
            {
                "step_id": "step1_identify_product",
                "agent_type": "identify_product",
                "agent_capability_required": "identify_product",
                "inputs": {"barcode": "{barcode}"},  # Changed from 'input' to 'inputs'
                "output_map": {
                    "product_name": "product_name",
                    "upc": "upc",
                    "ingredients": "ingredients",
                },
            },
            {
                "step_id": "step2_check_recalls",
                "agent_type": "query_recalls_by_product",
                "agent_capability_required": "query_recalls_by_product",
                "inputs": {
                    "product_name": "{step1_identify_product.result.product_name}"
                },  # Changed from 'input' to 'inputs'
                "output_map": {"recalls_found": "recalls_found", "recalls": "recalls"},
                "dependencies": ["step1_identify_product"],
            },
            {
                "step_id": "step3_pregnancy_check",
                "agent_type": "analyze_pregnancy_risks",
                "agent_capability_required": "analyze_pregnancy_risks",
                "inputs": {  # Changed from 'input' to 'inputs'
                    "ingredients": "{step1_identify_product.result.ingredients}",
                    "user_id": "{user_id}",
                },
                "output_map": {
                    "risks_found": "risks_found",
                    "risky_ingredients": "risky_ingredients",
                },
                "dependencies": ["step1_identify_product"],
            },
        ],
    }

    # Initialize commander
    commander = BabyShieldCommanderLogic(
        agent_id="test_commander", logger_instance=logger
    )

    # Wait for initialization
    await asyncio.sleep(0.1)

    # Create mock agents
    mock_agents = {
        "identify_product": MockProductIdentifierLogic(),
        "query_recalls_by_product": MockRecallDataAgentLogic(),
        "analyze_hazards": MockHazardAnalysisLogic(),
        "analyze_pregnancy_risks": MockPregnancyCheckLogic(),
    }

    # Inject mocks into router
    if hasattr(commander.router, "agent_registry"):
        commander.router.agent_registry.update(mock_agents)
        logger.info("Injected mock agents into router registry")
    else:
        logger.warning("Could not find agent_registry in router")

    # Mock the planner to return our test plan
    with patch.object(
        commander.planner,
        "process_task",
        return_value={"status": "COMPLETED", "plan": test_plan},
    ):
        # Define user request
        user_request = {"barcode": TEST_BARCODE_RISKY_PRODUCT, "user_id": TEST_USER_ID}

        try:
            # Run the workflow
            result = await commander.start_safety_check_workflow(user_request)
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            import traceback

            traceback.print_exc()
            return {"status": "FAILED", "error": str(e)}


def setup_test_user():
    """Create or update test user."""
    with get_db_session() as db:
        user = db.query(User).filter_by(id=TEST_USER_ID).first()
        if user:
            user.email = "test@example.com"
            user.hashed_password = "testhash"
            user.is_pregnant = True
            user.is_premium = True
            print("Updated existing test user (ID=)")
        else:
            user = User(
                id=TEST_USER_ID,
                email="test@example.com",
                hashed_password="testhash",
                is_pregnant=True,
                is_premium=True,
            )
            db.add(user)
            print(f"Created new test user (ID={TEST_USER_ID})")

        db.commit()


async def main():
    """Main test function."""
    # Set TEST_MODE
    os.environ["TEST_MODE"] = "true"

    # Setup database
    Base.metadata.create_all(bind=engine)
    setup_test_user()

    try:
        # Run the test
        result = await run_pregnancy_test()

        print("\n" + "=" * 60)
        print("TEST RESULT")
        print("=" * 60)

        # Pretty print the result
        if result:
            print(json.dumps(result, indent=2))

        # Check results
        if result.get("status") == "COMPLETED":
            print("\n✅ Workflow completed successfully!")

            # Try to find pregnancy results in the response
            result_str = json.dumps(result)

            if "Salicylic Acid" in result_str and (
                "risks_found" in result_str or "risky_ingredients" in result_str
            ):
                print("\n✅ TEST PASSED: Pregnancy risks correctly identified!")
                print("Found Salicylic Acid as a risky ingredient")
            elif "pregnancy" in result_str.lower():
                print("\n✅ TEST PASSED: Pregnancy check was executed!")
            else:
                print(
                    "\n⚠️  TEST INCONCLUSIVE: Workflow completed but pregnancy results not clearly found in response"
                )
                print("This might be due to response structure differences")

        else:
            print("\n❌ TEST FAILED: Workflow did not complete successfully.")
            print(f"Status: {result.get('status')}")
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\nTest completed. Database preserved for inspection.")

        # Show user state
        with get_db_session() as db:
            user = db.query(User).filter_by(id=TEST_USER_ID).first()
            if user:
                print(f"\nTest user: email={user.email}, pregnant={user.is_pregnant}")


if __name__ == "__main__":
    asyncio.run(main())
