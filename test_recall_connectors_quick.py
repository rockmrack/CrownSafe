#!/usr/bin/env python3
"""Quick test of RecallDataAgent with real API calls (limited to 5 recalls per agency)
This script tests the actual workflow without requiring a full database setup.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from agents.recall_data_agent.connectors import ConnectorRegistry  # noqa: E402


async def quick_test():
    """Quick test of live recall fetching."""
    print("=" * 80)
    print("BABYSHIELD RECALL DATA AGENT - QUICK TEST")
    print("=" * 80)
    print()

    registry = ConnectorRegistry()

    print(f"✅ Total connectors registered: {len(registry.connectors)}")
    print()

    # Test each operational connector (limit to 5 recalls each for speed)
    operational_connectors = [
        "CPSC",
        "FDA",
        "NHTSA",
        "Health_Canada",
        "EU_RAPEX",
        "USDA_FSIS",
    ]

    print("Testing operational connectors (fetching 5 recalls each)...")
    print("-" * 80)

    total_recalls = 0

    for connector_name in operational_connectors:
        connector = registry.connectors.get(connector_name)
        if connector:
            try:
                print(f"\n🔍 Testing {connector_name}...")

                start_time = datetime.now()
                recalls = await connector.fetch_recalls(limit=5)
                duration = (datetime.now() - start_time).total_seconds()

                total_recalls += len(recalls)

                print(f"   ✅ Fetched: {len(recalls)} recalls")
                print(f"   ⏱️  Duration: {duration:.2f}s")

                if recalls:
                    # Show first recall details
                    recall = recalls[0]
                    print(f"   📦 Sample: {recall.get('product_name', 'N/A')[:50]}")
                    print(f"   🏷️  Brand: {recall.get('brand', 'N/A')[:30]}")
                    print(f"   ⚠️  Hazard: {recall.get('hazard', 'N/A')[:50]}")

            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")

    print()
    print("=" * 80)
    print("✅ QUICK TEST COMPLETE")
    print(f"   Total recalls fetched: {total_recalls}")
    print(f"   Operational connectors: {len(operational_connectors)}")
    print("=" * 80)
    print()

    # Show what would happen in full ingestion
    print("📊 FULL INGESTION PROJECTION:")
    print(f"   • With {len(registry.connectors)} total connectors")
    print("   • Average ~100 recalls per agency")
    print(f"   • Expected total: ~{len(registry.connectors) * 100:,} recalls")
    print("   • Duration: ~45-60 seconds (concurrent)")
    print()

    return total_recalls


if __name__ == "__main__":
    print("\n")
    recalls = asyncio.run(quick_test())

    if recalls > 0:
        print("✅ RecallDataAgent is working! You can now:")
        print("   1. Test product queries (see NEXT_STEPS.md)")
        print("   2. Run full ingestion with proper database (see production setup)")
        print("   3. Integrate with your API endpoints")
        print()
        sys.exit(0)
    else:
        print("⚠️  No recalls fetched. Check your internet connection.")
        sys.exit(1)
