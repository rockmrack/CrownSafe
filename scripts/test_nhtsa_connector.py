# scripts/test_nhtsa_connector.py

import asyncio
import json
import logging
import os
import sys
from unittest.mock import AsyncMock, patch

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from agents.recall_data_agent.connectors import NHTSAConnector

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# --- Mock API Response ---
# This is a simplified structure based on the real NHTSA API response for a car seat recall.
MOCK_NHTSA_RESPONSE = {
    "results": [
        {
            "ReportReceivedDate": "2025-04-15T00:00:00",
            "NHTSACampaignNumber": "25V123456",
            "Component": "CHILD SEAT",
            "Conequence": "The harness webbing may fray, increasing the risk of injury in a crash.",
            "Make": "Safety 1st",
            "Model": "Grow and Go Sprint",
            "Summary": "Child car seat harness may fail during crash",
            "DefectSummary": "Harness webbing defect in child safety seats",
        },
        {
            "ReportReceivedDate": "2025-03-22T00:00:00",
            "NHTSACampaignNumber": "25V098765",
            "Component": "CHILD SEAT",
            "Conequence": "Seat base may separate from vehicle attachment points.",
            "Make": "Graco",
            "Model": "4Ever DLX",
            "Summary": "Child seat base separation risk",
            "DefectSummary": "Base attachment mechanism defective",
        },
    ]
}
# --------------------------


async def main():
    """Main function to test the NHTSAConnector with a mocked API call."""
    logger = logging.getLogger(__name__)
    logger.info("--- Starting NHTSA Connector Test ---")

    # We use @patch to intercept any 'aiohttp.ClientSession.get' call
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Configure the mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = MOCK_NHTSA_RESPONSE
        mock_response.raise_for_status.return_value = None
        mock_get.return_value.__aenter__.return_value = mock_response

        # Initialize and run the connector
        nhtsa_connector = NHTSAConnector()
        nhtsa_recalls = await nhtsa_connector.fetch_recent_recalls()

        print("\n" + "=" * 60)
        print("          NHTSA Connector Test Result")
        print("=" * 60)

        for recall in nhtsa_recalls:
            print(f"ID: {recall.recall_id}")
            print(f"Agency: {recall.source_agency}")
            print(f"Product: {recall.product_name}")
            print(f"Date: {recall.recall_date}")
            print(f"Hazard: {recall.hazard}")
            print(f"URL: {recall.url}")
            print("-" * 40)

        # Validate the result
        if len(nhtsa_recalls) == 2:
            first_recall = nhtsa_recalls[0]
            if (
                first_recall.recall_id == "NHTSA-25V123456"
                and first_recall.source_agency == "NHTSA"
                and "Safety 1st" in first_recall.product_name
            ):
                print("\n✅✅✅ NHTSA Connector Test PASSED: Successfully parsed the mock JSON response.")
            else:
                print("\n❌❌❌ NHTSA Connector Test FAILED: Incorrect data parsing.")
                print(f"Expected ID: NHTSA-25V123456, Got: {first_recall.recall_id}")
                print(f"Expected Agency: NHTSA, Got: {first_recall.source_agency}")
        else:
            print(f"\n❌❌❌ NHTSA Connector Test FAILED: Expected 2 recalls, got {len(nhtsa_recalls)}")

    print("\n--- Test Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
