import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from .agent_logic import DrugBankAgentLogic

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AGENT_ID = "drugbank_agent_01"
AGENT_NAME = "DrugBank Data Analysis Agent"
AGENT_TYPE = "research"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class DrugBankAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.agent_name = AGENT_NAME
        self.agent_type = AGENT_TYPE
        self.logic = DrugBankAgentLogic(agent_id=self.agent_id, logger_instance=logger)

        # Define capabilities for discovery service
        self.capabilities = [
            {
                "name": "drug_info",
                "description": "Retrieve comprehensive drug information including indications, contraindications, and warnings",
                "parameters": {"drug_name": "string (required)"},
            },
            {
                "name": "check_drug_interactions",  # FIXED: Changed from "check_interactions" to "check_drug_interactions"
                "description": "Check for drug-drug interactions between multiple medications",
                "parameters": {"drug_names": "array of strings (required, minimum 2)"},
            },
            {
                "name": "search_drugs",
                "description": "Search for drugs by name, class, or indication",
                "parameters": {
                    "query": "string (required)",
                    "search_type": "string (optional, default='name', options: 'name', 'class', 'indication')",
                },
            },
            {
                "name": "pa_criteria",
                "description": "Extract prior authorization relevant criteria for a specific drug and indication",
                "parameters": {"drug_name": "string (required)", "indication": "string (optional)"},
            },
        ]

        # Initialize MCP client
        self.mcp_client = MCPClient(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            mcp_server_url=MCP_SERVER_URL,
            message_handler=self.handle_message,
            capabilities=self.capabilities,
        )

        self.running = False
        logger.info(f"DrugBankAgent initialized: {self.agent_id}")

    async def handle_message(self, message: MCPMessage) -> None:
        """Handle incoming MCP messages"""
        try:
            msg_type = message.mcp_header.message_type
            sender_id = message.mcp_header.sender_id
            correlation_id = message.mcp_header.correlation_id

            logger.info(f"Received message type: {msg_type} from {sender_id}")

            if msg_type == "TASK_ASSIGN":
                await self.handle_task_assign(message)
            elif msg_type == "PING":
                # Respond to ping
                await self.mcp_client.send_message(
                    payload={"timestamp": datetime.now(timezone.utc).isoformat()},
                    message_type="PONG",
                    target_agent_id=sender_id,
                    correlation_id=correlation_id,
                )
            elif msg_type == "INFO_REQUEST":
                # Handle info request about drug capabilities
                await self.handle_info_request(message)
            else:
                logger.warning(f"Unhandled message type: {msg_type}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def handle_task_assign(self, message: MCPMessage) -> None:
        """Handle task assignment from router"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload

        task_id = payload.get("task_id", "unknown")
        workflow_id = payload.get("workflow_id", "unknown")

        logger.info(f"Processing task {task_id} for workflow {workflow_id}")

        try:
            # Process the task using our logic
            result = self.logic.process_task(payload)

            # Determine response type based on result status
            if result.get("status") == "COMPLETED":
                response_type = "TASK_COMPLETE"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "status": "COMPLETED",
                    "result": result,
                }
            elif result.get("status") == "PARTIAL":
                # Handle partial success (e.g., some drugs not found in interaction check)
                response_type = "TASK_COMPLETE"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "status": "PARTIAL",
                    "result": result,
                    "warning": result.get("error", "Some data could not be retrieved"),
                }
            else:
                response_type = "TASK_FAIL"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": result.get("error", "Task processing failed"),
                }

            # Send response back to router
            await self.mcp_client.send_message(
                payload=response_payload,
                message_type=response_type,
                target_agent_id=sender_id,
                correlation_id=correlation_id,
            )

            logger.info(f"Task {task_id} completed with status: {result.get('status')}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)

            # Send failure response
            await self.mcp_client.send_message(
                payload={
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": str(e),
                },
                message_type="TASK_FAIL",
                target_agent_id=sender_id,
                correlation_id=correlation_id,
            )

    async def handle_info_request(self, message: MCPMessage) -> None:
        """Handle information requests about drug data capabilities"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload

        info_type = payload.get("info_type", "capabilities")

        if info_type == "capabilities":
            response_payload = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "capabilities": self.capabilities,
                "data_source": "DrugBank (Mock Data)",
                "supported_drug_classes": [
                    "SGLT2 inhibitors",
                    "GLP-1 receptor agonists",
                    "Biguanides",
                    "Anticoagulants",
                ],
            }
        elif info_type == "status":
            response_payload = {
                "agent_id": self.agent_id,
                "status": "active",
                "mock_data_loaded": True,
                "memory_manager_available": self.logic.memory_manager is not None,
            }
        else:
            response_payload = {"error": f"Unknown info_type: {info_type}"}

        await self.mcp_client.send_message(
            payload=response_payload,
            message_type="INFO_RESPONSE",
            target_agent_id=sender_id,
            correlation_id=correlation_id,
        )

    async def start(self) -> None:
        """Start the agent"""
        logger.info(f"Starting {self.agent_name}...")
        self.running = True

        try:
            # Connect to MCP server
            await self.mcp_client.connect()

            # Register with discovery service
            await self.mcp_client.register_self()

            logger.info(f"{self.agent_name} started successfully")
            logger.info(f"Mock data loaded from: {self.logic.mock_data_path}")
            logger.info(f"Memory manager available: {self.logic.memory_manager is not None}")

            # Log available drugs in mock data
            drug_count = len(self.logic.mock_data.get("drug_search", {}))
            logger.info(f"Available drugs in database: {drug_count}")

            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error starting agent: {e}", exc_info=True)
            self.running = False

    async def stop(self) -> None:
        """Stop the agent"""
        logger.info(f"Stopping {self.agent_name}...")
        self.running = False

        try:
            # Unregister from discovery service
            await self.mcp_client.send_message(
                payload={"agent_id": self.agent_id, "reason": "Graceful shutdown"},
                message_type="AGENT_UNREGISTER",
                target_agent_id="discovery_service",
            )

            await self.mcp_client.disconnect()
            logger.info(f"{self.agent_name} stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping agent: {e}", exc_info=True)


def signal_handler(signame):
    """Handle shutdown signals"""

    def handler(signum, frame):
        logger.info(f"Received {signame}, initiating shutdown...")
        asyncio.create_task(agent.stop())

    return handler


async def main():
    global agent
    agent = DrugBankAgent()

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler("SIGINT"))
    signal.signal(signal.SIGTERM, signal_handler("SIGTERM"))

    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await agent.stop()


if __name__ == "__main__":
    # Check if running in test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run a quick test of the agent logic
        logger.info("Running in test mode...")
        test_agent = DrugBankAgent()

        # Test drug info retrieval
        test_result = test_agent.logic.process_task(
            {"task_name": "drug_info", "drug_name": "empagliflozin"}
        )
        logger.info(f"Test result: {json.dumps(test_result, indent=2)}")

        # Test interaction check
        test_result = test_agent.logic.process_task(
            {"task_name": "check_interactions", "drug_names": ["warfarin", "aspirin"]}
        )
        logger.info(f"Interaction test result: {json.dumps(test_result, indent=2)}")
    else:
        # Normal operation
        asyncio.run(main())
