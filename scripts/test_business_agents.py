import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.business.metrics_agent.agent_logic import MetricsAgentLogic  # noqa: E402
from agents.value_add.alternatives_agent.agent_logic import AlternativesAgentLogic  # noqa: E402

logging.basicConfig(level=logging.INFO)


def test_business_agents():
    print("--- Testing MetricsAgent Logic ---")
    metrics_logic = MetricsAgentLogic(agent_id="test_metrics_agent_01")

    print("\n1. Testing 'user_signup' event tracking...")
    result = metrics_logic.track_event(
        user_id=123,
        event_name="user_signup",
        event_properties={"source": "organic", "country": "US"},
    )
    assert result["status"] == "success"
    print("   -> SUCCESS: Correctly tracked a signup event.")

    print("\n2. Testing 'product_scan' event tracking...")
    result = metrics_logic.track_event(
        user_id=456,
        event_name="product_scan",
        event_properties={"scan_type": "barcode", "recall_found": True},
    )
    assert result["status"] == "success"
    print("   -> SUCCESS: Correctly tracked a product scan event.")

    print("\n--- Testing AlternativesAgent Logic ---")
    alt_logic = AlternativesAgentLogic(agent_id="test_alt_agent_01")

    print("\n3. Testing alternatives for a known category...")
    result = alt_logic.get_alternatives("Super Baby Rocker", "Rocker")
    assert result["status"] == "success"
    assert len(result["alternatives"]) == 2
    print(f"   -> SUCCESS: Found {len(result['alternatives'])} alternatives for 'Rocker'.")
    print(f"      Suggestion 1: {result['alternatives'][0]['name']}")

    print("\n4. Testing alternatives for an unknown category...")
    result = alt_logic.get_alternatives("Mega Stroller 5000", "Stroller")
    assert result["status"] == "success"
    assert len(result["alternatives"]) == 0
    print("   -> SUCCESS: Correctly returned 0 alternatives for an unknown category.")

    print("\n--- All business & value-add agent tests passed successfully! ---")


if __name__ == "__main__":
    test_business_agents()
