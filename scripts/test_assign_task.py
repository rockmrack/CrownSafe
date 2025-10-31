# RossNetAgents/scripts/test_assign_task.py

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, Optional

# --- Adjust Python Path ---
# Ensure the project root directory (RossNetAgents) is added to the Python path
# This allows importing modules like core_infra
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # RossNetAgents directory
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")  # Add print statement for verification
    # Verify core_infra exists
    core_infra_path = os.path.join(project_root, "core_infra")
    if not os.path.isdir(core_infra_path):
        print(f"ERROR: Cannot find core_infra directory at {core_infra_path}")
        sys.exit(1)
except Exception as e:
    print(f"Error adjusting sys.path: {e}")
    sys.exit(1)


# --- Imports (Now should work) ---
try:
    from core_infra.mcp_client_library.client import MCPClient

    from core_infra.mcp_client_library.exceptions import ConnectionError, MCPClientError
except ImportError as e:
    print(f"Failed to import MCPClient: {e}")
    print("Ensure you are running this script from the 'RossNetAgents' directory")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# Set higher level for noisy libraries if needed
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logger = logging.getLogger("TestTaskAssignScript")

CONTROLLER_AGENT_ID = "controller_agent_001"  # ID for this test script client
TARGET_AGENT_ID = "web_research_agent_01"  # The agent we want to send the task to
TASK_NAME = "perform_web_search"  # The capability name defined in the agent's CAPABILITIES
TASK_TIMEOUT_SECONDS = 30.0  # How long to wait for the task result

# --- Shared State for Response Handling ---
task_completion_event = asyncio.Event()
task_result: Optional[Dict[str, Any]] = None
task_correlation_id: Optional[str] = None  # Store the correlation ID of the sent task


# --- Message Handling for Controller ---
async def handle_controller_message(message: Dict[str, Any]):
    """
    Callback for the controller client to process responses.
    Looks for TASK_COMPLETE or TASK_FAIL related to our sent task
    by checking the correlation_id.
    """
    global task_result, task_completion_event, task_correlation_id
    header = message.get("mcp_header", {})
    payload = message.get("payload", {})
    message_type = header.get("message_type", "UNKNOWN")
    correlation_id = header.get("correlation_id")

    logger.debug(f"Controller received message type '{message_type}': {payload}")

    # Check if this message corresponds to the task we sent using correlation_id
    if correlation_id == task_correlation_id:
        if message_type in ["TASK_COMPLETE", "TASK_FAIL"]:
            logger.info(f"Received final task status: {message_type} for correlation_id: {correlation_id}")
            task_result = message  # Store the whole message
            task_completion_event.set()  # Signal that the task is done
        elif message_type == "TASK_ACKNOWLEDGE":
            logger.info(
                f"Received TASK_ACKNOWLEDGE for correlation_id: {correlation_id}, Status: {payload.get('status')}"
            )
        elif message_type == "STATUS_UPDATE":
            logger.info(
                f"Received STATUS_UPDATE for correlation_id: {correlation_id}, Description: {payload.get('status_description')}"  # noqa: E501
            )
        else:
            logger.debug(f"Received message type {message_type} with matching correlation ID, but not final status.")
    else:
        logger.debug(
            f"Received message with non-matching correlation ID: {correlation_id} (Expected: {task_correlation_id})"
        )


# --- Main Test Function ---
async def run_task_assignment():
    """
    Connects as a controller, sends a task, waits for completion or timeout.
    """
    global task_result, task_completion_event, task_correlation_id
    logger.info(f"Instantiating MCPClient for controller: {CONTROLLER_AGENT_ID}")

    client = MCPClient(agent_id=CONTROLLER_AGENT_ID, message_handler=handle_controller_message)

    subtask_id_to_send = str(uuid.uuid4())
    task_correlation_id = str(uuid.uuid4())

    try:
        logger.info("Controller connecting...")
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(2)  # Wait briefly for connection

        if not client.is_connected:
            logger.error("Controller failed to connect. Aborting.")
            connect_task.cancel()
            return

        logger.info("Controller connected.")

        task_input_data = {
            "query": "What is RossNet Architecture?",  # Changed query slightly
            "num_results": 3,
        }
        task_message = client._create_mcp_message(
            message_type="TASK_ASSIGN",
            recipient_id=TARGET_AGENT_ID,
            payload={
                "subtask_id": subtask_id_to_send,
                "task_name": TASK_NAME,
                "input_data": task_input_data,
            },
            correlation_id=task_correlation_id,
        )

        logger.info(
            f"Sending TASK_ASSIGN (Subtask ID: {subtask_id_to_send}, Corr ID: {task_correlation_id}) to {TARGET_AGENT_ID}..."  # noqa: E501
        )
        await client.send_message(task_message)
        logger.info("Task message sent.")

        logger.info(f"Waiting up to {TASK_TIMEOUT_SECONDS} seconds for task completion...")
        try:
            await asyncio.wait_for(task_completion_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
            logger.info("Task completion event received.")
            if task_result:
                logger.info(f"Final Task Result Message: {json.dumps(task_result, indent=2)}")
            else:
                logger.error("Completion event received, but no result was stored.")

        except asyncio.TimeoutError:
            logger.error(f"Timeout: Did not receive task completion message within {TASK_TIMEOUT_SECONDS} seconds.")

    except ConnectionError as e:
        logger.error(f"Connection error during task assignment test: {e}")
    except MCPClientError as e:
        logger.error(f"MCP Client Error during task assignment test: {e}")
    except Exception as e:
        logger.error(
            f"An unexpected error occurred in the task assignment test: {e}",
            exc_info=True,
        )
    finally:
        logger.info("Controller disconnecting...")
        if client and client.is_connected:
            await client.disconnect()
        if "connect_task" in locals() and not connect_task.done():
            connect_task.cancel()
            try:
                await connect_task
            except asyncio.CancelledError:
                logger.info("Controller connection task cancelled during cleanup.")
        logger.info("Task assignment test finished.")


# --- Script Execution ---
if __name__ == "__main__":
    logger.info("Starting MCP Task Assignment Test Script...")
    # Verify running from correct directory
    expected_dir_name = "RossNetAgents"
    current_working_dir = os.path.basename(os.getcwd())
    if current_working_dir != expected_dir_name:
        print(f"\nERROR: This script must be run from the '{expected_dir_name}' directory.")
        print(f"       Current directory: '{os.getcwd()}'")
        sys.exit(1)

    try:
        asyncio.run(run_task_assignment())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    except Exception as e:
        logger.critical(f"Script failed to run: {e}", exc_info=True)
    finally:
        logger.info("MCP Task Assignment Test Script finished.")
