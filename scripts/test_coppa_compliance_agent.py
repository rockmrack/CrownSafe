import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.governance.coppa_compliance_agent.agent_logic import (
    COPPA_ComplianceAgentLogic,
)

logging.basicConfig(level=logging.INFO)


def test_coppa_compliance_logic():
    print("--- Testing COPPA_ComplianceAgent Logic ---")

    logic = COPPA_ComplianceAgentLogic(agent_id="test_coppa_agent_01")

    print("\n1. Testing a user over 13...")
    user_over_13 = {"user_id": "user_adult_01", "birth_date": "2005-01-01"}
    result = logic.check_age_and_get_consent_status(user_over_13)
    assert result["status"] == "success"
    assert result["coppa_applies"] is False
    print("   -> SUCCESS: Correctly identified that COPPA does not apply.")

    print("\n2. Testing a user under 13 WITH consent...")
    user_under_13_with_consent = {
        "user_id": "user_child_01",
        "birth_date": "2020-01-01",
        "parental_consent_verified": True,
    }
    result = logic.check_age_and_get_consent_status(user_under_13_with_consent)
    assert result["status"] == "success"
    assert result["coppa_applies"] is True
    assert result["consent_obtained"] is True
    print("   -> SUCCESS: Correctly identified that user is under 13 and has consent.")

    print("\n3. Testing a user under 13 WITHOUT consent...")
    user_under_13_no_consent = {"user_id": "user_child_02", "birth_date": "2021-01-01"}
    result = logic.check_age_and_get_consent_status(user_under_13_no_consent)
    assert result["status"] == "success"
    assert result["coppa_applies"] is True
    assert result["consent_obtained"] is False
    print("   -> SUCCESS: Correctly identified that user is under 13 and requires consent.")

    print("\n4. Testing a user with no birth date provided...")
    user_no_birth_date = {"user_id": "user_unknown_01"}
    result = logic.check_age_and_get_consent_status(user_no_birth_date)
    assert result["status"] == "success"
    assert result["coppa_applies"] is True
    assert result["consent_obtained"] is False
    print("   -> SUCCESS: Correctly and safely defaulted to requiring consent when age is unknown.")

    print("\n5. Testing data deletion plan generation...")
    result = logic.generate_data_deletion_plan("user_child_01")
    assert result["status"] == "success"
    assert len(result["deletion_plan"]) > 0
    print("   -> SUCCESS: Correctly generated a data deletion plan.")
    print("      Plan Steps:")
    for step in result["deletion_plan"]:
        print(f"      - {step}")

    print("\n--- All tests passed successfully! COPPA_ComplianceAgent is working correctly. ---")


if __name__ == "__main__":
    test_coppa_compliance_logic()
