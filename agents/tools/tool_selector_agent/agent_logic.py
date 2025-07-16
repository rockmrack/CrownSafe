# C:\Users\rossd\Downloads\RossNetAgents\agents\tools\tool_selector_agent\agent_logic.py
# Updated to use MCP Discovery Service for basic tool/agent selection

import asyncio
import json
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

# Import client library components
from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.exceptions import MCPConnectionError, MCPMessageError

class ToolSelectorLogic:
    """Handles the logic for selecting appropriate tools/agents based on requested capabilities."""

    def __init__(self, agent_id: str, mcp_client: MCPClient, logger: logging.Logger):
        self.agent_id = agent_id
        self.mcp_client = mcp_client # Store the client instance
        self.logger = logger
        # In-memory state for pending selection requests
        # Key: correlation_id (unique ID for the selection request)
        # Value: {"status": str, "required_capabilities": list, "original_requester_id": str, "request_time": str}
        # Statuses: RECEIVED, PENDING_DISCOVERY, COMPLETED, FAILED
        self.pending_selections: Dict[str, Any] = {}
        self.logger.info("ToolSelectorLogic initialized.")

    async def process_message(self, message_type: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes incoming TASK_ASSIGN (for selection) or DISCOVERY_RESPONSE messages."""
        # Return value is optional response payload to be sent back by main.py's handler

        if message_type == "TASK_ASSIGN":
            # This agent is assigned the task of selecting a tool/agent
            return await self._handle_selection_request(payload)
        elif message_type == "DISCOVERY_RESPONSE":
            # This is the result of a discovery query initiated by this agent
            await self._handle_discovery_result(payload)
            return None # Discovery result handling sends its own response
        else:
            self.logger.warning(f"Received unhandled message type '{message_type}'. Ignoring.")
            return None

    async def _handle_selection_request(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handles a TASK_ASSIGN request to select a tool/agent."""
        required_capabilities = payload.get("required_capabilities")
        task_description = payload.get("task_description") # Alternative input
        correlation_id = payload.get("correlation_id") # ID for this selection task
        original_requester_id = payload.get("original_requester_id") # Who asked for the selection

        if not correlation_id or not original_requester_id:
             self.logger.error("Received selection request missing correlation_id or original_requester_id.")
             # Cannot easily report failure without routing info
             return None

        if not required_capabilities and task_description:
            self.logger.warning(f"Selection request {correlation_id} received task_description but not required_capabilities. LLM interpretation needed (Not Implemented).")
            # TODO: Implement LLM call to extract capabilities from description
            # For now, fail if capabilities aren't provided directly
            return self._create_failure_response(correlation_id, original_requester_id, "Missing 'required_capabilities' in payload.")

        if not isinstance(required_capabilities, list) or not required_capabilities:
            self.logger.error(f"Received selection request {correlation_id} with invalid or empty 'required_capabilities'.")
            return self._create_failure_response(correlation_id, original_requester_id, "Invalid or empty 'required_capabilities' provided.")

        self.logger.info(f"Received tool selection request {correlation_id} for capabilities: {required_capabilities} from {original_requester_id}.")

        # Store pending request state
        self.pending_selections[correlation_id] = {
            "status": "RECEIVED",
            "required_capabilities": required_capabilities,
            "original_requester_id": original_requester_id,
            "request_time": datetime.now().isoformat()
        }

        # Initiate discovery
        self.logger.info(f"Initiating discovery for selection request {correlation_id}. Capabilities: {required_capabilities}")
        self.pending_selections[correlation_id]["status"] = "PENDING_DISCOVERY"
        try:
            # Associate correlation_id with the query if possible
            await self.mcp_client.query_discovery(required_capabilities)
            # No immediate response payload needed here, wait for DISCOVERY_RESPONSE
            return None
        except Exception as e:
            self.logger.error(f"Failed to send DISCOVERY_QUERY for selection request {correlation_id}: {e}", exc_info=True)
            self.pending_selections[correlation_id]["status"] = "FAILED"
            # Need to send TASK_FAIL back to original requester
            failure_payload = self._create_failure_response(correlation_id, original_requester_id, f"Failed to initiate discovery: {e}")
            # Cleanup state?
            if correlation_id in self.pending_selections:
                 del self.pending_selections[correlation_id]
            return failure_payload


    async def _handle_discovery_result(self, discovery_payload: Dict[str, Any]):
        """Processes DISCOVERY_RESPONSE, selects agent, sends TASK_COMPLETE/FAIL."""
        query_payload = discovery_payload.get("query_payload", {})
        found_agents = discovery_payload.get("found_agents", [])
        status = discovery_payload.get("status")
        required_capabilities = query_payload.get("required_capabilities")

        self.logger.info(f"Handling DISCOVERY_RESPONSE for capabilities: {required_capabilities}. Status: {status}. Found: {len(found_agents)} agents.")

        # Find the corresponding pending selection request
        target_request_id = None
        for req_id, req_state in self.pending_selections.items():
             # Match based on capabilities and pending status
             if req_state["status"] == "PENDING_DISCOVERY" and req_state["required_capabilities"] == required_capabilities:
                  target_request_id = req_id
                  break

        if not target_request_id:
            self.logger.warning(f"Received DISCOVERY_RESPONSE for capabilities {required_capabilities}, but no matching selection request found in pending state.")
            return # Ignore stale/unmatched responses

        request_state = self.pending_selections[target_request_id]
        original_requester_id = request_state["original_requester_id"]

        # --- Select Agent ---
        selected_agent_id = None
        selection_details = {"strategy": "first_active"} # Document selection method

        if status == "success" and found_agents:
            # Simple strategy: pick the first agent that reports as ACTIVE
            for agent_info in found_agents:
                 if agent_info.get("metadata", {}).get("status") == "ACTIVE":
                      selected_agent_id = agent_info.get("agent_id")
                      selection_details["selected_agent_info"] = agent_info # Store info about selected agent
                      break
            if selected_agent_id:
                 self.logger.info(f"Discovery successful for selection request {target_request_id}. Selected agent: {selected_agent_id}")
            else:
                 self.logger.warning(f"Discovery for selection request {target_request_id} found agents, but none were ACTIVE.")
                 # Fall through to failure case

        # --- Send Response ---
        response_payload = None
        if selected_agent_id:
            request_state["status"] = "COMPLETED"
            response_payload = {
                "status_type": "TASK_COMPLETE",
                "message": "Tool/agent selection successful.",
                "selected_agent_id": selected_agent_id,
                "selection_details": selection_details,
                # Include original request details if helpful
                "original_request_capabilities": request_state["required_capabilities"],
            }
        else:
            request_state["status"] = "FAILED"
            error_msg = f"Tool/agent selection failed: No suitable agent found (Discovery Status: {status})."
            self.logger.error(f"{error_msg} Request ID: {target_request_id}")
            response_payload = self._create_failure_response(target_request_id, original_requester_id, error_msg)

        # Send response back to the original requester of the selection task
        if response_payload:
             # Add routing info needed by main.py handler
             response_payload["correlation_id"] = target_request_id
             response_payload["original_requester_id"] = original_requester_id
             try:
                  # Assuming main.py's handler will send this payload
                  # We need to signal main.py to send it.
                  # For simplicity, let's have logic send directly for now.
                  response_type = response_payload.get("status_type")
                  await self.mcp_client.send_message(response_type, response_payload)
                  self.logger.info(f"Sent selection {response_type} response for {target_request_id} to {original_requester_id}.")
             except Exception as e:
                  self.logger.error(f"Failed to send selection response for {target_request_id}: {e}", exc_info=True)

        # Cleanup completed/failed request state
        if target_request_id in self.pending_selections:
             del self.pending_selections[target_request_id]


    def _create_failure_response(self, correlation_id: str, original_requester_id: str, error_message: str) -> Dict[str, Any]:
        """Helper to create a TASK_FAIL payload."""
        return {
            "status_type": "TASK_FAIL",
            "error_message": error_message,
            "correlation_id": correlation_id,
            "original_requester_id": original_requester_id, # Needed by main handler
            "agent_id": self.agent_id # Identify this agent as the source of failure
        }