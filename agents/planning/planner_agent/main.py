# C:\Users\rossd\Downloads\RossNetAgents\agents\planning\planner_agent\main.py
# Version: 1.3.0 - Fixed Registration & Import Path

import asyncio
import os
import signal
import logging
import sys
from typing import Optional, Dict, Any, List
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
    print(f"CRITICAL_ERROR_PLANNER_MAIN: Failed to import core_infra: {e}")
    sys.exit(1)

# FIXED: Import the enhanced logic from planner_agent_01 directory
try:
    # Import from planner_agent_01 at project root
    from planner_agent_01.logic import MemoryAugmentedPlannerLogic as PlannerLogic

    print("Successfully imported MemoryAugmentedPlannerLogic from planner_agent_01")
except ImportError as e:
    print(f"Failed to import from planner_agent_01: {e}")
    # Fallback: Try the local agent_logic.py if it has the right class
    try:
        from .agent_logic import MemoryAugmentedPlannerLogic as PlannerLogic

        print("Using local agent_logic.py")
    except ImportError as e2:
        print(f"CRITICAL_ERROR: Cannot import MemoryAugmentedPlannerLogic: {e2}")
        print(f"Project root: {project_root_main}")
        print(f"Current directory: {os.getcwd()}")
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
AGENT_ID = "planner_agent_01"
AGENT_NAME = "PlannerAgent"
AGENT_TYPE = "PlannerAgent"
AGENT_VERSION = "1.3.0"  # Updated version for registration fix

# Logging setup
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
)

logger = logging.getLogger(f"{AGENT_ID}.main")
logic_logger = logging.getLogger(f"{AGENT_ID}.logic")

# Global instances
mcp_client_instance: Optional[MCPClient] = None
agent_logic_instance: Optional[PlannerLogic] = None
shutdown_in_progress = False


class PlannerAgentManager:
    """Main agent manager for PlannerAgent"""

    def __init__(self):
        self.mcp_client: Optional[MCPClient] = None
        self.planner_logic: Optional[PlannerLogic] = None
        self.stop_event = asyncio.Event()
        self.shutdown_complete = False

    async def handle_incoming_message(self, message: MCPMessage):
        """Handle incoming messages with proper response structure validation"""
        if not self.planner_logic or not self.mcp_client:
            logger.error("Logic/MCPClient instance missing in PlannerAgent handler")
            return

        try:
            # Extract message details
            header: MCPHeader = message.mcp_header
            message_type = header.message_type
            sender_id = header.sender_id
            correlation_id = header.correlation_id

            # FIXED: Add handlers for ERROR and PONG messages
            if message_type == "ERROR":
                await self._handle_error_message(message)
                return
            elif message_type == "PONG":
                # Simply acknowledge PONG messages
                logger.debug(f"Received PONG from {sender_id}")
                return

            # Reduced logging to avoid duplication with logic
            logger.debug(f"Processing {message_type} from {sender_id} (CorrID: {correlation_id})")

            # Convert message to dict format expected by logic
            message_dict = message.model_dump()

            # Process through logic - handle both async and sync versions
            try:
                if hasattr(self.planner_logic, "process_message") and asyncio.iscoroutinefunction(
                    self.planner_logic.process_message
                ):
                    response_from_logic = await self.planner_logic.process_message(
                        message_dict, self.mcp_client
                    )
                else:
                    # Handle synchronous process_message or fallback to process_task
                    if message_type == "TASK_ASSIGN" and hasattr(
                        self.planner_logic, "process_task"
                    ):
                        task_data = message_dict.get("payload", {})
                        if asyncio.iscoroutinefunction(self.planner_logic.process_task):
                            task_result_payload = await self.planner_logic.process_task(task_data)
                        else:
                            task_result_payload = self.planner_logic.process_task(task_data)

                        # Convert task result to message format
                        if task_result_payload and isinstance(task_result_payload, dict):
                            if task_result_payload.get("status") == "COMPLETED":
                                response_from_logic = {
                                    "message_type": "TASK_COMPLETE",
                                    "payload": task_result_payload,
                                }
                                logger.debug("Task completed successfully, sending TASK_COMPLETE")
                            else:
                                response_from_logic = {
                                    "message_type": "TASK_FAIL",
                                    "payload": task_result_payload,
                                }
                                logger.debug(
                                    f"Task failed with status: {task_result_payload.get('status')}, sending TASK_FAIL"
                                )
                        else:
                            logger.error(
                                f"Planner logic process_task returned invalid data: {task_result_payload}"
                            )
                            response_from_logic = {
                                "message_type": "TASK_FAIL",
                                "payload": {
                                    "status": "FAILED",
                                    "error": "Invalid response from planner logic",
                                    "agent_id": AGENT_ID,
                                    "correlation_id": correlation_id,
                                },
                            }
                    else:
                        # For other message types, try process_message sync
                        if hasattr(self.planner_logic, "process_message"):
                            response_from_logic = self.planner_logic.process_message(
                                message_dict, self.mcp_client
                            )
                        else:
                            logger.warning(f"No handler for message type: {message_type}")
                            response_from_logic = None
            except Exception as process_error:
                logger.error(f"Error in logic processing: {process_error}", exc_info=True)
                if message_type == "TASK_ASSIGN":
                    response_from_logic = {
                        "message_type": "TASK_FAIL",
                        "payload": {
                            "status": "FAILED",
                            "error": str(process_error),
                            "agent_id": AGENT_ID,
                            "correlation_id": correlation_id,
                            "message": f"Exception in planner logic: {str(process_error)}",
                        },
                    }
                else:
                    response_from_logic = None

            # Handle response if present
            if response_from_logic is not None:
                await self._handle_logic_response(response_from_logic, header)
            else:
                logger.debug(f"No response needed for {message_type}")

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_message_error(message, e)

    async def _handle_error_message(self, message: MCPMessage):
        """FIXED: Handle ERROR messages from the server"""
        header = message.mcp_header
        payload = message.payload
        correlation_id = header.correlation_id

        logger.error(f"Received ERROR message (CorrID: {correlation_id})")
        logger.error(f"Error details: {payload}")

        # Check if this is a registration error
        error_str = str(payload).lower()
        if (
            "registration" in error_str
            or "capabilities" in error_str
            or "discovery_register" in error_str
        ):
            logger.critical("REGISTRATION FAILED - Server rejected our capabilities format!")
            logger.critical("Error payload: %s", payload)
            logger.critical("Shutting down due to registration failure...")

            # Set shutdown event
            self.stop_event.set()

            # Force exit with error code
            sys.exit(1)
        else:
            # Log other errors but continue
            logger.error(f"Non-fatal error received: {payload}")

    async def _handle_logic_response(self, response: Dict[str, Any], original_header: MCPHeader):
        """Handle response from logic with proper validation"""
        try:
            if not isinstance(response, dict):
                logger.error(f"Logic returned non-dict response: {type(response)}")
                return

            response_message_type = response.get("message_type")
            response_payload = response.get("payload")

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

            # Only send TASK_FAIL for TASK_ASSIGN messages
            if message_type == "TASK_ASSIGN" and sender_id and self.mcp_client:
                error_payload = {
                    "correlation_id": correlation_id,
                    "agent_id": AGENT_ID,
                    "status": "FAILED",
                    "error_message": f"PlannerAgent failed to process {message_type}: {str(error)}",
                    "message": f"Internal error in {AGENT_NAME}: {str(error)}",
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

    def _get_capabilities_list(self) -> List[Dict[str, Any]]:
        """FIXED: Get capabilities in the correct format - list of dictionaries"""
        # Check if logic has memory manager
        memory_augmented = False
        if self.planner_logic and hasattr(self.planner_logic, "memory_manager"):
            memory_augmented = self.planner_logic.memory_manager is not None

        # Return capabilities as a list of dictionaries
        capabilities = [
            {
                "name": "planning",
                "description": "Creates a step-by-step execution plan based on a high-level research goal",
                "type": "planning",
                "version": AGENT_VERSION,
            },
            {
                "name": "llm_plan_generation",
                "description": "Generates research plans using LLM and memory-augmented intelligence",
                "memory_augmented": memory_augmented,
                "type": "llm_planning",
                "version": "2.6",
            },
        ]

        logger.info(f"Registering with capabilities (list format): {capabilities}")
        return capabilities

    async def initialize_components(self):
        """Initialize PlannerLogic and MCPClient"""
        try:
            # Initialize PlannerLogic (MemoryAugmentedPlannerLogic)
            self.planner_logic = PlannerLogic(agent_id=AGENT_ID, logger_instance=logic_logger)

            # FIXED: Get capabilities in correct format
            capabilities = self._get_capabilities_list()

            # Initialize MCPClient
            mcp_settings = MCPConfig()
            base_mcp_server_url = mcp_settings.DEFAULT_ROUTER_URL
            if "/ws/" in base_mcp_server_url:
                base_mcp_server_url = base_mcp_server_url.split("/ws/")[0]

            self.mcp_client = MCPClient(
                agent_id=AGENT_ID,
                agent_name=AGENT_NAME,
                agent_type=AGENT_TYPE,
                mcp_server_url=base_mcp_server_url,
                capabilities=capabilities,  # Now passing list of dicts
                message_handler=self.handle_incoming_message,
            )

            logger.info(f"PlannerAgent components initialized (Version: {AGENT_VERSION})")
            logger.info(
                f"Memory augmentation available: {any(cap.get('memory_augmented', False) for cap in capabilities)}"
            )
            logger.info(f"Environment loaded from: {env_source}")
            logger.info(f"MCP Server URL: {base_mcp_server_url}")

            return True

        except Exception as e:
            logger.critical(f"Failed to initialize PlannerAgent components: {e}", exc_info=True)
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

    async def run_main_loop(self):
        """Main agent event loop"""
        logger.info(f"{AGENT_ID} entering main event loop...")

        try:
            # Wait for shutdown signal
            await self.stop_event.wait()
            logger.info("Shutdown signal received")

        except Exception as e:
            logger.error(f"Error in main event loop: {e}", exc_info=True)

    async def shutdown(self):
        """Graceful shutdown of all components"""
        if self.shutdown_complete:
            return

        logger.info(f"Shutting down {AGENT_ID}...")

        try:
            # Shutdown PlannerLogic first
            if self.planner_logic and hasattr(self.planner_logic, "shutdown"):
                if asyncio.iscoroutinefunction(self.planner_logic.shutdown):
                    await self.planner_logic.shutdown()
                else:
                    self.planner_logic.shutdown()
                logger.debug("PlannerLogic shutdown complete")

            # Disconnect MCP client
            if self.mcp_client and self.mcp_client.is_connected:
                await self.mcp_client.disconnect()
                logger.debug("MCP client disconnected")

            self.shutdown_complete = True
            logger.info(f"{AGENT_ID} shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


async def main():
    """Main entry point"""
    agent_manager = PlannerAgentManager()

    # Update global instances for backward compatibility
    global mcp_client_instance, agent_logic_instance

    try:
        # Initialize components
        if not await agent_manager.initialize_components():
            logger.critical("Failed to initialize agent components")
            return 1

        # Update global references
        mcp_client_instance = agent_manager.mcp_client
        agent_logic_instance = agent_manager.planner_logic

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
        logger.info("PlannerAgent interrupted")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
