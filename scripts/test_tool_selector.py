# C:\Users\rossd\Downloads\RossNetAgents\scripts\test_tool_selector.py

import asyncio
import logging
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional

# --- Adjust Python Path ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")
    core_infra_path = os.path.join(project_root, 'core_infra')
    if not os.path.isdir(core_infra_path):
         print(f"ERROR: Cannot find core_infra directory at {core_infra_path}")
         sys.exit(1)
except Exception as e:
    print(f"Error adjusting sys.path: {e}")
    sys.exit(1)

# --- Imports ---
try:
    from core_infra.mcp_client_library.client import MCPClient
    from core_infra.mcp_client_library.exceptions import MCPClientError, ConnectionError
except ImportError as e:
     print(f"Failed to import MCPClient: {e}")
     print("Ensure you are running this script from the 'RossNetAgents' directory")
     print(f"Current sys.path: {sys.path}")
     sys.exit(1)

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logger = logging.getLogger("TestToolSelectorScript")

CONTROLLER_AGENT_ID = "controller_agent_004" # New ID for this test
TARGET_AGENT_ID = "tool_selector_agent_01"   # Target the ToolSelectorAgent
TASK_NAME = "select_and_run_tool"            # The capability name for the ToolSelector
TASK_TIMEOUT_SECONDS = 30.0                  # Timeout for waiting for ToolSelector's response

# --- Shared State for Response Handling ---
task_completion_event = asyncio.Event()
task_result: Optional[Dict[str, Any]] = None
task_correlation_id: Optional[str] = None

# --- Message Handling for Controller ---
async def handle_controller_message(message: Dict[str, Any]):
    """
    Callback for the controller client. Looks for the response
    from the ToolSelectorAgent for the task we sent.
    """
    global task_result, task_completion_event, task_correlation_id
    header = message.get("mcp_header", {})
    payload = message.get("payload", {})
    message_type = header.get("message_type", "UNKNOWN")
    correlation_id = header.get("correlation_id")

    logger.debug(f"Controller received message type '{message_type}': {payload}")

    # Check if this message corresponds to the tool selection task we sent
    if correlation_id == task_correlation_id:
        if message_type in ["TASK_COMPLETE", "TASK_FAIL"]:
            logger.info(f"Received final TOOL_SELECTOR task status: {message_type} for correlation_id: {correlation_id}")
            task_result = message # Store the tool selector's result message
            task_completion_event.set() # Signal that the tool selection task is done/failed
        elif message_type == "TASK_ACKNOWLEDGE":
             logger.info(f"Received TASK_ACKNOWLEDGE for tool selection task (CorrID: {correlation_id}), Status: {payload.get('status')}")
        else:
            logger.debug(f"Received other message type {message_type} with matching correlation ID.")
    else:
        logger.debug(f"Received message with non-matching correlation ID: {correlation_id} (Expected: {task_correlation_id})")


# --- Main Test Function ---
async def run_tool_selection():
    """
    Connects as a controller, sends a request to the ToolSelector,
    waits for its completion response (indicating delegation occurred).
    """
    global task_result, task_completion_event, task_correlation_id
    logger.info(f"Instantiating MCPClient for controller: {CONTROLLER_AGENT_ID}")

    client = MCPClient(
        agent_id=CONTROLLER_AGENT_ID,
        message_handler=handle_controller_message
    )

    subtask_id_to_send = str(uuid.uuid4()) # ID for the tool selection task itself
    task_correlation_id = str(uuid.uuid4()) # Correlation ID for this request

    try:
        logger.info("Controller connecting...")
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(2)

        if not client.is_connected:
            logger.error("Controller failed to connect. Aborting.")
            connect_task.cancel()
            return

        logger.info("Controller connected.")

        # Prepare TASK_ASSIGN message payload for the ToolSelectorAgent
        tool_selector_input_data = {
            "action_description": "Find recent news about AI agents",
            "input_data": { # This is the data for the *target* tool (WebSearchAgent)
                "query": "Recent news AI agents",
                "num_results": 4
            }
            # "required_capability": "web_search", # Optional hint
            # "constraints": {"priority": "medium"} # Optional constraints
        }
        task_message = client._create_mcp_message(
            message_type="TASK_ASSIGN",
            recipient_id=TARGET_AGENT_ID, # Send to ToolSelectorAgent
            payload={
                "subtask_id": subtask_id_to_send,
                "task_name": TASK_NAME, # select_and_run_tool
                "input_data": tool_selector_input_data
            },
            correlation_id=task_correlation_id
        )

        logger.info(f"Sending TASK_ASSIGN (Subtask ID: {subtask_id_to_send}, Corr ID: {task_correlation_id}) to {TARGET_AGENT_ID}...")
        await client.send_message(task_message)
        logger.info("Tool selection request message sent.")

        logger.info(f"Waiting up to {TASK_TIMEOUT_SECONDS} seconds for TOOL_SELECTOR task completion...")
        try:
            await asyncio.wait_for(task_completion_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
            logger.info("ToolSelector task completion event received.")
            if task_result:
                logger.info(f"Final TOOL_SELECTOR Task Result Message: {json.dumps(task_result, indent=2)}")
                if task_result.get("mcp_header", {}).get("message_type") == "TASK_COMPLETE":
                     output_data = task_result.get("payload", {}).get("output_data", {})
                     if output_data.get("status") == "DELEGATED":
                          logger.info(f"ToolSelector successfully delegated task to: {output_data.get('tool_used')}")
                          logger.info("Observe RouterAgent and WebResearchAgent logs for subtask execution...")
                          await asyncio.sleep(10) # Wait to observe subtask execution
                     else:
                          logger.warning(f"ToolSelector completed but did not delegate successfully: Status={output_data.get('status')}")
                else:
                     logger.error("ToolSelector task failed.")
            else:
                logger.error("Completion event received, but no result was stored for tool selector task.")

        except asyncio.TimeoutError:
            logger.error(f"Timeout: Did not receive tool selector task completion message within {TASK_TIMEOUT_SECONDS} seconds.")

    except ConnectionError as e:
        logger.error(f"Connection error during tool selector test: {e}")
    except MCPClientError as e:
        logger.error(f"MCP Client Error during tool selector test: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the tool selector test: {e}", exc_info=True)
    finally:
        logger.info("Controller disconnecting...")
        if client and client.is_connected:
            await client.disconnect()
        if 'connect_task' in locals() and not connect_task.done():
             connect_task.cancel()
             try:
                 await connect_task
             except asyncio.CancelledError:
                 logger.info("Controller connection task cancelled during cleanup.")
        logger.info("Tool selector test finished.")


# --- Script Execution ---
if __name__ == "__main__":
    logger.info("Starting MCP Tool Selector Test Script...")
    expected_dir_name = "RossNetAgents"
    current_working_dir = os.path.basename(os.getcwd())
    if current_working_dir != expected_dir_name:
         print(f"\nERROR: This script must be run from the '{expected_dir_name}' directory.")
         print(f"       Current directory: '{os.getcwd()}'")
         sys.exit(1)

    try:
        asyncio.run(run_tool_selection())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    except Exception as e:
         logger.critical(f"Script failed to run: {e}", exc_info=True)
    finally:
         logger.info("MCP Tool Selector Test Script finished.")