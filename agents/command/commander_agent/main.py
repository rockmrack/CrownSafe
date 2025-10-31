# C:\Users\rossd\Downloads\RossNetAgents\agents\command\commander_agent\main.py
# Step: Critical-Fixes-Commander-Main-Logic-Integration
# Addresses: Response handling, logging configuration, proper shutdown, error handling

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from dotenv import load_dotenv

from core_infra.mcp_client_library.exceptions import MCPConnectionError

# Import agent logic
from .agent_logic import CommanderLogic

# Agent Configuration
AGENT_ID = "commander_agent_01"
AGENT_NAME = "CommanderAgent"
AGENT_TYPE = "CommanderAgent"
AGENT_VERSION = "1.1.1"  # Updated version

AGENT_CAPABILITIES = [
    {
        "name": "user_request_handling",
        "description": "Receives initial user requests and initiates workflows",
    },
    {
        "name": "workflow_initiation",
        "description": "Starts the planning and execution process",
    },
    {
        "name": "plan_delegation",
        "description": "Delegates plan generation to a planning agent",
    },
    {
        "name": "execution_delegation",
        "description": "Delegates plan execution to a routing agent",
    },
    {
        "name": "final_result_reception",
        "description": "Receives the final status/result of a completed workflow",
    },
    {
        "name": "workflow_orchestration",
        "description": "Orchestrates multi-agent workflows from start to finish",
    },
]


# Environment setup
def setup_environment():
    """Setup environment variables with proper fallback."""
    try:
        # Try project root first
        project_root = Path(__file__).resolve().parents[3]
        dotenv_path = project_root / ".env"

        if dotenv_path.exists():
            load_dotenv(dotenv_path)
            return str(dotenv_path)
        # Fallback to current directory or standard locations
        load_dotenv()
        return "default locations"
    except Exception as e:
        load_dotenv()  # Final fallback
        return f"fallback due to error: {e}"


# Setup environment
env_source = setup_environment()

# Configuration from environment
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://127.0.0.1:8001")
LOG_LEVEL = os.getenv("PYTHON_LOGLEVEL", "INFO").upper()


# Logging setup - avoid duplicate handlers
def setup_logging() -> None:
    """Setup logging configuration to avoid duplication."""
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Force reconfiguration
    )

    # Prevent duplicate handlers
    logger = logging.getLogger()
    if len(logger.handlers) > 1:
        # Keep only the first handler
        for handler in logger.handlers[1:]:
            logger.removeHandler(handler)


setup_logging()

# Create logger
logger = logging.getLogger(f"{AGENT_ID}.main")

# Global instances
mcp_client_instance: MCPClient | None = None
commander_logic_instance: CommanderLogic | None = None
shutdown_in_progress = False


class CommanderAgentManager:
    """Main agent manager for CommanderAgent."""

    def __init__(self) -> None:
        self.mcp_client: MCPClient | None = None
        self.commander_logic: CommanderLogic | None = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False

    async def handle_incoming_message(self, message: MCPMessage) -> None:
        """Handle incoming messages with proper error handling and response processing."""
        if not self.commander_logic:
            logger.error("CommanderLogic instance not initialized. Cannot process message.")
            return

        try:
            # Process message through logic
            response = await self.commander_logic.process_message(message)

            # Handle response if needed (CommanderAgent typically doesn't send responses)
            if response is not None:
                logger.debug(f"Logic returned response: {response}")
                # CommanderAgent logic should return None for most messages
                # If a response is needed in the future, handle it here

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Continue processing other messages rather than crashing

    async def initialize_components(self) -> bool | None:
        """Initialize MCP client and CommanderLogic."""
        try:
            # Initialize MCPClient
            self.mcp_client = MCPClient(
                agent_id=AGENT_ID,
                agent_name=AGENT_NAME,
                agent_type=AGENT_TYPE,
                mcp_server_url=MCP_SERVER_URL,
                capabilities=AGENT_CAPABILITIES,
                message_handler=self.handle_incoming_message,
            )

            # Initialize CommanderLogic with dedicated logger
            logic_logger = logging.getLogger(f"{AGENT_ID}.logic")
            self.commander_logic = CommanderLogic(agent_id=AGENT_ID, mcp_client=self.mcp_client, logger=logic_logger)

            logger.info(f"CommanderAgent components initialized successfully (Version: {AGENT_VERSION})")
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {MCP_SERVER_URL}")

            return True

        except Exception as e:
            logger.critical(f"Failed to initialize CommanderAgent components: {e}", exc_info=True)
            return False

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        try:
            loop = asyncio.get_running_loop()

            def signal_handler(signum) -> None:
                signal_name = signal.Signals(signum).name
                logger.info(f"Received shutdown signal: {signal_name}")
                self.stop_event.set()

            # Add signal handlers for common shutdown signals
            for sig in [signal.SIGINT, signal.SIGTERM]:
                try:
                    loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
                    logger.debug(f"Added signal handler for {signal.Signals(sig).name}")
                except (NotImplementedError, OSError) as e:
                    logger.warning(f"Cannot add signal handler for {signal.Signals(sig).name}: {e}")

        except RuntimeError as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    async def connect_and_register(self) -> bool | None:
        """Connect to MCP server and register agent."""
        try:
            await self.mcp_client.connect()

            if not self.mcp_client._is_connected:
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
        """Main agent event loop."""
        logger.info(f"{AGENT_ID} entering main event loop...")

        try:
            # Start timeout checker task
            timeout_task = None
            if self.commander_logic:
                timeout_task = asyncio.create_task(self._run_timeout_checker())

            # Wait for shutdown signal
            await self.stop_event.wait()

            # Cancel timeout checker if running
            if timeout_task and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Error in main event loop: {e}", exc_info=True)

    async def _run_timeout_checker(self) -> None:
        """Background task to check for workflow timeouts."""
        try:
            while not self.stop_event.is_set():
                if self.commander_logic:
                    await self.commander_logic.check_timeouts()
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            logger.debug("Timeout checker cancelled")
        except Exception as e:
            logger.error(f"Error in timeout checker: {e}", exc_info=True)

    async def shutdown(self) -> None:
        """Graceful shutdown of all components."""
        if self.shutdown_complete:
            return

        logger.info(f"Shutting down {AGENT_ID}...")

        try:
            # Shutdown CommanderLogic first
            if self.commander_logic:
                await self.commander_logic.shutdown()
                logger.debug("CommanderLogic shutdown complete")

            # Disconnect MCP client
            if self.mcp_client and self.mcp_client._is_connected:
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected")

            self.shutdown_complete = True
            logger.info(f"{AGENT_ID} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main() -> int | None:
    """Main entry point."""
    agent_manager = CommanderAgentManager()

    # Update global instances for backward compatibility
    global mcp_client_instance, commander_logic_instance

    try:
        # Initialize components
        if not await agent_manager.initialize_components():
            logger.critical("Failed to initialize agent components")
            return 1

        # Update global references
        mcp_client_instance = agent_manager.mcp_client
        commander_logic_instance = agent_manager.commander_logic

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
        logger.info("CommanderAgent interrupted")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
