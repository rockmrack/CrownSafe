#!/usr/bin/env python3
"""Test a single recall connector (CPSC) to verify basic functionality"""

import asyncio
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from agents.recall_data_agent.connectors import CPSCConnector  # noqa: E402


async def test_cpsc():
    """Test CPSC connector only"""

    print("\n" + "=" * 80)
    print("TESTING CPSC CONNECTOR (US Consumer Product Safety Commission)")
    print("=" * 80 + "\n")

    connector = CPSCConnector()

    print("Fetching recalls from CPSC...")
    print("(This will take a few seconds...)\n")

    try:
        recalls = await connector.fetch_recent_recalls()

        # Limit to first 5 for display
        recalls = recalls[:5]

        print(f"SUCCESS! Fetched {len(recalls)} recalls from CPSC\n")

        if recalls:
            print("-" * 80)
            print("SAMPLE RECALLS:")
            print("-" * 80)

            for i, recall in enumerate(recalls[:3], 1):
                print(f"\n{i}. {recall.product_name}")
                print(f"   Brand: {recall.brand or 'N/A'}")
                print(f"   Recall ID: {recall.recall_id}")
                print(f"   Hazard: {(recall.hazard or 'N/A')[:100]}")
                print(f"   Date: {recall.recall_date}")

        print("\n" + "=" * 80)
        print("CPSC CONNECTOR IS WORKING!")
        print("=" * 80)
        print("\nYour RecallDataAgent can successfully fetch recalls from")
        print("the US Consumer Product Safety Commission API.\n")
        print("Next steps:")
        print("  • Test other connectors (FDA, NHTSA, etc.)")
        print("  • Set up database for full ingestion")
        print("  • Integrate with safety-check workflow\n")

        return True

    except Exception as e:
        print(f"ERROR: {e}\n")
        print("This could be due to:")
        print("  • Network connectivity issues")
        print("  • CPSC API temporarily unavailable")
        print("  • Missing dependencies\n")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_cpsc())
    sys.exit(0 if success else 1)
