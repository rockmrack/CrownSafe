# RossNetAgents/scripts/test_client_connection.py

import asyncio
import logging
import os
import sys
from typing import Any

# --- Adjust Python Path ---
# Add the parent directory (RossNetAgents) to the Python path
# This allows importing modules from core_infra, agents etc. when running the script directly.
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# --- Imports ---
# Now import from the client library
from core_infra.mcp_client_library.client import MCPClient  # noqa: E402

from core_infra.mcp_client_library.exceptions import ConnectionError, MCPClientError  # noqa: E402

# --- Configuration ---
# Configure basic logging for the script
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestClientScript")

# Define Agent ID for this test client
TEST_AGENT_ID = "test_agent_001"


# --- Message Handler ---
async def handle_incoming_message(message: dict[str, Any]):
    """
    Callback function to process messages received from the MCP Router.
    """
    message_type = message.get("mcp_header", {}).get("message_type", "UNKNOWN")
    sender = message.get("mcp_header", {}).get("sender_id", "UNKNOWN")
    payload = message.get("payload", {})
    logger.info(f"Received message of type '{message_type}' from '{sender}': {payload}")
    # Add specific logic here to handle different message types if needed for testing


# --- Main Test Function ---
async def run_test_client():
    """
    Instantiates the client, connects, waits, and disconnects.
    """
    logger.info(f"Instantiating MCPClient for agent: {TEST_AGENT_ID}")
    # Instantiate the client, passing our agent ID and message handler
    client = MCPClient(
        agent_id=TEST_AGENT_ID,
        message_handler=handle_incoming_message,
        # Optionally override settings here if needed, e.g., different router URL
        # settings_override=ClientSettings(MCP_ROUTER_WS_URL="ws://...")
    )

    try:
        logger.info("Attempting to connect client...")
        # Start the connection and listening loop (this runs until disconnect or error)
        # We run it in the background to allow the main script to do other things (like wait)
        connect_task = asyncio.create_task(client.connect())

        # Wait for the connection to establish (or fail)
        # Give it a bit more time than the connection timeout
        await asyncio.sleep(client.settings.CONNECTION_TIMEOUT_SECONDS + 2)

        if client.is_connected:
            logger.info("Client appears connected. Waiting for 15 seconds...")
            # Optional: Send a test message (e.g., register with discovery)
            try:
                logger.info("Attempting to send DISCOVERY_REGISTER message...")
                await client.send_discovery_register(
                    agent_type="TEST_CLIENT",
                    capabilities=[
                        {
                            "name": "test_capability",
                            "input_schema": {},
                            "output_schema": {},
                        }
                    ],
                )
                logger.info("DISCOVERY_REGISTER message sent.")
            except Exception as send_e:
                logger.error(f"Error sending register message: {send_e}")

            await asyncio.sleep(15)  # Keep connection open for a while
            logger.info("Wait finished.")
        else:
            logger.warning("Client did not connect successfully within the expected time.")
            # Check if the connect task raised an exception
            if connect_task.done() and connect_task.exception():
                logger.error(f"Connection task failed: {connect_task.exception()}")

    except ConnectionError as e:
        logger.error(f"Connection failed permanently: {e}")
    except MCPClientError as e:
        logger.error(f"MCP Client Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        logger.info("Attempting to disconnect client...")
        if client and client.is_connected:  # Check if client exists and is connected
            await client.disconnect()
        # Ensure the connection task is cancelled if it's still running
        if "connect_task" in locals() and not connect_task.done():
            connect_task.cancel()
            try:
                await connect_task  # Allow cancellation to propagate
            except asyncio.CancelledError:
                logger.info("Connection task cancelled.")
        logger.info("Client test finished.")


# --- Script Execution ---
if __name__ == "__main__":
    logger.info("Starting MCP Client Connection Test Script...")
    try:
        asyncio.run(run_test_client())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    logger.info("MCP Client Connection Test Script finished.")
