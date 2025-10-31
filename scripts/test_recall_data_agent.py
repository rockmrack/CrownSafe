# scripts/test_recall_data_agent.py

import asyncio
import json
import logging
import os
import sys
from typing import List
from unittest.mock import patch

# Color support
try:
    from colorama import Fore, Style, init

    init(autoreset=True)
except ImportError:

    class Fore:
        GREEN = ""
        RED = ""

    class Style:
        BRIGHT = ""
        RESET_ALL = ""


# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

# Import DB setup and agent logic
from agents.recall_data_agent.agent_logic import RecallDataAgentLogic  # noqa: E402
from agents.recall_data_agent.models import Recall  # noqa: E402
from core_infra.database import Base, engine  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Test Configuration ---
MOCK_CPSC_RECALL = Recall(
    recall_id="CPSC-001",
    source_agency="CPSC",
    recall_date="2025-07-20",
    description="Potential choking hazard from small parts.",
    hazard="Choking hazard",
    remedy="Stop using and return for a full refund",
    product_name="Happy Baby Super-Puffs",
    url="http://cpsc.gov/recalls/001",
)
# --------------------------


# Mock connector classes
class MockCPSCConnector:
    async def fetch_recent_recalls(self) -> List[Recall]:
        return [MOCK_CPSC_RECALL]


class EmptyConnector:
    async def fetch_recent_recalls(self) -> List[Recall]:
        return []


async def main():
    logger.info("--- Starting RecallDataAgent Live Database Test ---")

    # 1. Setup in-memory DB
    Base.metadata.create_all(bind=engine)
    logger.info("In-memory tables created.")

    # 2. Patch connectors in the connectors module
    with (
        patch("agents.recall_data_agent.connectors.CPSCConnector", new=MockCPSCConnector),
        patch("agents.recall_data_agent.connectors.FDAConnector", new=EmptyConnector),
        patch("agents.recall_data_agent.connectors.EU_RAPEX_Connector", new=EmptyConnector),
        patch("agents.recall_data_agent.connectors.UK_OPSS_Connector", new=EmptyConnector),
        patch("agents.recall_data_agent.connectors.SG_CPSO_Connector", new=EmptyConnector),
    ):
        try:
            # 3. Initialize agent logic
            agent_logic = RecallDataAgentLogic(agent_id="test_rda_001", logger_instance=logger)

            # 4. Test WRITE
            logger.info("--- Testing WRITE (run_ingestion_cycle) ---")
            write_result = await agent_logic.run_ingestion_cycle()
            print(json.dumps(write_result, indent=2))
            if write_result.get("total_upserted") == 1:
                print(Fore.GREEN + Style.BRIGHT + "✔ WRITE succeeded.")
            else:
                print(Fore.RED + Style.BRIGHT + "✖ WRITE failed.")

            # 5. Test READ
            logger.info("--- Testing READ (process_task) ---")
            task_inputs = {"product_name": MOCK_CPSC_RECALL.product_name}
            read_result = await agent_logic.process_task(task_inputs)
            print(json.dumps(read_result, indent=2))

            # 6. Validate
            if read_result.get("status") == "COMPLETED":
                recalls = read_result["result"]["recalls"]
                if len(recalls) == 1 and recalls[0]["recall_id"] == MOCK_CPSC_RECALL.recall_id:
                    print(Fore.GREEN + Style.BRIGHT + f"✔ READ succeeded: {recalls[0]['recall_id']}")
                else:
                    print(Fore.RED + Style.BRIGHT + "✖ READ mismatch.")
            else:
                print(Fore.RED + Style.BRIGHT + f"✖ READ failed: {read_result.get('error')}")

        finally:
            # Cleanup
            Base.metadata.drop_all(bind=engine)
            logger.info("In-memory tables dropped.")

    print("--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
