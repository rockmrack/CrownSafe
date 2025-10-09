# C:\Users\rossd\Downloads\RossNetAgents\agents\research\drug_safety_agent\agent_logic.py
# Version: 2.0.1
# Change:
# - CRITICAL FIX: Corrected argument passing to _make_sync_openfda_request when called via run_in_executor.
# - Added defensive type checking for drug_name_processed in _make_sync_openfda_request.
# - Retains targeted query, 'requests' library, and enhanced logging from V2.0.0.

import logging
import os
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import requests
from urllib.parse import urlencode

# Handle optional dotenv import
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

    def load_dotenv(dotenv_path=None, verbose=False, override=False, interpolate=True, encoding="utf-8"):  # type: ignore
        pass


logger_dsa_logic_default = logging.getLogger(__name__)


class MessageType(Enum):
    TASK_ASSIGN = "TASK_ASSIGN"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    PONG = "PONG"


@dataclass
class AdverseReaction:
    term: str
    count: int


@dataclass
class DrugSafetyQueryResult:
    drug_queried: str
    total_reports: int
    top_adverse_reactions: List[AdverseReaction]
    search_time_ms: int = 0
    error: Optional[str] = None
    source: str = "openFDA_drug_event_api"


class DrugSafetyAgentLogic:
    def __init__(
        self,
        agent_id: str,
        version: str,
        logger_instance: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.version = version
        self.logger = logger_instance if logger_instance else logger_dsa_logic_default
        self._load_environment()

        self.api_base_url = os.getenv(
            "OPENFDA_API_URL", "https://api.fda.gov/drug/event.json"
        ).rstrip("/")
        self.user_agent = f"CureViaX/{self.version} (DrugSafetyAgent; mailto:contact@example.com)"

        self.working_headers = {"User-Agent": self.user_agent}
        self.max_retries = 2
        self.retry_delay_base = 2
        self.request_timeout_seconds = 30
        self.rate_limit_delay = 0.2
        self._last_request_time = 0.0

        self.logger.info(
            f"DrugSafetyAgentLogic initialized for agent {self.agent_id} (Version 2.0.1 - Arg Fix & Defensive Check). "
            f"API URL: {self.api_base_url}"
        )

    def _load_environment(self):
        # ... (same as V2.0.0) ...
        if not DOTENV_AVAILABLE:
            self.logger.warning("python-dotenv not available.")
            return
        try:
            project_root = Path(__file__).resolve().parents[3]
            dotenv_path = project_root / ".env"
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                self.logger.debug(f"Loaded .env from {dotenv_path}")
            else:
                self.logger.info("No .env found by logic.")
        except Exception as e:
            self.logger.warning(f"Error loading .env in logic: {e}")

    def get_capabilities(self) -> List[Dict[str, Any]]:
        # ... (same as V2.0.0) ...
        return [
            {
                "name": "query_adverse_events",
                "description": "Queries openFDA for adverse event reports related to a specific drug.",
                "parameters": {
                    "drug_name": "string (required, name of the drug to query)",
                    "max_reactions": "integer (optional, default 5, number of top reactions to return)",
                },
                "output_format": {
                    "drug_queried": "string",
                    "total_reports": "integer",
                    "top_adverse_reactions": "list_of_objects",
                    "error": "string",
                },
            }
        ]

    async def _rate_limit(self):
        # ... (same as V2.0.0) ...
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self._last_request_time = time.time()

    def _validate_parameters(
        self, drug_name: Any, max_reactions: Any
    ) -> tuple[bool, Optional[str], str, int]:
        # ... (same as V2.0.0) ...
        validated_drug_name = ""
        validated_max_reactions = 5
        if not drug_name or not isinstance(drug_name, str) or not drug_name.strip():
            return (
                False,
                "drug_name is required and non-empty.",
                validated_drug_name,
                validated_max_reactions,
            )
        validated_drug_name = drug_name.strip()
        if len(validated_drug_name) > 500:
            return (
                False,
                "drug_name too long.",
                validated_drug_name,
                validated_max_reactions,
            )
        try:
            validated_max_reactions = int(max_reactions) if max_reactions is not None else 5
            if not 1 <= validated_max_reactions <= 20:
                return (
                    False,
                    "max_reactions must be 1-20.",
                    validated_drug_name,
                    validated_max_reactions,
                )
        except (ValueError, TypeError):
            return (
                False,
                f"max_reactions not int.",
                validated_drug_name,
                validated_max_reactions,
            )
        return True, None, validated_drug_name, validated_max_reactions

    # <<< --- V2.0.1: Corrected _make_sync_openfda_request --- >>>
    def _make_sync_openfda_request(
        self, drug_name_for_search_term: str, api_specific_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Synchronous API request to openFDA using 'requests' library.
        Constructs the primary search term using drug_name_for_search_term.
        Uses api_specific_params for 'limit' and potentially 'count'.
        """
        # Defensive type check for drug_name_for_search_term
        if not isinstance(drug_name_for_search_term, str):
            err_msg = f"CRITICAL TYPE ERROR: _make_sync_openfda_request expected string for drug_name_for_search_term, got {type(drug_name_for_search_term)}: {drug_name_for_search_term}"
            self.logger.error(err_msg)
            raise ValueError(err_msg)  # Fail fast

        # Construct the base search term using the drug name for the medicinalproduct field
        search_term_value = f"patient.drug.medicinalproduct:{drug_name_for_search_term.upper()}"

        # Combine with other API specific params like limit, count
        # The caller (_fetch_adverse_event_data) will now prepare the full api_params dict
        # This method now expects api_specific_params to contain the full query structure.
        # Let's adjust: this method should take the *full* params dict.
        # No, let's keep it simpler: this method takes the drug name, and the *additional* params.

        # Revised: This method takes the drug name to build the core search,
        # and api_specific_params for things like 'limit' and 'count'.

        final_api_params = {"search": search_term_value, **api_specific_params}

        log_url = f"{self.api_base_url}?{urlencode(final_api_params)}"
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(
                    f"openFDA API request (attempt {attempt + 1}/{self.max_retries + 1}) using 'requests'"
                )
                self.logger.info(f"  Target URL (constructed): {log_url}")  # Log full URL
                self.logger.debug(
                    f"  Final Parameters: {final_api_params}, Headers: {self.working_headers}"
                )

                response = requests.get(
                    self.api_base_url,  # Base URL
                    params=final_api_params,  # All params including search, limit, count
                    headers=self.working_headers,
                    timeout=self.request_timeout_seconds,
                )
                self.logger.info(f"  Response Status: {response.status_code} from {response.url}")
                if response.request and response.request.headers:
                    self.logger.debug(
                        f"  ACTUAL REQUEST HEADERS SENT by 'requests': {dict(response.request.headers)}"
                    )

                response.raise_for_status()
                json_response = response.json()
                self.logger.info(f"openFDA API request successful (attempt {attempt + 1}).")
                return json_response

            except requests.exceptions.Timeout as e:
                last_exception = TimeoutError(f"Request Timeout on attempt {attempt + 1}: {e}")
            except requests.exceptions.HTTPError as e:
                err_msg = (
                    f"HTTP {e.response.status_code} from openFDA. URL: {e.request.url}. "
                    f"Body: {e.response.text[:500] if e.response and e.response.text else 'N/A'}"
                )
                # For count queries, 404 can mean 0 results.
                # Check if 'count' was in final_api_params for this specific call.
                is_count_query = "count" in final_api_params
                if e.response.status_code == 404 and is_count_query:
                    self.logger.warning(
                        f"openFDA returned 404 for count query on drug '{drug_name_for_search_term}'. Assuming 0 results for this count."
                    )
                    return {"results": []}
                elif e.response.status_code == 429 or e.response.status_code >= 500:
                    last_exception = ConnectionError(err_msg)
                else:
                    last_exception = ConnectionError(err_msg)
                    raise last_exception
            except requests.exceptions.ConnectionError as e:
                last_exception = ConnectionError(f"Connection Error on attempt {attempt + 1}: {e}")
            except requests.exceptions.JSONDecodeError as e:
                last_exception = ValueError(
                    f"JSONDecodeError on attempt {attempt + 1}: {e}. Response: {response.text[:200] if 'response' in locals() else 'N/A'}"
                )
                raise last_exception
            except Exception as e:
                last_exception = RuntimeError(
                    f"Unexpected error during 'requests' API call attempt {attempt + 1}: {e}"
                )

            self.logger.error(str(last_exception))
            if attempt < self.max_retries:
                if not isinstance(last_exception, (ConnectionError, TimeoutError)):
                    self.logger.error(f"Non-retryable error on attempt {attempt+1}. Failing early.")
                    raise last_exception
                delay = self.retry_delay_base * (2**attempt)
                self.logger.warning(f"Request attempt {attempt+1} failed. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                self.logger.error(f"All {self.max_retries + 1} attempts failed.")
                if last_exception:
                    raise last_exception
                raise RuntimeError(
                    f"All {self.max_retries + 1} attempts failed with an unspecified error."
                )

        critical_fallback_error = "All openFDA API request attempts failed after retries (sync)."
        self.logger.critical(critical_fallback_error)
        if last_exception:
            raise last_exception
        raise RuntimeError(critical_fallback_error)

    def _parse_openfda_response(
        self,
        response_json_for_reactions: Dict[str, Any],
        drug_name: str,
        max_reactions_to_return: int,
    ) -> List[AdverseReaction]:
        """Parses the JSON response from an openFDA 'count' query for reactions."""
        top_reactions_list: List[AdverseReaction] = []
        if (
            response_json_for_reactions
            and "results" in response_json_for_reactions
            and isinstance(response_json_for_reactions["results"], list)
        ):
            for item in response_json_for_reactions["results"][:max_reactions_to_return]:
                if isinstance(item, dict) and "term" in item and "count" in item:
                    top_reactions_list.append(
                        AdverseReaction(term=str(item["term"]), count=int(item["count"]))
                    )
                else:
                    self.logger.warning(
                        f"Unexpected item structure in reaction results for {drug_name}: {item}"
                    )
        return top_reactions_list

    async def _fetch_adverse_event_data(
        self, drug_name_validated: str, max_reactions: int
    ) -> DrugSafetyQueryResult:
        start_time_ns = time.perf_counter_ns()
        query_for_log = f"drug_name: {drug_name_validated}, max_reactions: {max_reactions}"

        total_reports_for_drug = 0
        top_reactions_data: List[AdverseReaction] = []
        final_error: Optional[str] = None

        try:
            await self._rate_limit()
            loop = asyncio.get_running_loop()

            # 1. Get total reports for the drug
            self.logger.info(
                f"Fetching total adverse event report count for drug: '{drug_name_validated}'"
            )
            # Parameters for the total count query
            total_count_api_params = {
                "limit": "1"
            }  # 'search' will be added by _make_sync_openfda_request

            # <<< --- V2.0.1: CORRECTED ARGUMENT PASSING --- >>>
            response_total_json = await loop.run_in_executor(
                None,
                self._make_sync_openfda_request,
                drug_name_validated,  # This is drug_name_for_search_term (string)
                total_count_api_params,  # This is api_specific_params (dict)
            )

            if (
                response_total_json
                and "meta" in response_total_json
                and "results" in response_total_json["meta"]
            ):
                total_reports_for_drug = response_total_json["meta"]["results"].get("total", 0)
            self.logger.info(
                f"Total adverse event reports found for '{drug_name_validated}': {total_reports_for_drug}"
            )

            if total_reports_for_drug > 0:
                self.logger.info(
                    f"Fetching top {max_reactions} adverse reactions for drug: '{drug_name_validated}'"
                )
                reaction_count_field = "patient.reaction.reactionmeddrapt.exact"
                # Parameters for the reaction count query
                reaction_api_params = {
                    "count": reaction_count_field,
                    "limit": str(max_reactions),
                }

                await self._rate_limit()
                # <<< --- V2.0.1: CORRECTED ARGUMENT PASSING --- >>>
                response_reactions_json = await loop.run_in_executor(
                    None,
                    self._make_sync_openfda_request,
                    drug_name_validated,  # drug_name_for_search_term (string)
                    reaction_api_params,  # api_specific_params (dict)
                )

                top_reactions_data = self._parse_openfda_response(
                    response_reactions_json, drug_name_validated, max_reactions
                )
                self.logger.info(
                    f"Found {len(top_reactions_data)} top reactions for '{drug_name_validated}'."
                )
            else:
                self.logger.info(
                    f"Skipping reaction fetch as no total reports found for '{drug_name_validated}'."
                )

        except (
            TimeoutError,
            requests.exceptions.RequestException,
            ValueError,
            RuntimeError,
            ConnectionError,
        ) as e:
            final_error = f"API Error during openFDA fetch for {drug_name_validated}: {type(e).__name__} - {str(e)}"
            self.logger.error(final_error)
        except Exception as e_unhandled:
            final_error = f"Unexpected failure processing openFDA data for {drug_name_validated}: {type(e_unhandled).__name__} - {str(e_unhandled)}"
            self.logger.error(final_error, exc_info=True)

        search_time_ms = (time.perf_counter_ns() - start_time_ns) // 1_000_000
        return DrugSafetyQueryResult(
            drug_queried=drug_name_validated,
            total_reports=total_reports_for_drug,
            top_adverse_reactions=top_reactions_data,
            search_time_ms=search_time_ms,
            error=final_error,
        )

    def _validate_message_structure(self, message_data: Any) -> tuple[bool, Optional[str]]:
        # ... (same as V2.0.0) ...
        if not isinstance(message_data, dict):
            return False, f"Msg not dict: {type(message_data).__name__}"
        if "mcp_header" not in message_data or not isinstance(message_data["mcp_header"], dict):
            return False, "Missing/invalid mcp_header"
        if "payload" not in message_data or not isinstance(message_data["payload"], dict):
            return False, "Missing/invalid payload"
        return True, None

    async def process_message(
        self, message_data: Dict[str, Any], client: Any
    ) -> Optional[Dict[str, Any]]:
        # ... (same as V2.0.0, with PONG/ACK handling) ...
        is_valid_msg, msg_err = self._validate_message_structure(message_data)
        if not is_valid_msg:
            self.logger.error(f"Invalid msg structure: {msg_err}. Msg: {str(message_data)[:500]}")
            return None
        header = message_data["mcp_header"]
        payload = message_data["payload"]
        message_type_str = header.get("message_type", "UNKNOWN")
        sender_id = header.get("sender_id", "UnknownSender")
        correlation_id = header.get("correlation_id")
        try:
            message_type = MessageType(message_type_str)
        except ValueError:
            self.logger.warning(
                f"Unknown msg type '{message_type_str}' from {sender_id}. Ignoring."
            )
            return None
        if message_type == MessageType.PONG:
            self.logger.debug(f"PONG from {sender_id} for CorrID: {correlation_id}.")
            return None
        if message_type == MessageType.DISCOVERY_ACK:
            self.logger.info(
                f"Registration confirmed by {sender_id} (CorrID: {correlation_id}). Agent: {payload.get('agent_id')}"
            )
            return None
        self.logger.info(
            f"Processing {message_type.value} from {sender_id} (CorrID: {correlation_id})"
        )
        if message_type == MessageType.TASK_ASSIGN:
            return await self._handle_task_assign(payload, correlation_id)
        else:
            self.logger.warning(f"Unhandled msg type: {message_type.value}")
            return None

    async def _handle_task_assign(
        self, payload: Dict[str, Any], incoming_correlation_id: Optional[str]
    ) -> Dict[str, Any]:
        # ... (same as V2.0.0) ...
        task_id = payload.get("task_id", "unknown_task")
        workflow_id = payload.get("workflow_id", "unknown_workflow")
        response_payload_base = {
            "workflow_id": workflow_id,
            "task_id": task_id,
            "agent_id": self.agent_id,
        }
        try:
            parameters = payload.get("parameters", {})
            if not isinstance(parameters, dict):
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {
                        **response_payload_base,
                        "error_message": "Invalid params: must be dict",
                    },
                }
            drug_name_param = parameters.get("drug_name")
            max_reactions_param = parameters.get("max_reactions", 5)
            (
                is_valid_params,
                param_err_msg,
                validated_drug_name,
                validated_max_reactions,
            ) = self._validate_parameters(drug_name_param, max_reactions_param)
            if not is_valid_params:
                self.logger.error(f"Invalid params for task {task_id}: {param_err_msg}")
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {
                        **response_payload_base,
                        "error_message": param_err_msg,
                    },
                }
            self.logger.info(
                f"Performing openFDA search for task {task_id} with drug: '{validated_drug_name}', max_reactions: {validated_max_reactions}"
            )
            query_result_obj = await self._fetch_adverse_event_data(
                validated_drug_name, validated_max_reactions
            )
            if query_result_obj.error:
                self.logger.error(
                    f"openFDA search failed for task {task_id}: {query_result_obj.error}"
                )
                return {
                    "message_type": MessageType.TASK_FAIL.value,
                    "payload": {
                        **response_payload_base,
                        "error_message": query_result_obj.error,
                    },
                }
            result_data_dict = asdict(query_result_obj)
            final_payload = {
                **response_payload_base,
                "status": "COMPLETED",
                "result": result_data_dict,
            }
            self.logger.info(
                f"openFDA search completed for task {task_id}: {query_result_obj.total_reports} total reports, {len(query_result_obj.top_adverse_reactions)} top reactions retrieved."
            )
            return {
                "message_type": MessageType.TASK_COMPLETE.value,
                "payload": final_payload,
            }
        except Exception as e:
            error_msg = f"Unexpected error in _handle_task_assign: {type(e).__name__} - {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "message_type": MessageType.TASK_FAIL.value,
                "payload": {**response_payload_base, "error_message": error_msg},
            }

    async def shutdown(self):
        # ... (same as V2.0.0) ...
        self.logger.info(
            f"DrugSafetyAgentLogic (requests version) shutting down for agent {self.agent_id}"
        )
        self.logger.info(f"DrugSafetyAgentLogic shutdown complete for agent {self.agent_id}")

    def get_status(self) -> Dict[str, Any]:
        # ... (same as V2.0.0) ...
        return {
            "agent_id": self.agent_id,
            "version": self.version,
            "api_base_url": self.api_base_url,
            "http_client": "requests",
            "last_request_timestamp": self._last_request_time,
        }
