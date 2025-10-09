import asyncio
import logging
import json
import signal
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage
from .agent_logic import PatientStratificationAgentLogic, DecisionType

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AGENT_ID = "patient_stratification_agent_01"
AGENT_NAME = "Patient Stratification Analysis Agent"
AGENT_TYPE = "orchestrator"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class PatientStratificationAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.agent_name = AGENT_NAME
        self.agent_type = AGENT_TYPE
        self.logic = PatientStratificationAgentLogic(agent_id=self.agent_id, logger_instance=logger)

        # Define capabilities for discovery service
        self.capabilities = [
            {
                "name": "predict_approval_likelihood",
                "description": "Orchestrate comprehensive PA approval prediction using multiple data sources",
                "parameters": {
                    "patient_id": "string (required)",
                    "drug_name": "string (required)",
                    "insurer_id": "string (required)",
                    "urgency": "string (optional, default='routine', options: 'routine', 'urgent', 'stat')",
                },
            },
            {
                "name": "analyze_pa_case",
                "description": "Perform detailed PA case analysis without prediction",
                "parameters": {
                    "patient_id": "string (required)",
                    "drug_name": "string (required)",
                    "insurer_id": "string (required)",
                },
            },
            {
                "name": "get_decision_explanation",
                "description": "Get detailed explanation for a previous PA decision",
                "parameters": {"decision_id": "string (required)"},
            },
            {
                "name": "validate_pa_request",
                "description": "Validate if PA request has all required information",
                "parameters": {
                    "patient_id": "string (required)",
                    "drug_name": "string (required)",
                    "insurer_id": "string (required)",
                },
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

        # Performance tracking
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time = datetime.now(timezone.utc)

        self.running = False
        logger.info(f"PatientStratificationAgent initialized: {self.agent_id}")

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
                # Respond to ping with stats
                await self.mcp_client.send_message(
                    payload={
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "status": "healthy",
                        "requests_processed": self.request_count,
                        "success_rate": self.success_count / max(self.request_count, 1),
                    },
                    message_type="PONG",
                    target_agent_id=sender_id,
                    correlation_id=correlation_id,
                )
            elif msg_type == "METRICS_REQUEST":
                await self.handle_metrics_request(message)
            elif msg_type == "INFO_REQUEST":
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
        task_name = payload.get("task_name", "").lower()

        logger.info(f"Processing task {task_id} ({task_name}) for workflow {workflow_id}")
        self.request_count += 1

        try:
            result = None

            if "predict" in task_name or "approval" in task_name:
                result = await self._handle_predict_approval(payload)
            elif "analyze" in task_name:
                result = await self._handle_analyze_case(payload)
            elif "explain" in task_name:
                result = await self._handle_get_explanation(payload)
            elif "validate" in task_name:
                result = await self._handle_validate_request(payload)
            else:
                result = {
                    "status": "error",
                    "message": f"Unknown task type: {task_name}",
                }

            # Send response based on result status
            if result.get("status") == "success":
                self.success_count += 1
                response_type = "TASK_COMPLETE"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "status": "COMPLETED",
                    "result": result,
                }
            else:
                self.error_count += 1
                response_type = "TASK_FAIL"
                response_payload = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": result.get("message", "Task processing failed"),
                    "error_details": result.get("details"),
                }

            await self.mcp_client.send_message(
                payload=response_payload,
                message_type=response_type,
                target_agent_id=sender_id,
                correlation_id=correlation_id,
            )

            logger.info(f"Task {task_id} completed with status: {result.get('status')}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            self.error_count += 1

            await self.mcp_client.send_message(
                payload={
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "error_message": str(e),
                    "error_type": type(e).__name__,
                },
                message_type="TASK_FAIL",
                target_agent_id=sender_id,
                correlation_id=correlation_id,
            )

    async def _handle_predict_approval(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approval prediction request"""
        patient_id = payload.get("patient_id")
        drug_name = payload.get("drug_name")
        insurer_id = payload.get("insurer_id")
        urgency = payload.get("urgency", "routine")

        if not all([patient_id, drug_name, insurer_id]):
            return {
                "status": "error",
                "message": "Missing required parameters: patient_id, drug_name, and insurer_id",
            }

        return await self.logic.predict_approval_likelihood(
            patient_id, drug_name, insurer_id, urgency
        )

    async def _handle_analyze_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case analysis without prediction"""
        # Similar to predict but without LLM synthesis
        # This would be implemented in the logic class
        return {
            "status": "success",
            "message": "Case analysis not yet implemented",
            "placeholder": True,
        }

    async def _handle_get_explanation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle decision explanation request"""
        decision_id = payload.get("decision_id")

        if not decision_id:
            return {
                "status": "error",
                "message": "Missing required parameter: decision_id",
            }

        # This would retrieve stored decision details
        return {
            "status": "success",
            "message": "Decision explanation not yet implemented",
            "decision_id": decision_id,
            "placeholder": True,
        }

    async def _handle_validate_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PA request validation"""
        # This would check if all required data is available
        return {
            "status": "success",
            "message": "Request validation not yet implemented",
            "placeholder": True,
        }

    async def handle_metrics_request(self, message: MCPMessage) -> None:
        """Handle metrics request"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id

        uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        metrics = {
            "agent_id": self.agent_id,
            "uptime_seconds": uptime_seconds,
            "total_requests": self.request_count,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "success_rate": self.success_count / max(self.request_count, 1),
            "average_requests_per_minute": (self.request_count / uptime_seconds) * 60
            if uptime_seconds > 0
            else 0,
            "logic_metrics": self.logic.metrics,
            "cache_stats": {
                "decision_cache_size": len(self.logic.decision_cache),
                "evidence_cache_size": len(self.logic.evidence_cache),
            },
        }

        await self.mcp_client.send_message(
            payload=metrics,
            message_type="METRICS_RESPONSE",
            target_agent_id=sender_id,
            correlation_id=correlation_id,
        )

    async def handle_info_request(self, message: MCPMessage) -> None:
        """Handle information request"""
        correlation_id = message.mcp_header.correlation_id
        sender_id = message.mcp_header.sender_id
        payload = message.payload

        info_type = payload.get("info_type", "general")

        if info_type == "general":
            info = {
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "agent_type": self.agent_type,
                "capabilities": self.capabilities,
                "description": "Advanced PA decision orchestrator using multi-agent synthesis",
                "version": "2.0.0",
                "dependencies": [
                    "patient_data_agent",
                    "guideline_agent",
                    "policy_analysis_agent",
                    "drugbank_agent",
                ],
            }
        elif info_type == "configuration":
            info = {
                "config": self.logic.config,
                "evidence_weights": self.logic.evidence_weights,
                "llm_models": {"primary": "gpt-4-turbo", "fallback": "gpt-3.5-turbo"},
            }
        elif info_type == "performance":
            info = {
                "average_processing_time_ms": self.logic.metrics.get("average_processing_time", 0),
                "cache_hit_rate": self.logic.metrics["cache_hits"]
                / max(
                    self.logic.metrics["cache_hits"] + self.logic.metrics["cache_misses"],
                    1,
                ),
                "total_llm_tokens": self.logic.metrics["total_llm_tokens"],
                "decisions_by_type": self._count_decisions_by_type(),
            }
        else:
            info = {"error": f"Unknown info_type: {info_type}"}

        await self.mcp_client.send_message(
            payload=info,
            message_type="INFO_RESPONSE",
            target_agent_id=sender_id,
            correlation_id=correlation_id,
        )

    def _count_decisions_by_type(self) -> Dict[str, int]:
        """Count cached decisions by type"""
        counts = {"Approve": 0, "Deny": 0, "Pend": 0}
        for decision_data in self.logic.decision_cache.values():
            decision = decision_data.get("decision", "Pend")
            if decision in counts:
                counts[decision] += 1
        return counts

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
            logger.info(f"Configuration: {json.dumps(self.logic.config, indent=2)}")
            logger.info(f"Evidence weights: {json.dumps(self.logic.evidence_weights, indent=2)}")

            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)

                # Periodic health check
                if int(datetime.now().timestamp()) % 60 == 0:
                    logger.debug(
                        f"Health check - Requests: {self.request_count}, Success rate: {self.success_count/max(self.request_count, 1):.2%}"
                    )

        except Exception as e:
            logger.error(f"Error starting agent: {e}", exc_info=True)
            self.running = False

    async def stop(self) -> None:
        """Stop the agent"""
        logger.info(f"Stopping {self.agent_name}...")
        self.running = False

        try:
            # Log final metrics
            logger.info(
                f"Final metrics - Total: {self.request_count}, Success: {self.success_count}, Errors: {self.error_count}"
            )
            logger.info(f"Logic metrics: {json.dumps(self.logic.metrics, indent=2)}")

            # Unregister from discovery service
            await self.mcp_client.send_message(
                payload={
                    "agent_id": self.agent_id,
                    "reason": "Graceful shutdown",
                    "final_metrics": {
                        "total_requests": self.request_count,
                        "success_rate": self.success_count / max(self.request_count, 1),
                    },
                },
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
    agent = PatientStratificationAgent()

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
        # Run a quick test
        logger.info("Running in test mode...")
        test_agent = PatientStratificationAgent()

        # Test prediction
        import asyncio

        async def test():
            result = await test_agent.logic.predict_approval_likelihood(
                "patient-001", "Empagliflozin", "UHC", "routine"
            )
            logger.info(f"Test result: {json.dumps(result, indent=2)}")

        asyncio.run(test())
    else:
        # Normal operation
        asyncio.run(main())
