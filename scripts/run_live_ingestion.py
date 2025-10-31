# scripts/run_live_ingestion.py

import asyncio
import logging
import os
import sys

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.recall_data_agent.agent_logic import RecallDataAgentLogic
from core_infra.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def main():
    """
    Runs the live data ingestion cycle to populate the database with fresh recalls.
    """
    logger = logging.getLogger(__name__)
    logger.info("--- Starting Live Data Ingestion from All Connectors ---")

    # 1. Set up the database tables if they don't exist.
    Base.metadata.create_all(bind=engine)

    # 2. Run the LIVE ingestion cycle.
    recall_agent_logic = RecallDataAgentLogic(agent_id="live_ingestor_002", logger_instance=logger)
    ingestion_result = await recall_agent_logic.run_ingestion_cycle()

    print("\n" + "=" * 50)
    print("          LIVE INGESTION RESULT")
    print("=" * 50)
    print(f"Live ingestion complete. Added {ingestion_result.get('total_upserted', 0)} new recalls to the database.")
    print("The database is now populated with the latest recall data.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
