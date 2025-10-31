# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_router_service\utils.py
# Step 74: Integrated improvements based on Claude's suggestions - FIXED

import copy  # For deepcopy
import json
import uuid
from datetime import datetime, timezone  # Ensure timezone is imported
from typing import Any  # Added Union for safe_json_serialize

# Attempt to import logger from config, fallback to basic logging
try:
    from .config import logger  # Assuming .config has a configured logger
except ImportError:
    import logging

    # Default to DEBUG for more visibility during development/testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("mcp_router_service.utils")

logger.debug("MCP Router Utils module loaded (Step 74 Version - FIXED).")


def parse_mcp_message(message_text: str) -> dict[str, Any] | None:
    """Parses raw text received over WebSocket; returns MCP message dict or None on failure."""
    if not message_text or not isinstance(message_text, str):
        logger.error("parse_mcp_message: Received empty or non-string input.")
        return None
    try:
        message_dict = json.loads(message_text)
        # Basic structure validation
        if isinstance(message_dict, dict) and "mcp_header" in message_dict and "payload" in message_dict:
            if isinstance(message_dict["mcp_header"], dict) and isinstance(message_dict["payload"], dict):
                # Deeper check for essential header fields
                header = message_dict["mcp_header"]
                if not header.get("message_type"):
                    logger.error(
                        f"parse_mcp_message: Missing required field 'message_type' in header. Msg: {message_text[:200]}",
                    )
                    return None
                if not header.get("sender_id"):  # Added check for sender_id
                    logger.error(
                        f"parse_mcp_message: Missing required field 'sender_id' in header. Msg: {message_text[:200]}",
                    )
                    return None
                return message_dict
            else:
                logger.error(
                    f"parse_mcp_message: Invalid structure - header/payload not dicts. Msg: {message_text[:200]}",
                )
                return None
        else:
            logger.error(
                f"parse_mcp_message: Parsed JSON lacks basic MCP structure (mcp_header/payload keys). Msg: {message_text[:200]}",  # noqa: E501
            )
            return None
    except json.JSONDecodeError:
        logger.error(
            f"parse_mcp_message: Failed JSON decode for message: {message_text[:200]}",
            exc_info=True,
        )
        return None
    except Exception as e:
        logger.error(
            f"parse_mcp_message: Unexpected error parsing message: {e}. Msg: {message_text[:200]}",
            exc_info=True,
        )
        return None


def create_mcp_message(
    sender_id: str,
    message_type: str,
    payload: dict[str, Any],
    target_agent_id: str | None = None,
    target_service: str | None = None,
    correlation_id: str | None = None,
    version: str = "1.0",
    message_id: str | None = None,
) -> dict[str, Any] | None:
    """Creates a complete MCP message dictionary, ready for JSON serialization."""
    if not sender_id or not message_type:
        logger.error("create_mcp_message requires sender_id and message_type.")
        return None
    try:
        # Create header, removing None values for optional fields
        current_correlation_id = correlation_id if correlation_id else str(uuid.uuid4())
        header = {
            "message_id": message_id if message_id else str(uuid.uuid4()),
            "sender_id": sender_id,
            "target_agent_id": target_agent_id,
            "target_service": target_service,
            "message_type": message_type,
            "correlation_id": current_correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": version,
        }

        cleaned_header = {k: v for k, v in header.items() if v is not None}

        if not isinstance(payload, dict):
            logger.warning(
                f"Payload for message type '{message_type}' (CorrID: {current_correlation_id}) is not a dict (type: {type(payload)}). Wrapping in 'data' field.",  # noqa: E501
            )
            message_payload_safe = copy.deepcopy({"data": payload})
        else:
            message_payload_safe = copy.deepcopy(payload)

        message = {"mcp_header": cleaned_header, "payload": message_payload_safe}
        logger.debug(
            f"Created MCP Message: Type='{message_type}', Sender='{sender_id}', Target='{target_agent_id or target_service}', CorrID='{current_correlation_id}'",  # noqa: E501
        )
        return message
    except Exception as e:
        logger.error(
            f"Error creating MCP message (Type: {message_type}, CorrID: {correlation_id}): {e}",
            exc_info=True,
        )
        return None


def create_mcp_response(
    target_agent_id: str,
    correlation_id: str | None,
    sender_service: str,
    response_message_type: str,
    response_payload: dict[str, Any],
    message_id: str | None = None,
) -> dict[str, Any] | None:
    """Helper to create a standard response message addressed to the original sender (target_agent_id)."""
    if not target_agent_id or not sender_service or not response_message_type:
        logger.error("create_mcp_response requires target_agent_id, sender_service, and response_message_type.")
        return None

    payload_copy = copy.deepcopy(response_payload)  # Deep copy to avoid modifying the input dict

    if response_message_type == "DISCOVERY_RESPONSE" and isinstance(payload_copy, dict):
        results = payload_copy.get("results", [])
        status = payload_copy.get("status", "")

        if not isinstance(results, list):  # Ensure results is a list
            logger.warning(
                f"DISCOVERY_RESPONSE payload 'results' (CorrID: {correlation_id}) is not a list (Type: {type(results)}). Correcting to empty list.",  # noqa: E501
            )
            results = []
            payload_copy["results"] = results

        current_results_count = len(results)
        logger.info(
            f"Processing {response_message_type} for Target='{target_agent_id}', CorrID='{correlation_id}': Initial status='{status}', initial results_count={current_results_count}",  # noqa: E501
        )

        corrected_status = status
        if status == "success" and not results:
            logger.warning(
                f"Fixing inconsistent DISCOVERY_RESPONSE (CorrID: {correlation_id}): 'success' status with empty results. Changing status to 'not_found'.",  # noqa: E501
            )
            corrected_status = "not_found"
        elif status == "not_found" and results:
            logger.warning(
                f"Fixing inconsistent DISCOVERY_RESPONSE (CorrID: {correlation_id}): 'not_found' status with {current_results_count} results. Changing status to 'success'.",  # noqa: E501
            )
            corrected_status = "success"
        elif not status:  # If status is empty or None
            corrected_status = "success" if results else "not_found"
            logger.warning(
                f"Fixing DISCOVERY_RESPONSE (CorrID: {correlation_id}): Missing status. Based on results ({current_results_count}), setting status to '{corrected_status}'.",  # noqa: E501
            )

        if corrected_status != status:  # Only update if changed
            payload_copy["status"] = corrected_status
            logger.info(
                f"DISCOVERY_RESPONSE (CorrID: {correlation_id}): Status corrected from '{status}' to '{corrected_status}'.",  # noqa: E501
            )
        status = corrected_status  # Use the potentially corrected status for logging

    # Log the payload that will be used for the message creation
    payload_log_snippet = (
        {k: v for k, v in payload_copy.items() if k != "results"}
        if isinstance(payload_copy, dict)
        else str(payload_copy)
    )
    results_count_for_log = (
        len(payload_copy.get("results", [])) if isinstance(payload_copy, dict) and "results" in payload_copy else "N/A"
    )

    logger.debug(
        f"Final response payload for create_mcp_message (CorrID: {correlation_id}): {payload_log_snippet}, results_count={results_count_for_log}, status='{payload_copy.get('status', 'N/A') if isinstance(payload_copy, dict) else 'N/A'}'",  # noqa: E501
    )

    if (
        isinstance(payload_copy, dict)
        and payload_copy.get("results")
        and isinstance(payload_copy["results"], list)
        and payload_copy["results"]
    ):
        first_result_snippet = (
            str(payload_copy["results"][0])[:100] + "..."
            if len(str(payload_copy["results"][0])) > 100
            else str(payload_copy["results"][0])
        )
        logger.debug(f"First result snippet in final payload (CorrID: {correlation_id}): {first_result_snippet}")

    return create_mcp_message(
        message_id=message_id,
        sender_id=sender_service,
        target_agent_id=target_agent_id,
        message_type=response_message_type,
        payload=payload_copy,
        correlation_id=correlation_id,
    )


def create_mcp_error_response(
    target_agent_id: str,
    correlation_id: str | None,
    sender_service: str,
    error_payload: dict[str, Any],
    error_message_type: str = "ERROR",
) -> dict[str, Any] | None:
    """Helper to create a standard ERROR or TASK_FAIL response message."""
    if "error_code" not in error_payload or "error_message" not in error_payload:
        logger.warning(
            f"Creating error response ({error_message_type}) for CorrID '{correlation_id}' without standard error_code/error_message. Adding defaults.",  # noqa: E501
        )
        error_payload.setdefault("error_code", "E_UNKNOWN")
        error_payload.setdefault("error_message", "An unspecified error occurred.")

    logger.debug(
        f"Creating error response: Type='{error_message_type}', Sender='{sender_service}', Target='{target_agent_id}', CorrID='{correlation_id}'",  # noqa: E501
    )
    logger.debug(f"Error payload content for CorrID '{correlation_id}': {error_payload}")

    safe_payload = copy.deepcopy(error_payload)

    return create_mcp_message(
        sender_id=sender_service,
        target_agent_id=target_agent_id,
        message_type=error_message_type,
        payload=safe_payload,
        correlation_id=correlation_id,
    )


def safe_json_serialize(obj: Any, default_msg: str = "Object not serializable") -> str:
    """Safely serialize an object to JSON, with fallback handling for non-serializable objects.
    Returns a JSON string.
    """
    try:
        return json.dumps(obj)
    except (TypeError, ValueError, OverflowError) as e:  # Added OverflowError
        logger.error(f"JSON serialization error: {e}. Object type: {type(obj)}", exc_info=True)

        if isinstance(obj, dict):
            sanitized = {}
            for key, value in obj.items():  # Fixed variable names
                try:
                    json.dumps({key: value})
                    sanitized[key] = value
                except Exception:
                    sanitized[key] = f"UNSERIALIZABLE_VALUE:{str(value)[:100]}"  # Truncate long string representations
            logger.warning(f"Attempting to send sanitized dict after serialization error: {list(sanitized.keys())}")
            return json.dumps(sanitized)
        elif isinstance(obj, list):
            sanitized = []
            for item in obj:
                try:
                    json.dumps(item)
                    sanitized.append(item)
                except Exception:
                    sanitized.append(f"UNSERIALIZABLE_ITEM:{str(item)[:100]}")  # Truncate
            logger.warning(f"Attempting to send sanitized list after serialization error. Length: {len(sanitized)}")
            return json.dumps(sanitized)
        else:
            logger.error(f"Cannot sanitize non-dict/list object of type {type(obj)}. Returning error placeholder.")
            return json.dumps({"error": default_msg, "original_type": str(type(obj))})
