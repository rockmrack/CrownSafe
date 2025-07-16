# C:\Users\rossd\Downloads\RossNetAgents\agents\routing\router_agent\main.py
# Step: Critical-Fixes-Router-Main-TypeErrorFix
# Addresses: TypeError in process_message call

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
    from core_infra.mcp_client_library.exceptions import MCPConnectionError, MCPError
except ImportError as e:
    print(f"CRITICAL_ERROR_ROUTER_MAIN: Failed to import core_infra: {e}")
    sys.exit(1)

# Ensure agent_logic can be imported
# Assuming agent_logic.py is in the same directory as this main.py
try:
    from .agent_logic import RouterLogic
except ImportError:
    # Fallback if running the script directly for some reason and '.' is not in path
    from agent_logic import RouterLogic


# Environment setup
def setup_environment():
    """Setup environment variables with proper fallback"""
    dotenv_paths = [
        os.path.join(project_root_main, '.env'),
        ".env" # For running from project root
    ]
    
    loaded_path = None
    for dotenv_path in dotenv_paths:
        if os.path.exists(dotenv_path):
            if load_dotenv(dotenv_path):
                loaded_path = dotenv_path
                break # Stop at first successful load
    
    if not loaded_path: # If no .env file was found and loaded
        load_dotenv()  # Try loading from default locations (e.g., if vars are already in env)
        return "system environment or default locations"
    return str(loaded_path)

env_source = setup_environment()

# Agent Configuration
AGENT_ID = "router_agent_01"
AGENT_NAME = "RouterAgent"
AGENT_TYPE = "RouterAgent"
AGENT_VERSION = "1.2.1"  # Incremented for TypeError fix

AGENT_CAPABILITIES = [
    {"name": "routing", "description": "Routes sub-tasks based on a plan"},
    {"name": "dependency_management", "description": "Manages task dependencies within a workflow"},
    {"name": "workflow_orchestration", "description": "Coordinates the execution flow between agents"},
    {"name": "task_delegation", "description": "Delegates tasks to specialized worker agents"},
    {"name": "result_aggregation", "description": "Aggregates results from multiple worker agents"}
]

# Configuration from environment
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "ws://127.0.0.1:8001")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Logging setup
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True # Override any root logger configs
)

logger = logging.getLogger(f"{AGENT_ID}.main")
logic_logger = logging.getLogger(f"{AGENT_ID}.logic") # Separate logger for logic module

# Global instances (for potential direct access if needed, though manager is preferred)
# These are less critical now with the AgentManager pattern but kept for context if any part relies on them.
mcp_client_instance: Optional[MCPClient] = None
router_logic_instance: Optional[RouterLogic] = None

class RouterAgentManager:
    """Main agent manager for RouterAgent"""
    
    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.router_logic: Optional[RouterLogic] = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False # Flag to prevent multiple shutdown calls

    async def handle_incoming_message(self, message: MCPMessage):
        """Handle incoming messages with proper response processing"""
        if not self.router_logic or not self.mcp_client:
            logger.error("Logic/MCPClient instance missing in RouterAgent handler during message processing.")
            return

        try:
            header: MCPHeader = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            logger.debug(f"MAIN_HANDLER: Processing {message_type} from {sender_id} (CorrID: {correlation_id})")

            message_dict = message.model_dump() # Pass the full message dict to logic
            
            # CRITICAL FIX: RouterLogic.process_message expects only message_dict (self is implicit)
            # The RouterLogic instance already has self.mcp_client.
            await self.router_logic.process_message(message_dict)
            
            # RouterLogic's process_message does not return a direct response to send back here.
            # It handles sending messages (like TASK_ASSIGN to workers or TASK_COMPLETE to Commander)
            # internally using its own mcp_client instance.
            # So, no _handle_logic_response call is typically needed here for RouterAgent,
            # unless process_message was redesigned to return something for main.py to send.
            # Based on RouterLogic's current design, it sends its own messages.

            logger.debug(f"MAIN_HANDLER: Logic processing complete for {message_type} from {sender_id}")

        except Exception as e:
            logger.error(f"MAIN_HANDLER: Error processing message: {e}", exc_info=True)
            # RouterLogic should handle its own error reporting (e.g., failing a workflow if needed)
            # This main.py error handler is for unexpected errors in the main handling loop itself.
            # We might not want to send a TASK_FAIL from here if the error is in main.py's handling
            # rather than the logic's processing of a specific task.
            # await self._handle_message_error(message, e) # Consider if this is appropriate here

    # _handle_logic_response and _handle_message_error might not be directly used
    # if RouterLogic handles all its own outgoing messages and error reporting.
    # Kept for structural similarity if needed in future.

    async def initialize_components(self):
        """Initialize RouterLogic and MCPClient"""
        try:
            base_mcp_url = MCP_SERVER_URL
            if "/ws/" in base_mcp_url.lower(): # Ensure we get the base URL
                base_mcp_url = base_mcp_url.split('/ws/')[0]

            self.mcp_client = MCPClient(
                agent_id=AGENT_ID,
                agent_name=AGENT_NAME,
                agent_type=AGENT_TYPE,
                mcp_server_url=base_mcp_url,
                capabilities=AGENT_CAPABILITIES,
                message_handler=self.handle_incoming_message # This method will be called by MCPClient
            )
            
            self.router_logic = RouterLogic( # RouterLogic needs the mcp_client to send its own messages
                agent_id=AGENT_ID,
                mcp_client=self.mcp_client, 
                logger=logic_logger
            )
            
            logger.info(f"RouterAgent components initialized (Version: {AGENT_VERSION})")
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {base_mcp_url}")
            
            return True

        except Exception as e:
            logger.critical(f"Failed to initialize RouterAgent components: {e}", exc_info=True)
            return False

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        try:
            loop = asyncio.get_running_loop()
            
            def signal_handler_callback(signum): # Renamed to avoid conflict
                signal_name = signal.Signals(signum).name
                logger.info(f"Received shutdown signal: {signal_name}. Setting stop event.")
                self.stop_event.set()
            
            for sig_name in ['SIGINT', 'SIGTERM']:
                sig = getattr(signal, sig_name, None)
                if sig is not None:
                    try:
                        loop.add_signal_handler(sig, lambda s=sig: signal_handler_callback(s))
                        logger.debug(f"Added signal handler for {signal.Signals(sig).name}")
                    except (NotImplementedError, OSError, ValueError) as e: # Added ValueError
                        logger.warning(f"Cannot add signal handler for {signal.Signals(sig).name} on this system: {e}. Use Ctrl+C if available.")
                else:
                    logger.warning(f"Signal {sig_name} not available on this platform.")
                    
        except RuntimeError as e: # e.g. "Cannot add signal handler" if not in main thread
            logger.warning(f"Could not setup signal handlers: {e}. This might be normal if not running in main thread.")

    async def connect_and_register(self):
        """Connect to MCP server and register agent"""
        if not self.mcp_client:
            logger.critical("MCPClient not initialized. Cannot connect.")
            return False
        try:
            await self.mcp_client.connect()
            if not self.mcp_client.is_connected:
                logger.critical("Failed to connect to MCP server after connect() call.")
                return False
            await self.mcp_client.register_self()
            logger.info(f"{AGENT_ID} connected and registered successfully.")
            return True
        except MCPConnectionError as e:
            logger.critical(f"MCP Connection Error during connect/register: {e}")
            return False
        except Exception as e:
            logger.critical(f"Unexpected error during connection/registration: {e}", exc_info=True)
            return False

    async def run_main_loop(self):
        """Main agent event loop"""
        if not self.mcp_client or not self.router_logic:
            logger.critical("Agent not initialized properly. Cannot run main loop.")
            return

        logger.info(f"{AGENT_ID} entering main event loop. Waiting for stop_event...")
        try:
            await self.stop_event.wait() # Wait until stop_event is set
            logger.info(f"{AGENT_ID} stop_event received, exiting main loop.")
        except asyncio.CancelledError:
            logger.info(f"{AGENT_ID} main loop cancelled.")
        except Exception as e:
            logger.error(f"Error in main event loop for {AGENT_ID}: {e}", exc_info=True)

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.shutdown_complete:
            logger.debug(f"{AGENT_ID} shutdown already in progress or completed.")
            return
            
        logger.info(f"Shutting down {AGENT_ID}...")
        self.shutdown_complete = True # Set flag early
        
        try:
            if self.router_logic and hasattr(self.router_logic, 'shutdown'):
                logger.debug(f"Calling shutdown for {AGENT_ID} logic...")
                await self.router_logic.shutdown()
                logger.debug("RouterLogic shutdown complete.")
            
            if self.mcp_client and self.mcp_client.is_connected:
                logger.debug(f"Disconnecting MCPClient for {AGENT_ID}...")
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected.")
            
            logger.info(f"{AGENT_ID} shutdown sequence finished.")
            
        except Exception as e:
            logger.error(f"Error during {AGENT_ID} shutdown: {e}", exc_info=True)

async def main_async_runner(): # Renamed to avoid conflict with module-level main
    """Main entry point for the agent"""
    agent_manager = RouterAgentManager()
    
    # For direct script execution context, update globals if any part relies on them (legacy)
    global mcp_client_instance, router_logic_instance 
    
    try:
        if not await agent_manager.initialize_components():
            # Critical log already in initialize_components
            return 1 
        
        mcp_client_instance = agent_manager.mcp_client
        router_logic_instance = agent_manager.router_logic
        
        agent_manager.setup_signal_handlers()
        
        if not await agent_manager.connect_and_register():
            # Critical log already in connect_and_register
            return 1
        
        await agent_manager.run_main_loop()
        return 0
        
    except KeyboardInterrupt:
        logger.info(f"{AGENT_NAME} main execution interrupted by KeyboardInterrupt.")
        # stop_event should be set by signal handler if possible, or this is the fallback
        if not agent_manager.stop_event.is_set():
            agent_manager.stop_event.set()
        return 0 # Normal exit for Ctrl+C
    except Exception as e:
        logger.critical(f"Unexpected critical error in {AGENT_NAME} main_async_runner: {e}", exc_info=True)
        return 1
    finally:
        logger.info(f"Performing final shutdown for {AGENT_NAME}...")
        await agent_manager.shutdown()
        logger.info(f"{AGENT_NAME} final shutdown actions complete.")


if __name__ == "__main__":
    logger.info(f"Starting {AGENT_NAME} (ID: {AGENT_ID}, Version: {AGENT_VERSION})")
    try:
        exit_code = asyncio.run(main_async_runner())
        logger.info(f"{AGENT_NAME} exiting with code {exit_code}.")
        sys.exit(exit_code)
    except KeyboardInterrupt: # Catch KeyboardInterrupt here if asyncio.run is interrupted
        logger.info(f"{AGENT_NAME} main process interrupted by KeyboardInterrupt before or during asyncio.run.")
        sys.exit(0)
    except Exception as e: # Catch any other unexpected errors at the top level
        logger.critical(f"Fatal error at {AGENT_NAME} entry point: {e}", exc_info=True)
        sys.exit(1)