import os
import sys
import asyncio
import logging
import json
from dotenv import load_dotenv

# Ensure project root is on sys.path so "import agents…" works
sys.path.insert(0, os.getcwd())

from agents.recall_data_agent.connectors import (
    FDAConnector,
    CPSCConnector,
    EURapexConnector,
    UKOPSSConnector,
    NHTSAConnector,
    USDAFSISConnector,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s │ %(message)s")
logger = logging.getLogger("test-live")


async def main():
    logger.info("🔍 Starting LIVE Recall Connectors Test (US, Europe, UK)")

    # --- US FDA ---
    logger.info("→ Fetching live US FDA recalls…")
    try:
        fda_recs = await FDAConnector().fetch_recent_recalls()
        logger.info(f"   → Retrieved {len(fda_recs)} FDA recalls")
        print(
            "\nUS FDA LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in fda_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ US FDA live fetch failed")

    # --- US CPSC ---
    logger.info("→ Fetching live US CPSC recalls…")
    try:
        cpsc_recs = await CPSCConnector().fetch_recent_recalls()
        logger.info(f"   → Retrieved {len(cpsc_recs)} CPSC recalls")
        print(
            "\nUS CPSC LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in cpsc_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ US CPSC live fetch failed")

    # --- US NHTSA ---
    logger.info("→ Fetching live US NHTSA recalls…")
    try:
        nhtsa_recs = await NHTSAConnector().fetch_recent_recalls()
        logger.info(f"   → Retrieved {len(nhtsa_recs)} NHTSA recalls")
        print(
            "\nUS NHTSA LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in nhtsa_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ US NHTSA live fetch failed")

    # --- USDA FSIS ---
    logger.info("→ Fetching live USDA FSIS recalls…")
    try:
        usda_recs = await USDAFSISConnector().fetch_recent_recalls()
        logger.info(f"   → Retrieved {len(usda_recs)} USDA FSIS recalls")
        print(
            "\nUSDA FSIS LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in usda_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ USDA FSIS live fetch failed")

    # --- EU RAPEX ---
    logger.info("→ Fetching live EU RAPEX recalls…")
    try:
        rapex_recs = await EURapexConnector().fetch_recent_recalls(limit=5)
        logger.info(f"   → Retrieved {len(rapex_recs)} EU RAPEX recalls")
        print(
            "\nEU RAPEX LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in rapex_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ EU RAPEX live fetch failed")

    # --- UK OPSS ---
    logger.info("→ Fetching live UK OPSS recalls…")
    try:
        uk_recs = await UKOPSSConnector().fetch_recent_recalls(limit=5)
        logger.info(f"   → Retrieved {len(uk_recs)} UK OPSS recalls")
        print(
            "\nUK OPSS LIVE SAMPLE:\n",
            json.dumps([json.loads(r.model_dump_json()) for r in uk_recs[:3]], indent=2),
        )
    except Exception:
        logger.exception("‼︎ UK OPSS live fetch failed")

    # --- Summary ---
    logger.info("📊 Testing all connectors together...")
    try:
        all_connectors = [
            ("US FDA", FDAConnector()),
            ("US CPSC", CPSCConnector()),
            ("US NHTSA", NHTSAConnector()),
            ("USDA FSIS", USDAFSISConnector()),
            ("EU RAPEX", EURapexConnector()),
            ("UK OPSS", UKOPSSConnector()),
        ]
        total_recalls = 0
        print("\n" + "=" * 60)
        print("SUMMARY OF ALL CONNECTORS:")
        print("=" * 60)
        for name, connector in all_connectors:
            try:
                if name in ["EU RAPEX", "UK OPSS"]:
                    recalls = await connector.fetch_recent_recalls(limit=10)
                else:
                    recalls = await connector.fetch_recent_recalls()
                total_recalls += len(recalls)
                print(f"{name:12} → {len(recalls):3d} recalls")
                if recalls:
                    sample = recalls[0]
                    print(f"             Sample: {sample.recall_id} - {sample.product_name[:50]}...")
            except Exception as e:
                print(f"{name:12} → ERROR: {str(e)[:50]}...")
        print("=" * 60)
        print(f"TOTAL RECALLS FETCHED: {total_recalls}")
        print("=" * 60)
    except Exception:
        logger.exception("‼︎ Summary generation failed")
    logger.info("✅ LIVE test complete")


if __name__ == "__main__":
    asyncio.run(main())
