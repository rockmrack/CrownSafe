import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.premium.pregnancy_product_safety_agent.agent_logic import (
    PregnancyProductSafetyAgentLogic,
)

logging.basicConfig(level=logging.INFO)


def test_pregnancy_safety_logic():
    print("--- Testing PregnancyProductSafetyAgent Logic ---")

    logic = PregnancyProductSafetyAgentLogic(agent_id="test_preg_agent_01")

    print("\n1. Testing a product with a known unsafe ingredient (Retinol)...")
    # This product was added to our mock ingredient DB
    result = logic.check_product_safety("5060381320015")
    assert result["status"] == "success"
    assert result["is_safe"] is False
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["ingredient"] == "retinol"
    print("   -> SUCCESS: Correctly identified the product as unsafe.")
    print(f"      Reason: {result['alerts'][0]['reason']}")

    print("\n2. Testing a product that is safe...")
    # This product has no unsafe ingredients
    result = logic.check_product_safety("724120000133")  # Organic Baby Wash
    assert result["status"] == "success"
    assert result["is_safe"] is True
    assert len(result["alerts"]) == 0
    print("   -> SUCCESS: Correctly identified the product as safe.")

    print("\n3. Testing a product not in the ingredient database...")
    result = logic.check_product_safety("999999999999")
    assert result["status"] == "error"
    assert "not found" in result["message"]
    print("   -> SUCCESS: Correctly handled a product not found in the database.")

    print("\n--- All tests passed successfully! PregnancyProductSafetyAgent is working. ---")


if __name__ == "__main__":
    test_pregnancy_safety_logic()
