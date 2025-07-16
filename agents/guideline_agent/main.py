import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from .agent_logic import GuidelineAgentLogic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

AGENT_ID = "guideline_agent_01"
AGENT_NAME = "Clinical Guideline Analysis Agent"
AGENT_TYPE = "research"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class GuidelineAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.agent_name = AGENT_NAME
        self.agent_type = AGENT_TYPE
        self.logic = GuidelineAgentLogic(agent_id=self.agent_id, logger_instance=logger)
        
        # Define capabilities for discovery service
        self.capabilities = [
            {
                "name": "query_guidelines",
                "description": "Search clinical guidelines for treatment recommendations and criteria",
                "parameters": {
                    "query": "string (optional)",
                    "drug_name": "string (optional)",
                    "condition": "string (optional)"
                }
            },
            {
                "name": "ingest_guideline",
                "description": "Ingest a clinical guideline document into memory",
                "parameters": {
                    "guideline_id": "string (required)"
                }
            }
        ]
        
        # Initialize MCP client
        self.mcp_client = MCPClient(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            mcp_server_url=MCP_SERVER_URL,
            message_handler=self.handle_message,
            capabilities=self.capabilities
        )
        
        self.running = False
        logger.info(f"GuidelineAgent initialized: {self.agent_id}")

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
                    correlation_id=correlation_id
                )
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
                    "result": result
                }
            else:
                response_type = "TASK_FAIL"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": result.get("error", "Task processing failed")
                }
            
            # Send response back to router
            await self.mcp_client.send_message(
                payload=response_payload,
                message_type=response_type,
                target_agent_id=sender_id,
                correlation_id=correlation_id
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
                    "error_message": str(e)
                },
                message_type="TASK_FAIL",
                target_agent_id=sender_id,
                correlation_id=correlation_id
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
    agent = GuidelineAgent()
    
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
    asyncio.run(main())