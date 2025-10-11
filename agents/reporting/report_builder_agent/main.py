# C:\Users\rossd\Downloads\RossNetAgents\agents\reporting\report_builder_agent\main.py
# Version: 1.4.1 - Fixed response handling to match logic output format

import asyncio
import os
import signal
import sys
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Ensure project root is in sys.path for core_infra imports
project_root_main = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if project_root_main not in sys.path:
    sys.path.insert(0, project_root_main)

try:
    from core_infra.mcp_client_library.client import MCPClient
    from core_infra.mcp_client_library.models import MCPMessage, MCPHeader
    from core_infra.mcp_client_library.config import Settings as MCPConfig
    from core_infra.mcp_client_library.exceptions import MCPConnectionError
except ImportError as e:
    print(f"CRITICAL_ERROR_REPORTBUILDER_MAIN: Failed to import core_infra: {e}")
    sys.exit(1)

# Import agent logic with better error handling
try:
    from agents.reporting.report_builder_agent.agent_logic import (
        ReportBuilderAgentLogic,
    )
except ImportError:
    try:
        from .agent_logic import ReportBuilderAgentLogic
    except ImportError as e:
        print(f"CRITICAL_ERROR_REPORTBUILDER_MAIN: Failed to import agent_logic: {e}")
        sys.exit(1)


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
AGENT_ID = "report_builder_agent_01"
AGENT_NAME = "ReportBuilderAgent"
AGENT_TYPE = "ReportingAgent"
AGENT_VERSION = "1.4.1"  # Updated version for response handling fix

# Connection Configuration
MAX_CONNECT_RETRIES = int(os.getenv("REPORTBUILDER_MAX_RETRIES", "10"))
BASE_RETRY_DELAY = float(os.getenv("REPORTBUILDER_RETRY_DELAY", "2.0"))
MAX_RETRY_DELAY = float(os.getenv("REPORTBUILDER_MAX_RETRY_DELAY", "60.0"))
CONNECTION_HEALTH_CHECK_INTERVAL = int(os.getenv("REPORTBUILDER_HEALTH_CHECK", "30"))

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
mcp_client_instance: Optional[MCPClient] = None
agent_logic_instance: Optional[ReportBuilderAgentLogic] = None


class ReportBuilderAgentManager:
    """Main agent manager for ReportBuilderAgent with enhanced connection stability"""

    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.report_builder_logic: Optional[ReportBuilderAgentLogic] = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False
        self.connection_retry_count = 0
        self.last_successful_connection = None
        self._health_check_task: Optional[asyncio.Task] = None

    async def handle_incoming_message(self, message: MCPMessage):
        """Handle incoming messages with proper response processing"""
        if not self.report_builder_logic or not self.mcp_client:
            logger.error("Logic/MCPClient instance missing in ReportBuilderAgent handler")
            return

        try:
            # Extract message details
            header: MCPHeader = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            # Log TASK_ASSIGN reception immediately for debugging
            if message_type == "TASK_ASSIGN":
                logger.critical(
                    f"🎯 TASK_ASSIGN RECEIVED: From {sender_id}, CorrID: {correlation_id}"
                )
                logger.critical(f"🎯 TASK_PAYLOAD: {message.payload}")

            logger.debug(f"Processing {message_type} from {sender_id} (CorrID: {correlation_id})")

            # Convert message to dict format expected by logic
            message_dict = message.model_dump()

            # Process through logic
            response_from_logic = await self.report_builder_logic.process_message(
                message_dict, self.mcp_client
            )

            # Handle response if present
            if response_from_logic is not None:
                await self._handle_logic_response(response_from_logic, header)
            else:
                logger.debug(f"No response needed for {message_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_message_error(message, e)

    async def _handle_logic_response(self, response: Dict[str, Any], original_header: MCPHeader):
        """Handle response from logic with proper validation - FIXED VERSION"""
        try:
            # The response from logic is a flat structure with message_type and payload at top level
            if not isinstance(response, dict):
                logger.error(f"Logic returned non-dict response: {type(response)}")
                return

            # Extract message_type and payload directly from response (not from mcp_header)
            response_message_type = response.get("message_type")
            response_payload = response.get("payload", {})

            if not response_message_type:
                logger.error(f"Logic response missing message_type: {response}")
                return

            if not isinstance(response_payload, dict):
                logger.error(f"Logic response payload is not dict: {type(response_payload)}")
                return

            # Use the original sender as target
            target_agent_id = original_header.sender_id
            # Use the original correlation ID
            correlation_id = original_header.correlation_id

            if not target_agent_id:
                logger.error("Cannot send response: original sender_id is missing")
                return

            logger.info(
                f"Sending {response_message_type} response to {target_agent_id} (CorrID: {correlation_id})"
            )

            await self.mcp_client.send_message(
                payload=response_payload,
                message_type=response_message_type,
                target_agent_id=target_agent_id,
                correlation_id=correlation_id,
            )

            logger.debug(f"Successfully sent {response_message_type} response")

        except Exception as e:
            logger.error(f"Error handling logic response: {e}", exc_info=True)

    async def _handle_message_error(self, message: MCPMessage, error: Exception):
        """Handle errors during message processing"""
        try:
            if not message or not message.mcp_header:
                logger.error("Cannot send error response: message/header missing")
                return

            header = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            if message_type == "TASK_ASSIGN" and sender_id and self.mcp_client:
                workflow_id = None
                task_id = None
                if message.payload and isinstance(message.payload, dict):
                    workflow_id = message.payload.get("workflow_id")
                    task_id = message.payload.get("task_id")

                error_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": AGENT_ID,
                    "error_message": f"ReportBuilderAgent failed to process {message_type}: {str(error)}",
                }

                await self.mcp_client.send_message(
                    payload=error_payload,
                    message_type="TASK_FAIL",
                    target_agent_id=sender_id,
                    correlation_id=correlation_id,
                )

                logger.info(f"Sent TASK_FAIL response for error in {message_type}")

        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}", exc_info=True)

    async def connect_with_retry(self) -> bool:
        """Connect to MCP server with exponential backoff retry logic"""
        logger.info(f"Starting connection attempt for {AGENT_ID}")

        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                logger.info(f"🔄 Connection attempt {attempt}/{MAX_CONNECT_RETRIES} for {AGENT_ID}")

                # Clear any existing connection state
                if self.mcp_client and hasattr(self.mcp_client, "_is_connected"):
                    self.mcp_client._is_connected = False

                # Attempt connection
                await self.mcp_client.connect()

                if not self.mcp_client.is_connected:
                    raise MCPConnectionError("Connection established but is_connected is False")

                # Register with discovery service
                await self.mcp_client.register_self()

                # Verify connection is still active after registration
                if not self.mcp_client.is_connected:
                    raise MCPConnectionError("Connection lost during registration")

                # Success!
                self.connection_retry_count = 0
                self.last_successful_connection = asyncio.get_event_loop().time()
                logger.info(
                    f"✅ {AGENT_ID} connected and registered successfully on attempt {attempt}"
                )

                # Start health monitoring
                await self._start_health_monitoring()

                return True

            except Exception as e:
                self.connection_retry_count = attempt
                logger.warning(f"❌ Connection attempt {attempt}/{MAX_CONNECT_RETRIES} failed: {e}")

                if attempt < MAX_CONNECT_RETRIES:
                    # Calculate exponential backoff delay
                    delay = min(BASE_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                    logger.info(f"⏳ Retrying in {delay:.1f} seconds...")

                    try:
                        await asyncio.wait_for(self.stop_event.wait(), timeout=delay)
                        # If stop_event is set during delay, abort retry attempts
                        if self.stop_event.is_set():
                            logger.info(
                                "Stop event set during retry delay, aborting connection attempts"
                            )
                            return False
                    except asyncio.TimeoutError:
                        pass  # Normal timeout, continue to next attempt
                else:
                    logger.critical(
                        f"💥 All {MAX_CONNECT_RETRIES} connection attempts failed for {AGENT_ID}"
                    )

        return False

    async def _start_health_monitoring(self):
        """Start periodic health check to monitor connection stability"""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()

        self._health_check_task = asyncio.create_task(self._connection_health_monitor())
        logger.debug(f"Started connection health monitoring for {AGENT_ID}")

    async def _connection_health_monitor(self):
        """Monitor connection health and attempt reconnection if needed"""
        logger.debug(f"Connection health monitor started for {AGENT_ID}")

        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(CONNECTION_HEALTH_CHECK_INTERVAL)

                if self.stop_event.is_set():
                    break

                # Check connection status
                if not self.mcp_client or not self.mcp_client.is_connected:
                    logger.warning(
                        f"🚨 Connection health check failed for {AGENT_ID} - attempting reconnection"
                    )

                    if await self.connect_with_retry():
                        logger.info(f"✅ Reconnection successful for {AGENT_ID}")
                    else:
                        logger.error(f"💥 Reconnection failed for {AGENT_ID}")
                        self.stop_event.set()  # Trigger shutdown
                        break
                else:
                    logger.debug(f"✅ Connection health check passed for {AGENT_ID}")

            except asyncio.CancelledError:
                logger.debug(f"Health monitor cancelled for {AGENT_ID}")
                break
            except Exception as e:
                logger.error(f"Error in connection health monitor: {e}", exc_info=True)

    async def initialize_components(self):
        """Initialize ReportBuilderAgentLogic and MCPClient"""
        try:
            # Initialize ReportBuilderAgentLogic
            self.report_builder_logic = ReportBuilderAgentLogic(
                agent_id=AGENT_ID, version=AGENT_VERSION, logger_instance=logic_logger
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
                capabilities=self.report_builder_logic.get_capabilities(),
                message_handler=self.handle_incoming_message,
            )

            logger.info(f"ReportBuilderAgent components initialized (Version: {AGENT_VERSION})")
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {base_mcp_server_url}")
            logger.info(
                f"Connection config: Max retries={MAX_CONNECT_RETRIES}, Base delay={BASE_RETRY_DELAY}s, Health check={CONNECTION_HEALTH_CHECK_INTERVAL}s"
            )

            return True

        except Exception as e:
            logger.critical(
                f"Failed to initialize ReportBuilderAgent components: {e}",
                exc_info=True,
            )
            return False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_running_loop()

            def signal_handler(signum):
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

    async def connect_and_register(self):
        """Connect to MCP server and register agent with retry logic"""
        return await self.connect_with_retry()

    async def run_main_loop(self):
        """Main agent event loop with enhanced monitoring"""
        logger.info(f"{AGENT_ID} entering main event loop...")

        try:
            # Log initial connection status
            if self.mcp_client and self.mcp_client.is_connected:
                logger.info(f"✅ {AGENT_ID} main loop starting with active connection")
            else:
                logger.warning(f"⚠️ {AGENT_ID} main loop starting without active connection")

            # Wait for shutdown signal
            await self.stop_event.wait()
            logger.info("Shutdown signal received in main loop")

        except Exception as e:
            logger.error(f"Error in main event loop: {e}", exc_info=True)

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.shutdown_complete:
            logger.debug(f"{AGENT_ID} shutdown already in progress or complete")
            return

        logger.info(f"Shutting down {AGENT_ID}...")
        self.shutdown_complete = True

        try:
            # Cancel health monitoring first
            if self._health_check_task and not self._health_check_task.done():
                logger.debug("Cancelling health check task...")
                self._health_check_task.cancel()
                try:
                    await asyncio.wait_for(self._health_check_task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                logger.debug("Health check task cancelled")

            # Shutdown ReportBuilderAgentLogic
            if self.report_builder_logic and hasattr(self.report_builder_logic, "shutdown"):
                logger.debug("Shutting down ReportBuilderAgentLogic...")
                await self.report_builder_logic.shutdown()
                logger.debug("ReportBuilderAgentLogic shutdown complete")

            # Disconnect MCP client
            if self.mcp_client and self.mcp_client.is_connected:
                logger.debug("Disconnecting MCP client...")
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected")

            logger.info(f"✅ {AGENT_ID} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main entry point with enhanced startup sequencing"""
    logger.info(f"🚀 Starting {AGENT_NAME} (ID: {AGENT_ID}, Version: {AGENT_VERSION})")

    agent_manager = ReportBuilderAgentManager()

    # Update global instances for backward compatibility
    global mcp_client_instance, agent_logic_instance

    try:
        # Initialize components
        logger.info("Initializing agent components...")
        if not await agent_manager.initialize_components():
            logger.critical("❌ Failed to initialize agent components")
            return 1

        # Update global references
        mcp_client_instance = agent_manager.mcp_client
        agent_logic_instance = agent_manager.report_builder_logic

        # Setup signal handlers
        agent_manager.setup_signal_handlers()

        # Enhanced startup delay to ensure MCP Router is ready
        startup_delay = float(os.getenv("REPORTBUILDER_STARTUP_DELAY", "5.0"))
        if startup_delay > 0:
            logger.info(f"⏳ Waiting {startup_delay}s for MCP Router to stabilize...")
            await asyncio.sleep(startup_delay)

        # Connect and register with retry logic
        logger.info("Attempting connection to MCP Router...")
        if not await agent_manager.connect_and_register():
            logger.critical("❌ Failed to connect and register agent after all retries")
            return 1

        logger.info(f"✅ {AGENT_ID} successfully connected and ready for tasks")

        # Run main loop
        await agent_manager.run_main_loop()

        return 0

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        agent_manager.stop_event.set()
        return 0
    except Exception as e:
        logger.critical(f"💥 Unexpected error in main: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Performing final shutdown...")
        await agent_manager.shutdown()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        logger.info(f"🏁 {AGENT_NAME} exiting with code {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info(f"🛑 {AGENT_NAME} interrupted")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}", exc_info=True)
        sys.exit(1)
