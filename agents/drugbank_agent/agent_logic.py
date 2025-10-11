import logging
import json
import copy
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import re
from functools import lru_cache
import time
import os
import threading
from collections import deque, OrderedDict

logger = logging.getLogger(__name__)

# P0: Capability constants for discovery registration - FIXED: Added check_drug_safety
CAPABILITIES = [
    "drug_safety_lookup",
    "drug_class_lookup",
    "drugbank_query",
    "get_drug_info",
    "check_drug_interactions",
    "search_drugs",
    "get_pa_criteria",
    "check_drug_safety",  # Added for discovery compatibility
]

# P0: Rate limiting configuration - ENHANCED: Allow env override
RATE_LIMIT_REQUESTS = int(os.getenv("DRUGBANK_RATE_LIMIT_REQUESTS", "5"))  # requests per second
RATE_LIMIT_WINDOW = float(os.getenv("DRUGBANK_RATE_LIMIT_WINDOW", "1.0"))  # window in seconds


class DrugBankAgentLogic:
    """
    Specialized agent for retrieving and managing structured drug data.
    Handles drug information, interactions, indications, and PA-relevant details.
    MVP version uses local mock data with ability to extend to real APIs.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger

        # P0: Load API key from environment
        self.drugbank_api_key = os.getenv("DRUGBANK_TOKEN")
        if not self.drugbank_api_key:
            self.logger.warning("DRUGBANK_TOKEN not set - using mock data only mode")
            self.api_enabled = False
        else:
            self.api_enabled = True
            self.logger.info("DrugBank API key loaded successfully")

        # Initialize memory manager if available
        self.memory_manager = None
        try:
            from core_infra.enhanced_memory_manager import EnhancedMemoryManager

            self.memory_manager = EnhancedMemoryManager()
            self.logger.info("EnhancedMemoryManager initialized for DrugBankAgent")
        except Exception as e:
            self.logger.warning(f"Could not initialize EnhancedMemoryManager: {e}")

        # Mock data path
        self.mock_data_path = Path(__file__).parent.parent.parent / "data" / "mock_drugbank_data.json"

        # P1: Fallback CSV path
        self.fallback_csv_path = Path(__file__).parent.parent.parent / "data" / "drugbank_snapshot.csv"

        # Load mock data
        self._load_mock_data()

        # P1: Load fallback CSV data if available
        self.fallback_data = self._load_fallback_csv()

        # FIXED: Thread-safe locks for shared state
        self.cache_lock = threading.Lock()
        self.rate_limit_lock = threading.Lock()

        # FIXED: Use OrderedDict for LRU-style cache with max size
        self.drug_cache = OrderedDict()
        self.max_cache_size = 1000

        # P0: Thread-safe rate limiting tracker
        self.last_api_calls = deque(maxlen=RATE_LIMIT_REQUESTS)

        # Interaction severity mapping
        self.severity_levels = {
            "contraindicated": 5,
            "major": 4,
            "moderate": 3,
            "minor": 2,
            "unknown": 1,
            "none": 0,  # Added for clarity
        }

        # ADDED: Default management recommendations by severity
        self.default_management = {
            "contraindicated": "Avoid combination - seek alternative therapy",
            "major": "Use only if benefit outweighs risk - close monitoring required",
            "moderate": "Monitor therapy closely for adverse effects",
            "minor": "Monitor therapy as appropriate",
            "unknown": "Insufficient data - monitor therapy",
            "none": "No special precautions needed",
        }

        # P2: Drug name synonyms mapping - ENHANCED with more entries
        self.drug_synonyms = {
            "metformin hcl": "metformin",
            "metformin hydrochloride": "metformin",
            "metformin er": "metformin",
            "metformin xr": "metformin",
            "metformin extended release": "metformin",
            "empagliflozin": "empagliflozin",
            "jardiance": "empagliflozin",
            "ozempic": "semaglutide",
            "wegovy": "semaglutide",
            "rybelsus": "semaglutide",
            "trulicity": "dulaglutide",
            "victoza": "liraglutide",
            "saxenda": "liraglutide",
        }

        self.logger.info(f"DrugBankAgentLogic initialized for {agent_id}")
        self.logger.info(f"Advertising capabilities: {CAPABILITIES}")
        self.logger.info(f"Rate limiting: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW}s")

    def get_capabilities(self) -> List[str]:
        """Return agent capabilities for discovery"""
        return CAPABILITIES

    def _normalize_drug_name(self, drug_name: str) -> str:
        """P2: Normalize drug name to handle synonyms"""
        normalized = drug_name.lower().strip()

        # Check if it's a known synonym
        if normalized in self.drug_synonyms:
            return self.drug_synonyms[normalized]

        # FIXED: Extended suffix removal list
        suffixes_to_remove = [
            " hcl",
            " hydrochloride",
            " sodium",
            " potassium",
            " er",
            " xr",
            " extended release",
            " sr",
            " sustained release",
            " la",
            " long acting",
            " immediate release",
            " ir",
        ]

        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
                break

        return normalized

    def _check_rate_limit(self) -> bool:
        """P0: Check if we're within rate limit - thread-safe"""
        if not self.api_enabled:
            return True  # No rate limit for mock data

        with self.rate_limit_lock:
            current_time = time.time()
            # Remove calls older than the window
            while self.last_api_calls and current_time - self.last_api_calls[0] >= RATE_LIMIT_WINDOW:
                self.last_api_calls.popleft()

            # Check if we can make another call
            if len(self.last_api_calls) < RATE_LIMIT_REQUESTS:
                self.last_api_calls.append(current_time)
                return True

            return False

    def _wait_for_rate_limit(self):
        """FIXED: Smarter wait to reduce CPU usage"""
        if not self.api_enabled:
            return

        while not self._check_rate_limit():
            with self.rate_limit_lock:
                if self.last_api_calls:
                    # Calculate time until oldest call expires
                    time_to_reset = self.last_api_calls[0] + RATE_LIMIT_WINDOW - time.time()
                    if time_to_reset > 0:
                        # Sleep for the exact time needed (with small buffer)
                        time.sleep(max(0.05, min(time_to_reset + 0.01, 0.5)))
                    else:
                        # Should be ready now
                        time.sleep(0.05)
                else:
                    # No calls in queue, should be ready
                    time.sleep(0.05)

    def _load_fallback_csv(self) -> Dict[str, Dict[str, Any]]:
        """P1: Load fallback data from CSV snapshot"""
        fallback_data = {}

        if not self.fallback_csv_path.exists():
            self.logger.debug(f"No fallback CSV found at {self.fallback_csv_path}")
            return fallback_data

        try:
            import csv

            # FIXED: Handle UTF-8 edge cases
            with open(self.fallback_csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    drug_name = row.get("name", "").lower()  # Store in lowercase
                    if drug_name:
                        fallback_data[drug_name] = {
                            "drugbank_id": row.get("drugbank_id", ""),
                            "drug_class": row.get("drug_class", ""),
                            "indications": row.get("indications", "").split("|") if row.get("indications") else [],
                            "contraindications": row.get("contraindications", "").split("|")
                            if row.get("contraindications")
                            else [],
                        }

            self.logger.info(f"Loaded {len(fallback_data)} drugs from fallback CSV")
        except Exception as e:
            self.logger.warning(f"Could not load fallback CSV: {e}")

        return fallback_data

    def _load_mock_data(self):
        """Load mock data from local JSON file with enhanced error handling"""
        try:
            if not self.mock_data_path.exists():
                # Create default mock data if file doesn't exist
                self._create_default_mock_data()

            with open(self.mock_data_path, "r") as f:
                self.mock_data = json.load(f)

            self.logger.info(f"Successfully loaded mock data from {self.mock_data_path}")

            # Validate mock data structure
            required_keys = ["drug_search", "drug_interactions", "drug_details"]
            for key in required_keys:
                if key not in self.mock_data:
                    self.mock_data[key] = {}
                    self.logger.warning(f"Missing '{key}' in mock data, initialized as empty")

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from {self.mock_data_path}: {e}")
            self._create_default_mock_data()
        except Exception as e:
            self.logger.error(f"Unexpected error loading mock data: {e}")
            self._create_default_mock_data()

    def _create_default_mock_data(self):
        """Create comprehensive default mock data for common drugs"""
        self.logger.info("Creating default mock data...")

        default_data = {
            "drug_search": {
                "empagliflozin": "DB09038",
                "dapagliflozin": "DB06292",
                "canagliflozin": "DB08907",
                "ertugliflozin": "DB11827",
                "semaglutide": "DB13928",
                "liraglutide": "DB06655",
                "dulaglutide": "DB09045",
                "metformin": "DB00331",
                "warfarin": "DB00682",
                "aspirin": "DB00945",
            },
            "drug_interactions": {
                "DB09038": [  # empagliflozin
                    {
                        "drugbank_id": "DB00331",
                        "name": "metformin",
                        "description": "May increase risk of lactic acidosis when combined with metformin in renal impairment",
                        "severity": "moderate",
                        "management": "Monitor renal function and signs of lactic acidosis",
                    }
                ],
                "DB00331": [  # metformin - ADDED: Bidirectional interaction
                    {
                        "drugbank_id": "DB09038",
                        "name": "empagliflozin",
                        "description": "May increase risk of lactic acidosis when combined with empagliflozin in renal impairment",
                        "severity": "moderate",
                        "management": "Monitor renal function and signs of lactic acidosis",
                    }
                ],
                "DB00682": [  # warfarin
                    {
                        "drugbank_id": "DB00945",
                        "name": "aspirin",
                        "description": "Increased risk of bleeding when warfarin is combined with aspirin",
                        "severity": "major",
                        "management": "Avoid combination if possible; if used together, monitor INR and signs of bleeding closely",
                    }
                ],
                "DB00945": [  # aspirin - ADDED: Bidirectional interaction
                    {
                        "drugbank_id": "DB00682",
                        "name": "warfarin",
                        "description": "Increased risk of bleeding when aspirin is combined with warfarin",
                        "severity": "major",
                        "management": "Avoid combination if possible; if used together, monitor INR and signs of bleeding closely",
                    }
                ],
            },
            "drug_details": {
                "DB09038": {
                    "name": "empagliflozin",
                    "drug_class": "SGLT2 inhibitor",
                    "indications": [
                        "Type 2 diabetes mellitus",
                        "Heart failure with reduced ejection fraction",
                        "Chronic kidney disease",
                    ],
                    "contraindications": [
                        "Type 1 diabetes",
                        "Diabetic ketoacidosis",
                        "Severe renal impairment (eGFR < 30)",
                        "Dialysis",
                    ],
                    "common_dosing": {
                        "diabetes": "10mg once daily, may increase to 25mg",
                        "heart_failure": "10mg once daily",
                        "ckd": "10mg once daily",
                    },
                    "warnings": [
                        "Risk of ketoacidosis",
                        "Risk of genital mycotic infections",
                        "Risk of volume depletion",
                    ],
                    "monitoring": [
                        "Renal function",
                        "Blood glucose",
                        "Signs of ketoacidosis",
                        "Volume status",
                    ],
                },
                "DB13928": {
                    "name": "semaglutide",
                    "drug_class": "GLP-1 receptor agonist",
                    "indications": [
                        "Type 2 diabetes mellitus",
                        "Cardiovascular risk reduction in T2DM",
                        "Chronic weight management",
                    ],
                    "contraindications": [
                        "Personal or family history of medullary thyroid carcinoma",
                        "Multiple endocrine neoplasia syndrome type 2",
                        "Pregnancy",
                    ],
                    "common_dosing": {
                        "diabetes_subq": "0.25mg weekly x 4 weeks, then 0.5mg weekly, may increase to 1mg or 2mg weekly",
                        "diabetes_oral": "3mg daily x 30 days, then 7mg daily, may increase to 14mg daily",
                        "weight_management": "0.25mg weekly x 4 weeks, then increase by 0.25mg every 4 weeks to target 2.4mg weekly",
                    },
                    "warnings": [
                        "Risk of thyroid C-cell tumors",
                        "Risk of pancreatitis",
                        "Risk of diabetic retinopathy complications",
                        "Gastrointestinal adverse reactions",
                    ],
                    "monitoring": [
                        "Blood glucose",
                        "HbA1c",
                        "Signs of pancreatitis",
                        "Diabetic retinopathy in patients with history",
                    ],
                },
                "DB00331": {
                    "name": "metformin",
                    "drug_class": "Biguanide",
                    "indications": [
                        "Type 2 diabetes mellitus",
                        "Prediabetes",
                        "Polycystic ovary syndrome (off-label)",
                    ],
                    "contraindications": [
                        "Severe renal impairment (eGFR < 30)",
                        "Metabolic acidosis",
                        "Diabetic ketoacidosis",
                    ],
                    "common_dosing": {
                        "diabetes": "500mg twice daily, may increase to 1000mg twice daily",
                        "extended_release": "500-1000mg once daily with evening meal, max 2000mg daily",
                    },
                    "warnings": [
                        "Risk of lactic acidosis",
                        "Vitamin B12 deficiency with long-term use",
                        "GI side effects common initially",
                    ],
                    "monitoring": [
                        "Renal function",
                        "Vitamin B12 levels annually",
                        "Blood glucose",
                    ],
                },
            },
        }

        # Save default data
        try:
            self.mock_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mock_data_path, "w") as f:
                json.dump(default_data, f, indent=2)
            self.logger.info(f"Created default mock data at {self.mock_data_path}")
        except Exception as e:
            self.logger.error(f"Failed to save default mock data: {e}")

        self.mock_data = default_data

    def _normalize_task_name(self, task_name: str) -> str:
        """P0: Normalize task names to canonical form"""
        normalized = task_name.lower().strip()

        # FIXED: Removed duplicate mapping key
        task_mappings = {
            "drug_safety_lookup": ["safety_lookup", "drug_safety"],
            "drug_class_lookup": ["class_lookup", "get_drug_class"],
            "drugbank_query": ["query_drugbank", "drugbank_search"],
            "get_drug_info": ["drug_info", "drug_information", "get_drug"],
            "check_drug_interactions": [
                "interactions",
                "drug_interactions",
                "interaction_check",
            ],
            "search_drugs": ["drug_search", "search", "find_drugs"],
            "get_pa_criteria": [
                "pa_criteria",
                "prior_auth_criteria",
                "prior_authorization",
            ],
            "check_drug_safety": ["drug_safety_check", "safety_check", "check_safety"],
        }

        # Check exact matches first
        for canonical, variations in task_mappings.items():
            if normalized == canonical or normalized in variations:
                return canonical

        # Check partial matches
        for canonical, variations in task_mappings.items():
            # Check if any key terms are in the task name
            key_terms = canonical.split("_")
            if any(term in normalized for term in key_terms):
                return canonical

            for var in variations:
                if var in normalized:
                    return canonical

        return normalized

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for task processing"""
        try:
            # P0: Normalize task name
            raw_task_type = task_data.get("task_name", "").lower()
            task_type = self._normalize_task_name(raw_task_type)

            self.logger.info(f"Processing task: '{raw_task_type}' -> normalized: '{task_type}'")

            # FIXED: Route drug_safety_lookup and check_drug_safety to safety handler
            if task_type in ("drug_safety_lookup", "check_drug_safety"):
                return self._handle_drug_safety(task_data)
            elif task_type == "get_drug_info":
                return self._handle_drug_info_request(task_data)
            elif task_type == "check_drug_interactions":
                return self._handle_interaction_check(task_data)
            elif task_type in ["search_drugs", "drugbank_query"]:
                return self._handle_drug_search(task_data)
            elif task_type == "get_pa_criteria":
                return self._handle_pa_criteria_request(task_data)
            elif task_type == "drug_class_lookup":
                return self._handle_drug_class_lookup(task_data)
            else:
                return {
                    "status": "FAILED",
                    "error": f"Unknown task type: {task_type}",
                    "raw_task_type": raw_task_type,
                    "supported_tasks": CAPABILITIES,
                    "agent_id": self.agent_id,
                }

        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _handle_drug_safety(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """ADDED: Dedicated handler for drug safety checks"""
        drug_name = task_data.get("drug_name", "").strip()

        if not drug_name:
            return {
                "status": "FAILED",
                "error": "No drug name provided",
                "agent_id": self.agent_id,
            }

        # Normalize drug name
        drug_name = self._normalize_drug_name(drug_name)

        # Get full drug info
        info_resp = self._handle_drug_info_request({"drug_name": drug_name})

        if info_resp.get("status") != "COMPLETED":
            return info_resp

        drug_info = info_resp.get("drug_info", {})

        # Extract safety-specific information
        safety_summary = {
            "drug_name": drug_name,
            "warnings": drug_info.get("warnings", []),
            "contraindications": drug_info.get("contraindications", []),
            "monitoring_requirements": drug_info.get("monitoring", []),
            "drug_class": drug_info.get("drug_class", "Unknown"),
            "safety_profile": self._assess_safety_profile(drug_info),
        }

        return {
            "status": "COMPLETED",
            "drug_name": drug_name,
            "safety_summary": safety_summary,
            "agent_id": self.agent_id,
        }

    def _assess_safety_profile(self, drug_info: Dict[str, Any]) -> str:
        """Assess overall safety profile based on warnings and contraindications"""
        warnings_count = len(drug_info.get("warnings", []))
        contraindications_count = len(drug_info.get("contraindications", []))

        # Simple heuristic for safety profile
        if contraindications_count >= 5 or warnings_count >= 5:
            return "High Risk - Multiple warnings/contraindications"
        elif contraindications_count >= 3 or warnings_count >= 3:
            return "Moderate Risk - Several precautions needed"
        elif contraindications_count >= 1 or warnings_count >= 1:
            return "Low Risk - Standard precautions apply"
        else:
            return "Minimal Risk - Well tolerated"

    def _handle_drug_class_lookup(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """P0: Handle drug class lookup requests"""
        drug_name = task_data.get("drug_name", "").strip()

        if not drug_name:
            return {
                "status": "FAILED",
                "error": "No drug name provided",
                "agent_id": self.agent_id,
            }

        # Normalize drug name
        drug_name = self._normalize_drug_name(drug_name)

        try:
            # Get drug ID and details
            drug_id = self._get_drug_id(drug_name)
            if drug_id:
                drug_details = self._get_drug_details(drug_id)
                if drug_details:
                    return {
                        "status": "COMPLETED",
                        "drug_name": drug_name,
                        "drug_class": drug_details.get("drug_class", "Unknown"),
                        "agent_id": self.agent_id,
                    }

            # Check fallback data - FIXED: Use lowercase
            fallback_key = drug_name.lower()
            if fallback_key in self.fallback_data:
                return {
                    "status": "COMPLETED",
                    "drug_name": drug_name,
                    "drug_class": self.fallback_data[fallback_key].get("drug_class", "Unknown"),
                    "source": "fallback",
                    "agent_id": self.agent_id,
                }

            return {
                "status": "NOT_FOUND",
                "drug_name": drug_name,
                "message": f"Drug class not found for '{drug_name}'",
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to lookup drug class: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    @lru_cache(maxsize=128)
    def _handle_drug_info_request_cached(self, drug_name: str) -> Dict[str, Any]:
        """P0: Cached version of drug info request"""
        # This is the actual implementation, separated for caching
        return self._get_drug_info_internal(drug_name)

    def _handle_drug_info_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve comprehensive drug information"""
        drug_name = task_data.get("drug_name", "").strip()

        if not drug_name:
            return {
                "status": "FAILED",
                "error": "No drug name provided",
                "agent_id": self.agent_id,
            }

        # P2: Normalize drug name
        drug_name = self._normalize_drug_name(drug_name)

        try:
            # P0: Use LRU cache - FIXED: Deep copy to avoid mutation
            cached_result = copy.deepcopy(self._handle_drug_info_request_cached(drug_name))
            if cached_result["status"] == "COMPLETED":
                cached_result["source"] = "cache"

            return cached_result

        except Exception as e:
            self.logger.error(f"Failed to get drug info for {drug_name}: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _get_drug_info_internal(self, drug_name: str) -> Dict[str, Any]:
        """Internal method to get drug info (called by cached method)"""
        try:
            # Check memory first
            cached_info = self._get_cached_drug_info(drug_name)
            if cached_info:
                self.logger.info(f"Retrieved {drug_name} info from memory cache")
                return {
                    "status": "COMPLETED",
                    "drug_info": cached_info,
                    "source": "memory_cache",
                    "agent_id": self.agent_id,
                }

            # Try API if enabled (with rate limiting)
            if self.api_enabled:
                try:
                    self._wait_for_rate_limit()
                    # API call would go here
                    # For now, fall through to mock data
                except Exception as e:
                    self.logger.warning(f"API call failed: {e}")
                    # FIXED: Remove rate limit token on failure
                    with self.rate_limit_lock:
                        if self.last_api_calls:
                            self.last_api_calls.pop()

            # Get DrugBank ID from mock data
            drug_id = self._get_drug_id(drug_name)
            if not drug_id:
                # P1: Try fallback data - FIXED: Use lowercase
                fallback_key = drug_name.lower()
                if fallback_key in self.fallback_data:
                    fallback_info = self.fallback_data[fallback_key]
                    drug_info = {
                        "name": drug_name,
                        "drugbank_id": fallback_info.get("drugbank_id", "Unknown"),
                        "drug_class": fallback_info.get("drug_class", "Unknown"),
                        "indications": fallback_info.get("indications", []),
                        "contraindications": fallback_info.get("contraindications", []),
                        "source": "fallback_csv",
                    }

                    self._cache_drug_info(drug_name, drug_info)

                    return {
                        "status": "COMPLETED",
                        "drug_info": drug_info,
                        "source": "fallback_data",
                        "agent_id": self.agent_id,
                    }

                return {
                    "status": "NOT_FOUND",
                    "error": f"Drug '{drug_name}' not found in database",
                    "agent_id": self.agent_id,
                }

            # Get detailed drug information
            drug_info = self._get_drug_details(drug_id)
            if not drug_info:
                drug_info = self._create_basic_drug_info(drug_name, drug_id)

            # Cache the information
            self._cache_drug_info(drug_name, drug_info)

            return {
                "status": "COMPLETED",
                "drug_info": drug_info,
                "source": "mock_data",
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Internal error getting drug info: {e}")
            raise

    def _handle_interaction_check(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for drug-drug interactions"""
        drug_names = task_data.get("drug_names", [])

        if not drug_names or len(drug_names) < 2:
            return {
                "status": "FAILED",
                "error": "At least two drug names required for interaction check",
                "agent_id": self.agent_id,
            }

        try:
            # P2: Normalize all drug names
            drug_names = [self._normalize_drug_name(name.strip()) for name in drug_names]

            # Get drug IDs for all drugs
            drug_ids = {}
            missing_drugs = []

            for drug_name in drug_names:
                drug_id = self._get_drug_id(drug_name)
                if drug_id:
                    drug_ids[drug_name] = drug_id
                else:
                    # P1: Check fallback data - FIXED: Use lowercase
                    fallback_key = drug_name.lower()
                    if fallback_key in self.fallback_data:
                        drug_ids[drug_name] = self.fallback_data[fallback_key].get(
                            "drugbank_id", f"FALLBACK_{drug_name}"
                        )
                    else:
                        missing_drugs.append(drug_name)

            if len(drug_ids) < 2:
                return {
                    "status": "PARTIAL",
                    "error": f"Could not find enough drugs in database. Missing: {missing_drugs}",
                    "found_drugs": list(drug_ids.keys()),
                    "agent_id": self.agent_id,
                }

            # Check interactions - ENHANCED: Now bidirectional
            interactions = self._check_drug_interactions_bidirectional(drug_ids)

            # Analyze severity
            severity_summary = self._analyze_interaction_severity(interactions)

            return {
                "status": "COMPLETED",
                "drug_count": len(drug_ids),
                "checked_drugs": list(drug_ids.keys()),
                "missing_drugs": missing_drugs,
                "interactions": interactions,
                "severity_summary": severity_summary,
                "highest_severity": severity_summary.get("highest_severity", "none"),
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to check interactions: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _check_drug_interactions_bidirectional(self, drug_ids: Dict[str, str]) -> List[Dict[str, Any]]:
        """ENHANCED: Check for interactions between multiple drugs - bidirectional"""
        interactions = []
        checked_pairs = set()

        # Check all unique pairs
        drug_list = list(drug_ids.items())
        for i in range(len(drug_list)):
            for j in range(i + 1, len(drug_list)):
                drug1_name, drug1_id = drug_list[i]
                drug2_name, drug2_id = drug_list[j]

                # Create sorted pair to track
                pair = tuple(sorted([drug1_name, drug2_name]))
                if pair in checked_pairs:
                    continue

                checked_pairs.add(pair)

                # Check drug1 -> drug2
                drug1_interactions = self.mock_data.get("drug_interactions", {}).get(drug1_id, [])
                for interaction in drug1_interactions:
                    if interaction.get("drugbank_id") == drug2_id:
                        # FIXED: Use management from data or default
                        management = interaction.get("management")
                        if not management:
                            severity = interaction.get("severity", "unknown")
                            management = self.default_management.get(severity, "Monitor therapy")

                        interactions.append(
                            {
                                "drugs": list(pair),
                                "description": interaction.get("description", "Interaction detected"),
                                "severity": interaction.get("severity", "unknown"),
                                "management": management,
                                "direction": f"{drug1_name} → {drug2_name}",
                            }
                        )
                        break
                else:
                    # If not found, check drug2 -> drug1
                    drug2_interactions = self.mock_data.get("drug_interactions", {}).get(drug2_id, [])
                    for interaction in drug2_interactions:
                        if interaction.get("drugbank_id") == drug1_id:
                            # FIXED: Use management from data or default
                            management = interaction.get("management")
                            if not management:
                                severity = interaction.get("severity", "unknown")
                                management = self.default_management.get(severity, "Monitor therapy")

                            interactions.append(
                                {
                                    "drugs": list(pair),
                                    "description": interaction.get("description", "Interaction detected"),
                                    "severity": interaction.get("severity", "unknown"),
                                    "management": management,
                                    "direction": f"{drug2_name} → {drug1_name}",
                                }
                            )
                            break

        return interactions

    def _handle_drug_search(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for drugs by various criteria"""
        search_query = task_data.get("query", "").strip()
        search_type = task_data.get("search_type", "name")  # name, class, indication

        if not search_query:
            return {
                "status": "FAILED",
                "error": "No search query provided",
                "agent_id": self.agent_id,
            }

        try:
            results = []

            if search_type == "name":
                # Search by drug name (partial match)
                for name, drug_id in self.mock_data.get("drug_search", {}).items():
                    if search_query.lower() in name.lower():
                        drug_details = self._get_drug_details(drug_id)
                        results.append(
                            {
                                "drug_name": name,
                                "drug_id": drug_id,
                                "drug_class": drug_details.get("drug_class", "Unknown") if drug_details else "Unknown",
                            }
                        )

                # Also search fallback data - FIXED: Consistent case handling
                for name_lower, drug_data in self.fallback_data.items():
                    if search_query.lower() in name_lower:  # Both are lowercase now
                        # Check if not already in results
                        if not any(r["drug_name"].lower() == name_lower for r in results):
                            results.append(
                                {
                                    "drug_name": name_lower.title(),  # Capitalize for display
                                    "drug_id": drug_data.get("drugbank_id", "Unknown"),
                                    "drug_class": drug_data.get("drug_class", "Unknown"),
                                    "source": "fallback",
                                }
                            )

            elif search_type == "class":
                # Search by drug class
                for drug_id, details in self.mock_data.get("drug_details", {}).items():
                    if search_query.lower() in details.get("drug_class", "").lower():
                        results.append(
                            {
                                "drug_name": details["name"],
                                "drug_id": drug_id,
                                "drug_class": details["drug_class"],
                            }
                        )

                # Search fallback data by class
                for name_lower, drug_data in self.fallback_data.items():
                    if search_query.lower() in drug_data.get("drug_class", "").lower():
                        if not any(r["drug_name"].lower() == name_lower for r in results):
                            results.append(
                                {
                                    "drug_name": name_lower.title(),
                                    "drug_id": drug_data.get("drugbank_id", "Unknown"),
                                    "drug_class": drug_data.get("drug_class", "Unknown"),
                                    "source": "fallback",
                                }
                            )

            elif search_type == "indication":
                # Search by indication
                for drug_id, details in self.mock_data.get("drug_details", {}).items():
                    for indication in details.get("indications", []):
                        if search_query.lower() in indication.lower():
                            results.append(
                                {
                                    "drug_name": details["name"],
                                    "drug_id": drug_id,
                                    "drug_class": details["drug_class"],
                                    "matching_indication": indication,
                                }
                            )
                            break

                # FIXED: Search fallback data by indication
                for name_lower, drug_data in self.fallback_data.items():
                    for indication in drug_data.get("indications", []):
                        if search_query.lower() in indication.lower():
                            if not any(r["drug_name"].lower() == name_lower for r in results):
                                results.append(
                                    {
                                        "drug_name": name_lower.title(),
                                        "drug_id": drug_data.get("drugbank_id", "Unknown"),
                                        "drug_class": drug_data.get("drug_class", "Unknown"),
                                        "matching_indication": indication,
                                        "source": "fallback",
                                    }
                                )
                                break

            # Use debug level for large result sets
            if len(results) > 10:
                self.logger.debug(f"Found {len(results)} drugs matching '{search_query}'")
            else:
                self.logger.info(f"Found {len(results)} drugs matching '{search_query}'")

            return {
                "status": "COMPLETED",
                "search_query": search_query,
                "search_type": search_type,
                "result_count": len(results),
                "results": results[:10],  # Limit to 10 results
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to search drugs: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _handle_pa_criteria_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PA-relevant criteria for a drug"""
        drug_name = task_data.get("drug_name", "").strip()
        indication = task_data.get("indication", "").strip()

        if not drug_name:
            return {
                "status": "FAILED",
                "error": "No drug name provided",
                "agent_id": self.agent_id,
            }

        # P2: Normalize drug name
        drug_name = self._normalize_drug_name(drug_name)

        try:
            # Get drug information
            drug_id = self._get_drug_id(drug_name)
            if not drug_id:
                # FIXED: Use lowercase for fallback lookup
                fallback_key = drug_name.lower()
                if fallback_key in self.fallback_data:
                    # Use fallback data
                    fallback_info = self.fallback_data[fallback_key]
                    pa_criteria = {
                        "drug_name": drug_name,
                        "drug_class": fallback_info.get("drug_class", "Unknown"),
                        "fda_approved_indications": fallback_info.get("indications", []),
                        "contraindications": fallback_info.get("contraindications", []),
                        "source": "fallback",
                        "pa_recommendations": ["Limited data available - verify with current resources"],
                    }

                    return {
                        "status": "COMPLETED",
                        "drug_name": drug_name,
                        "indication": indication,
                        "pa_criteria": pa_criteria,
                        "agent_id": self.agent_id,
                    }

            if not drug_id:
                return {
                    "status": "NOT_FOUND",
                    "error": f"Drug '{drug_name}' not found",
                    "agent_id": self.agent_id,
                }

            drug_details = self._get_drug_details(drug_id)
            if not drug_details:
                return {
                    "status": "NOT_FOUND",
                    "error": f"No details available for '{drug_name}'",
                    "agent_id": self.agent_id,
                }

            # Extract PA criteria
            pa_criteria = self._extract_pa_criteria(drug_details, indication)

            return {
                "status": "COMPLETED",
                "drug_name": drug_name,
                "indication": indication,
                "pa_criteria": pa_criteria,
                "agent_id": self.agent_id,
            }

        except Exception as e:
            self.logger.error(f"Failed to extract PA criteria: {e}")
            return {"status": "FAILED", "error": str(e), "agent_id": self.agent_id}

    def _get_drug_id(self, drug_name: str) -> Optional[str]:
        """Get DrugBank ID for a drug name - IMPROVED: Better matching logic"""
        # Case-insensitive lookup
        drug_name_lower = drug_name.lower().strip()

        # First try exact match
        for name, dbid in self.mock_data.get("drug_search", {}).items():
            if name.lower() == drug_name_lower:
                self.logger.debug(f"Found DrugBank ID '{dbid}' for '{drug_name}' (exact match)")
                return dbid

        # Then try prefix match (safer than substring)
        for name, dbid in self.mock_data.get("drug_search", {}).items():
            if name.lower().startswith(drug_name_lower) or drug_name_lower.startswith(name.lower()):
                self.logger.debug(f"Found DrugBank ID '{dbid}' for '{drug_name}' (prefix match)")
                return dbid

        self.logger.warning(f"No DrugBank ID found for '{drug_name}'")
        return None

    def _get_drug_details(self, drug_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed drug information by DrugBank ID"""
        return self.mock_data.get("drug_details", {}).get(drug_id)

    def _create_basic_drug_info(self, drug_name: str, drug_id: str) -> Dict[str, Any]:
        """Create basic drug info structure when detailed info is not available"""
        return {
            "name": drug_name,
            "drugbank_id": drug_id,
            "drug_class": "Not specified",
            "indications": [],
            "contraindications": [],
            "warnings": [],
            "common_dosing": {},
            "monitoring": [],
            "data_completeness": "basic",
        }

    def _analyze_interaction_severity(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the severity of drug interactions - FIXED: Proper none handling"""
        if not interactions:
            return {
                "highest_severity": "none",
                "severity_counts": {},
                "clinical_significance": "No interactions found",
            }

        severity_counts = {}
        highest_severity = "none"  # Fixed: Default to "none" not "unknown"
        highest_severity_level = 0

        for interaction in interactions:
            severity = interaction.get("severity", "unknown").lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Check if this is the highest severity so far
            level = self.severity_levels.get(severity, 0)
            if level > highest_severity_level:
                highest_severity_level = level
                highest_severity = severity

        # Determine clinical significance
        if highest_severity in ["contraindicated", "major"]:
            clinical_significance = "Clinically significant - May require therapy modification"
        elif highest_severity == "moderate":
            clinical_significance = "Potentially significant - Monitor therapy closely"
        else:
            clinical_significance = "Minor clinical significance - Monitor as appropriate"

        return {
            "highest_severity": highest_severity,
            "severity_counts": severity_counts,
            "total_interactions": len(interactions),
            "clinical_significance": clinical_significance,
        }

    def _extract_pa_criteria(self, drug_details: Dict[str, Any], indication: str) -> Dict[str, Any]:
        """Extract PA-relevant criteria from drug details"""
        pa_criteria = {
            "drug_name": drug_details.get("name", ""),
            "drug_class": drug_details.get("drug_class", ""),
            "fda_approved_indications": drug_details.get("indications", []),
            "contraindications": drug_details.get("contraindications", []),
            "warnings": drug_details.get("warnings", []),
            "monitoring_requirements": drug_details.get("monitoring", []),
            "dosing_information": {},
        }

        # Check if the requested indication is FDA approved
        if indication:
            indication_lower = indication.lower()
            approved_for_indication = any(
                indication_lower in approved_ind.lower() for approved_ind in pa_criteria["fda_approved_indications"]
            )
            pa_criteria["requested_indication_approved"] = approved_for_indication
            pa_criteria["requested_indication"] = indication

        # Get relevant dosing information
        common_dosing = drug_details.get("common_dosing", {})
        if indication and common_dosing:
            # Try to find indication-specific dosing
            for dosing_key, dosing_info in common_dosing.items():
                if indication.lower() in dosing_key.lower():
                    pa_criteria["dosing_information"]["indication_specific"] = dosing_info
                    break

            # Include all dosing as fallback
            if not pa_criteria["dosing_information"]:
                pa_criteria["dosing_information"] = common_dosing
        else:
            pa_criteria["dosing_information"] = common_dosing

        # Generate PA recommendations
        pa_criteria["pa_recommendations"] = self._generate_pa_recommendations(pa_criteria)

        return pa_criteria

    def _generate_pa_recommendations(self, pa_criteria: Dict[str, Any]) -> List[str]:
        """Generate PA recommendations based on drug criteria"""
        recommendations = []

        # Check if indication is approved
        if pa_criteria.get("requested_indication_approved") is False:
            recommendations.append("Off-label use - Ensure appropriate documentation and justification")

        # Check for contraindications that might affect PA
        high_risk_contraindications = ["pregnancy", "renal", "hepatic", "dialysis"]
        for contraindication in pa_criteria.get("contraindications", []):
            if any(risk in contraindication.lower() for risk in high_risk_contraindications):
                recommendations.append(f"Verify patient does not have: {contraindication}")

        # Check for monitoring requirements
        if pa_criteria.get("monitoring_requirements"):
            recommendations.append(
                "Ensure monitoring plan is in place for: " + ", ".join(pa_criteria["monitoring_requirements"][:3])
            )

        # Check drug class for specific requirements
        drug_class = pa_criteria.get("drug_class", "").lower()
        if "sglt2" in drug_class:
            recommendations.append("Verify eGFR is appropriate for SGLT2 inhibitor use")
            recommendations.append("Confirm no history of diabetic ketoacidosis")
        elif "glp-1" in drug_class:
            recommendations.append("Verify no personal/family history of medullary thyroid carcinoma")
            recommendations.append("Document previous diabetes therapy trials if applicable")

        return recommendations

    def _get_cached_drug_info(self, drug_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve drug information from cache/memory"""
        # Check in-memory cache first - FIXED: Thread-safe access
        with self.cache_lock:
            if drug_name.lower() in self.drug_cache:
                # Move to end (LRU behavior)
                self.drug_cache.move_to_end(drug_name.lower())
                return self.drug_cache[drug_name.lower()]

        # Check persistent memory if available
        if self.memory_manager:
            try:
                results = self.memory_manager.collection.get(where={"drug_name": drug_name.lower()}, limit=1)
                if results and results["documents"]:
                    # FIXED: Parse the stored JSON and extract info
                    wrapper = json.loads(results["documents"][0])
                    return wrapper.get("info", wrapper)  # Backward-safe extraction
            except Exception as e:
                self.logger.debug(f"Could not retrieve from memory: {e}")

        return None

    def _cache_drug_info(self, drug_name: str, drug_info: Dict[str, Any]):
        """Cache drug information for future use - ENHANCED: Thread-safe with LRU eviction"""
        # FIXED: Deep copy before caching to prevent mutation
        drug_info_copy = copy.deepcopy(drug_info)

        # Store in memory cache with thread safety
        with self.cache_lock:
            # Implement LRU eviction
            if len(self.drug_cache) >= self.max_cache_size:
                # Remove oldest item
                self.drug_cache.popitem(last=False)

            # Add new item
            self.drug_cache[drug_name.lower()] = drug_info_copy

        # Store in persistent memory if available
        if self.memory_manager:
            try:
                doc_id = f"drug_{drug_name.lower().replace(' ', '_')}"
                doc_content = {"drug": drug_name, "info": drug_info_copy}

                self.memory_manager.collection.upsert(
                    ids=[doc_id],
                    documents=[json.dumps(doc_content)],
                    metadatas=[
                        {
                            "drug_name": drug_name.lower(),
                            "drugbank_id": drug_info_copy.get("drugbank_id", ""),
                            "drug_class": drug_info_copy.get("drug_class", ""),
                            "cached_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ],
                )
                self.logger.debug(f"Cached drug info for {drug_name}")
            except Exception as e:
                self.logger.warning(f"Could not cache to memory: {e}")

    def is_healthy(self) -> bool:
        """P2: Health check method"""
        try:
            # Check if mock data is loaded
            if not hasattr(self, "mock_data") or not self.mock_data:
                return False

            # Check if we can perform a basic lookup
            test_drug = "metformin"
            drug_id = self._get_drug_id(test_drug)

            return drug_id is not None
        except Exception:
            return False
