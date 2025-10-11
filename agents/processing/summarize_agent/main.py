# C:\Users\rossd\Downloads\RossNetAgents\agents\processing\summarize_agent\main.py
# Step 108: Main script for SummarizeAgent (Stub)

import asyncio
import os
import signal
import logging
import sys
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure project root is in sys.path
project_root_main = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root_main not in sys.path:
    sys.path.insert(0, project_root_main)

try:
    from core_infra.mcp_client_library.client import MCPClient
    from core_infra.mcp_client_library.models import MCPMessage, MCPHeader
    from core_infra.mcp_client_library.config import Settings as MCPConfig
except ImportError as e:
    print(f"CRITICAL_ERROR_SUMMARIZE_MAIN: Failed to import core_infra: {e}")
    sys.exit(f"ImportError: {e}")

from .agent_logic import SummarizeAgentLogic  # Relative import

# Load .env from project root
dotenv_main_path = os.path.join(project_root_main, ".env")
if os.path.exists(dotenv_main_path):
    load_dotenv(dotenv_main_path)
elif os.path.exists(".env"):
    load_dotenv(".env")

AGENT_ID = "summarize_agent_01"  # Unique ID for this agent
AGENT_NAME = "SummarizeAgent"
AGENT_TYPE = "ProcessingAgent"  # Or a more specific type if we define one
AGENT_VERSION = "1.0.0"  # Stub version

LOG_LEVEL_MAIN = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL_MAIN, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_for_main = logging.getLogger(f"{AGENT_ID}.main")
logger_for_logic_passed = logging.getLogger(f"{AGENT_ID}.logic")

mcp_client_instance: Optional[MCPClient] = None
agent_logic_instance: Optional[SummarizeAgentLogic] = None


async def handle_incoming_message(message: MCPMessage):
    global agent_logic_instance, mcp_client_instance
    if not agent_logic_instance or not mcp_client_instance:
        logger_for_main.error("Logic or MCPClient instance missing in handler.")
        return

    logic_logger = agent_logic_instance.logger
    try:
        header: MCPHeader = message.mcp_header
        _ = message.payload  # payload_received (reserved for future validation)

        logic_logger.info(
            f"MAIN_HANDLER: Received Type='{header.message_type}', From='{header.sender_id}', CorrID='{header.correlation_id}'."
        )

        # The agent_logic.process_message expects the full MCPMessage as a dict
        message_as_dict_for_logic = message.model_dump()

        response_from_logic = await agent_logic_instance.process_message(
            message_data=message_as_dict_for_logic, client=mcp_client_instance
        )

        if response_from_logic and isinstance(response_from_logic, dict):
            response_message_type = response_from_logic.get("message_type")
            response_payload_to_send = response_from_logic.get("payload")

            if not response_message_type or not isinstance(response_payload_to_send, dict):
                logic_logger.error(f"Logic returned invalid response: {response_from_logic}")
                return

            # The response from logic should be sent back to the original sender of the TASK_ASSIGN,
            # which is the RouterAgent. The correlation_id should be the one from the
            # incoming TASK_ASSIGN message's header.
            target_for_reply = header.sender_id
            correlation_for_reply = header.correlation_id

            # Ensure agent_id of this summarizer is in the payload being sent out
            # The logic already does this if it constructs the payload correctly.
            # response_payload_to_send["agent_id"] = AGENT_ID # Logic should handle this

            logic_logger.info(
                f"MAIN_HANDLER: Sending {response_message_type} for CorrID='{correlation_for_reply}' back to '{target_for_reply}'."
            )

            await mcp_client_instance.send_message(
                payload=response_payload_to_send,
                message_type=response_message_type,
                target_agent_id=target_for_reply,
                correlation_id=correlation_for_reply,
            )
            logic_logger.info(
                f"MAIN_HANDLER: Sent {response_message_type} response for CorrID='{correlation_for_reply}' to '{target_for_reply}'."
            )

        elif response_from_logic is not None:
            logic_logger.warning(
                f"Logic processed {header.message_type} but returned non-dict/non-None: {type(response_from_logic)}"
            )

    except Exception as e:
        current_message_type_str = message.mcp_header.message_type if message and message.mcp_header else "UnknownType"
        logic_logger.error(
            f"MAIN_HANDLER: Error processing message (Type: {current_message_type_str}): {e}",
            exc_info=True,
        )
        # Send TASK_FAIL if it was a TASK_ASSIGN
        if current_message_type_str == "TASK_ASSIGN" and mcp_client_instance:
            try:
                fail_payload = {
                    "correlation_id": message.mcp_header.correlation_id,
                    "agent_id": AGENT_ID,
                    "error_message": f"SummarizeAgent failed: {str(e)}",
                    "workflow_id": message.payload.get("workflow_id"),  # Pass through if available
                    "task_id": message.payload.get("task_id"),  # Pass through if available
                }
                fail_payload = {k: v for k, v in fail_payload.items() if v is not None}
                logger_for_main.info(
                    f"MAIN_HANDLER: Sending TASK_FAIL for CorrID {message.mcp_header.correlation_id} to {message.mcp_header.sender_id}"
                )
                await mcp_client_instance.send_message(
                    payload=fail_payload,
                    message_type="TASK_FAIL",
                    target_agent_id=message.mcp_header.sender_id,
                    correlation_id=message.mcp_header.correlation_id,
                )
            except Exception as send_err:
                logger_for_main.error(f"MAIN_HANDLER: Failed to send TASK_FAIL notification: {send_err}")


async def main_agent_loop():
    global mcp_client_instance, agent_logic_instance
    logger_for_main.info(
        f"Initializing {AGENT_TYPE} '{AGENT_NAME}' (ID: {AGENT_ID}, Version: {AGENT_VERSION}) - Step 108"
    )

    try:
        agent_logic_instance = SummarizeAgentLogic(
            agent_id=AGENT_ID, version=AGENT_VERSION, logger=logger_for_logic_passed
        )
    except Exception as e:
        logger_for_main.critical(f"Failed to initialize SummarizeAgentLogic: {e}.", exc_info=True)
        return

    mcp_settings = MCPConfig()
    base_mcp_server_url = mcp_settings.DEFAULT_ROUTER_URL
    if "/ws/" in base_mcp_server_url:
        base_mcp_server_url = base_mcp_server_url.split("/ws/")[0]

    mcp_client_instance = MCPClient(
        agent_id=AGENT_ID,
        agent_name=AGENT_NAME,
        agent_type=AGENT_TYPE,
        mcp_server_url=base_mcp_server_url,
        capabilities=agent_logic_instance.get_capabilities(),
        message_handler=handle_incoming_message,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    active_signal_handlers = {}

    def signal_handler_func_wrapper(sig_name):
        if not stop_event.is_set():
            logger_for_main.info(f"Shutdown signal {sig_name} received.")
            stop_event.set()

    for sig_name_enum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(
                sig_name_enum,
                lambda s=sig_name_enum.name: signal_handler_func_wrapper(s),
            )
        except Exception as e:
            logger_for_main.warning(f"Cannot add signal handler for {sig_name_enum.name}: {e}.")

    try:
        await mcp_client_instance.connect()
        if mcp_client_instance.is_connected:
            await mcp_client_instance.register_self()
            logger_for_main.info(f"{AGENT_ID} connected and registered. Waiting for tasks... (Press Ctrl+C to stop)")
            await stop_event.wait()
        else:
            logger_for_main.critical("MCPClient connection failed.")
            return
    except Exception as e:
        logger_for_main.critical(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        logger_for_main.info(f"Shutting down {AGENT_ID}...")
        if mcp_client_instance and mcp_client_instance.is_connected:
            await mcp_client_instance.disconnect()
        for sig_name_enum in active_signal_handlers:
            try:
                loop.remove_signal_handler(sig_name_enum)
            except Exception:
                pass  # Ignore errors removing handlers
        logger_for_main.info(f"{AGENT_ID} has shut down.")


if __name__ == "__main__":
    asyncio.run(main_agent_loop())
    logger_for_main.info(f"{AGENT_ID} main execution finished.")
