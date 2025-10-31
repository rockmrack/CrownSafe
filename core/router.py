# core_infra/mcp_router_service/router.py
# MODIFIED for Step 98.1.14: Add CRITICAL entry log to handle_message

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import WebSocket

from . import discovery, state
from .config import logger  # Assuming logger is configured in config.py
from .utils import create_mcp_error_response, create_mcp_message, parse_mcp_message


async def forward_message(
    sender_id: str,  # This is the original sender_id from the message header
    message_to_forward: Dict[str, Any],
    target_agent_id: str,  # The agent_id to forward the message to
    label: str,
) -> bool:
    hdr = message_to_forward.get("mcp_header", {})
    corr_id = hdr.get("correlation_id", "N/A")
    msg_type = hdr.get("message_type", "UNKNOWN_TYPE")

    logger.info(
        f"FORWARDING MSG [{label}]: Type='{msg_type}', OriginalSender='{hdr.get('sender_id', 'UNKNOWN')}', Target='{target_agent_id}', CorrID='{corr_id}'"  # noqa: E501
    )

    message_content_snippet = "Could not serialize for logging"
    try:
        message_content_snippet = json.dumps(message_to_forward)
        if len(message_content_snippet) > 300:
            message_content_snippet = message_content_snippet[:300] + "..."
    except Exception:
        pass
    logger.debug(f"FORWARDING MSG CONTENT to {target_agent_id}: {message_content_snippet}")

    ws = state.get_connection(target_agent_id)

    if not ws:
        logger.warning(
            f"FORWARDING MSG [{label}]: No active WebSocket connection for target '{target_agent_id}'. Cannot deliver."
        )
        return False

    try:
        await ws.send_json(message_to_forward)  # FastAPI WebSocket handles dict to json
        logger.info(f"FORWARDING MSG [{label}]: Successfully delivered Type='{msg_type}' to '{target_agent_id}'.")
        return True
    except Exception as e:
        logger.error(
            f"FORWARDING MSG [{label}]: Error delivering Type='{msg_type}' to '{target_agent_id}': {e}",
            exc_info=True,
        )
        return False


async def handle_message(agent_id: str, message_text: str, websocket: WebSocket):
    """Handles incoming messages, parses them, and routes them appropriately."""

    # --- ADDED CRITICAL LOG (GPT Suggestion B) ---
    # Attempt to parse for logging details, but log raw snippet regardless
    log_snippet_critical = message_text[:300] + "..." if len(message_text) > 300 else message_text
    msg_type_log = "UNPARSABLE_JSON"
    sender_log = agent_id  # agent_id from path is the connected agent
    target_agent_log = "N/A"
    target_service_log = "N/A"
    corr_id_log = "N/A"
    try:
        parsed_for_log = json.loads(message_text)
        if isinstance(parsed_for_log, dict) and "mcp_header" in parsed_for_log:
            header_for_log = parsed_for_log["mcp_header"]
            msg_type_log = header_for_log.get("message_type", "NO_MSG_TYPE_IN_HDR")
            sender_log = header_for_log.get("sender_id", agent_id)  # Prefer header sender_id
            target_agent_log = header_for_log.get("target_agent_id", "N/A")
            target_service_log = header_for_log.get("target_service", "N/A")
            corr_id_log = header_for_log.get("correlation_id", "N/A")
    except json.JSONDecodeError:
        logger.warning(
            f"MCP_ROUTER_RAW_RECV: Could not parse JSON for detailed critical log from '{agent_id}'. Raw: {log_snippet_critical}"  # noqa: E501
        )
    except Exception:  # Catch any other error during this pre-logging parse
        logger.warning(
            f"MCP_ROUTER_RAW_RECV: Error during pre-logging parse from '{agent_id}'. Raw: {log_snippet_critical}"
        )

    logger.critical(
        f"MCP_ROUTER_RAW_RECV: From PathAgentID='{agent_id}', ApparentSender='{sender_log}', "
        f"MsgType='{msg_type_log}', TargetAgent='{target_agent_log}', TargetService='{target_service_log}', "
        f"CorrID='{corr_id_log}'. Raw Snippet: {log_snippet_critical}"
    )
    # --- END ADDED CRITICAL LOG ---

    logger.debug(f"ROUTER RECV: from='{agent_id}' snippet='{message_text[:200]}'")  # Existing debug log
    msg: Optional[Dict[str, Any]] = None
    try:
        msg = parse_mcp_message(message_text)
        if not msg or "mcp_header" not in msg:
            logger.warning(f"ROUTER: Malformed message from '{agent_id}'; dropping. raw='{message_text}'")
            return

        hdr = msg.get("mcp_header", {})
        payload = msg.get("payload", {})
        mtype = hdr.get("message_type", "")
        corr = hdr.get("correlation_id", "")
        target_svc = hdr.get("target_service")
        header_sender_id = hdr.get("sender_id")

        if header_sender_id != agent_id:  # Path agent_id must match sender_id in header
            logger.error(
                f"ROUTER: Sender ID mismatch in message from connection '{agent_id}': Header sender_id is '{header_sender_id}'. Rejecting message."  # noqa: E501
            )
            # Optionally send an error back to the client
            err_resp = create_mcp_error_response(
                sender_id="MCP_ROUTER",
                correlation_id=corr,
                target_agent_id=agent_id,
                payload={
                    "error_code": "E001",
                    "error_message": f"Header sender_id '{header_sender_id}' does not match connection agent_id '{agent_id}'.",  # noqa: E501
                },
            )
            if err_resp:
                await websocket.send_json(err_resp)
            return

        if target_svc == "MCP_DISCOVERY":
            logger.debug(f"ROUTER ROUTE→DISCOVERY: Type='{mtype}', From='{agent_id}', CorrID='{corr}'")
            await discovery.handle_discovery_message(msg, agent_id)  # Pass full msg and path agent_id
            return

        if mtype == "PROCESS_USER_REQUEST":
            target_commander_id = None
            all_connected_agents = list(state.get_all_connections().keys())
            logger.debug(
                f"ROUTER: Searching for CommanderAgent among: {all_connected_agents} for PROCESS_USER_REQUEST from '{agent_id}'"  # noqa: E501
            )
            for connected_agent_id_str in all_connected_agents:
                if "commander_agent" in connected_agent_id_str.lower():  # More specific check
                    target_commander_id = connected_agent_id_str
                    logger.info(
                        f"ROUTER: Found CommanderAgent '{target_commander_id}' to handle PROCESS_USER_REQUEST from '{agent_id}'"  # noqa: E501
                    )
                    break

            if target_commander_id:
                # The sender_id for forward_message should be the original sender (agent_id from path)
                success = await forward_message(agent_id, msg, target_commander_id, label="PROCESS_USER_REQUEST")
                if not success:
                    err_resp = create_mcp_error_response(
                        sender_id="MCP_ROUTER",
                        correlation_id=corr,
                        target_agent_id=agent_id,
                        payload={
                            "error_code": "E008",
                            "error_message": f"Could not forward PROCESS_USER_REQUEST to '{target_commander_id}'",
                        },
                    )
                    if err_resp:
                        await websocket.send_json(err_resp)
            else:
                logger.error(f"ROUTER: No CommanderAgent found to handle PROCESS_USER_REQUEST from '{agent_id}'")
                err_resp = create_mcp_error_response(
                    sender_id="MCP_ROUTER",
                    correlation_id=corr,
                    target_agent_id=agent_id,
                    payload={
                        "error_code": "E007",
                        "error_message": "No CommanderAgent available to process request",
                    },
                )
                if err_resp:
                    await websocket.send_json(err_resp)
            return

        target_agent_id_for_task = hdr.get("target_agent_id")
        if mtype == "TASK_ASSIGN":  # This is for agent-to-agent task assignment
            logger.info(
                f"ROUTER HANDLE: TASK_ASSIGN from='{agent_id}' to='{target_agent_id_for_task}', CorrID='{corr}'"
            )
            if not target_agent_id_for_task:
                err_resp = create_mcp_error_response(
                    sender_id="MCP_ROUTER",
                    correlation_id=corr,
                    target_agent_id=agent_id,
                    payload={
                        "error_code": "E004",
                        "error_message": "Missing target_agent_id for TASK_ASSIGN",
                    },
                )
                if err_resp:
                    await websocket.send_json(err_resp)
                return
            # The sender_id for forward_message should be the original sender (agent_id from path)
            success = await forward_message(agent_id, msg, target_agent_id_for_task, label="TASK_ASSIGN")
            if not success:
                err_resp = create_mcp_error_response(
                    sender_id="MCP_ROUTER",
                    correlation_id=corr,
                    target_agent_id=agent_id,
                    payload={
                        "error_code": "E005",
                        "error_message": f"Could not forward TASK_ASSIGN to '{target_agent_id_for_task}'",
                    },
                )
                if err_resp:
                    await websocket.send_json(err_resp)
            return

        if mtype in (
            "TASK_COMPLETE",
            "TASK_FAIL",
        ):  # TASK_ACK was removed from this group as it's usually server->client
            original_requester = target_agent_id_for_task
            logger.info(
                f"ROUTER HANDLE: {mtype} from='{agent_id}' routing to original_requester='{original_requester}', CorrID='{corr}'"  # noqa: E501
            )
            if not original_requester:
                logger.warning(
                    f"ROUTER: No target_agent_id (original_requester_id) on {mtype} from '{agent_id}'; dropping."
                )
                return
            # The sender_id for forward_message should be the original sender (agent_id from path)
            await forward_message(agent_id, msg, original_requester, label=mtype)
            return

        if mtype == "PING":
            logger.debug(f"ROUTER HANDLE: PING from='{agent_id}', CorrID='{corr}'")
            pong_payload = {
                "timestamp": payload.get("timestamp")
                if isinstance(payload, dict)
                else datetime.now(timezone.utc).timestamp(),
                "status": "acknowledged",
            }
            # PONG is sent from MCP_ROUTER back to the pinger (agent_id)
            pong_msg = create_mcp_message(
                sender_id="MCP_ROUTER",
                target_agent_id=agent_id,
                message_type="PONG",
                payload=pong_payload,
                correlation_id=corr,
            )
            if pong_msg:
                await websocket.send_json(pong_msg)
            else:
                logger.error(f"ROUTER: Unable to build PONG for '{agent_id}', CorrID='{corr}'")
            return

        logger.warning(
            f"ROUTER HANDLE: Unhandled message_type='{mtype}', TargetService='{target_svc}', From='{agent_id}', CorrID='{corr}'"  # noqa: E501
        )
        err_resp = create_mcp_error_response(
            sender_id="MCP_ROUTER",
            correlation_id=corr,
            target_agent_id=agent_id,
            payload={
                "error_code": "E003",
                "error_message": f"Unhandled message type '{mtype}' by router",
            },
        )
        if err_resp:
            await websocket.send_json(err_resp)

    except json.JSONDecodeError:
        logger.error(f"ROUTER: Invalid JSON from '{agent_id}': {message_text}")
        # Attempt to send an error response for unparseable JSON
        try:
            err_resp_unparseable = create_mcp_error_response(
                sender_id="MCP_ROUTER",
                target_agent_id=agent_id,  # Send back to the sender
                correlation_id=None,  # No correlation_id if message is unparseable
                payload={
                    "error_code": "E002",
                    "error_message": "Invalid JSON format received.",
                },
            )
            if err_resp_unparseable:
                await websocket.send_json(err_resp_unparseable)
        except Exception as send_err_ex:
            logger.error(f"ROUTER: Failed to send unparseable JSON error to '{agent_id}': {send_err_ex}")

    except Exception:
        logger.exception(f"ROUTER: Internal error handling message from '{agent_id}'")
        try:
            corr_id_for_error = (
                msg.get("mcp_header", {}).get("correlation_id", "") if msg and isinstance(msg, dict) else None
            )  # Use None if not found
            err_resp = create_mcp_error_response(
                sender_id="MCP_ROUTER",
                correlation_id=corr_id_for_error,
                target_agent_id=agent_id,
                payload={
                    "error_code": "E999",
                    "error_message": "Internal router error processing message.",
                },
            )
            if err_resp:
                await websocket.send_json(err_resp)
        except Exception as send_err_ex:
            logger.error(f"ROUTER: Failed to send internal error notification to '{agent_id}': {send_err_ex}")
