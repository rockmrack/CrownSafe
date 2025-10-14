# agents/recall_data_agent/main.py
"""
RecallDataAgent Entry Point
Can be run standalone for manual ingestion or scheduled via Celery/cron.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)

from agents.recall_data_agent.agent_logic import RecallDataAgentLogic
from core_infra.database import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def run_manual_ingestion():
    """
    Run a manual ingestion cycle.
    This can be triggered by:
    - Cron job: python agents/recall_data_agent/main.py
    - Celery task: celery worker runs this
    - Manual execution for testing
    """
    logger.info("=" * 80)
    logger.info("BABYSHIELD RECALL DATA AGENT - MANUAL INGESTION")
    logger.info("=" * 80)

    # Ensure database tables exist
    logger.info("Verifying database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables verified/created")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return {"status": "error", "error": str(e)}

    # Initialize agent
    agent_id = f"manual_ingestor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    agent = RecallDataAgentLogic(agent_id=agent_id)

    # Run ingestion cycle
    logger.info("Starting ingestion cycle from all 39+ agencies...")
    logger.info("-" * 80)

    result = await agent.run_ingestion_cycle()

    # Display results
    logger.info("-" * 80)
    logger.info("INGESTION CYCLE COMPLETE")
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Total Fetched: {result.get('total_fetched', 0)}")
    logger.info(f"Total Upserted: {result.get('total_upserted', 0)}")
    logger.info(f"Total Skipped: {result.get('total_skipped', 0)}")
    logger.info(f"Duration: {result.get('duration_seconds', 0):.2f} seconds")

    if result.get("errors"):
        logger.warning(f"Errors encountered: {len(result['errors'])}")
        for error in result["errors"][:5]:  # Show first 5 errors
            logger.warning(f"  - {error}")

    # Get database statistics
    stats = agent.get_statistics()
    if stats.get("status") == "success":
        logger.info("-" * 80)
        logger.info("DATABASE STATISTICS")
        logger.info(f"Total Recalls in Database: {stats.get('total_recalls', 0)}")
        logger.info("Recalls by Agency:")
        for agency, count in sorted(
            stats.get("by_agency", {}).items(), key=lambda x: x[1], reverse=True
        ):
            logger.info(f"  {agency}: {count}")

    logger.info("=" * 80)

    return result


async def test_query_mode():
    """
    Test mode: Query for a specific product.
    Usage: python agents/recall_data_agent/main.py --test
    """
    logger.info("=" * 80)
    logger.info("RECALL DATA AGENT - TEST QUERY MODE")
    logger.info("=" * 80)

    agent = RecallDataAgentLogic(agent_id="test_agent")

    # Test queries
    test_cases = [
        {"product_name": "baby", "brand": None},
        {"product_name": "crib", "brand": None},
        {"model_number": "ABC123", "product_name": None},
    ]

    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n--- Test Case {i} ---")
        logger.info(f"Inputs: {test_case}")

        result = await agent.process_task(test_case)

        logger.info(f"Status: {result.get('status')}")
        if result.get("status") == "COMPLETED":
            recalls_found = result.get("result", {}).get("recalls_found", 0)
            logger.info(f"Recalls Found: {recalls_found}")

            if recalls_found > 0:
                recalls = result.get("result", {}).get("recalls", [])
                logger.info(f"First recall: {recalls[0].get('product_name')}")
        else:
            logger.error(f"Error: {result.get('error')}")

    logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="BabyShield RecallDataAgent - Manual Ingestion Tool"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run in test query mode instead of ingestion"
    )
    args = parser.parse_args()

    if args.test:
        # Test mode
        asyncio.run(test_query_mode())
    else:
        # Normal ingestion mode
        result = asyncio.run(run_manual_ingestion())

        # Exit with appropriate code
        if result.get("status") == "success":
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
