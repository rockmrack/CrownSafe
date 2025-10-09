# scripts/test_recall_connectors_live.py

import os
import asyncio
import logging
import json
from dotenv import load_dotenv

from agents.recall_data_agent.connectors import FDAConnector, EURapexConnector

# Load your .env (must contain FDA_API_KEY and OPENDATASOFT_API_KEY)
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s │ %(message)s")
logger = logging.getLogger("live-test")


async def main():
    logger.info("🔍 Starting LIVE Recall Connectors Test")

    # --- FDA ---
    logger.info("→ Fetching live FDA recalls…")
    try:
        fda_recs = await FDAConnector().fetch_recent_recalls()
        logger.info(f"   → Retrieved {len(fda_recs)} FDA recalls")
        print("\nFDA live sample:")
        print(json.dumps([json.loads(r.model_dump_json()) for r in fda_recs[:5]], indent=2))
    except Exception as e:
        logger.error("‼︎ FDA live fetch failed", exc_info=True)

    # --- EU RAPEX (Opendatasoft) ---
    logger.info("→ Fetching live EU RAPEX recalls…")
    try:
        rapex_recs = await EURapexConnector().fetch_recent_recalls(limit=5)
        logger.info(f"   → Retrieved {len(rapex_recs)} EU RAPEX recalls")
        print("\nEU RAPEX live sample:")
        print(json.dumps([json.loads(r.model_dump_json()) for r in rapex_recs[:5]], indent=2))
    except Exception as e:
        logger.error("‼︎ EU RAPEX live fetch failed", exc_info=True)

    logger.info("✅ LIVE test complete")


if __name__ == "__main__":
    asyncio.run(main())
