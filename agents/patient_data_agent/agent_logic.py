import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict, field
import hashlib
from concurrent.futures import ThreadPoolExecutor
import copy
import threading
import re
from collections import OrderedDict
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

@dataclass
class PatientRecord:
    """Structured representation of a patient record"""
    patient_id: str
    name: str
    diagnoses_icd10: List[str] = field(default_factory=list)
    medication_history: List[str] = field(default_factory=list)
    labs: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    age: Optional[int] = None
    gender: Optional[str] = None
    provider_type: Optional[str] = None
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_log: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AuditEntry:
    """Audit log entry for patient data access"""
    timestamp: str
    action: str
    patient_id: str
    user_id: str
    details: Dict[str, Any]
    success: bool

class PatientDataAgentLogic:
    """
    Specialized agent for retrieving and managing patient data.
    Simulates an EMR system with enhanced security and search capabilities.
    """
    
    # FIXED: Define allowed mutable fields
    ALLOWED_MUTABLE_FIELDS = {
        'diagnoses_icd10', 'medication_history', 'labs', 'notes', 
        'age', 'gender', 'provider_type'
    }
    
    # FIXED: Define field types for validation
    FIELD_TYPES = {
        'diagnoses_icd10': (list, str),  # Can be list or string (will convert)
        'medication_history': (list, str),
        'labs': dict,
        'notes': str,
        'age': int,
        'gender': str,
        'provider_type': str
    }
    
    # FIXED: Comprehensive ICD-10 regex pattern
    ICD10_PATTERN = re.compile(r'^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-TV-Z]{1,4})?$')
    
    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        
        # Initialize memory manager if available
        self.memory_manager = None
        try:
            from core_infra.enhanced_memory_manager import EnhancedMemoryManager
            self.memory_manager = EnhancedMemoryManager()
            self.logger.info("EnhancedMemoryManager initialized for PatientDataAgent")
        except Exception as e:
            self.logger.warning(f"Could not initialize EnhancedMemoryManager: {e}")
        
        # Patient data path
        self.patient_data_path = Path(__file__).parent.parent.parent / "data" / "mock_patient_records.json"
        
        # Load patient data
        self.patient_records = {}
        self._load_patient_data()
        
        # FIXED: Thread-safe lock for all shared state
        self.data_lock = threading.RLock()
        
        # FIXED: Use LRU cache with size limit
        self._search_cache = lru_cache(maxsize=100)(self._search_patients_internal)
        self.query_cache = OrderedDict()
        self.max_cache_size = 500
        
        # Audit log with size management
        self.audit_log = []
        self.max_audit_entries = 10000
        self.audit_retention = 5000
        
        # FIXED: Add write throttling
        self._last_save_time = 0
        self._save_interval = 5.0  # Minimum seconds between saves
        self._pending_save = False
        
        # Privacy settings - ENHANCED with role-based access
        self.privacy_config = {
            "mask_sensitive_data": False,
            "require_consent": False,
            "audit_all_access": True,
            "role_based_access": True  # ADDED
        }
        
        # ADDED: Role permissions
        self.role_permissions = {
            "physician": ["read", "write", "search"],
            "nurse": ["read", "search"],
            "admin": ["read", "write", "search", "audit", "export"],
            "researcher": ["read", "search"],  # Limited, anonymized access
            "system": ["read", "write", "search", "audit", "export"]  # Full access
        }
        
        # Supported search fields
        self.searchable_fields = {
            "name", "patient_id", "diagnoses_icd10", 
            "medication_history", "age", "gender"
        }
        
        self.logger.info(f"PatientDataAgentLogic initialized for {agent_id}")

    def get_patient_record(self, patient_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific patient's record by their ID.
        Compatible with Gemini test expectations.
        """
        self.logger.info(f"Retrieving record for patient_id: '{patient_id}'")
        
        # Log access for audit - FIXED: Include system user
        self._log_access("get_patient_record", patient_id, {
            "method": "direct_id",
            "user_id": "system"
        })
        
        with self.data_lock:
            record = self.patient_records.get(patient_id)
        
        if record:
            self.logger.info(f"Found record for patient '{patient_id}'.")
            # Return in the format expected by Gemini tests
            if isinstance(record, dict):
                return {"status": "success", "record": record}
            else:
                return {"status": "success", "record": asdict(record)}
        else:
            self.logger.warning(f"No record found for patient '{patient_id}'.")
            return {"status": "not_found", "message": f"Patient record '{patient_id}' not found."}

    def _load_patient_data(self):
        """Loads the mock patient data from the local JSON file."""
        try:
            if not self.patient_data_path.exists():
                self._create_default_patient_data()
                return
            
            with open(self.patient_data_path, 'r') as f:
                raw_data = json.load(f)
            
            # Convert to PatientRecord objects for internal use
            for patient_id, record_data in raw_data.items():
                if isinstance(record_data, dict):
                    # Ensure patient_id is in the record
                    record_data['patient_id'] = patient_id
                    self.patient_records[patient_id] = record_data
                
            self.logger.info(f"Successfully loaded {len(self.patient_records)} mock patient records from {self.patient_data_path}")
            
            # Cache in memory if available
            if self.memory_manager:
                try:
                    self._cache_patient_records()
                except Exception as e:
                    self.logger.warning(f"Could not cache patient records: {e}")
                    
        except FileNotFoundError:
            self.logger.error(f"CRITICAL: Mock patient data file not found at {self.patient_data_path}.")
            self._create_default_patient_data()
        except json.JSONDecodeError as e:
            self.logger.error(f"CRITICAL: Could not parse JSON from {self.patient_data_path}: {e}")
            self._create_default_patient_data()
        except Exception as e:
            self.logger.error(f"Unexpected error loading patient data: {e}")
            self._create_default_patient_data()

    def _create_default_patient_data(self):
        """Create default patient data matching Gemini's test expectations"""
        self.logger.info("Creating default patient data...")
        
        default_data = {
            "patient-001": {
                "patient_id": "patient-001",
                "name": "John Doe",
                "diagnoses_icd10": ["I50", "E11.9"],
                "medication_history": ["Metformin", "Lisinopril"],
                "labs": {
                    "LVEF": "40%",
                    "HbA1c": "7.8%"
                },
                "notes": "Patient meets all criteria for SGLT2 inhibitor therapy.",
                "age": 65,
                "gender": "M",
                "provider_type": "Cardiologist"
            },
            "patient-002": {
                "patient_id": "patient-002",
                "name": "Jane Smith",
                "diagnoses_icd10": ["I50"],
                "medication_history": ["Lisinopril", "Aspirin"],
                "labs": {
                    "LVEF": "40%"
                },
                "notes": "Patient has not been trialed on Metformin.",
                "age": 58,
                "gender": "F",
                "provider_type": "Primary Care"
            },
            "patient-003": {
                "patient_id": "patient-003",
                "name": "Peter Jones",
                "diagnoses_icd10": ["R07.9"],
                "medication_history": ["Metformin"],
                "labs": {
                    "LVEF": "55%"
                },
                "notes": "Primary diagnosis is non-specific chest pain, does not meet criteria for HF.",
                "age": 45,
                "gender": "M",
                "provider_type": "Emergency"
            }
        }
        
        # Save default data
        try:
            self.patient_data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.patient_data_path, 'w') as f:
                json.dump(default_data, f, indent=2)
            self.logger.info(f"Created default patient data at {self.patient_data_path}")
        except Exception as e:
            self.logger.error(f"Failed to save default patient data: {e}")
        
        self.patient_records = default_data

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for task processing"""
        try:
            task_type = task_data.get('task_name', '').lower()
            
            if 'patient' in task_type and ('get' in task_type or 'retrieve' in task_type):
                return self._handle_patient_retrieval(task_data)
            elif 'search' in task_type:
                return self._handle_patient_search(task_data)
            elif 'update' in task_type:
                return self._handle_patient_update(task_data)
            elif 'audit' in task_type:
                return self._handle_audit_request(task_data)
            elif 'privacy' in task_type or 'consent' in task_type:
                return self._handle_privacy_request(task_data)
            elif 'export' in task_type:
                return self._handle_export_request(task_data)
            elif 'validate' in task_type:
                return self._handle_validation_request(task_data)
            else:
                return {
                    "status": "FAILED",
                    "error": f"Unknown task type: {task_type}",
                    "supported_tasks": [
                        "get_patient_record",
                        "search_patients",
                        "update_patient",
                        "get_audit_log",
                        "check_privacy_consent",
                        "export_patient_data",
                        "validate_patient_data"
                    ],
                    "agent_id": self.agent_id
                }
                
        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _check_permissions(self, action: str, requester_role: str) -> bool:
        """ADDED: Check if role has permission for action"""
        if not self.privacy_config.get('role_based_access', True):
            return True
        
        with self.data_lock:
            allowed_actions = self.role_permissions.get(requester_role, [])
        
        # Map detailed actions to permission categories
        action_mapping = {
            'get_patient_record': 'read',
            'search_patients': 'search',
            'update_patient': 'write',
            'get_audit_log': 'audit',
            'export_patient_data': 'export'
        }
        
        required_permission = action_mapping.get(action, action)
        return required_permission in allowed_actions

    def _handle_patient_retrieval(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient record retrieval"""
        patient_id = task_data.get('patient_id', '').strip()
        requester_id = task_data.get('requester_id', 'unknown')
        requester_role = task_data.get('requester_role', 'nurse')  # Default to limited role
        
        if not patient_id:
            return {
                "status": "FAILED",
                "error": "No patient_id provided",
                "agent_id": self.agent_id
            }
        
        # FIXED: Check permissions
        if not self._check_permissions('get_patient_record', requester_role):
            return {
                "status": "FORBIDDEN",
                "error": f"Role '{requester_role}' does not have read permission",
                "agent_id": self.agent_id
            }
        
        try:
            # Use the public method for compatibility
            result = self.get_patient_record(patient_id)
            
            if result['status'] == 'success':
                # Apply privacy filters based on role
                filtered_record = self._apply_privacy_filters(
                    result['record'], 
                    requester_id,
                    requester_role
                )
                
                return {
                    "status": "COMPLETED",
                    "patient_id": patient_id,
                    "patient_data": filtered_record,
                    "retrieval_time": datetime.now(timezone.utc).isoformat(),
                    "agent_id": self.agent_id
                }
            else:
                return {
                    "status": "NOT_FOUND",
                    "patient_id": patient_id,
                    "message": result.get('message', 'Patient not found'),
                    "agent_id": self.agent_id
                }
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve patient {patient_id}: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_patient_search(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient search by various criteria"""
        search_criteria = task_data.get('criteria', {})
        max_results = task_data.get('max_results', 10)
        requester_id = task_data.get('requester_id', 'unknown')
        requester_role = task_data.get('requester_role', 'nurse')
        page = task_data.get('page', 1)  # ADDED: Pagination
        page_size = task_data.get('page_size', 10)
        
        # FIXED: Check permissions
        if not self._check_permissions('search_patients', requester_role):
            return {
                "status": "FORBIDDEN",
                "error": f"Role '{requester_role}' does not have search permission",
                "agent_id": self.agent_id
            }
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(search_criteria)
            
            with self.data_lock:
                if cache_key in self.query_cache:
                    self.logger.info("Retrieved search results from cache")
                    cached_results = self.query_cache[cache_key]
                    
                    # ADDED: Apply pagination
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    paginated_results = cached_results[start_idx:end_idx]
                    
                    return {
                        "status": "COMPLETED",
                        "search_criteria": search_criteria,
                        "result_count": len(cached_results),
                        "page": page,
                        "page_size": page_size,
                        "total_pages": (len(cached_results) + page_size - 1) // page_size,
                        "results": paginated_results,
                        "source": "cache",
                        "agent_id": self.agent_id
                    }
            
            # Perform search
            results = self._search_patients(search_criteria)
            
            # Cache results with size limit
            self._cache_search_results(cache_key, results)
            
            # Log search for audit - FIXED: Include user ID
            self._log_access("search_patients", "multiple", {
                "user_id": requester_id,
                "criteria": search_criteria,
                "result_count": len(results)
            })
            
            # ADDED: Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_results = results[start_idx:end_idx]
            
            return {
                "status": "COMPLETED",
                "search_criteria": search_criteria,
                "result_count": len(results),
                "page": page,
                "page_size": page_size,
                "total_pages": (len(results) + page_size - 1) // page_size,
                "results": paginated_results,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to search patients: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_patient_update(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient data updates"""
        patient_id = task_data.get('patient_id', '').strip()
        updates = task_data.get('updates', {})
        requester_id = task_data.get('requester_id', 'unknown')
        requester_role = task_data.get('requester_role', 'nurse')
        
        if not patient_id:
            return {
                "status": "FAILED",
                "error": "No patient_id provided",
                "agent_id": self.agent_id
            }
        
        if not updates:
            return {
                "status": "FAILED",
                "error": "No updates provided",
                "agent_id": self.agent_id
            }
        
        # FIXED: Check permissions
        if not self._check_permissions('update_patient', requester_role):
            return {
                "status": "FORBIDDEN",
                "error": f"Role '{requester_role}' does not have write permission",
                "agent_id": self.agent_id
            }
        
        try:
            with self.data_lock:
                # Check if patient exists
                if patient_id not in self.patient_records:
                    return {
                        "status": "NOT_FOUND",
                        "patient_id": patient_id,
                        "message": "Patient not found",
                        "agent_id": self.agent_id
                    }
                
                # Validate updates
                validation_result = self._validate_updates(updates)
                if not validation_result['valid']:
                    return {
                        "status": "FAILED",
                        "error": f"Invalid updates: {validation_result['errors']}",
                        "agent_id": self.agent_id
                    }
                
                # Apply updates
                updated_record = self._apply_updates(patient_id, updates)
            
            # FIXED: Clear cache after update
            self._invalidate_cache()
            
            # Log update for audit - FIXED: Include user ID
            self._log_access("update_patient", patient_id, {
                "user_id": requester_id,
                "updates": updates,
                "fields_updated": list(updates.keys())
            })
            
            return {
                "status": "COMPLETED",
                "patient_id": patient_id,
                "updated_record": updated_record,
                "fields_updated": list(updates.keys()),
                "update_time": datetime.now(timezone.utc).isoformat(),
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update patient {patient_id}: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_audit_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle audit log requests"""
        patient_id = task_data.get('patient_id')
        action_type = task_data.get('action_type')
        start_time = task_data.get('start_time')
        end_time = task_data.get('end_time')
        requester_id = task_data.get('requester_id', 'unknown')
        requester_role = task_data.get('requester_role', 'nurse')
        redact_user_ids = task_data.get('redact_user_ids', False)  # ADDED
        
        # FIXED: Check permissions
        if not self._check_permissions('get_audit_log', requester_role):
            return {
                "status": "FORBIDDEN",
                "error": f"Role '{requester_role}' does not have audit permission",
                "agent_id": self.agent_id
            }
        
        try:
            # Filter audit log
            filtered_log = self._filter_audit_log(
                patient_id=patient_id,
                action_type=action_type,
                start_time=start_time,
                end_time=end_time
            )
            
            # FIXED: Redact user IDs if requested
            if redact_user_ids:
                filtered_log = [
                    {**entry, 'user_id': 'REDACTED'} 
                    for entry in filtered_log
                ]
            
            return {
                "status": "COMPLETED",
                "audit_entries": filtered_log,
                "entry_count": len(filtered_log),
                "filters_applied": {
                    "patient_id": patient_id,
                    "action_type": action_type,
                    "time_range": f"{start_time} to {end_time}" if start_time else "all"
                },
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve audit log: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_privacy_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle privacy and consent checks"""
        patient_id = task_data.get('patient_id', '').strip()
        action = task_data.get('action', 'check_consent')
        
        if not patient_id:
            return {
                "status": "FAILED",
                "error": "No patient_id provided",
                "agent_id": self.agent_id
            }
        
        try:
            if action == 'check_consent':
                consent_status = self._check_patient_consent(patient_id)
                return {
                    "status": "COMPLETED",
                    "patient_id": patient_id,
                    "consent_status": consent_status,
                    "agent_id": self.agent_id
                }
            elif action == 'update_consent':
                consent_type = task_data.get('consent_type', 'general')
                consent_value = task_data.get('consent_value', False)
                result = self._update_patient_consent(patient_id, consent_type, consent_value)
                return {
                    "status": "COMPLETED",
                    "patient_id": patient_id,
                    "consent_updated": result,
                    "agent_id": self.agent_id
                }
            else:
                return {
                    "status": "FAILED",
                    "error": f"Unknown privacy action: {action}",
                    "agent_id": self.agent_id
                }
                
        except Exception as e:
            self.logger.error(f"Failed to handle privacy request: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_export_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient data export requests"""
        patient_ids = task_data.get('patient_ids', [])
        export_format = task_data.get('format', 'json')
        include_audit = task_data.get('include_audit', False)
        requester_id = task_data.get('requester_id', 'unknown')
        requester_role = task_data.get('requester_role', 'nurse')
        redact_audit_users = task_data.get('redact_audit_users', True)  # ADDED
        
        # FIXED: Check permissions
        if not self._check_permissions('export_patient_data', requester_role):
            return {
                "status": "FORBIDDEN",
                "error": f"Role '{requester_role}' does not have export permission",
                "agent_id": self.agent_id
            }
        
        try:
            if not patient_ids:
                # Export all patients if no specific IDs provided
                patient_ids = list(self.patient_records.keys())
            
            export_data = {
                "export_time": datetime.now(timezone.utc).isoformat(),
                "patient_count": len(patient_ids),
                "patients": {}
            }
            
            with self.data_lock:
                for patient_id in patient_ids:
                    if patient_id in self.patient_records:
                        patient_data = copy.deepcopy(self.patient_records[patient_id])
                        
                        # Apply privacy filters
                        patient_data = self._apply_privacy_filters(
                            patient_data, 
                            requester_id,
                            requester_role
                        )
                        
                        export_data["patients"][patient_id] = patient_data
                        
                        if include_audit:
                            audit_entries = self._filter_audit_log(patient_id=patient_id)
                            # FIXED: Redact user IDs in audit log
                            if redact_audit_users:
                                audit_entries = [
                                    {**entry, 'user_id': 'REDACTED'} 
                                    for entry in audit_entries
                                ]
                            export_data["patients"][patient_id]["audit_log"] = audit_entries
            
            # Format export based on requested format
            if export_format == 'json':
                formatted_export = json.dumps(export_data, indent=2)
            else:
                formatted_export = export_data
            
            return {
                "status": "COMPLETED",
                "export_format": export_format,
                "patient_count": len(export_data["patients"]),
                "export_data": formatted_export if export_format == 'json' else export_data,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export patient data: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _handle_validation_request(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle patient data validation requests"""
        patient_id = task_data.get('patient_id')
        validation_type = task_data.get('validation_type', 'complete')
        
        try:
            if patient_id:
                # Validate specific patient
                if patient_id not in self.patient_records:
                    return {
                        "status": "NOT_FOUND",
                        "patient_id": patient_id,
                        "message": "Patient not found",
                        "agent_id": self.agent_id
                    }
                
                validation_result = self._validate_patient_record(
                    self.patient_records[patient_id],
                    validation_type
                )
                
                return {
                    "status": "COMPLETED",
                    "patient_id": patient_id,
                    "validation_type": validation_type,
                    "is_valid": validation_result['valid'],
                    "issues": validation_result.get('issues', []),
                    "agent_id": self.agent_id
                }
            else:
                # Validate all patients
                validation_results = {}
                invalid_count = 0
                
                with self.data_lock:
                    for pid, record in self.patient_records.items():
                        result = self._validate_patient_record(record, validation_type)
                        validation_results[pid] = result
                        if not result['valid']:
                            invalid_count += 1
                
                return {
                    "status": "COMPLETED",
                    "validation_type": validation_type,
                    "total_patients": len(self.patient_records),
                    "invalid_count": invalid_count,
                    "validation_results": validation_results,
                    "agent_id": self.agent_id
                }
                
        except Exception as e:
            self.logger.error(f"Failed to validate patient data: {e}")
            return {
                "status": "FAILED",
                "error": str(e),
                "agent_id": self.agent_id
            }

    def _search_patients(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search patients by various criteria"""
        results = []
        
        with self.data_lock:
            for patient_id, record in self.patient_records.items():
                if self._matches_criteria(record, criteria):
                    results.append({
                        'patient_id': patient_id,
                        'name': record.get('name', 'Unknown'),
                        'match_score': self._calculate_match_score(record, criteria)
                    })
        
        # Sort by match score
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return results

    def _search_patients_internal(self, criteria_json: str) -> List[Dict[str, Any]]:
        """Internal search method for LRU caching"""
        criteria = json.loads(criteria_json)
        return self._search_patients(criteria)

    def _matches_criteria(self, record: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if patient record matches search criteria"""
        for field, value in criteria.items():
            if field not in self.searchable_fields:
                continue
            
            record_value = record.get(field)
            
            if field == 'diagnoses_icd10':
                # FIXED: Case-insensitive list matching
                if not self._list_contains_any(record_value or [], value):
                    return False
            elif field == 'medication_history':
                # FIXED: Case-insensitive list matching
                if not self._list_contains_any(record_value or [], value):
                    return False
            elif field == 'age':
                # Support age ranges
                if isinstance(value, dict):
                    min_age = value.get('min', 0)
                    max_age = value.get('max', 150)
                    if not (min_age <= (record_value or 0) <= max_age):
                        return False
                elif record_value != value:
                    return False
            elif field == 'name':
                # FIXED: Use partial matching for name
                if value.lower() not in str(record_value).lower():
                    return False
            else:
                # Simple string matching
                if str(record_value).lower() != str(value).lower():
                    return False
        
        return True

    def _list_contains_any(self, haystack: List[str], needles: Any) -> bool:
        """ADDED: Case-insensitive list matching helper"""
        if isinstance(needles, str):
            needles = [needles]
        elif not isinstance(needles, list):
            return False
        
        needles_lower = [n.lower() for n in needles]
        haystack_lower = [h.lower() for h in haystack]
        
        return any(needle in haystack_lower for needle in needles_lower)

    def _calculate_match_score(self, record: Dict[str, Any], criteria: Dict[str, Any]) -> float:
        """Calculate how well a record matches the search criteria"""
        score = 0.0
        max_score = len(criteria)
        
        for field, value in criteria.items():
            if field in record:
                if record[field] == value:
                    score += 1.0
                elif isinstance(record[field], list) and value in record[field]:
                    score += 0.8
                elif isinstance(record[field], str) and str(value).lower() in record[field].lower():
                    score += 0.5
        
        return score / max_score if max_score > 0 else 0.0

    def _apply_updates(self, patient_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply updates to patient record"""
        record = copy.deepcopy(self.patient_records[patient_id])
        
        # Apply each update
        for field, value in updates.items():
            if field in ['diagnoses_icd10', 'medication_history']:
                # For list fields, append if not already present
                if field not in record:
                    record[field] = []
                if isinstance(value, list):
                    record[field].extend([v for v in value if v not in record[field]])
                else:
                    if value not in record[field]:
                        record[field].append(value)
            elif field == 'labs':
                # For lab values, update or add
                if field not in record:
                    record[field] = {}
                record[field].update(value)
            else:
                # Simple field update
                record[field] = value
        
        # Update last_updated timestamp
        record['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        # Save back to records
        self.patient_records[patient_id] = record
        
        # Update persistent storage with throttling
        self._save_patient_records_throttled()
        
        return record

    def _validate_updates(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Validate proposed updates"""
        errors = []
        
        # Check for protected fields
        protected_fields = ['patient_id', 'created_at', 'access_log', 'last_updated']
        for field in protected_fields:
            if field in updates:
                errors.append(f"Cannot update protected field: {field}")
        
        # FIXED: Check for unknown fields
        for field in updates:
            if field not in self.ALLOWED_MUTABLE_FIELDS:
                errors.append(f"Unknown/immutable field: {field}")
        
        # FIXED: Validate data types for all fields
        for field, value in updates.items():
            if field in self.FIELD_TYPES:
                expected_types = self.FIELD_TYPES[field]
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)
                
                if not isinstance(value, expected_types):
                    errors.append(f"Field '{field}' must be of type {expected_types}, got {type(value)}")
                
                # Additional specific validations
                if field == 'age' and isinstance(value, int):
                    if value < 0 or value > 150:
                        errors.append("Age must be between 0 and 150")
                
                if field == 'gender' and isinstance(value, str):
                    if value not in ['M', 'F', 'O', 'U']:  # Male, Female, Other, Unknown
                        errors.append("Gender must be one of: M, F, O, U")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    def _validate_patient_record(self, record: Dict[str, Any], validation_type: str) -> Dict[str, Any]:
        """Validate a patient record"""
        issues = []
        
        # Required fields validation
        required_fields = ['patient_id', 'name']
        for field in required_fields:
            if field not in record or not record[field]:
                issues.append(f"Missing required field: {field}")
        
        if validation_type == 'complete':
            # Additional validation for complete check
            if 'diagnoses_icd10' in record:
                # FIXED: Use comprehensive ICD-10 validation
                for code in record.get('diagnoses_icd10', []):
                    if not isinstance(code, str):
                        issues.append(f"ICD-10 code must be string: {code}")
                    elif not self.ICD10_PATTERN.match(code):
                        issues.append(f"Invalid ICD-10 code format: {code}")
            
            if 'age' in record:
                age = record.get('age')
                if not isinstance(age, int) or age < 0 or age > 150:
                    issues.append(f"Invalid age value: {age}")
            
            if 'labs' in record:
                labs = record.get('labs', {})
                if not isinstance(labs, dict):
                    issues.append("Labs field must be a dictionary")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def _apply_privacy_filters(self, record: Dict[str, Any], requester_id: str, requester_role: str = None) -> Dict[str, Any]:
        """Apply privacy filters based on requester permissions"""
        # Create filtered copy
        filtered = copy.deepcopy(record)
        
        # FIXED: Enhanced privacy filtering based on role
        if requester_role == 'researcher':
            # Researchers get anonymized data
            filtered['name'] = 'ANONYMIZED'
            filtered['patient_id'] = hashlib.md5(filtered['patient_id'].encode()).hexdigest()[:8]
            if 'ssn' in filtered:
                filtered.pop('ssn')
            if 'dob' in filtered:
                filtered.pop('dob')
            if 'address' in filtered:
                filtered.pop('address')
            if 'phone' in filtered:
                filtered.pop('phone')
        elif self.privacy_config['mask_sensitive_data'] and requester_id != 'authorized_system':
            # Standard masking for non-authorized users
            if 'ssn' in filtered:
                filtered['ssn'] = '***-**-****'
            if 'dob' in filtered:
                filtered['dob'] = 'YYYY-MM-DD'
            # ADDED: Additional PII masking
            if 'address' in filtered:
                filtered['address'] = 'REDACTED'
            if 'phone' in filtered:
                filtered['phone'] = '***-***-****'
        
        return filtered

    def _check_patient_consent(self, patient_id: str) -> Dict[str, Any]:
        """Check patient consent status"""
        # In real system, this would check actual consent records
        # For demo, we'll use a simple approach
        if patient_id in self.patient_records:
            record = self.patient_records[patient_id]
            return {
                'has_general_consent': True,
                'has_research_consent': record.get('research_consent', False),
                'has_data_sharing_consent': record.get('data_sharing_consent', True),
                'last_updated': record.get('consent_updated', 'Unknown')
            }
        
        return {
            'has_general_consent': False,
            'error': 'Patient not found'
        }

    def _update_patient_consent(self, patient_id: str, consent_type: str, value: bool) -> bool:
        """Update patient consent status"""
        with self.data_lock:
            if patient_id in self.patient_records:
                consent_field = f"{consent_type}_consent"
                self.patient_records[patient_id][consent_field] = value
                self.patient_records[patient_id]['consent_updated'] = datetime.now(timezone.utc).isoformat()
                self._save_patient_records_throttled()
                return True
        return False

    def _log_access(self, action: str, patient_id: str, details: Dict[str, Any]):
        """Log access for audit trail"""
        if not self.privacy_config['audit_all_access']:
            return
        
        # FIXED: Extract user_id from details
        user_id = details.get('user_id', 'system')
        
        audit_entry = AuditEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            patient_id=patient_id,
            user_id=user_id,
            details=details,
            success=True
        )
        
        # FIXED: Thread-safe audit log append
        with self.data_lock:
            self.audit_log.append(asdict(audit_entry))
            
            # Trim audit log if too large
            if len(self.audit_log) > self.max_audit_entries:
                self.audit_log = self.audit_log[-self.audit_retention:]

    def _filter_audit_log(self, patient_id: Optional[str] = None, 
                         action_type: Optional[str] = None,
                         start_time: Optional[str] = None,
                         end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter audit log by criteria"""
        with self.data_lock:
            filtered = self.audit_log.copy()
        
        if patient_id:
            filtered = [e for e in filtered if e['patient_id'] == patient_id]
        
        if action_type:
            filtered = [e for e in filtered if e['action'] == action_type]
        
        if start_time:
            filtered = [e for e in filtered if e['timestamp'] >= start_time]
        
        if end_time:
            filtered = [e for e in filtered if e['timestamp'] <= end_time]
        
        return filtered

    def _generate_cache_key(self, criteria: Dict[str, Any]) -> str:
        """Generate cache key for search criteria"""
        # Sort criteria for consistent hashing
        sorted_criteria = json.dumps(criteria, sort_keys=True)
        return hashlib.md5(sorted_criteria.encode()).hexdigest()

    def _cache_search_results(self, cache_key: str, results: List[Dict[str, Any]]):
        """Cache search results with size management"""
        with self.data_lock:
            # Implement LRU eviction
            if len(self.query_cache) >= self.max_cache_size:
                # Remove oldest item
                self.query_cache.popitem(last=False)
            
            # Add new results
            self.query_cache[cache_key] = results

    def _invalidate_cache(self):
        """Invalidate all cached search results"""
        with self.data_lock:
            self.query_cache.clear()
            # Clear LRU cache as well
            self._search_cache.cache_clear()

    def _save_patient_records_throttled(self):
        """Save patient records with throttling to avoid disk churn"""
        current_time = time.time()
        
        with self.data_lock:
            # Check if enough time has passed since last save
            if current_time - self._last_save_time >= self._save_interval:
                self._save_patient_records()
                self._last_save_time = current_time
                self._pending_save = False
            else:
                # Mark that a save is pending
                self._pending_save = True
                
                # Schedule a delayed save if not already scheduled
                if not hasattr(self, '_save_timer') or not self._save_timer.is_alive():
                    import threading
                    self._save_timer = threading.Timer(
                        self._save_interval - (current_time - self._last_save_time),
                        self._delayed_save
                    )
                    self._save_timer.start()

    def _delayed_save(self):
        """Execute delayed save"""
        with self.data_lock:
            if self._pending_save:
                self._save_patient_records()
                self._last_save_time = time.time()
                self._pending_save = False

    def _save_patient_records(self):
        """Save patient records back to file"""
        try:
            # Already under data_lock when called
            with open(self.patient_data_path, 'w') as f:
                json.dump(self.patient_records, f, indent=2)
            self.logger.debug("Patient records saved to file")
        except Exception as e:
            self.logger.error(f"Failed to save patient records: {e}")

    def _cache_patient_records(self):
        """Cache patient records in memory if available"""
        if not self.memory_manager:
            return
        
        try:
            for patient_id, record in self.patient_records.items():
                doc_id = f"patient_{patient_id}"
                self.memory_manager.collection.upsert(
                    ids=[doc_id],
                    documents=[json.dumps(record)],
                    metadatas=[{
                        "patient_id": patient_id,
                        "patient_name": record.get('name', 'Unknown'),
                        "cached_at": datetime.now(timezone.utc).isoformat()
                    }]
                )
            self.logger.debug(f"Cached {len(self.patient_records)} patient records")
        except Exception as e:
            self.logger.warning(f"Could not cache patient records: {e}")