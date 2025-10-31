# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_client_library\models.py
# Step 106.3: Drastically simplify MCPMessage payload validation.

import logging
import uuid
from datetime import datetime, timezone
from typing import (
    Any,
)  # Removed Set, Union as not used in this simplified version

from pydantic import BaseModel, Field, field_validator, root_validator

logger = logging.getLogger(__name__)

# REQUIRED_PAYLOAD_FIELDS is not used by MCPMessage directly anymore in this version
# It can be kept for reference or used by application logic if needed.
REQUIRED_PAYLOAD_FIELDS = {
    "DISCOVERY_REGISTER": {
        "agent_id",
        "agent_name",
        "agent_type",
        "capabilities",
        "status",
    },
    "DISCOVERY_QUERY": {"requester_agent_id", "query_by_capability_list"},
    "DISCOVERY_RESPONSE": {"query", "results", "status"},
    "DISCOVERY_ACK": {"status", "agent_id"},
    "TASK_COMPLETE": {"workflow_id", "task_id", "agent_id"},
    "TASK_FAIL": {"workflow_id", "task_id", "agent_id", "error_message"},
    "PROCESS_USER_REQUEST": {"goal"},
}


class MCPHeader(BaseModel):
    sender_id: str = Field(..., description="Unique ID of the sending agent or service")
    message_type: str = Field(..., description="Type of the message")
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = Field("1.0")
    target_agent_id: str | None = Field(None)
    target_service: str | None = Field(None)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_iso(cls, v):
        try:
            datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except (ValueError, TypeError):
            raise ValueError("Timestamp must be ISO 8601 format")

    @field_validator("message_type")
    @classmethod
    def message_type_must_be_valid(cls, v: str) -> str:
        known_types = {
            "DISCOVERY_REGISTER",
            "DISCOVERY_QUERY",
            "DISCOVERY_RESPONSE",
            "DISCOVERY_ACK",
            "TASK_ASSIGN",
            "TASK_COMPLETE",
            "TASK_FAIL",
            "PING",
            "PONG",
            "ERROR",
            "PROCESS_USER_REQUEST",
        }
        if v not in known_types:
            logger.warning(f"Unknown message type in MCPHeader: '{v}'")
        return v


class MCPMessage(BaseModel):
    mcp_header: MCPHeader
    # Ensure payload is always treated as a dictionary.
    # If 'payload' key is missing from input, default_factory creates an empty dict.
    # If 'payload' key is present, its value will be used.
    # The type hint Dict[str, Any] means Pydantic will expect a dict-like structure.
    payload: dict[str, Any] = Field(default_factory=dict)

    @root_validator(pre=True)  # Keep this to ensure basic structure
    @classmethod
    def ensure_basic_structure(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict):
            raise ValueError("MCPMessage input must be a dictionary.")
        if "mcp_header" not in values:  # mcp_header is mandatory
            raise ValueError("MCPMessage input must contain 'mcp_header'.")

        # If 'payload' is missing, Pydantic's Field default_factory will handle it.
        # If 'payload' is present but not a dict, Pydantic will raise a validation error
        # because the type hint is Dict[str, Any]. So, this explicit check might be redundant
        # or could be made more specific if needed. For now, let Pydantic handle type.
        # if 'payload' in values and not isinstance(values['payload'], dict):
        #     logger.warning(f"MCPMessage 'payload' was provided but not as a dict (type: {type(values['payload'])}). This might cause issues.")  # noqa: E501
        # Not forcing to {} here, let Pydantic's type validation for Dict[str, Any] catch it if it's not a dict.
        return values

    # REMOVED the custom 'validate_payload_fields_conditionally' field_validator for 'payload'
    # We will rely on the receiving agent's logic to validate the contents of the payload
    # based on the message_type from the header. This Pydantic model will only ensure
    # that 'payload' itself is a dictionary (or an empty one if not provided).


logger.info("MCP Pydantic models loaded (Step 106.3 Simplified Payload Validation).")
