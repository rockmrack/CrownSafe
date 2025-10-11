# C:\Users\rossd\Downloads\RossNetAgents\agents\tools\tool_selector_agent\main.py

import asyncio
import os
import signal
import json
from dotenv import load_dotenv
import logging

# Import client library components
from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage  # Assuming this exists
from core_infra.mcp_client_library.exceptions import MCPConnectionError, MCPMessageError

# Import agent-specific logic
from .agent_logic import ToolSelectorLogic  # Make sure class name matches

# --- Configuration ---
load_dotenv()

AGENT_ID = "tool_selector_agent_01"  # Unique ID for this agent instance
AGENT_TYPE = "ToolSelectorAgent"
AGENT_VERSION = "1.0.0"  # Example version

# Define Capabilities for Discovery
AGENT_CAPABILITIES = [
    {
        "name": "tool_selection",
        "description": "Selects the appropriate tool or agent for a given subtask.",
    },
    {
        "name": "capability_matching",
        "description": "Matches task requirements to registered agent capabilities.",
    },
    # Add "llm_tool_selection" when LLM logic is implemented
    # Add more specific capabilities as needed
]

# Define Metadata for Discovery
AGENT_METADATA = {
    "version": AGENT_VERSION,
    "status": "ACTIVE",  # Standard status field
    "owner": "Alinari",
    "environment": os.getenv("ENVIRONMENT", "development"),
    "selection_strategy": "placeholder_keyword",  # Update when LLM logic added
    # Add other relevant metadata
}

ROUTER_URL = os.getenv("MCP_ROUTER_URL", "ws://127.0.0.1:8001")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(AGENT_ID)

# Global variable for the client instance to be accessed by signal handler
mcp_client_instance: MCPClient | None = None
# Global variable for the agent logic instance
tool_selector_logic_instance: ToolSelectorLogic | None = None


# Define the message handler callback BEFORE it's referenced
async def handle_incoming_message(client_ref: MCPClient, message: MCPMessage):
    global tool_selector_logic_instance
    # Use the global logic instance, ensuring it's initialized
    if tool_selector_logic_instance:
        message_type = (
            message.mcp_header.message_type
            if hasattr(message, "mcp_header")
            else message.get("mcp_header", {}).get("message_type")
        )
        payload = message.payload if hasattr(message, "payload") else message.get("payload", {})

        logger.debug(f"Received message: Type={message_type}, Payload={payload}")
        try:
            # ToolSelector might receive TASK_ASSIGN to select a tool/agent,
            # and potentially DISCOVERY_RESPONSE if it queries capabilities itself.
            # Delegate all processing to the logic class.
            response_payload = await tool_selector_logic_instance.process_message(message_type, payload)

            # If logic returns a response payload (e.g., TASK_COMPLETE/FAIL for the selection task)
            if response_payload:
                response_type = response_payload.get("status_type", "TASK_COMPLETE")
                correlation_id = payload.get("correlation_id")
                original_requester_id = payload.get("original_requester_id")

                if correlation_id and original_requester_id:
                    # Add necessary routing info back into the response payload
                    response_payload["correlation_id"] = correlation_id
                    response_payload["original_requester_id"] = original_requester_id
                    # Add task_id and workflow_id if relevant
                    response_payload["task_id"] = payload.get("task_id")
                    response_payload["workflow_id"] = payload.get("workflow_id")

                    await client_ref.send_message(
                        message_type=response_type,
                        payload=response_payload,
                        target_agent_id=original_requester_id,
                    )
                    logger.info(f"Sent {response_type} response for CorrID: {correlation_id}")
                else:
                    logger.warning(
                        f"Cannot send {response_type}: Missing correlation_id or original_requester_id in incoming message payload."
                    )

        except Exception as e:
            logger.error(f"Error processing message (Type: {message_type}): {e}", exc_info=True)
    else:
        logger.error("ToolSelectorLogic instance not available for message handling.")


async def main():
    """Initializes and runs the Tool Selector Agent."""
    global mcp_client_instance, tool_selector_logic_instance
    logger.info(f"Initializing {AGENT_TYPE} (ID: {AGENT_ID}, Version: {AGENT_VERSION})")

    # Initialize the MCPClient first, needed by logic if it performs discovery
    client = MCPClient(
        agent_id=AGENT_ID,
        router_url=ROUTER_URL,
        capabilities=AGENT_CAPABILITIES,  # Pass capabilities
        metadata=AGENT_METADATA,  # Pass metadata
        message_handler=handle_incoming_message,  # Pass the handler function
        loop=asyncio.get_event_loop(),
    )
    mcp_client_instance = client  # Store instance for signal handler

    # Initialize the agent's core logic, passing the client instance
    tool_selector_logic = ToolSelectorLogic(agent_id=AGENT_ID, mcp_client=client, logger=logger)
    tool_selector_logic_instance = tool_selector_logic  # Store instance

    # --- Graceful Shutdown Handling ---
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            logger.warning(f"Cannot add signal handler for {sig}. Use Ctrl+C manually.")

    # --- Connection and Run Loop ---
    try:
        await client.connect()  # Connects and automatically registers
        logger.info(f"{AGENT_ID} connected and registered. Waiting for tasks or shutdown signal...")
        await stop_event.wait()  # Keep running

    except MCPConnectionError as e:
        logger.critical(f"Initial connection failed: {e}. Agent cannot start.")
        return
    except Exception as e:
        logger.critical(f"An unexpected error occurred during agent runtime: {e}", exc_info=True)
    finally:
        logger.info(f"Shutting down {AGENT_ID}...")
        if client and client.is_connected:
            await client.disconnect()
        logger.info(f"{AGENT_ID} has shut down.")


if __name__ == "__main__":
    asyncio.run(main())
