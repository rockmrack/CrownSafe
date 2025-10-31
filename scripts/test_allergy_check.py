#!/usr/bin/env python3
# scripts/test_allergy_check.py
# Test Scenario: Single-Tier Subscription (Allergy Scan)

import os
import sys

# ─── 0) Ensure project root is on sys.path ─────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ─── 1) Imports ─────────────────────────────────────────────────────────────────
import asyncio
import json
import logging
from unittest.mock import AsyncMock, patch

from sqlalchemy import text

from agents.command.commander_agent.agent_logic import BabyShieldCommanderLogic
from core_infra.database import Allergy, Base, FamilyMember, SessionLocal, User, engine

# ─── 2) Configuration & Mocks ─────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
TEST_BARCODE_ALLERGEN_PRODUCT = "041220787346"
TEST_USER_ID = 1


class MockProductIdentifierLogic:
    def __init__(self, *args, **kwargs):
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {
                    "product_name": "Organic Baby Food with Milk",
                    "upc": TEST_BARCODE_ALLERGEN_PRODUCT,
                    "ingredients": [
                        "Organic Apples",
                        "Water",
                        "Whole Milk Powder",
                        "Vitamin C",
                    ],
                },
            }
        )


class MockRecallDataAgentLogic:
    def __init__(self, *args, **kwargs):
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"recalls_found": 0, "recalls": []},
            }
        )


class MockAllergySensitivityLogic:
    def __init__(self, *args, **kwargs):
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"allergens_found": 1, "allergens": ["milk"]},
            }
        )


class MockHazardAnalysisLogic:
    def __init__(self, *args, **kwargs):
        self.process_task = AsyncMock(
            return_value={
                "status": "COMPLETED",
                "result": {"summary": "Analysis complete.", "risk_level": "Low"},
            }
        )


# ─── 3) Utility: drop all tables (cascade support) ────────────────────────────
def drop_all_cascade():
    dialect = engine.dialect.name
    conn = engine.connect()
    trans = conn.begin()
    try:
        if dialect == "postgresql":
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        else:
            Base.metadata.drop_all(bind=engine)
        trans.commit()
    finally:
        conn.close()


# ─── 4) Main Test Runner ───────────────────────────────────────────────────────
async def main():
    # 4.1 Load the JSON plan
    plan_path = os.path.join(PROJECT_ROOT, "tests", "fixtures", "test_plan_with_allergy_check.json")
    with open(plan_path, "r") as f:
        test_plan = json.load(f)

    # 4.2 Inject concrete test inputs
    for step in test_plan.get("steps", []):
        if step["step_id"] == "step1_identify_product":
            step["inputs"]["barcode"] = TEST_BARCODE_ALLERGEN_PRODUCT
            step["inputs"]["image_url"] = None
        if step["step_id"] == "step3_allergy_check":
            step["inputs"]["user_id"] = TEST_USER_ID

    # 4.3 Reset & recreate schema
    drop_all_cascade()
    Base.metadata.create_all(bind=engine)

    # 4.4 Seed test data
    with SessionLocal() as db:
        user = User(id=TEST_USER_ID, email="user@test.com")
        child = FamilyMember(name="Charlie", user=user)
        milk_allergy = Allergy(allergen="milk", family_member=child)
        db.add_all([user, child, milk_allergy])
        db.commit()

    # 4.5 Wire mocks into CommanderAgent
    logger = logging.getLogger(__name__)
    commander = BabyShieldCommanderLogic(agent_id="test_commander", logger_instance=logger)
    commander.router.agent_registry["identify_product"] = MockProductIdentifierLogic()
    commander.router.agent_registry["query_recalls_by_product"] = MockRecallDataAgentLogic()
    commander.router.agent_registry["check_allergy_sensitivity"] = MockAllergySensitivityLogic()
    commander.router.agent_registry["analyze_hazards"] = MockHazardAnalysisLogic()

    # 4.6 Run the workflow
    user_request = {"barcode": TEST_BARCODE_ALLERGEN_PRODUCT, "user_id": TEST_USER_ID}
    with patch.object(
        commander.planner,
        "process_task",
        return_value={"status": "COMPLETED", "plan": test_plan},
    ):
        result = await commander.start_safety_check_workflow(user_request)

    # 4.7 Print & validate
    print("\n" + "=" * 60)
    print("        TEST RESULT: Allergy Scan")
    print("=" * 60)
    print(json.dumps(result, indent=2))

    # **Updated validation**:
    if result.get("status") == "COMPLETED":
        data = result.get("data", {})
        summary = data.get("summary")
        risk = data.get("risk_level")
        if summary == "Analysis complete." and risk == "Low":
            print("\n✅✅✅ TEST PASSED: Final analysis summary and risk level are correct.")
        else:
            print(f"\n❌❌❌ TEST FAILED: Unexpected data.summary={summary}, data.risk_level={risk}")
    else:
        print("\n❌❌❌ TEST FAILED: Workflow did not complete successfully.")

    # 4.8 Final cleanup
    drop_all_cascade()


if __name__ == "__main__":
    asyncio.run(main())
