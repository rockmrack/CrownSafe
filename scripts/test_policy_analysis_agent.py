import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.policy_analysis_agent.agent_logic import PolicyAnalysisAgentLogic

logging.basicConfig(level=logging.INFO)

def test_policy_analysis_agent():
    print("--- Testing PolicyAnalysisAgent Logic (MOCK_POLICY Mode) ---")
    
    logic = PolicyAnalysisAgentLogic(agent_id="test_policy_agent_01")

    print("\n1. Testing policy retrieval for a covered drug...")
    result = logic.get_policy_for_drug("Empagliflozin")
    assert result['status'] == 'success'
    assert result['policy']['status'] == 'Covered with Prior Authorization'
    print("   -> SUCCESS: Correctly retrieved policy for Empagliflozin.")

    print("\n2. Testing policy retrieval for a non-formulary drug...")
    result = logic.get_policy_for_drug("Sotagliflozin")
    assert result['status'] == 'success'
    assert result['policy']['status'] == 'Not on Formulary'
    print("   -> SUCCESS: Correctly retrieved policy for Sotagliflozin.")

    print("\n3. Testing a patient who MEETS ALL criteria...")
    patient_meets_criteria = {
        "diagnoses_icd10": ["I50", "E11.9"], # Has Heart Failure and Diabetes
        "medication_history": ["Metformin", "Lisinopril"], # Has tried Metformin
        "labs": {"LVEF": "40%"} # Has LVEF documented
    }
    result = logic.check_coverage_criteria("Empagliflozin", patient_meets_criteria)
    assert result['status'] == 'success'
    assert result['meets_criteria'] is True
    print("   -> SUCCESS: Correctly identified that the patient meets all criteria.")
    print(f"      Reason: {result['reason']}")

    print("\n4. Testing a patient who FAILS step therapy...")
    patient_fails_step_therapy = {
        "diagnoses_icd10": ["I50"],
        "medication_history": ["Lisinopril"], # Has NOT tried Metformin
        "labs": {"LVEF": "40%"}
    }
    result = logic.check_coverage_criteria("Empagliflozin", patient_fails_step_therapy)
    assert result['status'] == 'success'
    assert result['meets_criteria'] is False
    assert result['unmet_criteria'][0]['id'] == 'CRIT-02'
    print("   -> SUCCESS: Correctly identified failure due to missing step therapy.")
    print(f"      Unmet Criterion: {result['unmet_criteria'][0]['description']}")

    print("\n5. Testing a patient who FAILS diagnosis criteria...")
    patient_fails_diagnosis = {
        "diagnoses_icd10": ["R07.9"], # Chest pain, not HF or Diabetes
        "medication_history": ["Metformin"],
        "labs": {"LVEF": "55%"}
    }
    result = logic.check_coverage_criteria("Empagliflozin", patient_fails_diagnosis)
    assert result['status'] == 'success'
    assert result['meets_criteria'] is False
    assert result['unmet_criteria'][0]['id'] == 'CRIT-01'
    print("   -> SUCCESS: Correctly identified failure due to missing diagnosis.")

    print("\n--- All tests passed successfully! ---")

if __name__ == "__main__":
    test_policy_analysis_agent()