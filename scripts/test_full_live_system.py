import argparse
import asyncio
import logging

# Import live connectors directly
from agents.recall_data_agent.connectors.cpsc import CPSCConnector
from agents.recall_data_agent.connectors.cpso import SGCPSoConnector
from agents.recall_data_agent.connectors.fda import FDAConnector
from agents.recall_data_agent.connectors.opss import UKOPSSConnector
from agents.recall_data_agent.connectors.rapex import EURapexConnector

from agents.hazard_analysis_agent.agent_logic import HazardAnalysisLogic

# Import product and hazard analysis logic
from agents.product_identifier_agent.agent_logic import ProductIdentifierLogic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_live_direct")


async def run_live_test(barcode: str):
    logger.info(f"Starting 100% live test for barcode: {barcode}")

    # 1. Live recall ingestion
    connectors = [
        CPSCConnector(),
        FDAConnector(),
        EURapexConnector(),
        UKOPSSConnector(),
        SGCPSoConnector(),
    ]
    all_recalls = []
    for connector in connectors:
        try:
            batch = await connector.fetch_recent_recalls(barcode=barcode)
            if batch:
                all_recalls.extend(batch)
                logger.info(f"{len(batch)} recalls from {connector.__class__.__name__}")
            else:
                logger.info(f"No recalls from {connector.__class__.__name__}")
        except Exception as e:
            logger.error(f"Connector {connector.__class__.__name__} failed: {e}")

    logger.info(f"Total live recalls found: {len(all_recalls)}")
    logger.info(all_recalls)

    # 2. Live product identification
    identifier = ProductIdentifierLogic()
    try:
        product_info = await identifier.identify_product(barcode=barcode, image_url=None)
        logger.info(f"Product identified: {product_info}")
    except Exception as e:
        logger.error(f"Product identification failed: {e}")
        return

    # 3. Live hazard analysis
    analyzer = HazardAnalysisLogic()
    try:
        hazard_summary = await analyzer.analyze_hazards(product_name=product_info.get("name"), recalls=all_recalls)
        logger.info("Hazard analysis result:")
        logger.info(hazard_summary)
    except Exception as e:
        logger.error(f"Hazard analysis failed: {e}")
        return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 100% live end-to-end recall + hazard test")
    parser.add_argument("--barcode", required=True, help="Product barcode to test")
    args = parser.parse_args()
    asyncio.run(run_live_test(args.barcode))
