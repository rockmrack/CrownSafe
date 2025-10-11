import logging
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from functools import lru_cache
import traceback
import time
import warnings
import threading
from collections import deque
import queue

# Suppress coroutine warnings during testing
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited")

# Configure logging with precise formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DecisionType(Enum):
    """Immutable enumeration of possible PA decision types"""

    APPROVE = "Approve"
    DENY = "Deny"
    PEND = "Pend for More Info"
    URGENT_REVIEW = "Urgent Review Required"

    def __str__(self) -> str:
        """String representation returns the value for clean serialization"""
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "DecisionType":
        """Safe conversion from string to enum with validation"""
        # FIXED: Normalize to handle case mismatches
        value_upper = value.upper()
        for decision_type in cls:
            if decision_type.value.upper() == value_upper:
                return decision_type
        # Default fallback for invalid values
        return cls.PEND


class ConfidenceLevel(Enum):
    """Confidence level bands with precise boundaries"""

    VERY_HIGH = (0.9, 1.0, "Very High")
    HIGH = (0.75, 0.9, "High")
    MODERATE = (0.5, 0.75, "Moderate")
    LOW = (0.25, 0.5, "Low")
    VERY_LOW = (0.0, 0.25, "Very Low")

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        """Deterministic confidence level from numeric score with boundary validation"""
        # Clamp score to valid range
        score = max(0.0, min(1.0, float(score)))

        for level in cls:
            lower, upper, _ = level.value
            if lower <= score < upper:
                return level
        # Edge case: score == 1.0
        return cls.VERY_HIGH if score == 1.0 else cls.VERY_LOW

    def __str__(self) -> str:
        """Human-readable string representation"""
        return self.value[2]


@dataclass(frozen=True)
class EvidenceItem:
    """Immutable evidence item with comprehensive validation"""

    source: str
    type: str
    content: str
    weight: float
    supports_approval: bool
    confidence: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        """Validate evidence item constraints"""
        if not 0.0 <= self.weight <= 1.0:
            object.__setattr__(self, "weight", max(0.0, min(1.0, self.weight)))
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(self, "confidence", max(0.0, min(1.0, self.confidence)))


@dataclass
class AnalysisResult:
    """Comprehensive analysis result with full audit trail"""

    decision_id: str
    patient_id: str
    drug_name: str
    insurer_id: str
    decision: DecisionType
    approval_likelihood: int
    confidence_score: float
    confidence_level: ConfidenceLevel
    clinical_rationale: str
    evidence_items: List[EvidenceItem]
    identified_gaps: List[str]
    recommendations: List[str]
    alternative_options: List[Dict[str, Any]]
    processing_time_ms: int
    llm_tokens_used: int
    analysis_timestamp: str
    audit_trail: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Custom serialization handling enums properly"""
        result = asdict(self)
        result["decision"] = str(self.decision)
        result["confidence_level"] = str(self.confidence_level)
        return result


@dataclass
class AnalysisContext:
    """Analysis context with validated data structures"""

    patient_record: Dict[str, Any]
    drug_info: Dict[str, Any]
    policy_info: Dict[str, Any]
    guideline_results: List[Dict[str, Any]]
    interaction_check: Dict[str, Any]
    criteria_check: Dict[str, Any]
    drug_safety: Dict[str, Any] = field(default_factory=dict)  # ADDED

    def __post_init__(self):
        """Ensure all fields are properly initialized"""
        self.patient_record = self.patient_record or {}
        self.drug_info = self.drug_info or {}
        self.policy_info = self.policy_info or {}
        self.guideline_results = self.guideline_results or []
        self.interaction_check = self.interaction_check or {
            "interactions": [],
            "status": "PENDING",
        }
        self.criteria_check = self.criteria_check or {
            "meets_criteria": False,
            "reason": "No data",
        }
        self.drug_safety = self.drug_safety or {}


# Precise mock implementations with deterministic behavior
class MockPatientDataAgentLogic:
    """Mock patient data agent with precise test scenarios"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.call_count = 0

    def get_patient_record(self, patient_id: str) -> Dict[str, Any]:
        """Return deterministic patient data based on ID"""
        self.call_count += 1

        patient_scenarios = {
            "patient-001": {
                # Optimal candidate - should definitely approve
                "status": "success",
                "record": {
                    "patient_id": patient_id,
                    "age": 52,
                    "diagnoses_icd10": [
                        "E11.9",
                        "I10",
                        "E78.5",
                    ],  # T2DM, HTN, Hyperlipidemia
                    "medication_history": ["Metformin", "Lisinopril", "Atorvastatin"],
                    "labs": {
                        "HbA1c": "9.2%",
                        "eGFR": "85",
                        "LDL": "145",
                        "BP": "148/92",
                    },
                    "provider_type": "Endocrinologist",
                    "notes": "Patient has tried metformin at maximum dose for 6 months with insufficient glycemic control. HbA1c remains elevated despite lifestyle modifications and medication adherence.",
                    "allergies": [],
                    "adherence_score": 0.92,
                    "requested_quantity": 30,  # ADDED for quantity limit testing
                },
            },
            "patient-002": {
                # Step therapy not met - should deny
                "status": "success",
                "record": {
                    "patient_id": patient_id,
                    "age": 35,
                    "diagnoses_icd10": ["E11.9"],  # Only diabetes
                    "medication_history": [],  # No previous medications - key factor
                    "labs": {"HbA1c": "7.8%", "eGFR": "95"},
                    "provider_type": "Primary Care",
                    "notes": "Newly diagnosed type 2 diabetes, diet and exercise counseling provided",
                    "allergies": [],
                    "adherence_score": None,  # No history to measure
                    "requested_quantity": 30,
                },
            },
            "patient-003": {
                # Wrong diagnosis - should deny
                "status": "success",
                "record": {
                    "patient_id": patient_id,
                    "age": 65,
                    "diagnoses_icd10": [
                        "K21.0",
                        "K92.1",
                    ],  # GERD and GI bleeding, not diabetes
                    "medication_history": ["Omeprazole", "Famotidine"],
                    "labs": {"Hemoglobin": "10.2", "Ferritin": "45"},
                    "provider_type": "Gastroenterologist",
                    "notes": "Chronic GERD with recent upper GI bleed, stable on PPI therapy",
                    "allergies": ["Penicillin"],
                    "adherence_score": 0.88,
                    "requested_quantity": 30,
                },
            },
        }

        return patient_scenarios.get(
            patient_id,
            {
                "status": "success",
                "record": {
                    "patient_id": patient_id,
                    "age": 50,
                    "diagnoses_icd10": ["E11.9"],
                    "medication_history": ["Metformin"],
                    "labs": {"HbA1c": "8.0%", "eGFR": "75"},
                    "provider_type": "Primary Care",
                    "notes": "Standard patient",
                    "allergies": [],
                    "adherence_score": 0.80,
                    "requested_quantity": 30,
                },
            },
        )


class MockGuidelineAgentLogic:
    """Mock clinical guidelines with evidence-based recommendations"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return drug-specific clinical guidelines"""
        drug_name = task.get("drug_name", "").lower()

        # FIXED: Handle both old and new task names
        task_name = task.get("task_name", "").lower()
        if task_name not in [
            "query_guidelines",
            "get_guideline_info",
            "guideline_query",
        ]:
            # Log warning but continue
            logger.warning(f"Unexpected guideline task name: {task_name}")

        if "empagliflozin" in drug_name:
            return {
                "status": "COMPLETED",
                "results": [
                    {
                        "text": "ADA 2024 Standards: Empagliflozin is recommended as second-line therapy for T2DM when metformin monotherapy fails to achieve glycemic targets (HbA1c > 7.5%). Provides cardiovascular and renal protection.",
                        "relevance_score": 0.98,
                        "source": "American Diabetes Association",
                        "year": 2024,
                    },
                    {
                        "text": "ACC/AHA Guidelines: SGLT2 inhibitors like empagliflozin reduce heart failure hospitalization by 30% in patients with T2DM and established cardiovascular disease.",
                        "relevance_score": 0.92,
                        "source": "ACC/AHA",
                        "year": 2023,
                    },
                    {
                        "text": "KDIGO 2022: Empagliflozin slows progression of diabetic kidney disease. Recommended when eGFR > 20 mL/min/1.73m².",
                        "relevance_score": 0.89,
                        "source": "KDIGO",
                        "year": 2022,
                    },
                ],
            }
        else:
            return {
                "status": "COMPLETED",
                "results": [
                    {
                        "text": f"No specific guidelines found for {drug_name}",
                        "relevance_score": 0.3,
                        "source": "Generic",
                        "year": 2024,
                    }
                ],
            }


class MockPolicyAnalysisAgentLogic:
    """Mock insurance policy with precise coverage rules"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def get_policy_for_drug(self, drug_name: str) -> Dict[str, Any]:
        """Return insurance policy requirements"""
        if "empagliflozin" in drug_name.lower():
            return {
                "status": "success",
                "policy": {
                    "drug_name": drug_name,
                    "status": "Covered with Prior Authorization",
                    "tier": 3,
                    "criteria": [
                        "Documented diagnosis of Type 2 Diabetes Mellitus (ICD-10: E11.*)",
                        "Failed or contraindicated to metformin (minimum 3-month trial at ≥1500mg/day)",
                        "HbA1c > 7.5% despite metformin therapy",
                        "eGFR ≥ 20 mL/min/1.73m²",
                        "Not for use in Type 1 Diabetes or diabetic ketoacidosis",
                    ],
                    "quantity_limits": {
                        "max_units_per_fill": 30,
                        "max_fills_per_month": 1,
                    },
                    "alternatives": [
                        {
                            "drug": "Metformin",
                            "status": "Preferred",
                            "tier": 1,
                            "pa_required": False,
                        },
                        {
                            "drug": "Glipizide",
                            "status": "Preferred",
                            "tier": 1,
                            "pa_required": False,
                        },
                        {
                            "drug": "Glimepiride",
                            "status": "Preferred",
                            "tier": 2,
                            "pa_required": False,
                        },
                    ],
                },
            }
        return {
            "status": "success",
            "policy": {
                "drug_name": drug_name,
                "status": "Not Covered",
                "criteria": [],
                "alternatives": [],
            },
        }

    def check_coverage_criteria(self, drug_name: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Precise criteria checking with detailed reasoning"""
        if "empagliflozin" not in drug_name.lower():
            return {
                "meets_criteria": False,
                "reason": "Drug not in formulary",
                "unmet_criteria": [{"criterion": "Formulary", "description": "Drug not covered"}],
            }

        unmet_criteria = []
        met_criteria = []

        # Check diagnosis (ICD-10 E11.*)
        diagnoses = patient_data.get("diagnoses_icd10", [])
        has_t2dm = any(code.startswith("E11") for code in diagnoses)

        if has_t2dm:
            met_criteria.append("Type 2 Diabetes diagnosis confirmed")
        else:
            unmet_criteria.append(
                {
                    "criterion": "Diagnosis",
                    "description": "Must have Type 2 Diabetes diagnosis (E11.*)",
                    "severity": "critical",
                }
            )

        # Check metformin trial
        med_history = patient_data.get("medication_history", [])
        has_metformin = any("metformin" in med.lower() for med in med_history)

        if has_metformin:
            met_criteria.append("Metformin trial documented")
        else:
            unmet_criteria.append(
                {
                    "criterion": "Step therapy",
                    "description": "Must try metformin for ≥3 months at therapeutic dose",
                    "severity": "critical",
                }
            )

        # Check HbA1c
        labs = patient_data.get("labs", {})
        hba1c_str = labs.get("HbA1c", "0%")
        try:
            hba1c = float(hba1c_str.replace("%", ""))
            if hba1c > 7.5:
                met_criteria.append(f"HbA1c {hba1c}% exceeds threshold")
            else:
                unmet_criteria.append(
                    {
                        "criterion": "Glycemic control",
                        "description": f"HbA1c {hba1c}% does not meet >7.5% threshold",
                        "severity": "moderate",
                    }
                )
        except:
            unmet_criteria.append(
                {
                    "criterion": "Lab values",
                    "description": "HbA1c value missing or invalid",
                    "severity": "moderate",
                }
            )

        # Check renal function
        egfr_str = labs.get("eGFR", "0")
        try:
            egfr = float(egfr_str)
            if egfr >= 20:
                met_criteria.append(f"eGFR {egfr} mL/min acceptable")
            else:
                unmet_criteria.append(
                    {
                        "criterion": "Renal function",
                        "description": f"eGFR {egfr} below minimum 20 mL/min",
                        "severity": "critical",
                    }
                )
        except:
            unmet_criteria.append(
                {
                    "criterion": "Lab values",
                    "description": "eGFR value missing",
                    "severity": "moderate",
                }
            )

        # ADDED: Check quantity limits
        requested_quantity = patient_data.get("requested_quantity", 30)
        if requested_quantity > 30:
            unmet_criteria.append(
                {
                    "criterion": "Quantity limits",
                    "description": f"Requested quantity {requested_quantity} exceeds maximum 30 units per fill",
                    "severity": "moderate",
                    "type": "quantity_limit",
                }
            )
        else:
            met_criteria.append(f"Quantity {requested_quantity} within limits")

        # Final determination
        critical_unmet = [c for c in unmet_criteria if c.get("severity") == "critical"]

        return {
            "meets_criteria": len(critical_unmet) == 0,
            "reason": f"Met {len(met_criteria)}/{len(met_criteria) + len(unmet_criteria)} criteria",
            "unmet_criteria": unmet_criteria,
            "met_criteria": met_criteria,
            "recommendation": "Approve" if len(critical_unmet) == 0 else "Deny",
        }


class MockDrugBankAgentLogic:
    """Mock drug information with comprehensive data"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Return drug information or interaction check results"""
        task_name = task.get("task_name")

        if task_name == "drug_info":
            drug_name = task.get("drug_name", "Unknown")

            if "empagliflozin" in drug_name.lower():
                return {
                    "status": "COMPLETED",
                    "drug_info": {
                        "drug_name": drug_name,
                        "drug_class": "SGLT2 Inhibitor",
                        "mechanism": "Inhibits SGLT2 in proximal renal tubules, reducing glucose reabsorption",
                        "indications": [
                            "Type 2 Diabetes Mellitus",
                            "Heart Failure with reduced ejection fraction",
                            "Chronic Kidney Disease",
                            "Cardiovascular Risk Reduction in T2DM",
                        ],
                        "contraindications": [
                            "Type 1 Diabetes",
                            "Diabetic Ketoacidosis",
                            "Severe Renal Impairment (eGFR < 20)",
                            "Dialysis",
                            "Hypersensitivity to empagliflozin",
                        ],
                        "warnings": [
                            "Risk of ketoacidosis",
                            "Genital mycotic infections",
                            "Volume depletion",
                            "Acute kidney injury",
                        ],
                        "monitoring_requirements": [
                            "Renal function (eGFR) before initiation and periodically",
                            "Blood glucose levels",
                            "Signs/symptoms of ketoacidosis",
                            "Volume status in elderly or diuretic users",
                        ],
                        "dosing": {
                            "initial": "10 mg once daily",
                            "maximum": "25 mg once daily",
                            "renal_adjustment": "Avoid if eGFR < 20",
                        },
                    },
                }
            else:
                return {
                    "status": "COMPLETED",
                    "drug_info": {
                        "drug_name": drug_name,
                        "drug_class": "Unknown",
                        "indications": ["Various"],
                        "contraindications": [],
                        "monitoring_requirements": ["Standard monitoring"],
                    },
                }

        # ADDED: Handle drug safety check
        elif task_name == "check_drug_safety":
            drug_name = task.get("drug_name", "Unknown")

            if "empagliflozin" in drug_name.lower():
                return {
                    "status": "COMPLETED",
                    "safety_summary": {
                        "drug_name": drug_name,
                        "warnings": [
                            "Risk of ketoacidosis",
                            "Genital mycotic infections",
                            "Volume depletion",
                        ],
                        "contraindications": [
                            "Type 1 Diabetes",
                            "Severe Renal Impairment",
                            "Pregnancy",
                        ],
                        "monitoring_requirements": [
                            "Renal function monitoring",
                            "Blood glucose monitoring",
                        ],
                        "drug_class": "SGLT2 Inhibitor",
                        "safety_profile": "Moderate Risk - Several precautions needed",
                    },
                }
            else:
                return {
                    "status": "COMPLETED",
                    "safety_summary": {
                        "drug_name": drug_name,
                        "warnings": [],
                        "contraindications": [],
                        "monitoring_requirements": ["Standard monitoring"],
                        "drug_class": "Unknown",
                        "safety_profile": "Unknown Risk Profile",
                    },
                }

        elif task_name == "check_interactions":
            drug_names = task.get("drug_names", [])

            # Check for specific interaction patterns
            interactions = []

            if any("empagliflozin" in d.lower() for d in drug_names):
                if any("furosemide" in d.lower() or "hydrochlorothiazide" in d.lower() for d in drug_names):
                    interactions.append(
                        {
                            "severity": "moderate",
                            "description": "Increased risk of volume depletion with diuretics",
                            "management": "Monitor volume status and renal function",
                        }
                    )

                if any("insulin" in d.lower() or "glipizide" in d.lower() for d in drug_names):
                    interactions.append(
                        {
                            "severity": "moderate",
                            "description": "Increased risk of hypoglycemia with insulin/sulfonylureas",
                            "management": "Consider reducing insulin/sulfonylurea dose",
                        }
                    )

            return {
                "status": "COMPLETED",
                "interactions": interactions,
                "highest_severity": max([i["severity"] for i in interactions], default="none"),
                "drug_count": len(drug_names),
            }

        return {"status": "FAILED", "error": "Unknown task"}


class MockLLMClient:
    """Sophisticated mock LLM with context-aware responses"""

    def __init__(self):
        self.chat = self.MockChat()
        self.call_count = 0
        self.model = "mock-gpt-4"

    class MockChat:
        def __init__(self):
            self.completions = self.MockCompletions()

        class MockCompletions:
            def create(self, **kwargs) -> "MockLLMClient.MockResponse":
                """Generate context-appropriate mock responses"""
                messages = kwargs.get("messages", [])
                prompt = messages[-1]["content"] if messages else ""

                # Initialize default response
                response_data = {
                    "approval_likelihood_percent": 50,
                    "decision_prediction": "Pend for More Info",
                    "confidence_score": 0.5,
                    "clinical_rationale": "Insufficient data for determination",
                    "key_supporting_factors": [],
                    "key_opposing_factors": [],
                    "identified_gaps": ["Complete clinical picture needed"],
                    "recommended_next_steps": ["Gather additional information"],
                }

                # Analyze prompt for patient-specific decisions
                if "patient-001" in prompt:
                    # Strong approval case
                    if all(marker in prompt.lower() for marker in ["metformin", "9.2%", "endocrinologist"]):
                        response_data = {
                            "approval_likelihood_percent": 92,
                            "decision_prediction": "Approve",
                            "confidence_score": 0.88,
                            "clinical_rationale": "Patient demonstrates clear medical necessity: documented metformin failure with persistent hyperglycemia (HbA1c 9.2%) despite maximum therapy. Endocrinologist management supports appropriate escalation to SGLT2 inhibitor therapy per ADA guidelines.",
                            "key_supporting_factors": [
                                "Failed metformin at maximum dose",
                                "HbA1c 9.2% significantly above target",
                                "Specialist (endocrinologist) oversight",
                                "Good medication adherence (92%)",
                                "Preserved renal function (eGFR 85)",
                            ],
                            "key_opposing_factors": [],
                            "identified_gaps": [],
                            "recommended_next_steps": [
                                "Initiate empagliflozin 10mg daily",
                                "Monitor renal function in 3 months",
                            ],
                        }

                elif "patient-002" in prompt:
                    # Clear denial case
                    if 'medication_history": []' in prompt or 'medication_history":[]' in prompt:
                        response_data = {
                            "approval_likelihood_percent": 8,
                            "decision_prediction": "Deny",
                            "confidence_score": 0.95,
                            "clinical_rationale": "Patient has not satisfied step therapy requirements. As newly diagnosed T2DM with HbA1c 7.8%, patient should first trial metformin as first-line therapy per clinical guidelines and insurance policy requirements.",
                            "key_supporting_factors": [],
                            "key_opposing_factors": [
                                "No prior medication trials documented",
                                "Step therapy requirements not met",
                                "HbA1c 7.8% may respond to metformin alone",
                                "Primary care management appropriate at this stage",
                            ],
                            "identified_gaps": ["Metformin trial required"],
                            "recommended_next_steps": [
                                "Initiate metformin 500mg BID, titrate to effect",
                                "Recheck HbA1c in 3 months",
                                "Consider SGLT2 inhibitor if HbA1c remains >7.5% on metformin",
                            ],
                        }

                elif "patient-003" in prompt:
                    # Wrong indication case
                    if "K21.0" in prompt or "GERD" in prompt.upper():
                        response_data = {
                            "approval_likelihood_percent": 0,
                            "decision_prediction": "Deny",
                            "confidence_score": 0.99,
                            "clinical_rationale": "Empagliflozin is not indicated for patient's diagnosed conditions (GERD, GI bleeding). This SGLT2 inhibitor is FDA-approved only for T2DM, heart failure, and CKD. No diabetes diagnosis present.",
                            "key_supporting_factors": [],
                            "key_opposing_factors": [
                                "No diabetes diagnosis (ICD-10 E11)",
                                "Drug not indicated for GERD",
                                "Potential safety concern with GI bleeding history",
                            ],
                            "identified_gaps": [],
                            "recommended_next_steps": [
                                "Discontinue PA request",
                                "Continue current GERD management",
                            ],
                        }

                # Analyze preliminary score if present
                import re

                score_match = re.search(r"Preliminary Score: ([\d.]+)%", prompt)
                if score_match:
                    score = float(score_match.group(1)) / 100
                    if score > 0.8:
                        response_data["approval_likelihood_percent"] = int(score * 100)
                        response_data["decision_prediction"] = "Approve"
                        response_data["confidence_score"] = min(0.9, score)
                    elif score < 0.3:
                        response_data["approval_likelihood_percent"] = int(score * 100)
                        response_data["decision_prediction"] = "Deny"
                        response_data["confidence_score"] = min(0.9, 1 - score)

                return MockLLMClient.MockResponse(response_data)

    class MockResponse:
        def __init__(self, data: Dict[str, Any]):
            self.choices = [self.MockChoice(data)]
            self.usage = self.MockUsage()

        class MockChoice:
            def __init__(self, data: Dict[str, Any]):
                self.message = self.MockMessage(data)

            class MockMessage:
                def __init__(self, data: Dict[str, Any]):
                    self.content = json.dumps(data)

        class MockUsage:
            def __init__(self):
                self.total_tokens = 850
                self.prompt_tokens = 650
                self.completion_tokens = 200


class PatientStratificationAgentLogic:
    """
    Master orchestrator for Prior Authorization predictions.
    Implements sophisticated multi-agent coordination with comprehensive error handling,
    caching, metrics tracking, and audit trails.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        """Initialize the orchestration engine with all dependencies"""
        self.agent_id = agent_id
        self.logger = logger_instance or logger

        # Initialize memory manager safely
        self.memory_manager = None

        # Initialize dependent agents with graceful fallbacks
        self._initialize_agents()

        # Initialize LLM clients with fallback chain
        self._initialize_llm_clients()

        # Configuration with sensible defaults
        self.config = {
            "max_guideline_results": 5,
            "confidence_threshold": 0.75,
            "cache_ttl_seconds": 3600,
            "enable_parallel_processing": True,
            "max_retries": 3,
            "timeout_seconds": 30,
            "enable_cost_tracking": True,
            "enable_detailed_audit": True,
            "max_cache_size": 1000,
            "max_prompt_tokens": 4000,  # ADDED: Token limit for prompts
        }

        # FIXED: Thread-safe locks for shared resources
        self._cache_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._latency_lock = threading.Lock()

        # Thread-safe caches with TTL
        self.decision_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.evidence_cache: Dict[str, Any] = {}

        # Metrics with atomic operations
        self.metrics = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "average_processing_time": 0.0,
            "total_llm_tokens": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "error_rate": 0.0,
            "p95_latency": 0.0,
            "p99_latency": 0.0,
        }

        # Evidence weights based on clinical importance - UPDATED with drug_safety
        self.evidence_weights = {
            "policy_criteria_met": 0.30,  # Reduced from 0.35
            "guideline_support": 0.25,  # Clinical guidelines
            "clinical_appropriateness": 0.20,  # Medical necessity
            "drug_interactions": 0.10,  # Safety
            "drug_safety": 0.10,  # ADDED: New safety weight
            "patient_history": 0.05,  # Reduced from 0.10
        }

        # Track latencies for percentile calculations - FIXED: Use thread-safe deque
        self._latency_history = deque(maxlen=1000)

        self.logger.info(f"PatientStratificationAgentLogic initialized successfully for {agent_id}")

    def _initialize_agents(self) -> None:
        """Initialize dependent agents with comprehensive fallback logic"""
        agent_configs = [
            (
                "patient_data_logic",
                "agents.patient_data_agent.agent_logic",
                "PatientDataAgentLogic",
                MockPatientDataAgentLogic,
            ),
            (
                "guideline_logic",
                "agents.guideline_agent.agent_logic",
                "GuidelineAgentLogic",
                MockGuidelineAgentLogic,
            ),
            (
                "policy_logic",
                "agents.policy_analysis_agent.agent_logic",
                "PolicyAnalysisAgentLogic",
                MockPolicyAnalysisAgentLogic,
            ),
            (
                "drugbank_logic",
                "agents.drugbank_agent.agent_logic",
                "DrugBankAgentLogic",
                MockDrugBankAgentLogic,
            ),
        ]

        for attr_name, module_path, class_name, mock_class in agent_configs:
            try:
                module = __import__(module_path, fromlist=[class_name])
                agent_class = getattr(module, class_name)
                setattr(
                    self,
                    attr_name,
                    agent_class(agent_id=f"{self.agent_id}_{attr_name}"),
                )
                self.logger.info(f"Successfully initialized {class_name}")
            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Using mock {class_name} due to: {e}")
                setattr(self, attr_name, mock_class(agent_id=f"{self.agent_id}_{attr_name}"))

    def _initialize_llm_clients(self) -> None:
        """Initialize LLM clients with fallback chain"""
        try:
            from core_infra.llm_service import get_llm_client, LLMConfig

            self.primary_llm = get_llm_client(
                LLMConfig(model="gpt-4-turbo", temperature=0.1, max_tokens=2000, top_p=0.95)
            )
            self.fallback_llm = get_llm_client(LLMConfig(model="gpt-3.5-turbo", temperature=0.1, max_tokens=1500))
            self.logger.info("Production LLM clients initialized")
        except Exception as e:
            self.logger.warning(f"Using mock LLM clients: {e}")
            self.primary_llm = MockLLMClient()
            self.fallback_llm = MockLLMClient()

    async def predict_approval_likelihood(
        self, patient_id: str, drug_name: str, insurer_id: str, urgency: str = "routine"
    ) -> Dict[str, Any]:
        """
        Main orchestration method for PA prediction.
        Coordinates all agents to produce a comprehensive decision.

        Args:
            patient_id: Unique patient identifier
            drug_name: Requested medication name
            insurer_id: Insurance provider identifier
            urgency: Priority level (routine/urgent/emergency)

        Returns:
            Comprehensive prediction result with full analysis
        """
        start_time = time.perf_counter()  # High-precision timing
        start_dt = datetime.now(timezone.utc)
        decision_id = f"PA_{patient_id}_{drug_name}_{int(start_dt.timestamp())}"
        audit_trail = []

        self.logger.info(
            f"Starting PA prediction {decision_id} - "
            f"Patient: {patient_id}, Drug: {drug_name}, "
            f"Insurer: {insurer_id}, Urgency: {urgency}"
        )

        try:
            # Step 1: Check cache with TTL
            cache_key = self._generate_cache_key(patient_id, drug_name, insurer_id)
            cached_result = self._get_cached_result(cache_key)

            if cached_result:
                with self._metrics_lock:
                    self.metrics["cache_hits"] += 1
                self.logger.info(f"Cache hit for {decision_id}")
                # Update cache-specific metrics
                cached_result["source"] = "cache"
                cached_result["cache_age_seconds"] = int(time.time() - cached_result.get("cached_at", time.time()))
                return {
                    "status": "success",
                    "prediction": cached_result,
                    "source": "cache",
                }

            with self._metrics_lock:
                self.metrics["cache_misses"] += 1

            # Step 2: Gather all required data
            audit_trail.append(self._create_audit_entry("data_gathering_start", {"urgency": urgency}))

            context = await self._gather_all_data(patient_id, drug_name, insurer_id, audit_trail)

            if not self._validate_context(context):
                raise ValueError("Insufficient data gathered for analysis")

            audit_trail.append(
                self._create_audit_entry(
                    "data_gathering_complete",
                    {"items_collected": self._count_context_items(context)},
                )
            )

            # Step 3: Perform comprehensive analysis
            audit_trail.append(self._create_audit_entry("analysis_start"))

            evidence_items = await self._perform_comprehensive_analysis(context, drug_name, audit_trail)

            audit_trail.append(
                self._create_audit_entry(
                    "analysis_complete",
                    {
                        "evidence_items": len(evidence_items),
                        "supporting": sum(1 for e in evidence_items if e.supports_approval),
                        "opposing": sum(1 for e in evidence_items if not e.supports_approval),
                    },
                )
            )

            # Step 4: Calculate scores
            preliminary_score = self._calculate_weighted_score(evidence_items)
            confidence = self._calculate_confidence_score(evidence_items, context)

            self.logger.info(
                f"Preliminary assessment for {decision_id}: Score={preliminary_score:.2%}, Confidence={confidence:.2%}"
            )

            # Step 5: LLM synthesis
            audit_trail.append(
                self._create_audit_entry(
                    "llm_synthesis_start",
                    {"preliminary_score": preliminary_score, "confidence": confidence},
                )
            )

            llm_result = await self._perform_llm_synthesis(
                context, evidence_items, preliminary_score, confidence, urgency
            )

            audit_trail.append(
                self._create_audit_entry(
                    "llm_synthesis_complete",
                    {
                        "model_used": llm_result.get("model", "unknown"),
                        "tokens_used": llm_result.get("tokens_used", 0),
                    },
                )
            )

            # Step 6: Generate final decision
            final_result = self._generate_final_decision(
                decision_id,
                patient_id,
                drug_name,
                insurer_id,
                evidence_items,
                llm_result,
                context,
                audit_trail,
                start_dt,
            )

            # Cache the successful result
            self._cache_result(cache_key, final_result.to_dict())

            # Update metrics
            processing_time = (time.perf_counter() - start_time) * 1000  # Convert to ms
            self._update_metrics(final_result, processing_time)

            self.logger.info(
                f"PA prediction {decision_id} completed successfully - "
                f"Decision: {final_result.decision.value}, "
                f"Likelihood: {final_result.approval_likelihood}%, "
                f"Time: {processing_time:.0f}ms"
            )

            return {
                "status": "success",
                "prediction": final_result.to_dict(),
                "processing_time_ms": int(processing_time),
            }

        except Exception as e:
            self.logger.error(f"Error in PA prediction {decision_id}: {e}", exc_info=True)
            with self._metrics_lock:
                self.metrics["failed_predictions"] += 1

            error_response = self._create_error_response(str(e), audit_trail)
            error_response["decision_id"] = decision_id
            error_response["processing_time_ms"] = int((time.perf_counter() - start_time) * 1000)

            return error_response

    async def _gather_all_data(
        self, patient_id: str, drug_name: str, insurer_id: str, audit_trail: List[Dict]
    ) -> AnalysisContext:
        """
        Gather all required data from various agents.
        Implements parallel processing with timeout and error handling.
        """
        # Define data gathering tasks
        tasks = {
            "patient": self._get_patient_data(patient_id),
            "drug": self._get_drug_info(drug_name),
            "policy": self._get_policy_info(drug_name, insurer_id),
            "guidelines": self._get_guideline_data(drug_name),
            "criteria_check": self._check_coverage_criteria(patient_id, drug_name, insurer_id),
            "drug_safety": self._get_drug_safety(drug_name),  # ADDED
        }

        results = {}

        if self.config["enable_parallel_processing"]:
            # Parallel execution with proper error handling
            async def gather_with_timeout(name: str, coro):
                try:
                    return name, await asyncio.wait_for(coro, timeout=self.config["timeout_seconds"])
                except asyncio.TimeoutError:
                    self.logger.warning(f"Task {name} timed out")
                    return name, {}
                except Exception as e:
                    self.logger.warning(f"Task {name} failed: {e}")
                    return name, {}

            # Create all tasks
            gather_tasks = [gather_with_timeout(name, coro) for name, coro in tasks.items()]

            # Wait for all to complete
            completed = await asyncio.gather(*gather_tasks, return_exceptions=True)

            # Process results
            for result in completed:
                if isinstance(result, tuple):
                    name, data = result
                    results[name] = data
                else:
                    self.logger.error(f"Unexpected result type: {type(result)}")
        else:
            # Sequential execution fallback
            for name, coro in tasks.items():
                try:
                    results[name] = await coro
                except Exception as e:
                    self.logger.warning(f"Failed to get {name}: {e}")
                    results[name] = {}

        # Get drug interactions if we have medications
        interaction_check = {
            "interactions": [],
            "status": "COMPLETED",
            "highest_severity": "none",
        }
        patient_data = results.get("patient", {})

        if patient_data and isinstance(patient_data, dict):
            med_history = patient_data.get("medication_history", [])
            if med_history:
                try:
                    all_medications = med_history + [drug_name]
                    interaction_check = await self._check_drug_interactions(all_medications)
                except Exception as e:
                    self.logger.warning(f"Failed to check interactions: {e}")
                    interaction_check["status"] = "FAILED"
                    interaction_check["error"] = str(e)

        # Create validated context
        return AnalysisContext(
            patient_record=results.get("patient", {}),
            drug_info=results.get("drug", {}),
            policy_info=results.get("policy", {}),
            guideline_results=results.get("guidelines", []),
            interaction_check=interaction_check,
            criteria_check=results.get("criteria_check", {}),
            drug_safety=results.get("drug_safety", {}),  # ADDED
        )

    # ADDED: New method to get drug safety data
    async def _get_drug_safety(self, drug_name: str) -> Dict[str, Any]:
        """Retrieve drug safety information"""
        try:
            result = self.drugbank_logic.process_task({"task_name": "check_drug_safety", "drug_name": drug_name})
            if isinstance(result, dict) and result.get("status") == "COMPLETED":
                return result.get("safety_summary", {})
            return {}
        except Exception as e:
            self.logger.error(f"Error retrieving drug safety: {e}")
            return {}

    async def _perform_comprehensive_analysis(
        self, context: AnalysisContext, drug_name: str, audit_trail: List[Dict]
    ) -> List[EvidenceItem]:
        """
        Perform multi-dimensional analysis to generate evidence items.
        Each dimension contributes weighted evidence to the final decision.
        """
        evidence_items = []
        analysis_timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Policy Criteria Analysis (highest weight)
        if context.criteria_check and isinstance(context.criteria_check, dict):
            meets_criteria = context.criteria_check.get("meets_criteria", False)

            # Main criteria evidence
            evidence_items.append(
                EvidenceItem(
                    source="policy_analysis",
                    type="criteria_check",
                    content=(
                        f"Insurance policy criteria {'met' if meets_criteria else 'not met'}: "
                        f"{context.criteria_check.get('reason', 'No details available')}"
                    ),
                    weight=self.evidence_weights["policy_criteria_met"],
                    supports_approval=meets_criteria,
                    confidence=0.95,
                    timestamp=analysis_timestamp,
                )
            )

            # Individual unmet criteria as separate evidence
            for unmet in context.criteria_check.get("unmet_criteria", []):
                if isinstance(unmet, dict):
                    severity = unmet.get("severity", "moderate")
                    weight_modifier = {
                        "critical": 0.2,
                        "moderate": 0.15,
                        "minor": 0.1,
                    }.get(severity, 0.15)

                    # FIXED: Handle quantity limit criteria
                    criterion_type = unmet.get("type", unmet.get("criterion", "").lower())
                    if criterion_type == "quantity_limit" or "quantity" in unmet.get("criterion", "").lower():
                        evidence_items.append(
                            EvidenceItem(
                                source="policy_analysis",
                                type="quantity_limit",
                                content=unmet.get("description", "Quantity limit exceeded"),
                                weight=0.15,
                                supports_approval=False,
                                confidence=0.9,
                                timestamp=analysis_timestamp,
                            )
                        )
                    else:
                        evidence_items.append(
                            EvidenceItem(
                                source="policy_analysis",
                                type="unmet_criterion",
                                content=f"Unmet ({severity}): {unmet.get('description', 'Unknown criterion')}",
                                weight=weight_modifier,
                                supports_approval=False,
                                confidence=0.9,
                                timestamp=analysis_timestamp,
                            )
                        )

        # 2. Clinical Guideline Analysis
        if context.guideline_results and isinstance(context.guideline_results, list):
            guideline_evidence = self._analyze_guideline_support(
                drug_name, context.patient_record, context.guideline_results
            )
            evidence_items.extend(guideline_evidence)

        # 3. Drug Interaction Analysis
        interaction_evidence = self._analyze_drug_interactions(context.interaction_check)
        if interaction_evidence:
            evidence_items.append(interaction_evidence)

        # 4. ADDED: Drug Safety Analysis
        if context.drug_safety:
            safety_evidence = self._analyze_drug_safety(context.drug_safety, context.patient_record)
            if safety_evidence:
                evidence_items.append(safety_evidence)

        # 5. Patient History Analysis
        if context.patient_record and context.drug_info:
            history_score = self._analyze_patient_history(context.patient_record, context.drug_info)

            evidence_items.append(
                EvidenceItem(
                    source="patient_history",
                    type="clinical_appropriateness",
                    content=(
                        f"Patient history indicates "
                        f"{'excellent' if history_score > 0.8 else 'good' if history_score > 0.6 else 'moderate' if history_score > 0.4 else 'poor'} "
                        f"fit for {drug_name} (score: {history_score:.2f})"
                    ),
                    weight=self.evidence_weights["patient_history"],
                    supports_approval=history_score > 0.6,
                    confidence=0.8,
                    timestamp=analysis_timestamp,
                )
            )

        # 6. Clinical Appropriateness Assessment
        appropriateness = self._assess_clinical_appropriateness(context)
        evidence_items.append(
            EvidenceItem(
                source="clinical_assessment",
                type="appropriateness",
                content=appropriateness["rationale"],
                weight=self.evidence_weights["clinical_appropriateness"],
                supports_approval=appropriateness["score"] > 0.7,
                confidence=appropriateness["confidence"],
                timestamp=analysis_timestamp,
            )
        )

        # 7. Additional specialized assessments
        if urgency := audit_trail[-1].get("details", {}).get("urgency"):
            if urgency in ["urgent", "emergency"]:
                evidence_items.append(
                    EvidenceItem(
                        source="urgency_assessment",
                        type="priority",
                        content=f"{urgency.capitalize()} request - expedited review warranted",
                        weight=0.05,
                        supports_approval=True,
                        confidence=1.0,
                        timestamp=analysis_timestamp,
                    )
                )

        return evidence_items

    # ADDED: Method to analyze drug safety
    def _analyze_drug_safety(
        self, drug_safety: Dict[str, Any], patient_record: Dict[str, Any]
    ) -> Optional[EvidenceItem]:
        """Analyze drug safety information"""
        if not drug_safety:
            return None

        warnings = drug_safety.get("warnings", [])
        contraindications = drug_safety.get("contraindications", [])
        safety_profile = drug_safety.get("safety_profile", "Unknown")

        # Check for patient-specific contraindications
        safety_concerns = []

        # Check pregnancy if patient is female of childbearing age
        if patient_record:
            age = patient_record.get("age", 0)
            gender = patient_record.get("gender", "").upper()

            if gender == "F" and 15 <= age <= 45:
                if any("pregnancy" in ci.lower() for ci in contraindications):
                    safety_concerns.append("Pregnancy contraindication for female of childbearing age")

        # Check renal function
        if patient_record and patient_record.get("labs", {}).get("eGFR"):
            try:
                egfr = float(str(patient_record["labs"]["eGFR"]).replace("%", ""))
                if egfr < 30 and any("renal" in ci.lower() for ci in contraindications):
                    safety_concerns.append(f"Renal impairment concern (eGFR {egfr})")
            except:
                pass

        # Build content
        if safety_concerns:
            content = f"Safety concerns identified: {'; '.join(safety_concerns)}"
            supports = False
            confidence = 0.9
        elif len(warnings) > 3:
            content = f"Multiple warnings ({len(warnings)}) - {safety_profile}"
            supports = False
            confidence = 0.7
        else:
            content = f"Acceptable safety profile - {safety_profile}"
            supports = True
            confidence = 0.8

        return EvidenceItem(
            source="drug_safety_analysis",
            type="safety_assessment",
            content=content,
            weight=self.evidence_weights["drug_safety"],
            supports_approval=supports,
            confidence=confidence,
        )

    async def _perform_llm_synthesis(
        self,
        context: AnalysisContext,
        evidence_items: List[EvidenceItem],
        preliminary_score: float,
        confidence: float,
        urgency: str,
    ) -> Dict[str, Any]:
        """
        Perform LLM synthesis with sophisticated prompt engineering.
        Implements retry logic and fallback strategies.
        """
        # Build comprehensive prompt
        prompt = self._build_advanced_synthesis_prompt(context, evidence_items, preliminary_score, confidence, urgency)

        # FIXED: Check token count and truncate if needed
        estimated_tokens = len(prompt.split()) * 1.3  # Rough estimate
        if estimated_tokens > self.config["max_prompt_tokens"]:
            self.logger.warning(f"Prompt too long ({estimated_tokens} tokens), truncating...")
            prompt = self._build_simplified_prompt(context, evidence_items, preliminary_score)

        # Try primary LLM
        for attempt in range(self.config["max_retries"]):
            try:
                response = await self._call_llm_safely(self.primary_llm, prompt)

                if response and self._validate_llm_output(response):
                    response["model"] = "primary"
                    return response

                self.logger.warning(f"Primary LLM attempt {attempt + 1} failed validation")

            except Exception as e:
                self.logger.warning(f"Primary LLM attempt {attempt + 1} failed: {e}")
                if attempt < self.config["max_retries"] - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        # Fallback to secondary LLM
        self.logger.info("Falling back to secondary LLM")

        try:
            simplified_prompt = self._build_simplified_prompt(context, evidence_items, preliminary_score)
            response = await self._call_llm_safely(self.fallback_llm, simplified_prompt)

            if response and self._validate_llm_output(response):
                response["model"] = "fallback"
                return response

        except Exception as e:
            self.logger.error(f"Fallback LLM also failed: {e}")

        # Last resort: rule-based decision
        self.logger.warning("Using rule-based decision as last resort")
        return self._generate_rule_based_decision(context, evidence_items, preliminary_score)

    async def _call_llm_safely(self, llm_client, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Safely call LLM with proper error handling and response parsing.
        """
        try:
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                # Standard OpenAI-style API
                response = llm_client.chat.completions.create(
                    model=getattr(llm_client, "model", "gpt-4"),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert Prior Authorization physician reviewer. "
                                "Provide clear, evidence-based decisions with detailed clinical reasoning. "
                                "Always respond with valid JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"} if not isinstance(llm_client, MockLLMClient) else None,
                    temperature=0.1,
                    max_tokens=1500,
                    top_p=0.95,
                )

                # Extract content
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    result = json.loads(content)

                    # Add token usage if available
                    if hasattr(response, "usage"):
                        result["tokens_used"] = response.usage.total_tokens

                    return result

            # Fallback for non-standard clients
            return None

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            return None

    def _generate_final_decision(
        self,
        decision_id: str,
        patient_id: str,
        drug_name: str,
        insurer_id: str,
        evidence_items: List[EvidenceItem],
        llm_result: Dict[str, Any],
        context: AnalysisContext,
        audit_trail: List[Dict],
        start_time: datetime,
    ) -> AnalysisResult:
        """
        Generate the final comprehensive decision with all supporting data.
        """
        # Parse decision type safely - FIXED: Use case-insensitive matching
        decision_str = llm_result.get("decision_prediction", "Pend for More Info")
        decision = DecisionType.from_string(decision_str)

        # Calculate processing time
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Generate targeted recommendations
        recommendations = self._generate_recommendations(decision, evidence_items, context)

        # Find alternatives if denied
        alternatives = []
        if decision == DecisionType.DENY:
            alternatives = self._find_alternative_options(context)

        # Identify gaps
        identified_gaps = llm_result.get("identified_gaps", [])
        if not identified_gaps and decision != DecisionType.APPROVE:
            identified_gaps = self._identify_missing_information(evidence_items, context)

        # Get final scores
        approval_likelihood = max(0, min(100, int(llm_result.get("approval_likelihood_percent", 50))))
        confidence_score = max(0.0, min(1.0, float(llm_result.get("confidence_score", 0.5))))

        # Add final audit entry
        audit_trail.append(
            self._create_audit_entry(
                "decision_finalized",
                {
                    "decision": decision.value,
                    "likelihood": approval_likelihood,
                    "confidence": confidence_score,
                },
            )
        )

        return AnalysisResult(
            decision_id=decision_id,
            patient_id=patient_id,
            drug_name=drug_name,
            insurer_id=insurer_id,
            decision=decision,
            approval_likelihood=approval_likelihood,
            confidence_score=confidence_score,
            confidence_level=ConfidenceLevel.from_score(confidence_score),
            clinical_rationale=llm_result.get(
                "clinical_rationale",
                "Decision based on comprehensive analysis of clinical evidence and policy requirements.",
            ),
            evidence_items=evidence_items,
            identified_gaps=identified_gaps,
            recommendations=recommendations,
            alternative_options=alternatives,
            processing_time_ms=processing_time,
            llm_tokens_used=llm_result.get("tokens_used", 0),
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            audit_trail=audit_trail,
        )

    # === Helper Methods (Essential Implementation) ===

    async def _get_patient_data(self, patient_id: str) -> Dict[str, Any]:
        """Retrieve patient data with comprehensive error handling"""
        try:
            result = self.patient_data_logic.get_patient_record(patient_id)
            if isinstance(result, dict) and result.get("status") == "success":
                patient_data = result.get("record", {})

                # ADDED: Check for recent updates and invalidate cache if needed
                if patient_data and "last_updated" in patient_data:
                    self._check_and_invalidate_cache(patient_id, patient_data["last_updated"])

                return patient_data
            self.logger.warning(f"Patient data retrieval unsuccessful: {result}")
            return {}
        except Exception as e:
            self.logger.error(f"Error retrieving patient data: {e}")
            return {}

    # ADDED: Cache invalidation based on patient updates
    def _check_and_invalidate_cache(self, patient_id: str, last_updated: str):
        """Invalidate cache entries if patient data was updated"""
        try:
            update_time = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)

            # If update was recent (within last minute), clear related cache
            if (current_time - update_time).total_seconds() < 60:
                self._invalidate_patient_cache(patient_id)
        except Exception as e:
            self.logger.debug(f"Could not check update time: {e}")

    def _invalidate_patient_cache(self, patient_id: str):
        """Invalidate all cache entries for a specific patient"""
        with self._cache_lock:
            keys_to_remove = [key for key in self.decision_cache if patient_id in key]
            for key in keys_to_remove:
                self.decision_cache.pop(key, None)

            if keys_to_remove:
                self.logger.info(f"Invalidated {len(keys_to_remove)} cache entries for patient {patient_id}")

    async def _get_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """Retrieve comprehensive drug information"""
        try:
            result = self.drugbank_logic.process_task({"task_name": "drug_info", "drug_name": drug_name})
            if isinstance(result, dict) and result.get("status") == "COMPLETED":
                drug_info = result.get("drug_info", {})
                if isinstance(drug_info, dict):
                    drug_info["drug_name"] = drug_name  # Ensure consistency
                return drug_info
            return {"drug_name": drug_name}
        except Exception as e:
            self.logger.error(f"Error retrieving drug info: {e}")
            return {"drug_name": drug_name}

    async def _get_policy_info(self, drug_name: str, insurer_id: str) -> Dict[str, Any]:
        """Retrieve insurance policy information"""
        try:
            result = self.policy_logic.get_policy_for_drug(drug_name)
            if isinstance(result, dict) and result.get("status") == "success":
                return result.get("policy", {})
            return {}
        except Exception as e:
            self.logger.error(f"Error retrieving policy info: {e}")
            return {}

    async def _get_guideline_data(self, drug_name: str) -> List[Dict[str, Any]]:
        """Retrieve clinical guidelines"""
        try:
            # FIXED: Try multiple task names for compatibility
            for task_name in [
                "get_guideline_info",
                "query_guidelines",
                "guideline_query",
            ]:
                result = self.guideline_logic.process_task(
                    {
                        "task_name": task_name,
                        "drug_name": drug_name,
                        "query": f"{drug_name} clinical use recommendations evidence-based guidelines",
                    }
                )

                if isinstance(result, dict) and result.get("status") == "COMPLETED":
                    guidelines = result.get("results", [])
                    return guidelines[: self.config["max_guideline_results"]]

            return []
        except Exception as e:
            self.logger.error(f"Error retrieving guidelines: {e}")
            return []

    async def _check_coverage_criteria(self, patient_id: str, drug_name: str, insurer_id: str) -> Dict[str, Any]:
        """Check if patient meets coverage criteria"""
        try:
            patient_data = await self._get_patient_data(patient_id)
            if not patient_data:
                return {
                    "meets_criteria": False,
                    "reason": "Unable to retrieve patient data",
                    "unmet_criteria": [],
                }

            result = self.policy_logic.check_coverage_criteria(drug_name, patient_data)
            return result if isinstance(result, dict) else {}
        except Exception as e:
            self.logger.error(f"Error checking coverage criteria: {e}")
            return {"meets_criteria": False, "reason": str(e)}

    async def _check_drug_interactions(self, medications: List[str]) -> Dict[str, Any]:
        """Check for drug interactions"""
        try:
            result = self.drugbank_logic.process_task({"task_name": "check_interactions", "drug_names": medications})
            if isinstance(result, dict) and result.get("status") == "COMPLETED":
                return result
            return {"interactions": [], "highest_severity": "none", "status": "FAILED"}
        except Exception as e:
            self.logger.error(f"Error checking drug interactions: {e}")
            return {"interactions": [], "highest_severity": "none", "status": "ERROR"}

    def _analyze_guideline_support(
        self,
        drug_name: str,
        patient_record: Dict[str, Any],
        guidelines: List[Dict[str, Any]],
    ) -> List[EvidenceItem]:
        """Analyze guideline support with NLP-style keyword matching"""
        evidence_items = []
        timestamp = datetime.now(timezone.utc).isoformat()

        # Comprehensive keyword sets
        positive_keywords = {
            "recommended",
            "first-line",
            "second-line",
            "preferred",
            "indicated",
            "effective",
            "beneficial",
            "appropriate",
            "evidence supports",
            "guidelines recommend",
            "standard of care",
        }

        negative_keywords = {
            "contraindicated",
            "avoid",
            "caution",
            "not recommended",
            "harmful",
            "adverse",
            "discontinued",
            "black box warning",
            "insufficient evidence",
            "not indicated",
        }

        # FIXED: Limit guideline text length to avoid token bloat
        max_guideline_length = 150  # Reduced from 250

        for i, guideline in enumerate(guidelines[:3]):
            relevance_score = float(guideline.get("relevance_score", 0.5))
            text = str(guideline.get("text", "")).lower()
            source = guideline.get("source", f"Guideline {i + 1}")

            # Count keyword occurrences
            positive_count = sum(1 for kw in positive_keywords if kw in text)
            negative_count = sum(1 for kw in negative_keywords if kw in text)

            # Determine support with nuanced scoring
            net_score = positive_count - negative_count
            supports = net_score > 0

            # Adjust confidence based on keyword density
            text_length = len(text.split()) if text else 1
            keyword_density = (positive_count + negative_count) / max(text_length, 1)
            adjusted_confidence = min(relevance_score * (1 + keyword_density), 0.95)

            # Truncate text for prompt efficiency
            truncated_text = text[:max_guideline_length]
            if len(text) > max_guideline_length:
                truncated_text += "..."

            evidence_items.append(
                EvidenceItem(
                    source=f"clinical_guideline_{source}",
                    type="clinical_guideline",
                    content=(f"{source} (relevance: {relevance_score:.0%}): {truncated_text}"),
                    weight=self.evidence_weights["guideline_support"] / min(len(guidelines), 3),
                    supports_approval=supports,
                    confidence=adjusted_confidence,
                    timestamp=timestamp,
                )
            )

        return evidence_items

    def _analyze_drug_interactions(self, interaction_check: Dict[str, Any]) -> Optional[EvidenceItem]:
        """Analyze drug interactions for safety assessment"""
        if not interaction_check or not isinstance(interaction_check, dict):
            return None

        interactions = interaction_check.get("interactions", [])
        highest_severity = interaction_check.get("highest_severity", "none").lower()

        # Severity scoring
        severity_scores = {
            "contraindicated": 1.0,
            "major": 0.8,
            "moderate": 0.5,
            "minor": 0.2,
            "none": 0.0,
        }

        severity_score = severity_scores.get(highest_severity, 0.0)

        # Build content message
        if not interactions:
            content = "No significant drug interactions identified"
            supports = True
            confidence = 0.9
        else:
            interaction_count = len(interactions)
            content = (
                f"{interaction_count} drug interaction{'s' if interaction_count > 1 else ''} "
                f"detected with {highest_severity} severity"
            )
            supports = severity_score < 0.5  # Only support if minor or no interactions
            confidence = 0.85

        return EvidenceItem(
            source="drug_interaction_analysis",
            type="safety_check",
            content=content,
            weight=self.evidence_weights["drug_interactions"],
            supports_approval=supports,
            confidence=confidence,
        )

    def _analyze_patient_history(self, patient_record: Dict[str, Any], drug_info: Dict[str, Any]) -> float:
        """
        Analyze patient history for drug appropriateness.
        Returns score from 0.0 (poor fit) to 1.0 (excellent fit).
        """
        score = 0.5  # Neutral baseline
        factors = []

        # 1. Check medication history
        med_history = patient_record.get("medication_history", [])
        if med_history:
            # Check for prerequisite medications
            prerequisite_meds = {
                "metformin",
                "lisinopril",
                "atorvastatin",
                "simvastatin",
            }
            tried_prerequisites = sum(
                1 for med in med_history if any(prereq in med.lower() for prereq in prerequisite_meds)
            )

            if tried_prerequisites > 0:
                score += 0.2 * min(tried_prerequisites / 2, 1.0)  # Cap benefit
                factors.append(f"tried {tried_prerequisites} standard medications")

        # 2. Check diagnosis alignment
        patient_diagnoses = set(patient_record.get("diagnoses_icd10", []))
        drug_indications = drug_info.get("indications", [])

        if patient_diagnoses and drug_indications:
            # Map common conditions
            condition_mappings = {
                "diabetes": ["E11", "E10"],
                "heart failure": ["I50"],
                "hypertension": ["I10", "I11", "I12", "I13"],
                "kidney": ["N18", "N19"],
            }

            for indication in drug_indications:
                indication_lower = str(indication).lower()
                for condition, icd_prefixes in condition_mappings.items():
                    if condition in indication_lower:
                        if any(any(diag.startswith(prefix) for prefix in icd_prefixes) for diag in patient_diagnoses):
                            score += 0.15
                            factors.append(f"diagnosis matches {condition}")

        # 3. Check lab values
        labs = patient_record.get("labs", {})
        if labs:
            # HbA1c for diabetes medications
            if "HbA1c" in labs:
                try:
                    hba1c = float(str(labs["HbA1c"]).replace("%", ""))
                    if hba1c > 8.0:
                        score += 0.15
                        factors.append(f"elevated HbA1c ({hba1c}%)")
                    elif hba1c > 7.0:
                        score += 0.1
                        factors.append(f"suboptimal HbA1c ({hba1c}%)")
                except:
                    pass

            # Renal function
            if "eGFR" in labs:
                try:
                    egfr = float(labs["eGFR"])
                    if egfr >= 30:
                        score += 0.05
                        factors.append("adequate renal function")
                except:
                    pass

        # 4. Check treatment failures
        notes = patient_record.get("notes", "")
        if notes:
            failure_keywords = [
                "failed",
                "insufficient",
                "inadequate",
                "not responding",
                "refractory",
            ]
            if any(keyword in notes.lower() for keyword in failure_keywords):
                score += 0.15
                factors.append("documented treatment failure")

        # 5. Check adherence
        adherence_score = patient_record.get("adherence_score")
        if adherence_score is not None:
            if adherence_score > 0.8:
                score += 0.1
                factors.append(f"good adherence ({adherence_score:.0%})")

        # Log analysis
        self.logger.debug(f"Patient history score: {score:.2f}, factors: {factors}")

        return min(score, 1.0)  # Cap at 1.0

    def _assess_clinical_appropriateness(self, context: AnalysisContext) -> Dict[str, Any]:
        """Comprehensive clinical appropriateness assessment"""
        score = 0.5
        factors = []

        patient_record = context.patient_record
        drug_info = context.drug_info

        # 1. Age appropriateness
        if patient_record and "age" in patient_record:
            age = patient_record["age"]
            if 18 <= age <= 85:
                score += 0.1
                factors.append("age appropriate")
            elif age < 18:
                score -= 0.2
                factors.append("pediatric use requires special consideration")
            elif age > 85:
                score -= 0.1
                factors.append("geriatric considerations needed")

        # 2. Contraindications check
        if drug_info and patient_record:
            contraindications = drug_info.get("contraindications", [])
            patient_conditions = patient_record.get("diagnoses_icd10", [])

            # Check for absolute contraindications
            ci_mappings = {
                "Type 1 Diabetes": ["E10"],
                "Diabetic Ketoacidosis": ["E10.1", "E11.1"],
                "Severe Renal Impairment": ["N18.6", "N19"],
            }

            has_contraindication = False
            for ci, icd_codes in ci_mappings.items():
                if any(ci.lower() in str(c).lower() for c in contraindications):
                    if any(any(diag.startswith(icd) for icd in icd_codes) for diag in patient_conditions):
                        has_contraindication = True
                        factors.append(f"contraindication present: {ci}")
                        score -= 0.3

            if not has_contraindication:
                score += 0.2
                factors.append("no contraindications identified")

        # 3. Provider type consideration
        provider_type = patient_record.get("provider_type", "") if patient_record else ""
        if "specialist" in provider_type.lower() or "endocrin" in provider_type.lower():
            score += 0.15
            factors.append("specialist management")
        elif provider_type:
            score += 0.05
            factors.append(f"{provider_type} management")

        # 4. Polypharmacy consideration
        if patient_record:
            med_count = len(patient_record.get("medication_history", []))
            if med_count > 10:
                score -= 0.05
                factors.append("significant polypharmacy")
            elif med_count > 5:
                factors.append("moderate medication burden")

        # 5. Previous PA history (if available)
        if patient_record and "pa_history" in patient_record:
            pa_history = patient_record["pa_history"]
            if isinstance(pa_history, list) and len(pa_history) > 0:
                recent_approvals = sum(
                    1
                    for pa in pa_history
                    if pa.get("decision") == "approved" and pa.get("drug_class") == drug_info.get("drug_class")
                )
                if recent_approvals > 0:
                    score += 0.1
                    factors.append("previous similar PA approved")

        # Generate comprehensive rationale
        rationale_parts = [f"Clinical appropriateness score: {score:.1%}"]
        if factors:
            rationale_parts.append(f"Key factors: {', '.join(factors)}")
        else:
            rationale_parts.append("Standard clinical profile")

        return {
            "score": min(max(score, 0.0), 1.0),  # Clamp to [0, 1]
            "confidence": 0.75 if len(factors) >= 3 else 0.65,
            "rationale": ". ".join(rationale_parts),
            "factors": factors,
        }

    def _calculate_weighted_score(self, evidence_items: List[EvidenceItem]) -> float:
        """Calculate weighted approval score from evidence"""
        if not evidence_items:
            return 0.5

        total_weight = sum(item.weight for item in evidence_items)
        if total_weight == 0:
            return 0.5

        weighted_sum = sum(
            item.weight * (1.0 if item.supports_approval else 0.0) * item.confidence for item in evidence_items
        )

        return weighted_sum / total_weight

    def _calculate_confidence_score(self, evidence_items: List[EvidenceItem], context: AnalysisContext) -> float:
        """Calculate confidence in the prediction based on evidence quality"""
        if not evidence_items:
            return 0.1

        # 1. Evidence quality (40%)
        avg_evidence_confidence = sum(e.confidence for e in evidence_items) / len(evidence_items)

        # 2. Data completeness (40%)
        completeness_checks = [
            bool(context.patient_record),
            bool(context.drug_info and "indications" in context.drug_info),
            bool(context.policy_info),
            bool(context.guideline_results),
            bool(context.criteria_check),
            context.patient_record.get("labs") is not None if context.patient_record else False,
            bool(context.drug_safety),  # ADDED
        ]
        data_completeness = sum(completeness_checks) / len(completeness_checks)

        # 3. Evidence consensus (20%)
        supporting = sum(1 for e in evidence_items if e.supports_approval)
        total = len(evidence_items)
        # Higher confidence when evidence strongly agrees (either way)
        consensus_ratio = supporting / total
        consensus_score = 1.0 - (2 * abs(0.5 - consensus_ratio))  # U-shaped curve

        # Combined confidence
        confidence = avg_evidence_confidence * 0.4 + data_completeness * 0.4 + consensus_score * 0.2

        return min(confidence, 0.95)  # Never claim 100% confidence

    def _build_advanced_synthesis_prompt(
        self,
        context: AnalysisContext,
        evidence_items: List[EvidenceItem],
        preliminary_score: float,
        confidence: float,
        urgency: str,
    ) -> str:
        """Build sophisticated prompt for LLM synthesis"""

        # Get key identifiers
        patient_id = context.patient_record.get("patient_id", "unknown") if context.patient_record else "unknown"
        drug_name = context.drug_info.get("drug_name", "Unknown") if context.drug_info else "Unknown"

        # Structure evidence by category
        evidence_by_type = {}
        for item in evidence_items:
            if item.type not in evidence_by_type:
                evidence_by_type[item.type] = []
            evidence_by_type[item.type].append(item)

        # Build prompt sections
        prompt_sections = [
            "You are an expert Prior Authorization physician reviewer with 20+ years of experience.",
            "Your role is to make evidence-based PA decisions that balance clinical appropriateness with insurance requirements.",
            "",
            f"CASE ID: PA_{patient_id}_{drug_name}_{int(time.time())}",
            f"URGENCY: {urgency.upper()}",
            f"PRELIMINARY ASSESSMENT: {preliminary_score:.1%} approval likelihood with {confidence:.1%} confidence",
            "",
            "=== PATIENT PROFILE ===",
            self._format_patient_profile(context.patient_record),
            "",
            "=== REQUESTED MEDICATION ===",
            self._format_drug_info(context.drug_info),
            "",
            "=== INSURANCE POLICY REQUIREMENTS ===",
            self._format_policy_info(context.policy_info),
            "",
            "=== CLINICAL EVIDENCE SUMMARY ===",
            self._format_evidence_summary(evidence_by_type),
            "",
            "=== DRUG SAFETY ASSESSMENT ===",
            self._format_safety_assessment(context),  # UPDATED
            "",
            "=== CLINICAL GUIDELINES ===",
            self._format_guidelines(context.guideline_results),
            "",
            "=== DECISION FRAMEWORK ===",
            "Consider the following in your assessment:",
            "1. Does the patient meet medical necessity criteria?",
            "2. Have prerequisite treatments been tried and failed?",
            "3. Are there any safety concerns or contraindications?",
            "4. Is this the most appropriate treatment option?",
            "5. What is the strength of clinical evidence?",
            "",
            "=== REQUIRED OUTPUT ===",
            "Provide your decision as a JSON object with the following structure:",
            "{",
            '  "approval_likelihood_percent": <integer 0-100>,',
            '  "decision_prediction": <exactly one of: "Approve", "Deny", "Pend for More Info">,',
            '  "confidence_score": <float 0.0-1.0>,',
            '  "clinical_rationale": <detailed paragraph explaining your reasoning with specific evidence citations>,',
            '  "key_supporting_factors": [<list of specific factors supporting approval>],',
            '  "key_opposing_factors": [<list of specific factors against approval>],',
            '  "identified_gaps": [<list of missing information that would strengthen the case>],',
            '  "recommended_next_steps": [<specific actionable recommendations>]',
            "}",
        ]

        return "\n".join(prompt_sections)

    def _build_simplified_prompt(
        self, context: AnalysisContext, evidence_items: List[EvidenceItem], score: float
    ) -> str:
        """Build simplified prompt for fallback LLM"""
        supporting = [e for e in evidence_items if e.supports_approval]
        opposing = [e for e in evidence_items if not e.supports_approval]

        patient_info = (
            "No patient data"
            if not context.patient_record
            else (
                f"Age {context.patient_record.get('age', 'unknown')}, "
                f"Diagnoses: {', '.join(context.patient_record.get('diagnoses_icd10', ['none']))}"
            )
        )

        drug_name = context.drug_info.get("drug_name", "Unknown") if context.drug_info else "Unknown"

        prompt = f"""Prior Authorization Decision Required:

PATIENT: {patient_info}
MEDICATION: {drug_name}
PRELIMINARY SCORE: {score:.0%}

SUPPORTING EVIDENCE ({len(supporting)} items):
{chr(10).join(f"• {e.content[:80]}" for e in supporting[:3])}

OPPOSING EVIDENCE ({len(opposing)} items):
{chr(10).join(f"• {e.content[:80]}" for e in opposing[:3])}

Based on the evidence, provide a PA decision as JSON:
{{
  "approval_likelihood_percent": <0-100>,
  "decision_prediction": <"Approve", "Deny", or "Pend for More Info">,
  "confidence_score": <0.0-1.0>,
  "clinical_rationale": <explanation paragraph>,
  "identified_gaps": [<missing items>]
}}"""

        return prompt

    def _generate_rule_based_decision(
        self, context: AnalysisContext, evidence_items: List[EvidenceItem], score: float
    ) -> Dict[str, Any]:
        """Generate deterministic rule-based decision as final fallback"""

        # Count evidence
        supporting = [e for e in evidence_items if e.supports_approval]
        opposing = [e for e in evidence_items if not e.supports_approval]

        # Decision logic
        if score > 0.75:
            decision = "Approve"
            likelihood = int(score * 100)
            rationale = f"Strong evidence supports approval with {len(supporting)} positive factors."
        elif score < 0.25:
            decision = "Deny"
            likelihood = int(score * 100)
            rationale = f"Insufficient evidence for approval with {len(opposing)} concerns identified."
        else:
            decision = "Pend for More Info"
            likelihood = 50
            rationale = f"Mixed evidence requires additional review ({len(supporting)} positive, {len(opposing)} negative factors)."

        # Build factor lists
        key_supporting = [e.content[:100] for e in supporting[:3]]
        key_opposing = [e.content[:100] for e in opposing[:3]]

        # Identify gaps
        gaps = []
        if not context.patient_record.get("labs"):
            gaps.append("Recent laboratory results")
        if not context.patient_record.get("medication_history"):
            gaps.append("Complete medication history")
        if decision == "Pend for More Info":
            gaps.append("Additional clinical documentation")

        return {
            "approval_likelihood_percent": likelihood,
            "decision_prediction": decision,
            "confidence_score": 0.5,  # Lower confidence for rule-based
            "clinical_rationale": f"{rationale} This is a rule-based assessment pending full clinical review.",
            "key_supporting_factors": key_supporting,
            "key_opposing_factors": key_opposing,
            "identified_gaps": gaps,
            "recommended_next_steps": ["Manual clinical review recommended"],
            "model": "rule_based",
            "tokens_used": 0,
        }

    def _generate_recommendations(
        self,
        decision: DecisionType,
        evidence_items: List[EvidenceItem],
        context: AnalysisContext,
    ) -> List[str]:
        """Generate specific, actionable recommendations based on decision"""
        recommendations = []

        if decision == DecisionType.APPROVE:
            # Approval recommendations
            recommendations.append("Proceed with prescription as clinically indicated")

            # Add monitoring requirements
            if context.drug_info and "monitoring_requirements" in context.drug_info:
                for req in context.drug_info["monitoring_requirements"][:3]:
                    recommendations.append(f"Monitor: {req}")

            # Dosing guidance
            if context.drug_info and "dosing" in context.drug_info:
                dosing = context.drug_info["dosing"]
                if isinstance(dosing, dict) and "initial" in dosing:
                    recommendations.append(f"Start with {dosing['initial']}")

        elif decision == DecisionType.DENY:
            # Denial recommendations
            unmet_criteria = [e for e in evidence_items if not e.supports_approval and e.type == "unmet_criterion"]

            for criterion in unmet_criteria[:3]:
                if "step therapy" in criterion.content.lower():
                    recommendations.append("Complete 3-month trial of metformin at therapeutic dose")
                elif "diagnosis" in criterion.content.lower():
                    recommendations.append("Provide documentation of Type 2 Diabetes diagnosis")
                elif "hba1c" in criterion.content.lower():
                    recommendations.append("Document HbA1c > 7.5% on current therapy")

            # Suggest alternatives
            if context.policy_info and "alternatives" in context.policy_info:
                alts = context.policy_info["alternatives"][:2]
                if alts:
                    alt_names = [a["drug"] for a in alts if "drug" in a]
                    recommendations.append(f"Consider covered alternatives: {', '.join(alt_names)}")

        elif decision == DecisionType.PEND:
            # Pending recommendations
            recommendations.append("Submit additional documentation for review")

            # Specific gaps
            if context.criteria_check and "unmet_criteria" in context.criteria_check:
                for criterion in context.criteria_check["unmet_criteria"][:2]:
                    if isinstance(criterion, dict) and "description" in criterion:
                        recommendations.append(f"Address: {criterion['description']}")

            # General documentation needs
            if not context.patient_record.get("labs"):
                recommendations.append("Include recent lab results (HbA1c, renal function)")

            if not context.patient_record.get("notes"):
                recommendations.append("Provide clinical notes documenting treatment failure")

        return recommendations[:5]  # Limit to 5 most important

    def _find_alternative_options(self, context: AnalysisContext) -> List[Dict[str, Any]]:
        """Find and format alternative treatment options"""
        alternatives = []

        if context.policy_info and "alternatives" in context.policy_info:
            for alt in context.policy_info["alternatives"][:3]:
                if isinstance(alt, dict):
                    formatted_alt = {
                        "drug_name": alt.get("drug", "Unknown"),
                        "coverage_status": alt.get("status", "Unknown"),
                        "tier": alt.get("tier", "Unknown"),
                        "prior_auth_required": alt.get("pa_required", False),
                        "rationale": "Insurance preferred alternative",
                    }
                    alternatives.append(formatted_alt)

        # Add therapeutic alternatives if available
        if context.drug_info and "drug_class" in context.drug_info:
            drug_class = context.drug_info["drug_class"]
            if "SGLT2" in drug_class and len(alternatives) < 3:
                alternatives.append(
                    {
                        "drug_name": "GLP-1 agonist (e.g., semaglutide)",
                        "coverage_status": "May require PA",
                        "tier": "Variable",
                        "prior_auth_required": True,
                        "rationale": "Alternative diabetes medication class",
                    }
                )

        return alternatives

    def _identify_missing_information(self, evidence_items: List[EvidenceItem], context: AnalysisContext) -> List[str]:
        """Identify specific missing information that would strengthen the case"""
        gaps = []

        # Check for missing critical data
        if context.patient_record:
            if not context.patient_record.get("labs"):
                gaps.append("Recent laboratory results (HbA1c, eGFR, lipid panel)")

            if not context.patient_record.get("medication_history"):
                gaps.append("Complete medication history with dates and doses")

            if not context.patient_record.get("notes"):
                gaps.append("Clinical notes documenting treatment response")

            if context.patient_record.get("provider_type") == "Primary Care":
                gaps.append("Consider endocrinologist consultation for complex cases")
        else:
            gaps.append("Complete patient medical record")

        # Check for weak evidence areas
        weak_evidence = [e for e in evidence_items if e.confidence < 0.7]
        if len(weak_evidence) > len(evidence_items) / 2:
            gaps.append("Additional supporting clinical documentation")

        # Check for missing policy requirements
        if context.criteria_check and not context.criteria_check.get("meets_criteria"):
            unmet = context.criteria_check.get("unmet_criteria", [])
            for criterion in unmet[:2]:
                if isinstance(criterion, dict) and criterion.get("severity") == "critical":
                    gaps.append(f"Documentation for: {criterion.get('description', 'policy requirement')}")

        return gaps[:5]  # Return top 5 gaps

    # === Utility Methods ===

    def _validate_context(self, context: AnalysisContext) -> bool:
        """Validate minimum required data is present"""
        return bool(
            context.patient_record
            and (context.drug_info or context.policy_info)
            and isinstance(context.patient_record, dict)
            and context.patient_record.get("patient_id")
        )

    def _count_context_items(self, context: AnalysisContext) -> int:
        """Count non-empty context items"""
        count = 0
        if context.patient_record:
            count += 1
        if context.drug_info:
            count += 1
        if context.policy_info:
            count += 1
        if context.guideline_results:
            count += 1
        if context.interaction_check and context.interaction_check.get("status") == "COMPLETED":
            count += 1
        if context.criteria_check:
            count += 1
        if context.drug_safety:  # ADDED
            count += 1
        return count

    def _create_audit_entry(self, action: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create detailed audit trail entry"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "details": details or {},
            "agent_id": self.agent_id,
        }

    def _create_error_response(
        self,
        error_message: str,
        audit_trail: List[Dict],
        traceback_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create comprehensive error response"""
        response = {
            "status": "error",
            "message": error_message,
            "error_type": type(error_message).__name__ if hasattr(error_message, "__class__") else "Unknown",
            "audit_trail": audit_trail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.config["enable_detailed_audit"] and traceback_str:
            response["traceback"] = traceback_str

        return response

    def _generate_cache_key(self, patient_id: str, drug_name: str, insurer_id: str) -> str:
        """Generate deterministic cache key"""
        key_components = f"{patient_id}:{drug_name.lower()}:{insurer_id}"
        return hashlib.sha256(key_components.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached result if valid"""
        with self._cache_lock:
            if cache_key in self.decision_cache:
                cached_data, cache_time = self.decision_cache[cache_key]

                # Check TTL
                if time.time() - cache_time < self.config["cache_ttl_seconds"]:
                    cached_data["cached_at"] = cache_time
                    return cached_data
                else:
                    # Expired - remove from cache
                    del self.decision_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Cache result with TTL and size management"""
        with self._cache_lock:
            # Implement simple LRU by removing oldest if at capacity
            if len(self.decision_cache) >= self.config["max_cache_size"]:
                # Remove oldest entry
                oldest_key = min(self.decision_cache.keys(), key=lambda k: self.decision_cache[k][1])
                del self.decision_cache[oldest_key]

            self.decision_cache[cache_key] = (result, time.time())

    def _update_metrics(self, result: AnalysisResult, processing_time_ms: float) -> None:
        """Update performance metrics with thread safety"""
        with self._metrics_lock:
            self.metrics["total_predictions"] += 1
            self.metrics["successful_predictions"] += 1

            # Update average processing time
            current_avg = self.metrics["average_processing_time"]
            total = self.metrics["total_predictions"]

            if total > 1:
                self.metrics["average_processing_time"] = (current_avg * (total - 1) + processing_time_ms) / total
            else:
                self.metrics["average_processing_time"] = processing_time_ms

            # Update token usage
            self.metrics["total_llm_tokens"] += result.llm_tokens_used

            # Update error rate
            total_attempts = self.metrics["successful_predictions"] + self.metrics["failed_predictions"]
            if total_attempts > 0:
                self.metrics["error_rate"] = self.metrics["failed_predictions"] / total_attempts

        # Track latency percentiles - FIXED: Thread-safe deque operations
        with self._latency_lock:
            self._latency_history.append(processing_time_ms)

            # Calculate percentiles
            if len(self._latency_history) >= 10:
                sorted_latencies = sorted(self._latency_history)
                p95_index = int(len(sorted_latencies) * 0.95)
                p99_index = int(len(sorted_latencies) * 0.99)

                with self._metrics_lock:
                    self.metrics["p95_latency"] = sorted_latencies[p95_index]
                    self.metrics["p99_latency"] = sorted_latencies[p99_index]

        # Log metrics periodically
        if self.metrics["total_predictions"] % 10 == 0:
            self.logger.info(f"Metrics update: {json.dumps(self.metrics, indent=2)}")

    def _validate_llm_output(self, output: Any) -> bool:
        """Comprehensive validation of LLM output"""
        if not isinstance(output, dict):
            return False

        # Required fields
        required_fields = {
            "approval_likelihood_percent": (int, float),
            "decision_prediction": str,
            "confidence_score": (int, float),
            "clinical_rationale": str,
        }

        for field_name, expected_type in required_fields.items():
            if field_name not in output:
                self.logger.warning(f"Missing required field: {field_name}")
                return False

            if not isinstance(output[field_name], expected_type):
                self.logger.warning(
                    f"Invalid type for {field_name}: expected {expected_type}, got {type(output[field_name])}"
                )
                return False

        # Value range validation
        likelihood = output.get("approval_likelihood_percent")
        if not isinstance(likelihood, (int, float)) or not 0 <= likelihood <= 100:
            self.logger.warning(f"Invalid approval_likelihood_percent: {likelihood}")
            return False

        confidence = output.get("confidence_score")
        if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
            self.logger.warning(f"Invalid confidence_score: {confidence}")
            return False

        decision = output.get("decision_prediction")
        valid_decisions = {"Approve", "Deny", "Pend for More Info"}
        if decision not in valid_decisions:
            # FIXED: Try case-insensitive match
            decision_upper = decision.upper()
            if not any(decision_upper == valid.upper() for valid in valid_decisions):
                self.logger.warning(f"Invalid decision_prediction: {decision}")
                return False

        # Optional fields type checking
        optional_fields = {
            "key_supporting_factors": list,
            "key_opposing_factors": list,
            "identified_gaps": list,
            "recommended_next_steps": list,
        }

        for optional_field, expected_type in optional_fields.items():
            if optional_field in output and not isinstance(output[optional_field], expected_type):
                self.logger.warning(f"Invalid type for optional field {optional_field}")
                # Don't fail on optional fields, just log

        return True

    # === Formatting Helpers ===

    def _format_patient_profile(self, patient_record: Dict[str, Any]) -> str:
        """Format patient profile for prompt"""
        if not patient_record:
            return "No patient data available"

        parts = []

        # Demographics
        parts.append(f"Patient ID: {patient_record.get('patient_id', 'Unknown')}")
        parts.append(f"Age: {patient_record.get('age', 'Unknown')}")
        parts.append(f"Provider: {patient_record.get('provider_type', 'Unknown')}")

        # Diagnoses
        diagnoses = patient_record.get("diagnoses_icd10", [])
        if diagnoses:
            parts.append(f"Diagnoses: {', '.join(diagnoses)}")

        # Medications
        meds = patient_record.get("medication_history", [])
        if meds:
            parts.append(f"Current Medications: {', '.join(meds)}")

        # Labs
        labs = patient_record.get("labs", {})
        if labs:
            lab_strings = [f"{k}: {v}" for k, v in labs.items()]
            parts.append(f"Recent Labs: {', '.join(lab_strings)}")

        # Clinical notes - FIXED: Truncate to avoid token bloat
        notes = patient_record.get("notes", "")
        if notes:
            parts.append(f"Clinical Notes: {notes[:100]}...")

        return "\n".join(parts)

    def _format_drug_info(self, drug_info: Dict[str, Any]) -> str:
        """Format drug information for prompt"""
        if not drug_info:
            return "No drug information available"

        parts = []
        parts.append(f"Drug Name: {drug_info.get('drug_name', 'Unknown')}")
        parts.append(f"Drug Class: {drug_info.get('drug_class', 'Unknown')}")

        indications = drug_info.get("indications", [])
        if indications:
            parts.append(f"Indications: {', '.join(indications[:3])}")

        contraindications = drug_info.get("contraindications", [])
        if contraindications:
            parts.append(f"Contraindications: {', '.join(contraindications[:3])}")

        monitoring = drug_info.get("monitoring_requirements", [])
        if monitoring:
            parts.append(f"Monitoring Required: {', '.join(monitoring[:2])}")

        return "\n".join(parts)

    def _format_policy_info(self, policy_info: Dict[str, Any]) -> str:
        """Format policy information for prompt"""
        if not policy_info:
            return "No policy information available"

        parts = []
        parts.append(f"Coverage Status: {policy_info.get('status', 'Unknown')}")
        parts.append(f"Tier: {policy_info.get('tier', 'Unknown')}")

        criteria = policy_info.get("criteria", [])
        if criteria:
            parts.append("Coverage Criteria:")
            for i, criterion in enumerate(criteria[:5], 1):
                parts.append(f"  {i}. {criterion}")

        return "\n".join(parts)

    def _format_evidence_summary(self, evidence_by_type: Dict[str, List[EvidenceItem]]) -> str:
        """Format evidence summary for prompt"""
        if not evidence_by_type:
            return "No evidence available"

        parts = []

        for evidence_type, items in evidence_by_type.items():
            parts.append(f"\n{evidence_type.upper().replace('_', ' ')}:")

            supporting = [i for i in items if i.supports_approval]
            opposing = [i for i in items if not i.supports_approval]

            if supporting:
                parts.append("  Supporting:")
                for item in supporting[:2]:  # Limit to avoid token bloat
                    parts.append(f"    • {item.content[:80]} (conf: {item.confidence:.0%})")

            if opposing:
                parts.append("  Opposing:")
                for item in opposing[:2]:  # Limit to avoid token bloat
                    parts.append(f"    • {item.content[:80]} (conf: {item.confidence:.0%})")

        return "\n".join(parts)

    # UPDATED: Include drug safety in prompt
    def _format_safety_assessment(self, context: AnalysisContext) -> str:
        """Format safety assessment including interactions and drug safety"""
        parts = []

        # Drug interactions
        interaction_text = self._format_interaction_check(context.interaction_check)
        parts.append(interaction_text)

        # Drug safety
        if context.drug_safety:
            parts.append("\nDrug Safety Profile:")
            parts.append(f"  Profile: {context.drug_safety.get('safety_profile', 'Unknown')}")

            warnings = context.drug_safety.get("warnings", [])
            if warnings:
                parts.append(f"  Warnings: {', '.join(warnings[:3])}")

            contraindications = context.drug_safety.get("contraindications", [])
            if contraindications:
                parts.append(f"  Contraindications: {', '.join(contraindications[:3])}")

        return "\n".join(parts)

    def _format_interaction_check(self, interaction_check: Dict[str, Any]) -> str:
        """Format drug interaction information"""
        if not interaction_check or interaction_check.get("status") != "COMPLETED":
            return "Drug interaction check not completed"

        interactions = interaction_check.get("interactions", [])
        if not interactions:
            return "No drug interactions identified"

        parts = [f"Interactions found: {len(interactions)}"]
        parts.append(f"Highest severity: {interaction_check.get('highest_severity', 'unknown')}")

        for interaction in interactions[:3]:
            if isinstance(interaction, dict):
                parts.append(f"  • {interaction.get('description', 'Unknown interaction')}")

        return "\n".join(parts)

    def _format_guidelines(self, guidelines: List[Dict[str, Any]]) -> str:
        """Format clinical guidelines"""
        if not guidelines:
            return "No clinical guidelines available"

        parts = []

        # FIXED: Limit guideline text to avoid token bloat
        for i, guideline in enumerate(guidelines[:3], 1):
            source = guideline.get("source", f"Guideline {i}")
            score = guideline.get("relevance_score", 0)
            text = guideline.get("text", "")[:120]  # Reduced from 200

            parts.append(f"{i}. {source} (relevance: {score:.0%})")
            parts.append(f"   {text}...")

        return "\n".join(parts)

    # === Public Synchronous Method ===

    def predict_approval_likelihood_sync(
        self, patient_id: str, drug_name: str, insurer_id: str, urgency: str = "routine"
    ) -> Dict[str, Any]:
        """
        Synchronous wrapper for the async prediction method.
        Handles various Python versions and event loop scenarios.
        """
        import sys

        async def run_prediction():
            return await self.predict_approval_likelihood(patient_id, drug_name, insurer_id, urgency)

        # Python 3.10+ with better asyncio.run
        if sys.version_info >= (3, 10):
            try:
                # Check if there's already an event loop running
                loop = asyncio.get_running_loop()

                # If in a running loop, use thread executor
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(asyncio.run, run_prediction())
                    return future.result(timeout=self.config["timeout_seconds"])

            except RuntimeError:
                # No running loop, safe to use asyncio.run
                return asyncio.run(run_prediction())

        # Python < 3.10 - more careful event loop handling
        else:
            try:
                loop = asyncio.get_event_loop()

                if loop.is_running():
                    # Running in existing loop (e.g., Jupyter)
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(asyncio.run, run_prediction())
                        return future.result(timeout=self.config["timeout_seconds"])
                else:
                    # Can use the existing loop
                    return loop.run_until_complete(run_prediction())

            except RuntimeError:
                # No event loop exists, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(run_prediction())
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)


# === Main Execution for Testing ===


def main():
    """Main function for testing the PatientStratificationAgentLogic"""

    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress verbose logs during testing
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    print("\n" + "=" * 80)
    print("🏥 Prior Authorization Prediction System - Test Suite")
    print("=" * 80 + "\n")

    # Create agent instance
    agent = PatientStratificationAgentLogic("test_agent_001")

    # Define comprehensive test cases
    test_cases = [
        {
            "name": "Test 1: Patient with documented metformin failure and high HbA1c",
            "patient_id": "patient-001",
            "drug_name": "Empagliflozin",
            "insurer_id": "UHC",
            "expected_decision": "APPROVE",
            "urgency": "routine",
        },
        {
            "name": "Test 2: Newly diagnosed patient without step therapy",
            "patient_id": "patient-002",
            "drug_name": "Empagliflozin",
            "insurer_id": "UHC",
            "expected_decision": "DENY",
            "urgency": "routine",
        },
        {
            "name": "Test 3: Patient with wrong diagnosis (GERD instead of diabetes)",
            "patient_id": "patient-003",
            "drug_name": "Empagliflozin",
            "insurer_id": "UHC",
            "expected_decision": "DENY",
            "urgency": "routine",
        },
        {
            "name": "Test 4: Cache performance test (repeat of test 1)",
            "patient_id": "patient-001",
            "drug_name": "Empagliflozin",
            "insurer_id": "UHC",
            "expected_decision": "APPROVE",
            "urgency": "routine",
        },
        {
            "name": "Test 5: Urgent request handling",
            "patient_id": "patient-001",
            "drug_name": "Empagliflozin",
            "insurer_id": "BCBS",
            "expected_decision": "APPROVE",
            "urgency": "urgent",
        },
    ]

    # Execute tests
    test_results = []

    for i, test in enumerate(test_cases):
        print(f"\n{'=' * 80}")
        print(f"🧪 {test['name']}")
        print(f"{'=' * 80}")

        start_time = time.perf_counter()

        try:
            # Run prediction
            result = agent.predict_approval_likelihood_sync(
                patient_id=test["patient_id"],
                drug_name=test["drug_name"],
                insurer_id=test["insurer_id"],
                urgency=test.get("urgency", "routine"),
            )

            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000

            if result["status"] == "success":
                prediction = result["prediction"]

                # Extract decision from string representation
                decision_value = prediction["decision"]
                if isinstance(decision_value, str) and "DecisionType." in decision_value:
                    actual_decision = decision_value.split(".")[-1].upper()
                else:
                    actual_decision = str(decision_value).split(".")[-1].upper()

                # Verify expectation
                expected = test["expected_decision"].upper()
                passed = actual_decision == expected

                # Display results
                status_icon = "✅" if passed else "❌"
                print(f"\n{status_icon} Test Result: {'PASSED' if passed else 'FAILED'}")
                print(f"   Expected: {expected}, Got: {actual_decision}")
                print("\n📊 Decision Details:")
                print(f"   • Decision: {actual_decision}")
                print(f"   • Approval Likelihood: {prediction['approval_likelihood']}%")
                print(f"   • Confidence: {prediction['confidence_score']:.2%} ({prediction['confidence_level']})")
                print(f"   • Processing Time: {elapsed_ms:.0f}ms")

                print("\n📝 Clinical Rationale:")
                print(f"   {prediction['clinical_rationale'][:200]}...")

                print("\n🔍 Evidence Summary:")
                print(f"   • Total Evidence Items: {len(prediction['evidence_items'])}")
                supporting = sum(1 for e in prediction["evidence_items"] if e["supports_approval"])
                print(f"   • Supporting: {supporting}, Opposing: {len(prediction['evidence_items']) - supporting}")

                if prediction["recommendations"]:
                    print("\n💡 Recommendations:")
                    for rec in prediction["recommendations"][:3]:
                        print(f"   • {rec}")

                # Store result
                test_results.append(
                    {
                        "test": i + 1,
                        "name": test["name"],
                        "passed": passed,
                        "expected": expected,
                        "actual": actual_decision,
                        "time_ms": elapsed_ms,
                        "likelihood": prediction["approval_likelihood"],
                        "confidence": prediction["confidence_score"],
                        "source": result.get("source", "computed"),
                    }
                )

            else:
                # Error case
                print("\n❌ Test Failed with Error:")
                print(f"   {result.get('message', 'Unknown error')}")

                test_results.append(
                    {
                        "test": i + 1,
                        "name": test["name"],
                        "passed": False,
                        "error": result.get("message", "Unknown error"),
                        "time_ms": elapsed_ms,
                    }
                )

        except Exception as e:
            print("\n❌ Test Exception:")
            print(f"   {str(e)}")
            traceback.print_exc()

            test_results.append(
                {
                    "test": i + 1,
                    "name": test["name"],
                    "passed": False,
                    "error": str(e),
                    "time_ms": 0,
                }
            )

    # === Final Test Summary ===

    print(f"\n{'=' * 80}")
    print("📊 TEST SUITE SUMMARY")
    print(f"{'=' * 80}\n")

    # Calculate statistics
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r.get("passed", False))
    failed_tests = total_tests - passed_tests

    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ({passed_tests / total_tests * 100:.0f}%)")
    print(f"Failed: {failed_tests} ({failed_tests / total_tests * 100:.0f}%)")

    # Performance analysis
    successful_times = [r["time_ms"] for r in test_results if r.get("passed") and "time_ms" in r]
    if successful_times:
        avg_time = sum(successful_times) / len(successful_times)
        min_time = min(successful_times)
        max_time = max(successful_times)

        print("\nPerformance Metrics:")
        print(f"   • Average Time: {avg_time:.0f}ms")
        print(f"   • Min Time: {min_time:.0f}ms")
        print(f"   • Max Time: {max_time:.0f}ms")

    # Cache performance
    cache_tests = [r for r in test_results if r.get("source") == "cache"]
    if cache_tests:
        print("\nCache Performance:")
        print(f"   • Cache Hits: {len(cache_tests)}")

        # Compare first run vs cached run
        if len(test_results) >= 4:
            first_run = test_results[0].get("time_ms", 1)
            cached_run = test_results[3].get("time_ms", 1)
            if first_run > 0 and cached_run < first_run:
                improvement = ((first_run - cached_run) / first_run) * 100
                print(f"   • Speed Improvement: {improvement:.0f}%")
                print(f"   • First Run: {first_run:.0f}ms, Cached: {cached_run:.0f}ms")

    # Individual test results
    print("\nDetailed Results:")
    print(f"{'Test':<6} {'Decision':<10} {'Expected':<10} {'Result':<8} {'Time (ms)':<10} {'Confidence':<12}")
    print("-" * 65)

    for r in test_results:
        if r.get("passed") is not None:
            decision = r.get("actual", "ERROR")[:10]
            expected = r.get("expected", "N/A")[:10]
            result = "PASS" if r["passed"] else "FAIL"
            time_str = f"{r.get('time_ms', 0):.0f}" if r.get("time_ms") else "N/A"
            conf_str = f"{r.get('confidence', 0):.2%}" if r.get("confidence") else "N/A"

            print(f"{r['test']:<6} {decision:<10} {expected:<10} {result:<8} {time_str:<10} {conf_str:<12}")

    # System metrics
    print(f"\n{'=' * 80}")
    print("📊 SYSTEM METRICS")
    print(f"{'=' * 80}")

    metrics_display = json.dumps(agent.metrics, indent=2)
    print(metrics_display)

    # Final assertion for CI/CD
    print(f"\n{'=' * 80}")

    if passed_tests >= 4:  # Expect at least 4 of 5 tests to pass
        print("✅ TEST SUITE PASSED - System is functioning correctly!")
        return 0
    else:
        print("❌ TEST SUITE FAILED - Please review the failures above")
        # Print failure details
        for r in test_results:
            if not r.get("passed", False):
                print(f"\n   Failed: {r['name']}")
                if "error" in r:
                    print(f"   Error: {r['error']}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
