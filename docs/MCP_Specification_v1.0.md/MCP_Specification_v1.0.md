# RossNet Model Context Protocol (MCP) Specification v1.0

**Version:** 1.0
**Date:** 2024-07-30
**Status:** Draft

## 1. Overview

The Model Context Protocol (MCP) defines the standard for secure, reliable, and context-aware communication between internal agents, tools, and services within the RossNet ecosystem. It facilitates task delegation, status tracking, data exchange, and service discovery. MCP is designed to operate over reliable transport layers (e.g., TCP via WebSockets, gRPC streams, or message queues configured for reliable delivery).

## 2. Core Principles

*   **Standardization:** Consistent message formats and interaction patterns.
*   **Context-Awareness:** Messages carry essential metadata for tracing, state management, and routing.
*   **Discoverability:** Agents and services can dynamically discover each other.
*   **Security:** Authentication and authorization integrated into the protocol flow.
*   **Asynchronicity:** Supports both synchronous request/response and asynchronous message passing.

## 3. Message Structure

All MCP messages adhere to a standard envelope structure, serialized as JSON. Implementations may utilize Protobuf for efficiency, mapping directly to this logical structure.

```json
{
  "mcp_header": {
    "message_id": "uuid_string",       // Unique ID for this specific message
    "correlation_id": "uuid_string",   // ID linking related messages in a flow/conversation
    "sender_id": "agent_or_service_id_string", // Unique ID of the sender
    "recipient_id": "agent_or_service_id_string | 'MCP_ROUTER' | 'MCP_DISCOVERY'", // Target ID or system service
    "timestamp": "iso_8601_datetime_string", // UTC timestamp of message creation
    "version": "1.0",                  // MCP version
    "message_type": "string",          // Defined message type (e.g., 'TASK_ASSIGN', 'STATUS_UPDATE')
    "auth_token": "jwt_string | null", // Authentication token (JWT) - See Section 6
    "task_metadata": {                 // Optional: Context about the overarching task
      "task_id": "uuid_string | null", // ID of the overall task this message relates to
      "priority": "integer | null",    // Task priority (e.g., 1-5, 5=highest)
      "required_accuracy": "string | null" // e.g., 'standard', 'high', 'maximum'
      // Other relevant task context...
    }
  },
  "payload": {
    // Message-type specific payload (JSON object) - See Section 4
  }
}


5. Interaction Patterns
5.1. Simple Task Assignment
Controller -> MCP_ROUTER : TASK_ASSIGN (recipient=WorkerAgent)
MCP_ROUTER -> WorkerAgent : TASK_ASSIGN
WorkerAgent -> MCP_ROUTER : TASK_ACKNOWLEDGE (recipient=Controller, status=ACCEPTED)
MCP_ROUTER -> Controller : TASK_ACKNOWLEDGE
(WorkerAgent processes task)
WorkerAgent -> MCP_ROUTER : STATUS_UPDATE (recipient=Controller, optional)
MCP_ROUTER -> Controller : STATUS_UPDATE (optional)
WorkerAgent -> MCP_ROUTER : TASK_COMPLETE / TASK_FAIL (recipient=Controller)
MCP_ROUTER -> Controller : TASK_COMPLETE / TASK_FAIL
5.2. Agent Discovery & Task Assignment
PlannerAgent -> MCP_DISCOVERY : DISCOVERY_QUERY (query_by_capability=web_search)
MCP_DISCOVERY -> PlannerAgent : DISCOVERY_RESPONSE (results=[{agent_id=WebSearchAgent01, ...}])
PlannerAgent -> MCP_ROUTER : TASK_ASSIGN (recipient=WebSearchAgent01)
(Proceeds as Simple Task Assignment)
6. Authentication
Authentication is performed using JSON Web Tokens (JWT).
Agents obtain a short-lived JWT from a central RossNet Identity Service (implementation outside MCP spec).
The JWT MUST be included in the mcp_header.auth_token field for all messages sent to the MCP_ROUTER or other agents requiring authentication.
The MCP_ROUTER MUST validate the JWT before processing or forwarding messages. It may inject sender identity information based on the validated token for downstream trust.
Messages to public services like MCP_DISCOVERY might not require authentication, TBD by deployment policy.
7. Standard Error Codes
A non-exhaustive list of standard error codes for TASK_FAIL messages:
E001: UNAUTHENTICATED
E002: UNAUTHORIZED
E003: INVALID_PAYLOAD
E004: AGENT_NOT_FOUND
E005: CAPABILITY_NOT_FOUND
E006: TIMEOUT
E007: RESOURCE_UNAVAILABLE (e.g., external API down)
E008: INTERNAL_AGENT_ERROR
E009: TASK_REJECTED (Used in TASK_ACKNOWLEDGE with status REJECTED)
E999: UNKNOWN_ERROR
8. Versioning
This specification follows Semantic Versioning 2.0.0. The version is indicated in the mcp_header.version field. Implementations MUST handle version negotiation or reject messages with incompatible versions if necessary.
