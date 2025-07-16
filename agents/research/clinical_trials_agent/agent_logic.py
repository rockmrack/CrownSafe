# C:\Users\rossd\Downloads\RossNetAgents\agents\research\clinical_trials_agent\agent_logic.py
# Version: 3.0.0
# Change: Refactored to use 'requests' library via run_in_executor instead of 'aiohttp'
#         to address 403 Forbidden errors from ClinicalTrials.gov API.
#         Uses headers identified as working with curl/requests.

import logging
import os
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests # Changed from aiohttp
from urllib.parse import urlencode

# Handle optional dotenv import
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    def load_dotenv(dotenv_path=None, verbose=False, override=False, interpolate=True, encoding="utf-8"): # type: ignore
        pass

logger_cta_logic_default = logging.getLogger(__name__)

class MessageType(Enum):
    TASK_ASSIGN = "TASK_ASSIGN"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    PONG = "PONG"

@dataclass
class ClinicalTrial:
    nct_id: str
    title: str
    status: str
    url: str
    condition: Optional[str] = None
    intervention: Optional[str] = None
    start_date: Optional[str] = None
    completion_date: Optional[str] = None

@dataclass
class TrialsQueryResult:
    query_used_for_api: str # String representation of parameters sent
    trials_count_api: int   # 'totalCount' from API if available
    trials_returned_batch: int # Number of trials actually processed in this batch
    trials_data: List[ClinicalTrial]
    search_time_ms: int = 0
    error: Optional[str] = None
    source: str = "clinicaltrials.gov_api_v2"

class ClinicalTrialsAgentLogic:
    def __init__(self, agent_id: str, version: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger_instance if logger_instance else logger_cta_logic_default
        self._load_environment()

        self.api_base_url = os.getenv("CLINICAL_TRIALS_API_URL", "https://clinicaltrials.gov/api/v2").rstrip('/')
        
        # Using headers that worked with requests/curl
        # Note: 'Host' is typically set automatically by requests.
        # If issues persist, explicitly adding "Host": "clinicaltrials.gov" can be tried.
        self.working_headers = {
            "User-Agent": f"CureViaX/{self.version} (ClinicalTrialsAgent; mailto:contact@example.com)",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "*/*",
            "Connection": "keep-alive"
        }

        self.max_retries = 2 
        self.retry_delay_base = 3 
        self.request_timeout_seconds = 45 # Timeout for each requests call

        self.rate_limit_delay = 0.2 
        self._last_request_time = 0.0
        
        self.logger.info(
            f"ClinicalTrialsAgentLogic initialized for agent {self.agent_id} (Version 3.0.0 - Using 'requests' library). "
            f"API URL: {self.api_base_url}. Effective Headers: {self.working_headers}"
        )

    def _load_environment(self):
        if not DOTENV_AVAILABLE: self.logger.warning("python-dotenv not available."); return
        try:
            project_root = Path(__file__).resolve().parents[3]
            dotenv_path = project_root / '.env'
            if dotenv_path.exists(): load_dotenv(dotenv_path); self.logger.debug(f"Loaded .env from {dotenv_path}")
            else: self.logger.info("No .env found by logic.")
        except Exception as e: self.logger.warning(f"Error loading .env in logic: {e}")

    def get_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "retrieve_clinical_trials",
                "description": "Retrieves comprehensive clinical trial information from ClinicalTrials.gov.",
                "parameters": {
                    "drug_name": "string (optional, intervention name, max 500 chars)",
                    "disease_name": "string (optional, condition/disease name, max 500 chars)",
                    "search_terms": "string (optional, general search terms, max 500 chars)",
                    "max_trials": "integer (optional, default 5, range 1-100)"
                },
                "output_format": {"query_used_for_api": "string", "trials_count_api": "integer", "trials_returned_batch": "integer", "trials_data": "list_of_objects", "error": "string"},
                "data_source": "ClinicalTrials.gov API v2",
                "note": "At least one search parameter (drug_name, disease_name, or search_terms) must be provided."
            }
        ]

    async def _rate_limit(self): # This can remain async as it uses asyncio.sleep
        current_time = time.time(); time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay: await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = time.time()

    def _validate_parameters(self, drug_name: Any, disease_name: Any, search_terms: Any, max_trials: Any) -> tuple[bool, Optional[str], int, Dict[str,str]]:
        query_params: Dict[str,str] = {}; validated_max_trials = 5
        try:
            validated_max_trials = int(max_trials) if max_trials is not None else 5
            if not 1 <= validated_max_trials <= 100: return False, "max_trials must be 1-100.", validated_max_trials, query_params
        except (ValueError, TypeError): return False, f"max_trials not int.", validated_max_trials, query_params
        drug_name_s = drug_name.strip() if drug_name and isinstance(drug_name, str) else None
        disease_name_s = disease_name.strip() if disease_name and isinstance(disease_name, str) else None
        search_terms_s = search_terms.strip() if search_terms and isinstance(search_terms, str) else None
        if drug_name_s and len(drug_name_s) > 500: return False, "drug_name too long.", validated_max_trials, query_params
        if disease_name_s and len(disease_name_s) > 500: return False, "disease_name too long.", validated_max_trials, query_params
        if search_terms_s and len(search_terms_s) > 500: return False, "search_terms too long.", validated_max_trials, query_params
        if search_terms_s: query_params["query.term"] = search_terms_s
        elif drug_name_s and disease_name_s: query_params["query.intr"] = drug_name_s; query_params["query.cond"] = disease_name_s
        elif drug_name_s: query_params["query.intr"] = drug_name_s
        elif disease_name_s: query_params["query.cond"] = disease_name_s
        else: return False, "No valid search param provided.", validated_max_trials, query_params
        return True, None, validated_max_trials, query_params

    def _make_sync_api_request(self, query_params: Dict[str, str], max_trials_validated: int) -> Dict[str, Any]:
        """Synchronous API request using the 'requests' library."""
        studies_endpoint = f"{self.api_base_url}/studies"
        api_params = {**query_params, "pageSize": str(max_trials_validated), "format": "json"}
        log_url = f"{studies_endpoint}?{urlencode(api_params)}" # For logging

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1): # Initial attempt + self.max_retries
            try:
                # Rate limiting is handled in the async _fetch_clinical_trials_data before calling this sync method via executor
                self.logger.info(f"ClinicalTrials API request (attempt {attempt + 1}/{self.max_retries + 1}) using 'requests'")
                self.logger.info(f"  Target URL (constructed): {log_url}")
                self.logger.debug(f"  Parameters: {api_params}, Headers: {self.working_headers}")

                response = requests.get(
                    studies_endpoint,
                    params=api_params,
                    headers=self.working_headers,
                    timeout=self.request_timeout_seconds
                )
                
                self.logger.info(f"  Response Status: {response.status_code} from {response.url}")
                self.logger.debug(f"  Response Headers Received: {dict(response.headers)}")
                # Log actual request headers sent by 'requests' library
                if response.request and response.request.headers:
                     self.logger.debug(f"  ACTUAL REQUEST HEADERS SENT by 'requests': {dict(response.request.headers)}")


                response.raise_for_status() # Raises requests.exceptions.HTTPError for 4xx/5xx
                
                json_response = response.json() # Can raise requests.exceptions.JSONDecodeError
                self.logger.info(f"API request successful (attempt {attempt + 1}).")
                return json_response

            except requests.exceptions.Timeout as e:
                last_exception = TimeoutError(f"Request Timeout on attempt {attempt + 1}: {e}")
                self.logger.error(str(last_exception))
            except requests.exceptions.HTTPError as e: # Catches 4xx and 5xx errors
                err_msg_detail = (f"HTTP {e.response.status_code} {e.response.reason} from API. URL: {e.request.url}. "
                                  f"Body: {e.response.text[:500] if e.response and e.response.text else 'N/A'}")
                self.logger.error(err_msg_detail)
                # Map to standard Python exceptions
                if e.response.status_code == 400: current_exception = ValueError(err_msg_detail)
                elif e.response.status_code == 401: current_exception = PermissionError(f"Unauthorized (401): {err_msg_detail}")
                elif e.response.status_code == 403: current_exception = PermissionError(f"Forbidden (403): {err_msg_detail}")
                elif e.response.status_code == 404: current_exception = FileNotFoundError(f"Not Found (404): {err_msg_detail}")
                elif e.response.status_code == 429: current_exception = ConnectionError(f"Too Many Requests (429): {err_msg_detail}") # Retryable
                elif e.response.status_code >= 500: current_exception = ConnectionError(f"Server Error ({e.response.status_code}): {err_msg_detail}") # Retryable
                else: current_exception = ConnectionError(f"Client Error ({e.response.status_code}): {err_msg_detail}") # Other 4xx
                
                last_exception = current_exception
                if not (e.response.status_code == 429 or e.response.status_code >= 500): # Don't retry non-server/non-rate-limit client errors
                    raise last_exception # Fail fast
            except requests.exceptions.ConnectionError as e: # Includes DNS, refused, etc.
                last_exception = ConnectionError(f"Connection Error on attempt {attempt + 1}: {e}")
                self.logger.error(str(last_exception))
            except requests.exceptions.JSONDecodeError as e:
                last_exception = ValueError(f"JSONDecodeError on attempt {attempt + 1}: {e}. Response text: {response.text[:200] if 'response' in locals() else 'N/A'}")
                self.logger.error(str(last_exception), exc_info=True)
                raise last_exception # Non-retryable
            except Exception as e: # Catch-all for other unexpected issues
                last_exception = RuntimeError(f"Unexpected error during 'requests' API call attempt {attempt + 1}: {type(e).__name__} - {e}")
                self.logger.error(str(last_exception), exc_info=True)

            # Retry logic
            if attempt < self.max_retries:
                if last_exception and not isinstance(last_exception, (ConnectionError, TimeoutError)):
                    self.logger.error(f"Non-retryable error encountered on attempt {attempt + 1}. Failing early.")
                    raise last_exception
                
                delay = self.retry_delay_base * (2 ** attempt)
                self.logger.warning(f"Request attempt {attempt+1} failed with retryable error. Retrying in {delay}s... ({str(last_exception)})")
                time.sleep(delay) # Synchronous sleep for synchronous retry
                continue
            else: # Last attempt
                self.logger.error(f"All {self.max_retries + 1} attempts failed.")
                if last_exception: raise last_exception
                raise RuntimeError(f"All {self.max_retries + 1} attempts failed with an unspecified error.")
        
        # Fallback, should not be reached
        critical_fallback_error = "All API request attempts failed after retries (sync)."
        self.logger.critical(critical_fallback_error)
        if last_exception: raise last_exception
        raise RuntimeError(critical_fallback_error)

    def _parse_trial_data(self, study_json: Dict[str, Any]) -> Optional[ClinicalTrial]:
        # ... (This method remains the same as V2.4.x) ...
        try:
            protocol_section = study_json.get("protocolSection", {}); id_module = protocol_section.get("identificationModule", {}); status_module = protocol_section.get("statusModule", {})
            nct_id = id_module.get("nctId"); 
            if not nct_id: self.logger.warning("Skipping trial due to missing nctId."); return None
            brief_title = id_module.get("briefTitle", "N/A"); official_title = id_module.get("officialTitle")
            title_to_use = brief_title if brief_title and brief_title != "N/A" else official_title if official_title else "N/A"
            overall_status = status_module.get("overallStatus", "N/A"); trial_url = f"https://clinicaltrials.gov/study/{nct_id}"
            conditions_list = protocol_section.get("conditionsModule", {}).get("conditions", []); condition_str = "; ".join(conditions_list) if conditions_list else "N/A"
            arms_interventions_module = protocol_section.get("armsInterventionsModule", {}); interventions_list = arms_interventions_module.get("interventions", [])
            intervention_names = []
            if isinstance(interventions_list, list):
                for item in interventions_list:
                    if isinstance(item, dict) and item.get("name"): intervention_names.append(item.get("name"))
            intervention_str = "; ".join(intervention_names) if intervention_names else "N/A"
            start_date_struct = status_module.get("startDateStruct", {}); start_date = start_date_struct.get("date", "N/A") if isinstance(start_date_struct, dict) else "N/A"
            completion_date_struct = status_module.get("primaryCompletionDateStruct", {}); completion_date = completion_date_struct.get("date", "N/A") if isinstance(completion_date_struct, dict) else "N/A"
            return ClinicalTrial(nct_id=nct_id, title=title_to_use, status=overall_status, url=trial_url, condition=condition_str, intervention=intervention_str, start_date=start_date, completion_date=completion_date)
        except Exception as e: self.logger.warning(f"Error parsing trial {nct_id if 'nct_id' in locals() else 'Unknown'}: {e}", exc_info=True); return None

    async def _fetch_clinical_trials_data(self, query_params_dict: Dict[str, str], max_trials: int) -> TrialsQueryResult:
        start_time_ns = time.perf_counter_ns()
        query_params_str = json.dumps(query_params_dict)
        
        try:
            self.logger.info(f"Fetching Clinical Trials for params: {query_params_str}, max_trials: {max_trials} (using 'requests' via executor)")
            
            await self._rate_limit() # Perform rate limiting before dispatching to executor
            
            loop = asyncio.get_running_loop()
            api_response_json = await loop.run_in_executor(
                None, # Use default ThreadPoolExecutor
                self._make_sync_api_request, # The synchronous function
                query_params_dict,           # First arg for _make_sync_api_request
                max_trials                   # Second arg
            )
            
            studies_list_json = api_response_json.get("studies", [])
            trials_data_parsed: List[ClinicalTrial] = []

            if isinstance(studies_list_json, list):
                for study_json_item in studies_list_json:
                    if isinstance(study_json_item, dict):
                        parsed_trial = self._parse_trial_data(study_json_item)
                        if parsed_trial: trials_data_parsed.append(parsed_trial)
            else: self.logger.warning(f"'studies' field not a list. Response: {str(api_response_json)[:200]}")

            api_total_count = api_response_json.get("totalCount", 0) if isinstance(api_response_json, dict) else 0
            search_time_ms = (time.perf_counter_ns() - start_time_ns) // 1_000_000
            
            self.logger.info(f"Successfully fetched/parsed {len(trials_data_parsed)} trials in {search_time_ms}ms. API total: {api_total_count}.")
            return TrialsQueryResult(query_used_for_api=query_params_str, trials_count_api=api_total_count, trials_returned_batch=len(trials_data_parsed), trials_data=trials_data_parsed, search_time_ms=search_time_ms)
        
        except (TimeoutError, requests.exceptions.HTTPError, requests.exceptions.ConnectionError, 
                  requests.exceptions.RequestException, ValueError, PermissionError, FileNotFoundError, RuntimeError) as e:
            search_time_ms_on_error = (time.perf_counter_ns() - start_time_ns) // 1_000_000
            error_message = f"API Error (requests) for {query_params_str}: {type(e).__name__} - {str(e)}"
            self.logger.error(error_message)
            return TrialsQueryResult(query_used_for_api=query_params_str, trials_data=[], error=error_message, trials_returned_batch=0, trials_count_api=0, search_time_ms=search_time_ms_on_error)
        except Exception as e_unhandled: # Fallback for truly unexpected errors
            search_time_ms_on_error = (time.perf_counter_ns() - start_time_ns) // 1_000_000
            error_message = f"Unexpected failure processing clinical trials for {query_params_str}: {type(e_unhandled).__name__} - {str(e_unhandled)}"
            self.logger.error(error_message, exc_info=True)
            return TrialsQueryResult(query_used_for_api=query_params_str, trials_data=[], error=error_message, trials_returned_batch=0, trials_count_api=0, search_time_ms=search_time_ms_on_error)

    def _validate_message_structure(self, message_data: Any) -> tuple[bool, Optional[str]]:
        # ... (This method remains the same) ...
        if not isinstance(message_data, dict): return False, f"Msg not dict: {type(message_data).__name__}"
        if "mcp_header" not in message_data or not isinstance(message_data["mcp_header"], dict): return False, "Missing/invalid mcp_header"
        if "payload" not in message_data or not isinstance(message_data["payload"], dict): return False, "Missing/invalid payload"
        return True, None

    async def process_message(self, message_data: Dict[str, Any], client: Any) -> Optional[Dict[str, Any]]:
        # ... (This method remains largely the same, ensuring it calls the updated _fetch_clinical_trials_data) ...
        is_valid_msg, msg_err = self._validate_message_structure(message_data)
        if not is_valid_msg: self.logger.error(f"Invalid msg structure: {msg_err}. Msg: {str(message_data)[:500]}"); return None 
        header = message_data["mcp_header"]; payload = message_data["payload"]
        message_type_str = header.get("message_type", "UNKNOWN"); sender_id = header.get("sender_id", "UnknownSender")
        correlation_id = header.get("correlation_id")
        try: message_type = MessageType(message_type_str)
        except ValueError: self.logger.warning(f"Unknown msg type '{message_type_str}' from {sender_id}. Ignoring."); return None
        if message_type == MessageType.PONG: self.logger.debug(f"PONG from {sender_id} for CorrID: {correlation_id}."); return None
        if message_type == MessageType.DISCOVERY_ACK: self.logger.info(f"Registration confirmed by {sender_id} (CorrID: {correlation_id}). Agent: {payload.get('agent_id')}"); return None
        self.logger.info(f"Processing {message_type.value} from {sender_id} (CorrID: {correlation_id})")
        if message_type == MessageType.TASK_ASSIGN: return await self._handle_task_assign(payload, correlation_id)
        else: self.logger.warning(f"Unhandled msg type: {message_type.value}"); return None

    async def _handle_task_assign(self, payload: Dict[str, Any], incoming_correlation_id: Optional[str]) -> Dict[str, Any]:
        # ... (This method remains largely the same, ensuring it calls the updated _fetch_clinical_trials_data) ...
        task_id = payload.get("task_id", "unknown_task"); workflow_id = payload.get("workflow_id", "unknown_workflow")
        response_payload_base = {"workflow_id": workflow_id, "task_id": task_id, "agent_id": self.agent_id}
        try:
            parameters = payload.get("parameters", {}); 
            if not isinstance(parameters, dict):
                return {"message_type": MessageType.TASK_FAIL.value, "payload": {**response_payload_base, "error_message": "Invalid params: must be dict"}}
            drug_name = parameters.get("drug_name"); disease_name = parameters.get("disease_name"); 
            search_terms = parameters.get("search_terms"); max_trials_param = parameters.get("max_trials", 5)
            is_valid_params, param_err_msg, validated_max_trials, query_params_dict = self._validate_parameters(drug_name, disease_name, search_terms, max_trials_param)
            if not is_valid_params:
                self.logger.error(f"Invalid params for task {task_id}: {param_err_msg}")
                return {"message_type": MessageType.TASK_FAIL.value, "payload": {**response_payload_base, "error_message": param_err_msg}}
            self.logger.info(f"Performing ClinicalTrials search for task {task_id} with params: {query_params_dict}, max_trials: {validated_max_trials}")
            query_result_obj = await self._fetch_clinical_trials_data(query_params_dict, validated_max_trials)
            if query_result_obj.error: # This error should now be the detailed API error from 'requests'
                self.logger.error(f"ClinicalTrials search failed for task {task_id}: {query_result_obj.error}")
                return {"message_type": MessageType.TASK_FAIL.value, "payload": {**response_payload_base, "error_message": query_result_obj.error}}
            result_data_dict = asdict(query_result_obj) 
            final_payload = {**response_payload_base, "status": "COMPLETED", "result": result_data_dict}
            self.logger.info(f"ClinicalTrials search completed for task {task_id}: {len(query_result_obj.trials_data)} trials processed.")
            return {"message_type": MessageType.TASK_COMPLETE.value, "payload": final_payload}
        except Exception as e:
            error_msg = f"Unexpected error in _handle_task_assign: {type(e).__name__} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"message_type": MessageType.TASK_FAIL.value, "payload": {**response_payload_base, "error_message": error_msg}}

    async def shutdown(self):
        self.logger.info(f"ClinicalTrialsAgentLogic (requests version) shutting down for agent {self.agent_id}")
        # No aiohttp session to close
        self.logger.info(f"ClinicalTrialsAgentLogic shutdown complete for agent {self.agent_id}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "api_base_url": self.api_base_url,
            "http_client": "requests", # Indicate which client is used
            "last_request_timestamp": self._last_request_time
        }