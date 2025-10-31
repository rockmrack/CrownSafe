import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.governance.childrenscode_compliance_agent.agent_logic import (  # noqa: E402
    ChildrensCode_ComplianceAgentLogic,
)

logging.basicConfig(level=logging.INFO)


def test_childrenscode_compliance_logic():
    print("--- Testing ChildrensCode_ComplianceAgent Logic ---")

    logic = ChildrensCode_ComplianceAgentLogic(agent_id="test_cc_agent_01")

    print("\n1. Testing a user in the US (should not apply)...")
    user_us = {"user_id": "user_us_01", "country_code": "US", "age": 10}
    result = logic.verify_default_settings(user_us)
    assert result["compliance_status"] == "NOT_APPLICABLE"
    print("   -> SUCCESS: Correctly identified that the code does not apply.")

    print("\n2. Testing an adult user in the UK (should not apply)...")
    user_uk_adult = {"user_id": "user_uk_adult_01", "country_code": "UK", "age": 25}
    result = logic.verify_default_settings(user_uk_adult)
    assert result["compliance_status"] == "NOT_APPLICABLE"
    print("   -> SUCCESS: Correctly identified that the code does not apply to adults.")

    print("\n3. Testing a child user in the UK with COMPLIANT settings...")
    user_uk_child_compliant = {
        "user_id": "user_uk_child_01",
        "country_code": "UK",
        "age": 12,
        "settings": {
            "geo_location_sharing": False,
            "profile_visibility": "private",
            "community_content_filter": "strict",
        },
    }
    result = logic.verify_default_settings(user_uk_child_compliant)
    assert result["compliance_status"] == "COMPLIANT"
    print("   -> SUCCESS: Correctly verified compliant default settings.")

    print("\n4. Testing a child user in the UK with NON-COMPLIANT settings...")
    user_uk_child_non_compliant = {
        "user_id": "user_uk_child_02",
        "country_code": "UK",
        "age": 15,
        "settings": {
            "geo_location_sharing": True,  # Non-compliant
            "profile_visibility": "private",
            "community_content_filter": "moderate",  # Non-compliant
        },
    }
    result = logic.verify_default_settings(user_uk_child_non_compliant)
    assert result["compliance_status"] == "NON_COMPLIANT"
    assert len(result["issues"]) == 2
    print("   -> SUCCESS: Correctly identified 2 non-compliant settings.")
    print("      Issues Found:")
    for issue in result["issues"]:
        print(
            f"      - Setting '{issue['setting']}' is '{issue['current_value']}', should be '{issue['required_default']}'"  # noqa: E501
        )

    print("\n--- All tests passed successfully! ChildrensCode_ComplianceAgent is working correctly. ---")


if __name__ == "__main__":
    test_childrenscode_compliance_logic()
