# C:\Users\rossd\Downloads\RossNetAgents\agents\research\web_research_agent\main.py
# Step: Critical-Fixes-WebResearch-Main-ResponseHandling
# Addresses: Response handling, logging cleanup, error management, proper integration

import asyncio
import logging
import os
import signal
import sys
from typing import Any

from dotenv import load_dotenv

# Ensure project root is in sys.path for core_infra imports
project_root_main = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root_main not in sys.path:
    sys.path.insert(0, project_root_main)

try:
    from core_infra.mcp_client_library.client import MCPClient
    from core_infra.mcp_client_library.models import MCPHeader, MCPMessage

    from core_infra.mcp_client_library.config import Settings as MCPConfig
    from core_infra.mcp_client_library.exceptions import MCPConnectionError
except ImportError as e:
    print(f"CRITICAL_ERROR_WEBRESEARCH_MAIN: Failed to import core_infra: {e}")
    sys.exit(1)

from .agent_logic import WebResearchLogic  # noqa: E402


# Environment setup
def setup_environment():
    """Setup environment variables with proper fallback"""
    dotenv_paths = [os.path.join(project_root_main, ".env"), ".env"]

    for dotenv_path in dotenv_paths:
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            return dotenv_path

    load_dotenv()  # Final fallback
    return "default locations"


env_source = setup_environment()

# Agent Configuration
AGENT_ID = "web_research_agent_01"
AGENT_NAME = "WebResearchAgent"
AGENT_TYPE = "ResearchAgent"
AGENT_VERSION = "1.3.0"  # Updated version for critical fixes

# Configuration from environment
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Logging setup
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger(f"{AGENT_ID}.main")
logic_logger = logging.getLogger(f"{AGENT_ID}.logic")

# Global instances
mcp_client_instance: MCPClient | None = None
agent_logic_instance: WebResearchLogic | None = None


class WebResearchAgentManager:
    """Main agent manager for WebResearchAgent"""

    def __init__(self) -> None:
        self.mcp_client: MCPClient | None = None
        self.web_research_logic: WebResearchLogic | None = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False

    async def handle_incoming_message(self, message: MCPMessage) -> None:
        """Handle incoming messages with proper response processing"""
        if not self.web_research_logic or not self.mcp_client:
            logger.error("Logic/MCPClient instance missing in WebResearchAgent handler")
            return

        try:
            # Extract message details
            header: MCPHeader = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            # Reduced logging to avoid duplication with logic
            logger.debug(f"Processing {message_type} from {sender_id} (CorrID: {correlation_id})")

            # Convert message to dict format expected by logic
            message_dict = message.model_dump()

            # Process through logic
            response_from_logic = await self.web_research_logic.process_message(message_dict, self.mcp_client)

            # Handle response if present
            if response_from_logic is not None:
                await self._handle_logic_response(response_from_logic, header)
            else:
                # None response is normal for messages that don't require responses
                logger.debug(f"No response needed for {message_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_message_error(message, e)

    async def _handle_logic_response(self, response: dict[str, Any], original_header: MCPHeader) -> None:
        """Handle response from logic with proper validation"""
        try:
            # Validate response structure
            if not isinstance(response, dict):
                logger.error(f"Logic returned non-dict response: {type(response)}")
                return

            response_message_type = response.get("message_type")
            response_payload = response.get("payload")

            # Validate required fields
            if not response_message_type:
                logger.error(f"Logic response missing message_type: {response}")
                return

            if not isinstance(response_payload, dict):
                logger.error(f"Logic response payload is not dict: {type(response_payload)}")
                return

            # Determine target and correlation ID
            target_agent_id = original_header.sender_id
            correlation_id = original_header.correlation_id

            if not target_agent_id:
                logger.error("Cannot send response: original sender_id is missing")
                return

            # Send response
            logger.info(f"Sending {response_message_type} response to {target_agent_id} (CorrID: {correlation_id})")

            await self.mcp_client.send_message(
                payload=response_payload,
                message_type=response_message_type,
                target_agent_id=target_agent_id,
                correlation_id=correlation_id,
            )

            logger.debug(f"Successfully sent {response_message_type} response")

        except Exception as e:
            logger.error(f"Error handling logic response: {e}", exc_info=True)

    async def _handle_message_error(self, message: MCPMessage, error: Exception) -> None:
        """Handle errors during message processing"""
        try:
            if not message or not message.mcp_header:
                logger.error("Cannot send error response: message/header missing")
                return

            header = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            # Only send TASK_FAIL for TASK_ASSIGN messages
            if message_type == "TASK_ASSIGN" and sender_id and self.mcp_client:
                # Extract workflow and task IDs if available
                workflow_id = None
                task_id = None
                if message.payload and isinstance(message.payload, dict):
                    workflow_id = message.payload.get("workflow_id")
                    task_id = message.payload.get("task_id")

                error_payload = {
                    "correlation_id": correlation_id,
                    "agent_id": AGENT_ID,
                    "error_message": f"WebResearchAgent failed to process {message_type}: {str(error)}",
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "status": "FAILED",
                }

                # Remove None values
                error_payload = {k: v for k, v in error_payload.items() if v is not None}

                await self.mcp_client.send_message(
                    payload=error_payload,
                    message_type="TASK_FAIL",
                    target_agent_id=sender_id,
                    correlation_id=correlation_id,
                )

                logger.info(f"Sent TASK_FAIL response for error in {message_type}")

        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}", exc_info=True)

    async def initialize_components(self) -> bool | None:
        """Initialize WebResearchLogic and MCPClient"""
        try:
            # Initialize WebResearchLogic
            self.web_research_logic = WebResearchLogic(
                agent_id=AGENT_ID, version=AGENT_VERSION, logger_instance=logic_logger,
            )

            # Get MCP server URL
            mcp_settings = MCPConfig()
            base_mcp_server_url = mcp_settings.DEFAULT_ROUTER_URL
            if "/ws/" in base_mcp_server_url:
                base_mcp_server_url = base_mcp_server_url.split("/ws/")[0]

            # Initialize MCPClient
            self.mcp_client = MCPClient(
                agent_id=AGENT_ID,
                agent_name=AGENT_NAME,
                agent_type=AGENT_TYPE,
                mcp_server_url=base_mcp_server_url,
                capabilities=self.web_research_logic.get_capabilities(),
                message_handler=self.handle_incoming_message,
            )

            logger.info(f"WebResearchAgent components initialized (Version: {AGENT_VERSION})")
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {base_mcp_server_url}")

            return True

        except Exception as e:
            logger.critical(f"Failed to initialize WebResearchAgent components: {e}", exc_info=True)
            return False

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_running_loop()

            def signal_handler(signum) -> None:
                signal_name = signal.Signals(signum).name
                logger.info(f"Received shutdown signal: {signal_name}")
                self.stop_event.set()

            for sig in [signal.SIGINT, signal.SIGTERM]:
                try:
                    loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
                    logger.debug(f"Added signal handler for {signal.Signals(sig).name}")
                except (NotImplementedError, OSError) as e:
                    logger.warning(f"Cannot add signal handler for {signal.Signals(sig).name}: {e}")

        except RuntimeError as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    async def connect_and_register(self) -> bool | None:
        """Connect to MCP server and register agent"""
        try:
            await self.mcp_client.connect()

            if not self.mcp_client.is_connected:
                logger.critical("Failed to connect to MCP server")
                return False

            await self.mcp_client.register_self()
            logger.info(f"{AGENT_ID} connected and registered successfully")
            return True

        except MCPConnectionError as e:
            logger.critical(f"MCP Connection Error: {e}")
            return False
        except Exception as e:
            logger.critical(f"Unexpected error during connection: {e}", exc_info=True)
            return False

    async def run_main_loop(self) -> None:
        """Main agent event loop"""
        logger.info(f"{AGENT_ID} entering main event loop...")

        try:
            # Wait for shutdown signal
            await self.stop_event.wait()
            logger.info("Shutdown signal received")

        except Exception as e:
            logger.error(f"Error in main event loop: {e}", exc_info=True)

    async def shutdown(self) -> None:
        """Graceful shutdown of all components"""
        if self.shutdown_complete:
            return

        logger.info(f"Shutting down {AGENT_ID}...")

        try:
            # Shutdown WebResearchLogic first
            if self.web_research_logic and hasattr(self.web_research_logic, "shutdown"):
                await self.web_research_logic.shutdown()
                logger.debug("WebResearchLogic shutdown complete")

            # Disconnect MCP client
            if self.mcp_client and self.mcp_client.is_connected:
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected")

            self.shutdown_complete = True
            logger.info(f"{AGENT_ID} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main() -> int | None:
    """Main entry point"""
    agent_manager = WebResearchAgentManager()

    # Update global instances for backward compatibility
    global mcp_client_instance, agent_logic_instance

    try:
        # Initialize components
        if not await agent_manager.initialize_components():
            logger.critical("Failed to initialize agent components")
            return 1

        # Update global references
        mcp_client_instance = agent_manager.mcp_client
        agent_logic_instance = agent_manager.web_research_logic

        # Setup signal handlers
        agent_manager.setup_signal_handlers()

        # Connect and register
        if not await agent_manager.connect_and_register():
            logger.critical("Failed to connect and register agent")
            return 1

        # Run main loop
        await agent_manager.run_main_loop()

        return 0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        return 1
    finally:
        await agent_manager.shutdown()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("WebResearchAgent interrupted")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
