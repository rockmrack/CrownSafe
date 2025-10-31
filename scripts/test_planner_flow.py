# C:\Users\rossd\Downloads\RossNetAgents\scripts\test_planner_flow.py

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any

# --- Adjust Python Path ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added {project_root} to sys.path")
    core_infra_path = os.path.join(project_root, "core_infra")
    if not os.path.isdir(core_infra_path):
        print(f"ERROR: Cannot find core_infra directory at {core_infra_path}")
        sys.exit(1)
except Exception as e:
    print(f"Error adjusting sys.path: {e}")
    sys.exit(1)

# --- Imports ---
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
logging.getLogger("websockets.client").setLevel(logging.WARNING)
logger = logging.getLogger("TestPlannerFlowScript")

CONTROLLER_AGENT_ID = "controller_agent_002"  # Use a different ID than the previous test
TARGET_AGENT_ID = "planner_agent_01"  # Target the PlannerAgent
TASK_NAME = "decompose_high_level_task"  # The capability name for the Planner
TASK_TIMEOUT_SECONDS = 45.0  # Increase timeout slightly for multi-step process

# --- Shared State for Response Handling ---
task_completion_event = asyncio.Event()
task_result: dict[str, Any] | None = None
task_correlation_id: str | None = None


# --- Message Handling for Controller ---
async def handle_controller_message(message: dict[str, Any]):
    """Callback for the controller client to process responses.
    Looks for TASK_COMPLETE or TASK_FAIL from the PlannerAgent.
    """
    global task_result, task_completion_event, task_correlation_id
    header = message.get("mcp_header", {})
    payload = message.get("payload", {})
    message_type = header.get("message_type", "UNKNOWN")
    correlation_id = header.get("correlation_id")

    logger.debug(f"Controller received message type '{message_type}': {payload}")

    # Check if this message corresponds to the planning task we sent
    if correlation_id == task_correlation_id:
        if message_type in ["TASK_COMPLETE", "TASK_FAIL"]:
            logger.info(f"Received final PLANNER task status: {message_type} for correlation_id: {correlation_id}")
            task_result = message  # Store the planner's result message
            task_completion_event.set()  # Signal that the planning task is done
        elif message_type == "TASK_ACKNOWLEDGE":
            logger.info(
                f"Received TASK_ACKNOWLEDGE for planning task (CorrID: {correlation_id}), Status: {payload.get('status')}",  # noqa: E501
            )
        else:
            logger.debug(f"Received other message type {message_type} with matching correlation ID.")
    else:
        # We might receive messages related to subtasks (like TASK_COMPLETE from WebResearchAgent)
        # routed back to the original sender (this controller). Log them for now.
        logger.debug(
            f"Received message with non-matching correlation ID: {correlation_id} (Expected: {task_correlation_id}) - Likely subtask result.",  # noqa: E501
        )
        logger.debug(f"Subtask Result Message: {json.dumps(message, indent=2)}")


# --- Main Test Function ---
async def run_planner_flow():
    """Connects as a controller, sends a high-level task to the Planner,
    waits for the Planner's completion (the plan itself).
    """
    global task_result, task_completion_event, task_correlation_id
    logger.info(f"Instantiating MCPClient for controller: {CONTROLLER_AGENT_ID}")

    client = MCPClient(agent_id=CONTROLLER_AGENT_ID, message_handler=handle_controller_message)

    subtask_id_to_send = str(uuid.uuid4())  # ID for the planning task itself
    task_correlation_id = str(uuid.uuid4())  # Correlation ID for the planning task

    try:
        logger.info("Controller connecting...")
        connect_task = asyncio.create_task(client.connect())
        await asyncio.sleep(2)

        if not client.is_connected:
            logger.error("Controller failed to connect. Aborting.")
            connect_task.cancel()
            return

        logger.info("Controller connected.")

        # Prepare TASK_ASSIGN message payload for the PlannerAgent
        planner_input_data = {
            "user_request": "Generate a report on the future of renewable energy.",
            "overall_goal": "Create a comprehensive report on renewable energy trends.",
        }
        task_message = client._create_mcp_message(
            message_type="TASK_ASSIGN",
            recipient_id=TARGET_AGENT_ID,  # Send to PlannerAgent
            payload={
                "subtask_id": subtask_id_to_send,
                "task_name": TASK_NAME,  # decompose_high_level_task
                "input_data": planner_input_data,
            },
            correlation_id=task_correlation_id,
        )

        logger.info(
            f"Sending TASK_ASSIGN (Subtask ID: {subtask_id_to_send}, Corr ID: {task_correlation_id}) to {TARGET_AGENT_ID}...",  # noqa: E501
        )
        await client.send_message(task_message)
        logger.info("Planning task message sent.")

        logger.info(f"Waiting up to {TASK_TIMEOUT_SECONDS} seconds for PLANNER task completion...")
        try:
            await asyncio.wait_for(task_completion_event.wait(), timeout=TASK_TIMEOUT_SECONDS)
            logger.info("Planner task completion event received.")
            if task_result:
                logger.info(f"Final PLANNER Task Result Message: {json.dumps(task_result, indent=2)}")
                # Check if the planner succeeded and returned subtasks
                if task_result.get("mcp_header", {}).get("message_type") == "TASK_COMPLETE":
                    logger.info("Planner successfully generated a plan.")
                    # In a real controller, we would now parse task_result['payload']['output_data']['subtasks']
                    # and likely send new TASK_ASSIGN messages for those subtasks via the RouterAgent.
                    # For this test, we just observe the logs of other agents.
                    logger.info("Observe Router and WebResearchAgent logs for subtask execution...")
                    await asyncio.sleep(10)  # Wait longer to see if subtask completes
                else:
                    logger.error("Planner task failed.")
            else:
                logger.error("Completion event received, but no result was stored for planner task.")

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout: Did not receive planner task completion message within {TASK_TIMEOUT_SECONDS} seconds.",
            )

    except ConnectionError as e:
        logger.error(f"Connection error during planner flow test: {e}")
    except MCPClientError as e:
        logger.error(f"MCP Client Error during planner flow test: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the planner flow test: {e}", exc_info=True)
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
        logger.info("Planner flow test finished.")


# --- Script Execution ---
if __name__ == "__main__":
    logger.info("Starting MCP Planner Flow Test Script...")
    expected_dir_name = "RossNetAgents"
    current_working_dir = os.path.basename(os.getcwd())
    if current_working_dir != expected_dir_name:
        print(f"\nERROR: This script must be run from the '{expected_dir_name}' directory.")
        print(f"       Current directory: '{os.getcwd()}'")
        sys.exit(1)

    try:
        asyncio.run(run_planner_flow())
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
    except Exception as e:
        logger.critical(f"Script failed to run: {e}", exc_info=True)
    finally:
        logger.info("MCP Planner Flow Test Script finished.")
