# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_router_service\discovery.py
# Fixed version with proper variable scoping

import logging
from typing import Dict, Any, List, Optional, Set
import json
import uuid
import copy
import asyncio
from datetime import datetime, timezone

print(f"Loading discovery.py (Step 77 Version - Fixed): {__file__}")

from .state import get_connection
from .utils import create_mcp_response, create_mcp_error_response, safe_json_serialize

discovery_logger = logging.getLogger("MCP_DiscoveryService")
agent_registry: Dict[str, Dict[str, Any]] = {}
registry_lock = asyncio.Lock()

discovery_logger.info("Discovery: In-memory agent registry initialized (Step 77 Version - Fixed).")


def _normalize_capability_name(cap_name: str) -> str:
    """Normalizes capability names for comparison (lowercase, strip whitespace)."""
    if not isinstance(cap_name, str):
        discovery_logger.warning(
            f"Invalid capability name (not a string): {cap_name} (type: {type(cap_name)}). Attempting conversion."
        )
        return str(cap_name).lower().strip()
    return cap_name.lower().strip()


def _get_agent_capabilities(agent_info: Dict[str, Any]) -> Set[str]:
    """Extracts and normalizes capability names from agent registration info."""
    capabilities = set()
    if not isinstance(agent_info, dict):
        discovery_logger.warning(
            f"_get_agent_capabilities: agent_info is not a dict. Got: {type(agent_info)}"
        )
        return capabilities

    agent_caps_list = agent_info.get("capabilities", [])
    agent_id_for_log = agent_info.get("agent_id", "UnknownAgent")
    discovery_logger.debug(
        f"_get_agent_capabilities for '{agent_id_for_log}': Raw capabilities list: {agent_caps_list}"
    )

    if isinstance(agent_caps_list, list):
        for cap_item in agent_caps_list:
            if isinstance(cap_item, dict) and "name" in cap_item:
                cap_name_val = cap_item.get("name")
                if isinstance(cap_name_val, str):
                    normalized_cap = _normalize_capability_name(cap_name_val)
                    capabilities.add(normalized_cap)
                    discovery_logger.debug(
                        f"  Added capability from dict for '{agent_id_for_log}': '{cap_name_val}' -> '{normalized_cap}'"
                    )
                else:
                    discovery_logger.warning(
                        f"  Invalid capability name type in dict for '{agent_id_for_log}': {type(cap_name_val)}"
                    )
            elif isinstance(cap_item, str):
                normalized_cap = _normalize_capability_name(cap_item)
                capabilities.add(normalized_cap)
                discovery_logger.debug(
                    f"  Added capability from string for '{agent_id_for_log}': '{cap_item}' -> '{normalized_cap}'"
                )
            else:
                discovery_logger.warning(
                    f"  Invalid capability item format for '{agent_id_for_log}': {cap_item} (type: {type(cap_item)})"
                )
    elif agent_caps_list:
        discovery_logger.warning(
            f"  Invalid capabilities format for '{agent_id_for_log}': Expected list, got {type(agent_caps_list)}. Value: {agent_caps_list}"
        )

    discovery_logger.debug(f"  Extracted capabilities for '{agent_id_for_log}': {capabilities}")
    return capabilities


async def handle_discovery_message(message: Dict[str, Any], sender_id: str):
    """Handles incoming discovery service messages (REGISTER or QUERY)."""
    if not message or not isinstance(message, dict):
        discovery_logger.error(
            f"Invalid message format received from '{sender_id}': Not a dict or empty. Type: {type(message)}"
        )
        return

    header = message.get("mcp_header", {})
    payload = message.get("payload", {})
    message_type = header.get("message_type", "UNKNOWN_TYPE")
    correlation_id = header.get("correlation_id")

    discovery_logger.info(
        f"Discovery received '{message_type}' from '{sender_id}' (CorrID: {correlation_id})"
    )

    # *** ROBUSTIFIED LOGGING FOR PAYLOAD ***
    if isinstance(payload, dict):
        temp_log_payload_dict = {}
        for log_key, log_value in payload.items():  # Using very distinct loop variable names
            if log_key == "capabilities" and isinstance(log_value, list):
                temp_log_payload_dict[log_key] = f"<omitted_capabilities_len_{len(log_value)}>"
            else:
                # Attempt to convert log_value to string for logging to be safe, truncate if too long
                try:
                    val_str = str(log_value)
                    temp_log_payload_dict[log_key] = (
                        val_str[:100] + "..." if len(val_str) > 100 else val_str
                    )
                except Exception:
                    temp_log_payload_dict[log_key] = "<unloggable_value>"
        payload_str_snippet = str(temp_log_payload_dict)  # Convert the constructed dict to string
        if len(payload_str_snippet) > 300:  # Truncate the final string if it's still too long
            payload_str_snippet = payload_str_snippet[:297] + "..."
        discovery_logger.debug(f"Message payload (CorrID: {correlation_id}): {payload_str_snippet}")
    # *** END ROBUSTIFIED LOGGING ***

    response_message = None
    try:
        if message_type == "DISCOVERY_REGISTER":
            response_message = await handle_registration(payload, sender_id, correlation_id)
        elif message_type == "DISCOVERY_QUERY":
            response_message = await handle_query(payload, sender_id, correlation_id)
        else:
            discovery_logger.warning(
                f"Unknown message type '{message_type}' from '{sender_id}' (CorrID: {correlation_id})."
            )
            error_payload = {
                "error_code": "E003",
                "error_message": f"Unsupported message type '{message_type}'",
            }
            response_message = create_mcp_error_response(
                sender_id, correlation_id, "MCP_DISCOVERY", error_payload
            )
    except Exception as e:
        discovery_logger.error(
            f"Error processing message type '{message_type}' from '{sender_id}' (CorrID: {correlation_id}): {e}",
            exc_info=True,
        )
        error_payload = {
            "error_code": "E999",
            "error_message": f"Internal error processing message: {str(e)}",
        }
        response_message = create_mcp_error_response(
            sender_id, correlation_id, "MCP_DISCOVERY", error_payload
        )

    if response_message:
        sender_ws = get_connection(sender_id)
        if sender_ws:
            try:
                if "payload" in response_message and isinstance(response_message["payload"], dict):
                    response_msg_type = response_message.get("mcp_header", {}).get("message_type")
                    if response_msg_type == "DISCOVERY_RESPONSE":
                        status_in_payload = response_message["payload"].get("status")
                        results_in_payload = response_message["payload"].get("results", [])
                        results_count = (
                            len(results_in_payload) if isinstance(results_in_payload, list) else -1
                        )
                        discovery_logger.info(
                            f"Final check before sending DISCOVERY_RESPONSE (CorrID: {correlation_id}): status='{status_in_payload}', results_count={results_count}"
                        )

                response_to_send = copy.deepcopy(response_message)
                try:
                    response_json = safe_json_serialize(response_to_send)
                except (NameError, AttributeError):
                    discovery_logger.warning(
                        "safe_json_serialize not available, falling back to standard json.dumps"
                    )
                    response_json = json.dumps(response_to_send)

                await sender_ws.send_text(response_json)
                sent_msg_type = response_message.get("mcp_header", {}).get("message_type")
                discovery_logger.info(
                    f"Sent response (Type: {sent_msg_type}) to '{sender_id}' (CorrID: {correlation_id})"
                )

                log_snippet = (
                    response_json[:250] + "..." if len(response_json) > 250 else response_json
                )
                discovery_logger.debug(f"Response sent (CorrID: {correlation_id}): {log_snippet}")
            except Exception as e:
                discovery_logger.error(
                    f"Failed to send response to '{sender_id}' (CorrID: {correlation_id}): {e}",
                    exc_info=True,
                )
        else:
            discovery_logger.warning(
                f"Cannot send response: Sender '{sender_id}' (CorrID: {correlation_id}) disconnected"
            )


async def handle_registration(
    payload: Dict[str, Any], sender_id: str, correlation_id: Optional[str]
) -> Optional[Dict[str, Any]]:
    """Handles agent registration, updating the agent_registry."""
    agent_id_from_payload = payload.get("agent_id")
    if (
        not agent_id_from_payload
        or not isinstance(agent_id_from_payload, str)
        or agent_id_from_payload != sender_id
    ):
        discovery_logger.warning(
            f"Registration failed for sender '{sender_id}' (CorrID: {correlation_id}): Invalid/mismatched agent_id '{agent_id_from_payload}' in payload."
        )
        error_payload = {
            "error_code": "E002",
            "error_message": "Registration requires valid 'agent_id' in payload matching WebSocket sender_id",
        }
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)

    required_fields = ["agent_name", "agent_type", "capabilities", "status"]
    missing_fields = [field for field in required_fields if field not in payload]
    if missing_fields:
        discovery_logger.warning(
            f"Registration failed for '{agent_id_from_payload}' (CorrID: {correlation_id}): Incomplete payload. Missing: {missing_fields}"
        )
        error_payload = {
            "error_code": "E003",
            "error_message": f"Incomplete registration. Missing: {', '.join(missing_fields)}",
        }
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)

    capabilities_list = payload.get("capabilities", [])
    if not isinstance(capabilities_list, list):
        discovery_logger.warning(
            f"Registration failed for '{agent_id_from_payload}' (CorrID: {correlation_id}): Invalid 'capabilities' format (expected list)."
        )
        error_payload = {"error_code": "E003", "error_message": "Capabilities must be a list"}
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)

    registration_info = copy.deepcopy(payload)
    registration_info["_last_seen"] = datetime.now(timezone.utc).isoformat()

    async with registry_lock:
        agent_registry[agent_id_from_payload] = registration_info
        current_registry_size = len(agent_registry)

    registered_caps = _get_agent_capabilities(registration_info)
    discovery_logger.info(
        f"Agent '{agent_id_from_payload}' (Type: {registration_info.get('agent_type')}) registered/updated. Status: '{registration_info.get('status')}'. Caps: {registered_caps}. Total Agents: {current_registry_size}. (CorrID: {correlation_id})"
    )

    ack_payload = {"status": "registered", "agent_id": agent_id_from_payload}
    return create_mcp_response(
        sender_id, correlation_id, "MCP_DISCOVERY", "DISCOVERY_ACK", ack_payload
    )


async def handle_query(
    payload: Dict[str, Any], sender_id: str, correlation_id: Optional[str]
) -> Dict[str, Any]:
    """Handles discovery queries for finding agents."""
    discovery_logger.info(f"Processing query from '{sender_id}' (CorrID: {correlation_id})")

    query_by_agent_id_val = payload.get("query_by_agent_id")
    query_by_capability_list_val = payload.get("query_by_capability_list")
    required_status_val = (payload.get("required_status", "active")).lower()

    if not query_by_agent_id_val and not query_by_capability_list_val:
        discovery_logger.warning(
            f"Invalid query from '{sender_id}' (CorrID: {correlation_id}): No query parameters provided (query_by_agent_id or query_by_capability_list)."
        )
        error_payload = {
            "error_code": "E101",
            "error_message": "Query must include either query_by_agent_id or query_by_capability_list",
        }
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)

    query_results = []

    try:
        async with registry_lock:
            registry_snapshot = copy.deepcopy(agent_registry)

        discovery_logger.debug(
            f"Querying against registry snapshot of size {len(registry_snapshot)} (CorrID: {correlation_id})"
        )

        if query_by_agent_id_val:
            if not isinstance(query_by_agent_id_val, str):
                raise ValueError("'query_by_agent_id' must be a string")
            discovery_logger.info(
                f"Query by ID: '{query_by_agent_id_val}' (CorrID: {correlation_id})"
            )
            agent_info = registry_snapshot.get(query_by_agent_id_val)
            if agent_info:
                is_connected = get_connection(query_by_agent_id_val) is not None
                agent_status = (agent_info.get("status", "")).lower()
                discovery_logger.debug(
                    f"  Agent '{query_by_agent_id_val}': Connected={is_connected}, Status='{agent_status}' (Required: '{required_status_val}')"
                )
                if (
                    required_status_val == "any" or agent_status == required_status_val
                ) and is_connected:
                    # Fixed variable names in dictionary comprehension
                    clean_info = {
                        key_item: value_item
                        for key_item, value_item in agent_info.items()
                        if not key_item.startswith("_")
                    }
                    query_results.append(clean_info)
                    discovery_logger.info(f"  -> Matched agent '{query_by_agent_id_val}' by ID.")
                else:
                    discovery_logger.info(
                        f"  Agent '{query_by_agent_id_val}' found but did not meet status/connection criteria."
                    )
            else:
                discovery_logger.info(
                    f"  Agent '{query_by_agent_id_val}' not found in registry snapshot."
                )

        elif query_by_capability_list_val:
            if not isinstance(query_by_capability_list_val, list):
                raise ValueError("'query_by_capability_list' must be a list")
            if not query_by_capability_list_val:
                raise ValueError("'query_by_capability_list' cannot be empty")

            required_caps_set = set()
            for cap_str_item in query_by_capability_list_val:
                if isinstance(cap_str_item, str):
                    required_caps_set.add(_normalize_capability_name(cap_str_item))
                else:
                    discovery_logger.warning(
                        f"  Non-string capability in query_by_capability_list: {cap_str_item} (CorrID: {correlation_id}). Skipping."
                    )

            if not required_caps_set:
                raise ValueError(
                    "Effective 'query_by_capability_list' is empty after processing non-string items."
                )

            discovery_logger.info(
                f"Query by capabilities: {required_caps_set} (CorrID: {correlation_id})"
            )
            discovery_logger.info(
                f"Checking {len(registry_snapshot)} registered agents (CorrID: {correlation_id})..."
            )

            for (
                agent_id_key,
                agent_info_val,
            ) in registry_snapshot.items():  # Fixed variable names in loop
                discovery_logger.debug(
                    f"  Evaluating agent '{agent_id_key}' (CorrID: {correlation_id}):"
                )
                is_connected = get_connection(agent_id_key) is not None
                agent_status_val = (agent_info_val.get("status", "")).lower()

                discovery_logger.debug(f"    Connected: {is_connected}")
                discovery_logger.debug(
                    f"    Status: '{agent_status_val}' (Required: '{required_status_val.upper()}')"
                )

                if is_connected and (
                    required_status_val == "any" or agent_status_val == required_status_val
                ):
                    agent_capabilities_set = _get_agent_capabilities(agent_info_val)
                    discovery_logger.debug(f"    Agent capabilities: {agent_capabilities_set}")
                    discovery_logger.debug(f"    Required capabilities: {required_caps_set}")

                    capabilities_match = required_caps_set.issubset(agent_capabilities_set)
                    discovery_logger.debug(f"    Capabilities match: {capabilities_match}")

                    if capabilities_match:
                        # Fixed variable names in dictionary comprehension
                        clean_info = {
                            key_item: value_item
                            for key_item, value_item in agent_info_val.items()
                            if not key_item.startswith("_")
                        }
                        query_results.append(clean_info)
                        discovery_logger.info(
                            f"  -> Matched agent '{agent_id_key}' for capabilities {required_caps_set}."
                        )
                else:
                    discovery_logger.debug(
                        f"    Agent '{agent_id_key}' skipped (connection/status requirements not met)."
                    )
            discovery_logger.info(
                f"Capability query complete (CorrID: {correlation_id}). Found {len(query_results)} matching agents."
            )

        status_str = "success" if query_results else "not_found"
        discovery_logger.info(
            f"Query from '{sender_id}' (CorrID: {correlation_id}) processing complete. Final Status: '{status_str}'. Found {len(query_results)} agents."
        )

        response_payload = {
            "query": copy.deepcopy(payload),
            "results": copy.deepcopy(query_results),
            "status": status_str,
        }

        if query_results:
            result_ids = [res.get("agent_id", "unknown_id_in_result") for res in query_results]
            discovery_logger.debug(
                f"Results for CorrID '{correlation_id}' include agent IDs: {result_ids}"
            )

        return create_mcp_response(
            sender_id, correlation_id, "MCP_DISCOVERY", "DISCOVERY_RESPONSE", response_payload
        )

    except ValueError as ve:
        discovery_logger.warning(
            f"Invalid query from '{sender_id}' (CorrID: {correlation_id}): {ve}. Payload: {payload}"
        )
        error_payload = {"error_code": "E003", "error_message": str(ve)}
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)

    except Exception as e:
        discovery_logger.error(
            f"Unexpected error during query processing from '{sender_id}' (CorrID: {correlation_id}): {e}",
            exc_info=True,
        )
        error_payload = {
            "error_code": "E999",
            "error_message": f"Internal server error during query processing: {str(e)}",
        }
        return create_mcp_error_response(sender_id, correlation_id, "MCP_DISCOVERY", error_payload)
