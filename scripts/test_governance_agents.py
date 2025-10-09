import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.governance.datagovernance_agent.agent_logic import DataGovernanceAgentLogic
from agents.governance.legalcontent_agent.agent_logic import LegalContentAgentLogic

logging.basicConfig(level=logging.INFO)


def test_governance_agents():
    print("--- Testing DataGovernanceAgent Logic ---")
    dg_logic = DataGovernanceAgentLogic(agent_id="test_dg_agent_01")

    print("\n1. Testing data minimization (compliant)...")
    payload_ok = {"name": "test", "email": "test@test.com"}
    required_ok = ["name", "email"]
    result = dg_logic.check_data_minimization(payload_ok, required_ok)
    assert result["is_compliant"] is True
    print("   -> SUCCESS: Correctly identified a compliant payload.")

    print("\n2. Testing data minimization (non-compliant)...")
    payload_bad = {"name": "test", "email": "test@test.com", "ip_address": "127.0.0.1"}
    required_bad = ["name", "email"]
    result = dg_logic.check_data_minimization(payload_bad, required_bad)
    assert result["is_compliant"] is False
    print("   -> SUCCESS: Correctly identified a non-compliant payload.")

    print("\n3. Testing data residency (EU)...")
    result = dg_logic.determine_data_residency("DE")  # Germany
    assert result["storage_region"] == "EU_MAIN_REGION"
    print("   -> SUCCESS: Correctly assigned Germany to the EU region.")

    print("\n4. Testing data residency (Default)...")
    result = dg_logic.determine_data_residency("JP")  # Japan
    assert result["storage_region"] == "US_EAST_1"  # Our default
    print("   -> SUCCESS: Correctly assigned Japan to the default region.")

    print("\n--- Testing LegalContentAgent Logic ---")
    lc_logic = LegalContentAgentLogic(agent_id="test_lc_agent_01")

    print("\n5. Testing legal document retrieval (success)...")
    result = lc_logic.get_legal_document("privacy", "en", "gb")
    assert result["status"] == "success"
    assert result["version"] == 1.1
    assert "United Kingdom" in result["content"]
    print("   -> SUCCESS: Correctly retrieved the UK Privacy Policy.")

    print("\n6. Testing legal document retrieval (not found)...")
    result = lc_logic.get_legal_document("tos", "fr", "ca")  # Does not exist
    assert result["status"] == "not_found"
    print("   -> SUCCESS: Correctly handled a non-existent document.")

    print("\n--- All governance agent tests passed successfully! ---")


if __name__ == "__main__":
    test_governance_agents()
