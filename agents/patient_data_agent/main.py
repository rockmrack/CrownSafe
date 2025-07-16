import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from .agent_logic import PatientDataAgentLogic

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

AGENT_ID = "patient_data_agent_01"
AGENT_NAME = "Patient Data Management Agent"
AGENT_TYPE = "data"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class PatientDataAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.agent_name = AGENT_NAME
        self.agent_type = AGENT_TYPE
        self.logic = PatientDataAgentLogic(agent_id=self.agent_id, logger_instance=logger)
        
        # Define capabilities for discovery service
        self.capabilities = [
            {
                "name": "get_patient_record",
                "description": "Retrieve a specific patient's medical record by ID",
                "parameters": {
                    "patient_id": "string (required)"
                }
            },
            {
                "name": "search_patients",
                "description": "Search for patients by various criteria",
                "parameters": {
                    "criteria": "object (required) - search criteria",
                    "max_results": "integer (optional, default=10)"
                }
            },
            {
                "name": "update_patient",
                "description": "Update patient medical record",
                "parameters": {
                    "patient_id": "string (required)",
                    "updates": "object (required) - fields to update"
                }
            },
            {
                "name": "get_audit_log",
                "description": "Retrieve audit log for patient data access",
                "parameters": {
                    "patient_id": "string (optional)",
                    "action_type": "string (optional)",
                    "start_time": "string (optional)",
                    "end_time": "string (optional)"
                }
            },
            {
                "name": "check_privacy_consent",
                "description": "Check patient privacy and consent status",
                "parameters": {
                    "patient_id": "string (required)",
                    "action": "string (optional, default='check_consent')"
                }
            },
            {
                "name": "export_patient_data",
                "description": "Export patient data in various formats",
                "parameters": {
                    "patient_ids": "array of strings (optional)",
                    "format": "string (optional, default='json')",
                    "include_audit": "boolean (optional, default=false)"
                }
            },
            {
                "name": "validate_patient_data",
                "description": "Validate patient data for completeness and correctness",
                "parameters": {
                    "patient_id": "string (optional)",
                    "validation_type": "string (optional, default='complete')"
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
        logger.info(f"PatientDataAgent initialized: {self.agent_id}")

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
            elif msg_type == "DATA_SYNC":
                # Handle data synchronization requests
                await self.handle_data_sync(message)
            elif msg_type == "INFO_REQUEST":
                # Handle info requests about patient data
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
                # Patient not found
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

    async def handle_data_sync(self, message: MCPMessage) -> None:
        """Handle data synchronization requests"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload
        
        sync_type = payload.get("sync_type", "full")
        
        try:
            if sync_type == "full":
                # Full data sync
                patient_count = len(self.logic.patient_records)
                response_payload = {
                    "status": "success",
                    "sync_type": "full",
                    "patient_count": patient_count,
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            elif sync_type == "incremental":
                # Incremental sync (would need timestamp tracking in real system)
                response_payload = {
                    "status": "success",
                    "sync_type": "incremental",
                    "changes": 0,
                    "last_sync": datetime.now(timezone.utc).isoformat()
                }
            else:
                response_payload = {
                    "status": "error",
                    "message": f"Unknown sync type: {sync_type}"
                }
            
            await self.mcp_client.send_message(
                payload=response_payload,
                message_type="DATA_SYNC_RESPONSE",
                target_agent_id=sender_id,
                correlation_id=correlation_id
            )
            
        except Exception as e:
            logger.error(f"Error handling data sync: {e}")
            await self.mcp_client.send_message(
                payload={
                    "status": "error",
                    "message": str(e)
                },
                message_type="DATA_SYNC_RESPONSE",
                target_agent_id=sender_id,
                correlation_id=correlation_id
            )

    async def handle_info_request(self, message: MCPMessage) -> None:
        """Handle information requests about patient data"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload
        
        info_type = payload.get("info_type", "summary")
        
        try:
            if info_type == "summary":
                # Provide summary of patient data
                response_payload = {
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "capabilities": self.capabilities,
                    "data_source": "Mock EMR System",
                    "patient_count": len(self.logic.patient_records),
                    "audit_enabled": self.logic.privacy_config['audit_all_access'],
                    "privacy_features": list(self.logic.privacy_config.keys())
                }
            elif info_type == "statistics":
                # Provide statistics about patient data
                total_patients = len(self.logic.patient_records)
                patients_with_diabetes = sum(
                    1 for p in self.logic.patient_records.values()
                    if any('E11' in d for d in p.get('diagnoses_icd10', []))
                )
                patients_with_hf = sum(
                    1 for p in self.logic.patient_records.values()
                    if any('I50' in d for d in p.get('diagnoses_icd10', []))
                )
                
                response_payload = {
                    "total_patients": total_patients,
                    "patients_with_diabetes": patients_with_diabetes,
                    "patients_with_heart_failure": patients_with_hf,
                    "audit_entries": len(self.logic.audit_log)
                }
            elif info_type == "fields":
                # Provide information about searchable fields
                response_payload = {
                    "searchable_fields": list(self.logic.searchable_fields),
                    "protected_fields": ['patient_id', 'created_at', 'access_log'],
                    "lab_types": ["LVEF", "HbA1c", "eGFR", "BNP"]
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
            
        except Exception as e:
            logger.error(f"Error handling info request: {e}")
            await self.mcp_client.send_message(
                payload={"error": str(e)},
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
            logger.info(f"Loaded {len(self.logic.patient_records)} patient records")
            logger.info(f"Audit logging: {'Enabled' if self.logic.privacy_config['audit_all_access'] else 'Disabled'}")
            
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
    agent = PatientDataAgent()
    
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
        test_agent = PatientDataAgent()
        
        # Test patient retrieval
        test_result = test_agent.logic.process_task({
            "task_name": "get_patient_record",
            "patient_id": "patient-001"
        })
        logger.info(f"Patient retrieval test: {json.dumps(test_result, indent=2)}")
        
        # Test patient search
        test_result = test_agent.logic.process_task({
            "task_name": "search_patients",
            "criteria": {"diagnoses_icd10": "I50"}
        })
        logger.info(f"Patient search test: {json.dumps(test_result, indent=2)}")
    else:
        # Normal operation
        asyncio.run(main())