# C:\Users\rossd\Downloads\RossNetAgents\scripts\test_commander_flow.py
# Enhanced version with workflow monitoring and completion tracking (no emojis)

import asyncio
import json
import logging
import os

# Adjust path to import client library correctly from script location
import sys
import uuid
from datetime import datetime, timedelta

from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core_infra.mcp_client_library.client import MCPClient  # noqa: E402
from core_infra.mcp_client_library.models import MCPMessage  # noqa: E402

from core_infra.mcp_client_library.exceptions import MCPConnectionError  # noqa: E402

# --- Configuration ---
dotenv_path = os.path.join(project_root, ".env")

CONTROLLER_AGENT_ID = f"controller_agent_sub_{str(uuid.uuid4())[:8]}"
CONTROLLER_AGENT_NAME = "TestFlowController"
CONTROLLER_AGENT_TYPE = "ControllerAgent"
TARGET_COMMANDER_ID = "commander_agent_01"
MCP_SERVER_URL_ENV = os.getenv("MCP_SERVER_URL", "ws://127.0.0.1:8001")

# Research goal (ONLY THIS LINE IS CHANGED)
USER_RESEARCH_GOAL_STRING = os.getenv(
    "TEST_RESEARCH_GOAL",
    "Assess Sotagliflozin for patients with Type 2 Diabetes and Chronic Kidney Disease, specifically its effects on glycemic control, progression of kidney disease, major adverse cardiovascular events (MACE), and its overall safety profile based on pivotal clinical trial data.",  # noqa: E501
)
USER_REQUEST_PAYLOAD = {"goal": USER_RESEARCH_GOAL_STRING}

LOG_LEVEL_SCRIPT = os.getenv("LOG_LEVEL_SCRIPT", os.getenv("LOG_LEVEL", "INFO")).upper()
MAX_WAIT_TIME_SECONDS = int(os.getenv("TEST_FLOW_MAX_WAIT_SECONDS", "600"))  # 10 minutes
CHECK_INTERVAL_SECONDS = 10  # Check status every 10 seconds

# --- Logging Setup ---
log_format = f"%(asctime)s - {CONTROLLER_AGENT_ID} (%(name)s) - %(levelname)s - %(message)s"
logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL_SCRIPT, format=log_format, force=True)
logger = logging.getLogger(CONTROLLER_AGENT_NAME)

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    logger.info(f"Loaded .env from {dotenv_path}")
else:
    logger.warning(f".env file not found at {dotenv_path}. Using environment variables if set.")


# --- Workflow Monitor ---
class WorkflowMonitor:
    def __init__(self):
        self.workflow_complete = False
        self.workflow_failed = False
        self.error_message = None
        self.pdf_path = None
        self.task_updates = []

    async def handle_message(self, message: MCPMessage):
        """Process messages to track workflow status"""
        msg_type = message.mcp_header.message_type
        sender = message.mcp_header.sender_id
        corr_id = message.mcp_header.correlation_id

        logger.info(f"Received {msg_type} from {sender} (CorrID: {corr_id})")

        if msg_type == "TASK_COMPLETE":
            payload = message.payload
            # Check if this is the final completion from RouterAgent
            if sender and "router" in sender.lower():
                status = payload.get("status", "")
                if status == "COMPLETED":
                    self.workflow_complete = True
                    # Try to extract PDF path from task summary
                    task_summary = payload.get("task_summary", {})
                    report_result = task_summary.get("step3_compile_report", {}).get("result", {})
                    self.pdf_path = report_result.get("pdf_file_path")
                    logger.info(f"Workflow COMPLETED! PDF Path: {self.pdf_path}")
                elif status == "FAILED":
                    self.workflow_failed = True
                    self.error_message = payload.get("message", "Unknown error")
                    logger.error(f"Workflow FAILED: {self.error_message}")

        elif msg_type == "TASK_FAIL":
            self.task_updates.append(
                {
                    "time": datetime.now().isoformat(),
                    "sender": sender,
                    "type": "FAIL",
                    "error": message.payload.get("error_message", "Unknown error"),
                },
            )
            logger.error(f"Task failed from {sender}: {message.payload.get('error_message')}")

        elif msg_type == "PONG":
            logger.debug(f"PONG from {sender}")
        else:
            # Log other message types for debugging
            logger.debug(f"Message type {msg_type} from {sender}: {json.dumps(message.payload, indent=2)[:200]}...")


async def run_test():
    logger.info("Starting Enhanced MCP Commander Flow Test Script...")
    logger.info(f"Goal: {USER_RESEARCH_GOAL_STRING}")

    client: MCPClient | None = None
    monitor = WorkflowMonitor()

    controller_capabilities = [
        {
            "name": "test_controller_initiate_request",
            "description": "Sends initial user requests for testing workflows.",
        },
    ]

    try:
        # Create client with proper message handler
        client = MCPClient(
            agent_id=CONTROLLER_AGENT_ID,
            agent_name=CONTROLLER_AGENT_NAME,
            agent_type=CONTROLLER_AGENT_TYPE,
            mcp_server_url=MCP_SERVER_URL_ENV,
            capabilities=controller_capabilities,
            message_handler=monitor.handle_message,  # Use monitor instead of dummy handler
        )
        logger.info(f"Controller client initialized. Agent ID: {client.agent_id}")

        await client.connect()
        logger.info(f"Controller client connected to MCP Router at {MCP_SERVER_URL_ENV}.")

        await asyncio.sleep(2)  # Give connection time to stabilize

        # Send the research request
        logger.info(f"Sending PROCESS_USER_REQUEST to '{TARGET_COMMANDER_ID}'...")

        await client.send_message(
            message_type="PROCESS_USER_REQUEST",
            payload=USER_REQUEST_PAYLOAD,
            target_agent_id=TARGET_COMMANDER_ID,
        )
        logger.info("PROCESS_USER_REQUEST sent successfully.")

        # Monitor workflow progress
        start_time = datetime.now()
        timeout_time = start_time + timedelta(seconds=MAX_WAIT_TIME_SECONDS)

        logger.info(f"Monitoring workflow progress (timeout: {MAX_WAIT_TIME_SECONDS}s)...")

        while datetime.now() < timeout_time:
            # Check if workflow completed or failed
            if monitor.workflow_complete:
                logger.info("Workflow completed successfully!")
                if monitor.pdf_path:
                    logger.info(f"PDF Report generated at: {monitor.pdf_path}")
                    # Verify file exists
                    if os.path.exists(monitor.pdf_path):
                        file_size = os.path.getsize(monitor.pdf_path)
                        logger.info(f"PDF file verified: {file_size:,} bytes")
                    else:
                        logger.warning(f"PDF file not found at reported path: {monitor.pdf_path}")
                break

            if monitor.workflow_failed:
                logger.error(f"Workflow failed: {monitor.error_message}")
                break

            # Show progress
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Workflow in progress... ({elapsed:.0f}s elapsed)")

            # Keep connection alive
            if hasattr(client, "is_connected") and callable(getattr(client, "is_connected")):
                is_connected = client.is_connected()
            else:
                is_connected = getattr(client, "is_connected", True)

            if not is_connected:
                logger.warning("Client disconnected! Attempting to reconnect...")
                await client.connect()

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        # Check timeout
        if not monitor.workflow_complete and not monitor.workflow_failed:
            logger.error(f"Workflow timed out after {MAX_WAIT_TIME_SECONDS} seconds")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("WORKFLOW SUMMARY:")
        logger.info(
            f"Status: {'COMPLETED' if monitor.workflow_complete else 'FAILED' if monitor.workflow_failed else 'TIMEOUT'}",  # noqa: E501
        )
        logger.info(f"Duration: {(datetime.now() - start_time).total_seconds():.1f} seconds")
        logger.info(f"Task Updates: {len(monitor.task_updates)}")
        if monitor.pdf_path:
            logger.info(f"PDF Report: {monitor.pdf_path}")
        if monitor.error_message:
            logger.info(f"Error: {monitor.error_message}")
        logger.info("=" * 60 + "\n")

    except MCPConnectionError as e:
        logger.exception(f"MCP Connection Error: {e}")
    except Exception as e:
        logger.error(f"Test script failed with an unexpected error: {e}", exc_info=True)
    finally:
        if client:
            try:
                # Safe disconnect
                if hasattr(client, "is_connected"):
                    if callable(getattr(client, "is_connected")):
                        is_connected = client.is_connected()
                    else:
                        is_connected = getattr(client, "is_connected", True)

                    if is_connected:
                        logger.info("Disconnecting controller client...")
                        await client.disconnect()
                        logger.info("Controller client disconnected.")
                else:
                    logger.info("Client connection status unknown, attempting disconnect...")
                    await client.disconnect()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

        logger.info("Test script finished.")


if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        logger.info("Test script interrupted by user.")
    except SystemExit:
        pass
    except Exception as e_main:
        logger.critical(
            f"Fatal error in test_commander_flow.py main execution: {e_main}",
            exc_info=True,
        )
