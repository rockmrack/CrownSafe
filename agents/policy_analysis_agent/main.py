import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from .agent_logic import PolicyAnalysisAgentLogic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

AGENT_ID = "policy_analysis_agent_01"
AGENT_NAME = "Insurance Policy Analysis Agent"
AGENT_TYPE = "research"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class PolicyAnalysisAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.agent_name = AGENT_NAME
        self.agent_type = AGENT_TYPE
        self.logic = PolicyAnalysisAgentLogic(agent_id=self.agent_id, logger_instance=logger)
        
        # Define capabilities for discovery service
        self.capabilities = [
            {
                "name": "get_policy_for_drug",  # FIXED: Changed from "get_drug_policy" to "get_policy_for_drug"
                "description": "Retrieve coverage policy and criteria for a specific drug",
                "parameters": {
                    "drug_name": "string (required)",
                    "insurer": "string (optional, defaults to primary insurer)"
                }
            },
            {
                "name": "check_coverage_criteria",
                "description": "Evaluate if patient meets coverage criteria for a drug",
                "parameters": {
                    "drug_name": "string (required)",
                    "patient_evidence": "object (required) - contains diagnoses, labs, medications, etc.",
                    "insurer": "string (optional)"
                }
            },
            {
                "name": "search_formulary",
                "description": "Search the formulary by drug name, class, tier, or status",
                "parameters": {
                    "query": "string (required unless search_type is 'all')",
                    "search_type": "string (optional, default='name', options: 'name', 'class', 'tier', 'status', 'all')",
                    "insurer": "string (optional)"
                }
            },
            {
                "name": "get_alternatives",
                "description": "Get covered alternatives for a specific drug",
                "parameters": {
                    "drug_name": "string (required)",
                    "insurer": "string (optional)"
                }
            },
            {
                "name": "compare_policies",
                "description": "Compare drug coverage across multiple insurers",
                "parameters": {
                    "drug_name": "string (required)",
                    "insurers": "array of strings (optional, defaults to all available)"
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
        logger.info(f"PolicyAnalysisAgent initialized: {self.agent_id}")

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
            elif msg_type == "POLICY_UPDATE":
                # Handle policy updates
                await self.handle_policy_update(message)
            elif msg_type == "INFO_REQUEST":
                # Handle info requests about policies
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
                    "result": result
                }
            elif result.get("status") == "NOT_FOUND":
                # Drug not in formulary
                response_type = "TASK_COMPLETE"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "status": "NOT_FOUND",
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

    async def handle_policy_update(self, message: MCPMessage) -> None:
        """Handle policy update notifications"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload
        
        update_type = payload.get("update_type")
        
        if update_type == "reload":
            # Reload policies from file
            self.logic._load_policy_data()
            logger.info("Reloaded policy data")
            
            await self.mcp_client.send_message(
                payload={
                    "status": "success",
                    "message": "Policy data reloaded",
                    "policy_count": len(self.logic.policies)
                },
                message_type="POLICY_UPDATE_RESPONSE",
                target_agent_id=sender_id,
                correlation_id=correlation_id
            )

    async def handle_info_request(self, message: MCPMessage) -> None:
        """Handle information requests about policies"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload
        
        info_type = payload.get("info_type", "summary")
        
        if info_type == "summary":
            # Provide summary of loaded policies
            policy_summary = {}
            for insurer, policy in self.logic.policies.items():
                drug_count = len(policy.get('drugs', {}))
                policy_summary[insurer] = {
                    "drug_count": drug_count,
                    "policy_version": policy.get('policy_version', 'Unknown'),
                    "effective_date": policy.get('effective_date', 'Unknown')
                }
            
            response_payload = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "capabilities": self.capabilities,
                "loaded_policies": policy_summary,
                "total_insurers": len(self.logic.policies)
            }
        elif info_type == "formulary_stats":
            # Provide formulary statistics
            stats = {}
            for insurer in self.logic.policies:
                drugs = self.logic.policies[insurer].get('drugs', {})
                stats[insurer] = {
                    "total_drugs": len(drugs),
                    "pa_required": sum(1 for d in drugs.values() if 'Prior Authorization' in d.get('status', '')),
                    "covered": sum(1 for d in drugs.values() if d.get('status', '').startswith('Covered')),
                    "not_covered": sum(1 for d in drugs.values() if d.get('status', '') in ['Not on Formulary', 'Not Covered'])
                }
            
            response_payload = {
                "formulary_statistics": stats
            }
        else:
            response_payload = {
                "error": f"Unknown info_type: {info_type}"
            }
        
        await self.mcp_client.send_message(
            payload=response_payload,
            message_type="INFO_RESPONSE",
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
            logger.info(f"Loaded policies for {len(self.logic.policies)} insurer(s)")
            
            # Log loaded insurers
            for insurer in self.logic.policies:
                drug_count = len(self.logic.policies[insurer].get('drugs', {}))
                logger.info(f"  - {insurer}: {drug_count} drugs")
            
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
                payload={
                    "agent_id": self.agent_id,
                    "reason": "Graceful shutdown"
                },
                message_type="AGENT_UNREGISTER",
                target_agent_id="discovery_service"
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
    agent = PolicyAnalysisAgent()
    
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
        test_agent = PolicyAnalysisAgent()
        
        # Test policy retrieval
        test_result = test_agent.logic.process_task({
            "task_name": "get_drug_policy",
            "drug_name": "empagliflozin"
        })
        logger.info(f"Policy test result: {json.dumps(test_result, indent=2)}")
        
        # Test coverage check
        test_result = test_agent.logic.process_task({
            "task_name": "check_coverage_criteria",
            "drug_name": "empagliflozin",
            "patient_evidence": {
                "diagnoses_icd10": ["I50", "E11.9"],
                "medication_history": ["Metformin"],
                "labs": {"LVEF": "40%"}
            }
        })
        logger.info(f"Coverage test result: {json.dumps(test_result, indent=2)}")
    else:
        # Normal operation
        asyncio.run(main())