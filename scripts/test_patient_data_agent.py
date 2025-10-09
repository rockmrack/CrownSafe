import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from agents.patient_data_agent.agent_logic import PatientDataAgentLogic

logging.basicConfig(level=logging.INFO)


def test_patient_data_agent():
    print("--- Testing PatientDataAgent Logic (MOCK_EMR Mode) ---")

    logic = PatientDataAgentLogic(agent_id="test_patient_agent_01")

    print("\n1. Testing retrieval for an existing patient...")
    result = logic.get_patient_record("patient-001")
    assert result["status"] == "success"
    assert result["record"]["name"] == "John Doe"
    print("   -> SUCCESS: Correctly retrieved record for patient-001.")

    print("\n2. Testing retrieval for another existing patient...")
    result = logic.get_patient_record("patient-002")
    assert result["status"] == "success"
    assert result["record"]["name"] == "Jane Smith"
    print("   -> SUCCESS: Correctly retrieved record for patient-002.")

    print("\n3. Testing retrieval for a non-existent patient...")
    result = logic.get_patient_record("patient-999")
    assert result["status"] == "not_found"
    print("   -> SUCCESS: Correctly handled non-existent patient ID.")

    print("\n4. Testing patient search by diagnosis...")
    result = logic.process_task(
        {"task_name": "search_patients", "criteria": {"diagnoses_icd10": "I50"}}
    )
    assert result["status"] == "COMPLETED"
    assert result["result_count"] >= 2  # Should find patient-001 and patient-002
    print(f"   -> SUCCESS: Found {result['result_count']} patients with heart failure diagnosis.")

    print("\n5. Testing patient search by medication...")
    result = logic.process_task(
        {"task_name": "search_patients", "criteria": {"medication_history": "Metformin"}}
    )
    assert result["status"] == "COMPLETED"
    print(f"   -> SUCCESS: Found {result['result_count']} patients on Metformin.")

    print("\n6. Testing patient data validation...")
    result = logic.process_task({"task_name": "validate_patient_data", "patient_id": "patient-001"})
    assert result["status"] == "COMPLETED"
    assert result["is_valid"]
    print("   -> SUCCESS: Patient-001 data is valid.")

    print("\n7. Testing audit log functionality...")
    # First, get patient to trigger audit
    _ = logic.get_patient_record("patient-001")

    # Then check audit log
    result = logic.process_task({"task_name": "get_audit_log", "patient_id": "patient-001"})
    assert result["status"] == "COMPLETED"
    assert result["entry_count"] > 0
    print(f"   -> SUCCESS: Found {result['entry_count']} audit entries for patient-001.")

    print("\n8. Testing privacy consent check...")
    result = logic.process_task(
        {
            "task_name": "check_privacy_consent",
            "patient_id": "patient-001",
            "action": "check_consent",
        }
    )
    assert result["status"] == "COMPLETED"
    print(f"   -> SUCCESS: Retrieved consent status for patient-001.")

    print("\n9. Testing data export...")
    result = logic.process_task(
        {
            "task_name": "export_patient_data",
            "patient_ids": ["patient-001", "patient-002"],
            "format": "json",
        }
    )
    assert result["status"] == "COMPLETED"
    assert result["patient_count"] == 2
    print("   -> SUCCESS: Exported 2 patient records.")

    print("\n10. Testing comprehensive functionality...")
    # Test search with multiple criteria
    result = logic.process_task(
        {
            "task_name": "search_patients",
            "criteria": {"diagnoses_icd10": "I50", "medication_history": "Lisinopril"},
        }
    )
    assert result["status"] == "COMPLETED"
    print(f"   -> SUCCESS: Complex search found {result['result_count']} matching patients.")

    print("\n--- All tests passed successfully! ---")

    # Print summary
    print("\n=== Test Summary ===")
    print("The PatientDataAgent is functioning correctly with mock data.")
    print("All major capabilities have been tested:")
    print("  ✓ Patient record retrieval")
    print("  ✓ Patient search (by diagnosis, medication)")
    print("  ✓ Data validation")
    print("  ✓ Audit logging")
    print("  ✓ Privacy consent management")
    print("  ✓ Data export")
    print("  ✓ Error handling")
    print("\nThe agent is ready for integration with the PA system.")


if __name__ == "__main__":
    test_patient_data_agent()
