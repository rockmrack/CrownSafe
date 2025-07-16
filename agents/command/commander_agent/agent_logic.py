# C:\Users\rossd\Downloads\RossNetAgents\commander_agent_01\logic.py
# Version: Enhanced-CommanderAgent-With-MemoryManager-V2.0-FIXED
# Enhanced: Integrated with EnhancedMemoryManager V2.0 for advanced memory features

import asyncio
import uuid
import json
import copy
import traceback
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, Any, Optional, List, Tuple, Set, Deque
from collections import deque, defaultdict 
from enum import Enum

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage

# Enhanced Memory integration
try:
    from core_infra.enhanced_memory_manager import EnhancedMemoryManager
    ENHANCED_MEMORY_AVAILABLE = True
except ImportError:
    try:
        # Fallback to standard memory manager
        from core_infra.memory_manager import MemoryManager as EnhancedMemoryManager
        ENHANCED_MEMORY_AVAILABLE = False
    except ImportError:
        EnhancedMemoryManager = None
        ENHANCED_MEMORY_AVAILABLE = False

# Constants from your "Critical-Fixes" version
PLANNER_CAPABILITIES = ["planning", "llm_plan_generation"]
ROUTER_CAPABILITIES = ["routing", "workflow_orchestration"]
MAX_REQUEST_HISTORY_SIZE = 100
DEFAULT_WORKFLOW_TIMEOUT_MINUTES = 30
MAX_AGENT_FAILURES = 3
AGENT_FAILURE_RESET_HOURS = 1

class WorkflowStatus(Enum):
    RECEIVED_USER_REQUEST = "RECEIVED_USER_REQUEST"
    PENDING_PLANNER_DISCOVERY = "PENDING_PLANNER_DISCOVERY"
    PLANNER_DISCOVERED = "PLANNER_DISCOVERED"
    PLANNING_DELEGATED = "PLANNING_DELEGATED"
    PENDING_ROUTER_DISCOVERY = "PENDING_ROUTER_DISCOVERY"
    ROUTER_DISCOVERED = "ROUTER_DISCOVERED"
    ROUTING_DELEGATED = "ROUTING_DELEGATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class MessageType(Enum):
    PROCESS_USER_REQUEST = "PROCESS_USER_REQUEST"
    DISCOVERY_RESPONSE = "DISCOVERY_RESPONSE"
    TASK_COMPLETE = "TASK_COMPLETE"
    TASK_FAIL = "TASK_FAIL"
    TASK_ASSIGN = "TASK_ASSIGN"
    DISCOVERY_ACK = "DISCOVERY_ACK"
    PONG = "PONG"

class CommanderLogic:
    def __init__(self, agent_id: str, mcp_client: MCPClient, logger: logging.Logger):
        self.agent_id = agent_id
        self.mcp_client = mcp_client
        self.logger = logger
        self.ongoing_requests: Dict[str, Dict[str, Any]] = {}
        self.request_history: Deque[Tuple[str, Dict[str, Any]]] = deque(maxlen=MAX_REQUEST_HISTORY_SIZE)
        
        self.agent_failure_counts: Dict[str, int] = defaultdict(int)
        self.agent_failure_timestamps: Dict[str, datetime] = {}
        self.workflow_timeout_minutes = DEFAULT_WORKFLOW_TIMEOUT_MINUTES
        
        # Initialize Enhanced Memory Manager
        self.memory_manager = None
        self.enhanced_features_available = False
        
        if EnhancedMemoryManager:
            try:
                self.memory_manager = EnhancedMemoryManager()
                if hasattr(self.memory_manager, 'collection') and self.memory_manager.collection:
                    if ENHANCED_MEMORY_AVAILABLE:
                        self.logger.info("EnhancedMemoryManager V2.0 integrated successfully - ADVANCED MEMORY FEATURES ENABLED!")
                        self.enhanced_features_available = True
                        
                        # Check for enhanced features
                        if hasattr(self.memory_manager, 'temporal_patterns'):
                            self.logger.info("Temporal pattern analysis available")
                        if hasattr(self.memory_manager, 'contradictions'):
                            self.logger.info("Contradiction detection available")
                        if hasattr(self.memory_manager, 'research_gaps'):
                            self.logger.info("Research gap identification available")
                        if hasattr(self.memory_manager, 'cross_workflow_insights'):
                            self.logger.info("Cross-workflow insights available")
                    else:
                        self.logger.info("Standard MemoryManager (MVP-1.4) integrated successfully")
                        self.enhanced_features_available = False
                else:
                    self.logger.error("CommanderLogic: MemoryManager failed to initialize ChromaDB collection. Memory features disabled.")
                    self.memory_manager = None
            except Exception as e_mm_init:
                self.logger.error(f"CommanderLogic: Exception during MemoryManager instantiation: {e_mm_init}", exc_info=True)
                self.memory_manager = None
        else:
            self.logger.warning("MemoryManager not available - memory features disabled")

        memory_status = "ENHANCED V2.0" if self.enhanced_features_available else ("STANDARD MVP-1.4" if self.memory_manager else "NOT LOADED")
        self.logger.info(f"CommanderLogic initialized for agent_id '{agent_id}' with MemoryManager: {memory_status}")

    def _validate_message_structure(self, message: MCPMessage) -> tuple[bool, Optional[str]]:
        if not message: return False, "Message is None"
        if not message.mcp_header: return False, "Message header is missing"
        if not hasattr(message, 'payload') or message.payload is None: return False, "Message payload is missing"
        if not isinstance(message.payload, dict): return False, f"Payload must be dict, got {type(message.payload)}"
        return True, None

    def _validate_payload(self, payload: Any, context: str) -> bool:
        if not isinstance(payload, dict):
            self.logger.error(f"Invalid payload in {context}: Expected dict, got {type(payload)}")
            return False
        return True

    def _format_goal_for_display(self, goal: str, max_length: int = 100) -> str:
        if not goal: return "EMPTY_GOAL"
        return goal if len(goal) <= max_length else f"{goal[:max_length]}..."

    def _is_agent_circuit_broken(self, agent_id: str) -> bool:
        if agent_id not in self.agent_failure_counts: return False
        failure_count = self.agent_failure_counts[agent_id]
        if failure_count < MAX_AGENT_FAILURES: return False
        last_failure = self.agent_failure_timestamps.get(agent_id)
        if last_failure and (datetime.now(timezone.utc) - last_failure) > timedelta(hours=AGENT_FAILURE_RESET_HOURS):
            self.agent_failure_counts[agent_id] = 0; 
            if agent_id in self.agent_failure_timestamps: del self.agent_failure_timestamps[agent_id]
            self.logger.info(f"Circuit breaker reset for agent {agent_id}"); return False
        return True

    def _record_agent_failure(self, agent_id: str):
        self.agent_failure_counts[agent_id] += 1
        self.agent_failure_timestamps[agent_id] = datetime.now(timezone.utc)
        self.logger.warning(f"Agent {agent_id} failure count: {self.agent_failure_counts[agent_id]}")

    def _create_workflow_state(self, user_goal: str) -> Dict[str, Any]:
        timeout_time = datetime.now(timezone.utc) + timedelta(minutes=self.workflow_timeout_minutes)
        return {"status": WorkflowStatus.RECEIVED_USER_REQUEST.value, "user_goal": user_goal, "plan": None,
                "final_result": None, "error": None, "planner_discovery_corr_id": None,
                "router_discovery_corr_id": None, "target_planner_id": None, "target_router_id": None,
                "request_time": datetime.now(timezone.utc).isoformat(), 
                "completion_time": None,
                "timeout_time": timeout_time.isoformat(),
                "events": [], "enhanced_memory_used": self.enhanced_features_available}

    async def _send_mcp_message(self, message_type: str, payload: Dict[str, Any], target_agent_id: str, correlation_id: Optional[str] = None) -> bool:
        if not target_agent_id or not isinstance(target_agent_id, str) or not target_agent_id.strip():
            self.logger.error(f"Cannot send {message_type}: Invalid target_agent_id '{target_agent_id}' (CorrID: {correlation_id})")
            return False
        if self._is_agent_circuit_broken(target_agent_id):
            self.logger.error(f"Cannot send {message_type} to {target_agent_id}: Circuit breaker active (CorrID: {correlation_id})")
            return False
        try:
            await self.mcp_client.send_message(message_type=message_type, payload=payload, target_agent_id=target_agent_id, correlation_id=correlation_id)
            self.logger.debug(f"Sent {message_type} to {target_agent_id} (CorrID: {correlation_id})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send {message_type} to {target_agent_id} (CorrID: {correlation_id}): {e}", exc_info=True)
            self._record_agent_failure(target_agent_id)
            return False

    async def _query_discovery_service(self, capabilities: List[str], workflow_correlation_id: str, discovery_type: str) -> Optional[str]:
        """Helper to query discovery service with comprehensive error handling"""
        request_state = self.ongoing_requests.get(workflow_correlation_id)
        if not request_state:
            self.logger.error(f"Cannot query discovery for {discovery_type}: Workflow {workflow_correlation_id} not found")
            return None
        try:
            discovery_query_correlation_id = await self.mcp_client.query_discovery(capabilities)
            if discovery_query_correlation_id:
                request_state[f"{discovery_type.lower()}_discovery_corr_id"] = discovery_query_correlation_id
                self.logger.debug(f"Discovery query sent for {discovery_type}. Workflow: {workflow_correlation_id}, Discovery Query: {discovery_query_correlation_id}")
                self._record_event(workflow_correlation_id, f"{discovery_type} discovery initiated", {"discovery_query_id": discovery_query_correlation_id})
                return discovery_query_correlation_id
            else:
                error_msg = f"Failed {discovery_type.lower()} discovery: No correlation_id returned by MCPClient"
                self.logger.error(f"{error_msg} (Workflow: {workflow_correlation_id})")
                await self._fail_request(workflow_correlation_id, error_msg)
                return None
        except Exception as e:
            error_msg = f"Exception during {discovery_type.lower()} discovery query: {e}"
            self.logger.error(f"Exception in discovery query for {discovery_type} (Workflow: {workflow_correlation_id}): {e}", exc_info=True)
            await self._fail_request(workflow_correlation_id, error_msg)
            return None

    async def process_message(self, message: MCPMessage) -> Optional[Dict[str, Any]]:
        is_valid, error_msg = self._validate_message_structure(message)
        if not is_valid: self.logger.error(f"Invalid message structure: {error_msg}"); return None
        
        msg_type_str = message.mcp_header.message_type
        payload = message.payload
        header_correlation_id = message.mcp_header.correlation_id
        header_sender_id = message.mcp_header.sender_id

        try:
            msg_type = MessageType(msg_type_str)
        except ValueError:
            self.logger.warning(f"Received unknown message type '{msg_type_str}' from '{header_sender_id}'. Ignoring.")
            return None

        if msg_type == MessageType.PONG:
            self.logger.debug(f"Received PONG from '{header_sender_id}' (CorrID: {header_correlation_id})")
            return None

        self.logger.info(f"Processing {msg_type.value} from '{header_sender_id}' (CorrID: {header_correlation_id})")
        if not self._validate_payload(payload, f"{msg_type.value} processing"): return None

        try:
            # CRITICAL FIX: Pass correlation_id to _handle_user_request
            if msg_type == MessageType.PROCESS_USER_REQUEST: await self._handle_user_request(payload, header_correlation_id)
            elif msg_type == MessageType.DISCOVERY_RESPONSE:
                if not header_correlation_id: self.logger.error(f"DISCOVERY_RESPONSE from '{header_sender_id}' missing correlation_id"); return None
                await self._handle_discovery_result(payload, header_correlation_id)
            elif msg_type in [MessageType.TASK_COMPLETE, MessageType.TASK_FAIL]:
                if not header_correlation_id: self.logger.error(f"{msg_type.value} from '{header_sender_id}' missing correlation_id"); return None
                if not header_sender_id or not header_sender_id.strip(): self.logger.error(f"{msg_type.value} (CorrID: {header_correlation_id}) missing sender_id"); return None
                await self._handle_task_update(msg_type.value, header_correlation_id, payload, header_sender_id)
            elif msg_type == MessageType.DISCOVERY_ACK:
                self.logger.info(f"Received DISCOVERY_ACK from '{header_sender_id}' (CorrID: {header_correlation_id})")
            else:
                self.logger.warning(f"Unhandled message type enum '{msg_type.value}' from '{header_sender_id}'")
        except Exception as e:
            self.logger.error(f"Error processing {msg_type.value} from '{header_sender_id}': {e}", exc_info=True)
            await self._handle_processing_error(msg_type.value, header_correlation_id, e)
        return None

    async def _handle_processing_error(self, msg_type_str: str, header_correlation_id: Optional[str], error: Exception):
        workflow_cid_to_fail = header_correlation_id
        if msg_type_str == MessageType.DISCOVERY_RESPONSE.value and header_correlation_id:
            for cid, state in self.ongoing_requests.items():
                if (state.get("planner_discovery_corr_id") == header_correlation_id or state.get("router_discovery_corr_id") == header_correlation_id):
                    workflow_cid_to_fail = cid; break
        if workflow_cid_to_fail and workflow_cid_to_fail in self.ongoing_requests:
            await self._fail_request(workflow_cid_to_fail, f"Internal error processing {msg_type_str}: {error}")

    # CRITICAL FIX: Accept correlation_id parameter
    async def _handle_user_request(self, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        user_goal = payload.get("goal")
        if not user_goal or not isinstance(user_goal, str) or not user_goal.strip(): self.logger.error(f"Invalid user request goal: {payload}"); return
        # CRITICAL FIX: Use provided correlation_id instead of generating new one
        workflow_correlation_id = correlation_id or str(uuid.uuid4())
        goal_display = self._format_goal_for_display(user_goal)
        self.logger.info(f"New user request: '{goal_display}' (Workflow: {workflow_correlation_id})")
        self.ongoing_requests[workflow_correlation_id] = self._create_workflow_state(user_goal)
        self._record_event(workflow_correlation_id, "User request received", {"goal": user_goal, "enhanced_memory": self.enhanced_features_available})
        self.ongoing_requests[workflow_correlation_id]["status"] = WorkflowStatus.PENDING_PLANNER_DISCOVERY.value
        await self._query_discovery_service(PLANNER_CAPABILITIES, workflow_correlation_id, "Planner")

    async def _handle_discovery_result(self, discovery_payload: Dict[str, Any], discovery_query_correlation_id: str):
        self.logger.debug(f"Processing DISCOVERY_RESPONSE for query {discovery_query_correlation_id}")
        workflow_correlation_id, pending_type = self._find_workflow_for_discovery(discovery_query_correlation_id)
        if not workflow_correlation_id or not pending_type: self.logger.warning(f"DISCOVERY_RESPONSE for unknown query {discovery_query_correlation_id}"); return
        request_state = self.ongoing_requests.get(workflow_correlation_id)
        if not request_state: self.logger.error(f"Workflow {workflow_correlation_id} not found in ongoing_requests for discovery result"); return
        self.logger.info(f"Matched DISCOVERY_RESPONSE to {pending_type} for workflow {workflow_correlation_id}")
        target_agent_id = await self._process_discovery_results(discovery_payload, workflow_correlation_id, pending_type)
        if not target_agent_id: return
        if pending_type == "PLANNER":
            request_state["target_planner_id"] = target_agent_id; request_state["status"] = WorkflowStatus.PLANNER_DISCOVERED.value
            await self._delegate_planning(workflow_correlation_id, request_state, target_agent_id)
        elif pending_type == "ROUTER":
            request_state["target_router_id"] = target_agent_id; request_state["status"] = WorkflowStatus.ROUTER_DISCOVERED.value
            await self._delegate_execution(workflow_correlation_id, request_state, target_agent_id)

    def _find_workflow_for_discovery(self, discovery_query_correlation_id: str) -> Tuple[Optional[str], Optional[str]]:
        for cid, state in self.ongoing_requests.items():
            if state.get("planner_discovery_corr_id") == discovery_query_correlation_id: return cid, "PLANNER"
            if state.get("router_discovery_corr_id") == discovery_query_correlation_id: return cid, "ROUTER"
        return None, None

    async def _process_discovery_results(self, discovery_payload: Dict[str, Any], workflow_correlation_id: str, pending_type: str) -> Optional[str]:
        results = discovery_payload.get("results", []); discovery_status = discovery_payload.get("status", "unknown").lower()
        if not isinstance(results, list): results = []
        self._record_event(workflow_correlation_id, f"{pending_type} discovery response received", {"status": discovery_status, "agents_count": len(results)})
        if discovery_status != "success" or not results:
            error_msg = f"No agents found for {pending_type} (Status: {discovery_status}, Count: {len(results)})"
            self.logger.error(f"Discovery failed for {pending_type} (Workflow: {workflow_correlation_id}): {error_msg}"); await self._fail_request(workflow_correlation_id, f"Discovery failed for {pending_type}: {error_msg}"); return None
        active_agents = [agent for agent in results if isinstance(agent, dict) and agent.get("status", "").lower() == "active"]
        if not active_agents:
            error_msg = f"No active agents found for {pending_type} (Workflow: {workflow_correlation_id})"; self.logger.error(error_msg); await self._fail_request(workflow_correlation_id, error_msg); return None
        agent_info = active_agents[0]; target_agent_id = agent_info.get("agent_id")
        if not target_agent_id or not isinstance(target_agent_id, str) or not target_agent_id.strip():
            error_msg = f"Invalid agent_id for {pending_type} from discovery: {agent_info} (Workflow: {workflow_correlation_id})"; self.logger.error(error_msg); await self._fail_request(workflow_correlation_id, error_msg); return None
        if self._is_agent_circuit_broken(target_agent_id):
            error_msg = f"Agent {target_agent_id} circuit breaker active for {pending_type} (Workflow: {workflow_correlation_id})"; self.logger.error(error_msg); await self._fail_request(workflow_correlation_id, error_msg); return None
        self.logger.info(f"Selected active {pending_type} agent: {target_agent_id} for workflow {workflow_correlation_id}"); return target_agent_id

    async def _delegate_planning(self, workflow_correlation_id: str, request_state: Dict[str, Any], target_planner_id: str):
        user_goal = request_state.get("user_goal")
        if not user_goal or not isinstance(user_goal, str) or not user_goal.strip(): await self._fail_request(workflow_correlation_id, "Invalid user goal for planning delegation"); return
        self.logger.info(f"Delegating planning to {target_planner_id} for workflow {workflow_correlation_id}"); assign_payload = {"goal": user_goal}
        if await self._send_mcp_message(MessageType.TASK_ASSIGN.value, assign_payload, target_planner_id, workflow_correlation_id):
            request_state["status"] = WorkflowStatus.PLANNING_DELEGATED.value; self._record_event(workflow_correlation_id, "Planning task delegated", {"target_agent": target_planner_id})
        else: await self._fail_request(workflow_correlation_id, f"Failed to send TASK_ASSIGN to Planner {target_planner_id}")

    async def _delegate_execution(self, workflow_correlation_id: str, request_state: Dict[str, Any], target_router_id: str):
        plan = request_state.get("plan")
        if not plan or not isinstance(plan, dict): await self._fail_request(workflow_correlation_id, "Invalid plan for router execution"); return
        self.logger.info(f"Delegating execution to {target_router_id} for workflow {workflow_correlation_id}"); assign_payload = {"plan": copy.deepcopy(plan)}
        if await self._send_mcp_message(MessageType.TASK_ASSIGN.value, assign_payload, target_router_id, workflow_correlation_id):
            request_state["status"] = WorkflowStatus.ROUTING_DELEGATED.value; self._record_event(workflow_correlation_id, "Execution task delegated", {"target_agent": target_router_id})
        else: await self._fail_request(workflow_correlation_id, f"Failed to send TASK_ASSIGN to Router {target_router_id}")

    async def _handle_task_update(self, message_type_str: str, workflow_correlation_id: str, payload: Dict[str, Any], actual_sender_id: str):
        request_state = self.ongoing_requests.get(workflow_correlation_id)
        if not request_state: self.logger.warning(f"Received {message_type_str} for unknown workflow {workflow_correlation_id} from {actual_sender_id}"); return
        current_status = request_state.get("status", "UNKNOWN")
        self.logger.info(f"Received {message_type_str} for workflow {workflow_correlation_id} from {actual_sender_id} (Current Workflow Status: {current_status})")
        self._record_event(workflow_correlation_id, f"Received {message_type_str}", {"sender": actual_sender_id, "payload_snippet": str(payload)[:100]})
        if message_type_str == MessageType.TASK_COMPLETE.value: await self._handle_task_completion(workflow_correlation_id, request_state, payload, actual_sender_id)
        elif message_type_str == MessageType.TASK_FAIL.value: await self._handle_agent_failure(workflow_correlation_id, request_state, payload, actual_sender_id)

    async def _handle_task_completion(self, workflow_correlation_id: str, request_state: Dict[str, Any], payload: Dict[str, Any], actual_sender_id: str):
        current_status = request_state["status"]; target_planner_id = request_state.get("target_planner_id"); target_router_id = request_state.get("target_router_id")
        if current_status == WorkflowStatus.PLANNING_DELEGATED.value and actual_sender_id == target_planner_id:
            await self._handle_planner_completion(workflow_correlation_id, request_state, payload, actual_sender_id)
        elif current_status == WorkflowStatus.ROUTING_DELEGATED.value and actual_sender_id == target_router_id:
            await self._handle_router_completion(workflow_correlation_id, request_state, payload, actual_sender_id)
        else: self.logger.warning(f"Unexpected TASK_COMPLETE for workflow {workflow_correlation_id} from {actual_sender_id} in status {current_status}. Expected planner: {target_planner_id}, router: {target_router_id}")

    async def _handle_planner_completion(self, workflow_correlation_id: str, request_state: Dict[str, Any], payload: Dict[str, Any], planner_id: str):
        plan = payload.get("plan")
        if not plan or not isinstance(plan, dict): await self._fail_request(workflow_correlation_id, f"Planner {planner_id} provided invalid plan"); return
        self.logger.info(f"Received valid plan from {planner_id} for workflow {workflow_correlation_id}")
        request_state["plan"] = copy.deepcopy(plan); request_state["status"] = WorkflowStatus.PENDING_ROUTER_DISCOVERY.value
        
        # Log enhanced plan features if available
        if plan.get('memory_augmented'):
            strategy = plan.get('research_strategy', 'unknown')
            drug_class = plan.get('drug_intelligence', {}).get('drug_class', 'unknown')
            self.logger.info(f"Received memory-augmented plan with {strategy} strategy for {drug_class}")
            self._record_event(workflow_correlation_id, "Enhanced memory-augmented plan received", {
                "planner_id": planner_id, 
                "plan_id": plan.get("plan_id", "N/A"),
                "strategy": strategy,
                "drug_class": drug_class,
                "enhanced_features": plan.get('enhanced_features', {})
            })
        else:
            self._record_event(workflow_correlation_id, "Plan received from planner", {"planner_id": planner_id, "plan_id": plan.get("plan_id", "N/A")})
        
        await self._query_discovery_service(ROUTER_CAPABILITIES, workflow_correlation_id, "Router")
    
    async def _handle_router_completion(self, workflow_correlation_id: str, request_state: Dict[str, Any], router_payload: Dict[str, Any], router_id: str):
        workflow_status_from_router = router_payload.get("status")
        message_from_router = router_payload.get("message", "Workflow outcome reported by Router.")
        completion_timestamp = datetime.now(timezone.utc).isoformat()

        if workflow_status_from_router == WorkflowStatus.COMPLETED.value:
            self.logger.info(f"Received final TASK_COMPLETE (Workflow COMPLETED) from Router '{router_id}' for Workflow '{workflow_correlation_id}'. Message: {message_from_router}")
            request_state.update({
                "status": WorkflowStatus.COMPLETED.value,
                "final_result": copy.deepcopy(router_payload), 
                "completion_time": completion_timestamp
            })
            self._record_event(workflow_correlation_id, "Workflow completed by Router", {"router_id": router_id, "message": message_from_router})
            
            # Enhanced memory storage
            if self.memory_manager:
                await self._store_workflow_with_enhanced_memory(workflow_correlation_id, request_state, router_payload, completion_timestamp)
            else:
                self.logger.warning(f"MemoryManager not available. Skipping storage for workflow '{workflow_correlation_id}'.")
            
            self._archive_request(workflow_correlation_id)

        elif workflow_status_from_router == WorkflowStatus.FAILED.value:
            error_message_from_router = router_payload.get("message", router_payload.get("error_message", "Router reported workflow failure."))
            self.logger.error(f"Received TASK_COMPLETE (Workflow FAILED) from Router '{router_id}' for Workflow '{workflow_correlation_id}': {error_message_from_router}")
            await self._fail_request(workflow_correlation_id, f"Router Agent '{router_id}' reported workflow failure: {error_message_from_router}")
        else:
            self.logger.warning(f"Router '{router_id}' sent TASK_COMPLETE for Workflow '{workflow_correlation_id}' with unexpected status '{workflow_status_from_router}'. Treating as failure.")
            await self._fail_request(workflow_correlation_id, f"Router '{router_id}' sent TASK_COMPLETE with unclear status '{workflow_status_from_router}'.")

    async def _store_workflow_with_enhanced_memory(self, workflow_correlation_id: str, request_state: Dict[str, Any], router_payload: Dict[str, Any], completion_timestamp: str):
        """Store workflow with enhanced memory features if available"""
        self.logger.info(f"Attempting to store workflow '{workflow_correlation_id}' with {'enhanced' if self.enhanced_features_available else 'standard'} memory features")
        
        try:
            # Prepare workflow data
            user_goal = request_state.get("user_goal", "Unknown Goal")
            plan_data = request_state.get("plan", {})
            
            # Enhanced entity extraction from plan
            extracted_entities = {
                "drug_name": plan_data.get("extracted_drug_name"),
                "disease_name": plan_data.get("extracted_disease_name")
            }
            
            # Add enhanced entities if available
            if plan_data.get("extracted_entities"):
                extracted_entities.update(plan_data["extracted_entities"])
            
            # Extract task results
            task_summary = router_payload.get("task_summary", {})
            pubmed_results_payload = task_summary.get("step1_pubmed_search", {}).get("result")
            clinical_trials_payload = task_summary.get("step2a_find_trials", {}).get("result")
            drug_safety_payload = task_summary.get("step2b_check_drug_safety", {}).get("result")
            report_builder_step_result = task_summary.get("step3_compile_report", {}).get("result", {})
            pdf_path = report_builder_step_result.get("pdf_file_path") if isinstance(report_builder_step_result, dict) else None

            # Validate payloads
            pubmed_results_payload = pubmed_results_payload if isinstance(pubmed_results_payload, dict) else None
            clinical_trials_payload = clinical_trials_payload if isinstance(clinical_trials_payload, dict) else None
            drug_safety_payload = drug_safety_payload if isinstance(drug_safety_payload, dict) else None

            # Prepare enhanced workflow data
            enhanced_workflow_data = {
                "workflow_id": workflow_correlation_id,
                "goal": user_goal,
                "extracted_entities": extracted_entities,
                "plan_metadata": {
                    "memory_augmented": plan_data.get("memory_augmented", False),
                    "research_strategy": plan_data.get("research_strategy", "comprehensive"),
                    "drug_intelligence": plan_data.get("drug_intelligence", {}),
                    "enhanced_features": plan_data.get("enhanced_features", {})
                },
                "research_data": {
                    "pubmed": pubmed_results_payload,
                    "clinical_trials": clinical_trials_payload,
                    "drug_safety": drug_safety_payload
                },
                "pdf_path": pdf_path,
                "completion_timestamp": completion_timestamp,
                "system_metadata": {
                    "enhanced_memory_used": self.enhanced_features_available,
                    "commander_version": "Enhanced-V2.0-FIXED"
                }
            }

            # Use enhanced storage if available
            if self.enhanced_features_available and hasattr(self.memory_manager, 'store_workflow_outputs_enhanced'):
                self.logger.info(f"Using enhanced memory storage for workflow '{workflow_correlation_id}'")
                
                # CRITICAL FIX: Await the async method directly
                storage_result = await self.memory_manager.store_workflow_outputs_enhanced(enhanced_workflow_data)
                
                # Log enhanced storage results
                if isinstance(storage_result, dict):
                    standard_result = storage_result.get("standard_storage", {})
                    temporal_analysis = storage_result.get("temporal_analysis", {})
                    contradiction_detection = storage_result.get("contradiction_detection", {})
                    gap_analysis = storage_result.get("gap_analysis", {})
                    cross_workflow_insights = storage_result.get("cross_workflow_insights", {})
                    
                    self.logger.info(f"Enhanced storage completed for workflow '{workflow_correlation_id}':")
                    self.logger.info(f"  - Standard storage: {standard_result.get('status', 'unknown')}")
                    self.logger.info(f"  - Temporal patterns: {len(temporal_analysis.get('patterns_detected', []))}")
                    self.logger.info(f"  - Contradictions: {len(contradiction_detection.get('contradictions_found', []))}")
                    self.logger.info(f"  - Research gaps: {len(gap_analysis.get('gaps_identified', []))}")
                    self.logger.info(f"  - Cross-workflow insights: {len(cross_workflow_insights.get('insights_generated', []))}")
                    
                    # Record enhanced results in workflow events
                    self._record_event(workflow_correlation_id, "Enhanced memory storage completed", {
                        "temporal_patterns": len(temporal_analysis.get('patterns_detected', [])),
                        "contradictions": len(contradiction_detection.get('contradictions_found', [])),
                        "research_gaps": len(gap_analysis.get('gaps_identified', [])),
                        "insights": len(cross_workflow_insights.get('insights_generated', []))
                    })
                else:
                    self.logger.warning(f"Enhanced storage returned unexpected format for workflow '{workflow_correlation_id}': {type(storage_result)}")
                
            else:
                # Fallback to standard storage
                self.logger.info(f"Using standard memory storage for workflow '{workflow_correlation_id}'")
                
                # Standard storage might still be sync, so use asyncio.to_thread
                await asyncio.to_thread(
                    self.memory_manager.store_workflow_outputs,
                    workflow_id=workflow_correlation_id,
                    user_goal=user_goal,
                    extracted_entities=extracted_entities,
                    pubmed_results_payload=pubmed_results_payload,
                    clinical_trials_payload=clinical_trials_payload,
                    drug_safety_payload=drug_safety_payload,
                    pdf_path=pdf_path,
                    completion_timestamp=completion_timestamp
                )
                
                self._record_event(workflow_correlation_id, "Standard memory storage completed", {
                    "storage_type": "standard_mvp_1.4"
                })
            
            self.logger.info(f"Successfully stored workflow '{workflow_correlation_id}' outputs to memory")
            
        except Exception as e_mem_store:
            self.logger.error(f"Failed to store workflow '{workflow_correlation_id}' outputs to memory: {e_mem_store}", exc_info=True)
            self._record_event(workflow_correlation_id, "Memory storage failed", {"error": str(e_mem_store)})

    async def _handle_agent_failure(self, workflow_correlation_id: str, request_state: Dict[str, Any], payload: Dict[str, Any], sender_id: str):
        error_message = payload.get("error_message", f"Unknown error from {sender_id}")
        self.logger.error(f"Received TASK_FAIL for workflow {workflow_correlation_id} from {sender_id}: {error_message}")
        current_status = request_state["status"]
        if current_status == WorkflowStatus.PLANNING_DELEGATED.value and sender_id == request_state.get("target_planner_id"): fail_reason = f"Planner {sender_id} failed: {error_message}"
        elif current_status == WorkflowStatus.ROUTING_DELEGATED.value and sender_id == request_state.get("target_router_id"): fail_reason = f"Router {sender_id} failed: {error_message}"
        else: fail_reason = f"Agent {sender_id} failed during {current_status}: {error_message}"
        self._record_agent_failure(sender_id); await self._fail_request(workflow_correlation_id, fail_reason)

    async def _fail_request(self, workflow_correlation_id: str, error_message: str):
        request_state = self.ongoing_requests.get(workflow_correlation_id)
        if not request_state: self.logger.warning(f"Attempted to fail unknown workflow {workflow_correlation_id}: {error_message}"); return
        if request_state.get("status") != WorkflowStatus.FAILED.value: request_state["status"] = WorkflowStatus.FAILED.value
        request_state["error"] = error_message; request_state["completion_time"] = datetime.now(timezone.utc).isoformat()
        self._record_event(workflow_correlation_id, "Workflow failed", {"error": error_message, "final_status": request_state["status"]})
        self.logger.error(f"Workflow {workflow_correlation_id} FAILED: {error_message}"); self._archive_request(workflow_correlation_id)

    def _record_event(self, workflow_correlation_id: str, event_name: str, details: Optional[Dict[str, Any]] = None):
        request_state = self.ongoing_requests.get(workflow_correlation_id)
        if request_state:
            event_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event_name, "details": details or {}}
            request_state.setdefault("events", []).append(event_entry)
            self.logger.debug(f"Event recorded for workflow {workflow_correlation_id}: {event_name}")

    def _archive_request(self, workflow_correlation_id: str):
        if workflow_correlation_id in self.ongoing_requests:
            state_to_archive = copy.deepcopy(self.ongoing_requests[workflow_correlation_id])
            self.logger.info(f"Archiving workflow {workflow_correlation_id} (Status: {state_to_archive.get('status')})")
            self.request_history.append((workflow_correlation_id, state_to_archive))
            del self.ongoing_requests[workflow_correlation_id]
            self.logger.debug(f"Workflow archived. Active: {len(self.ongoing_requests)}, History: {len(self.request_history)}")

    async def check_timeouts(self):
        current_time = datetime.now(timezone.utc); timed_out_workflows = []
        for workflow_id, state in list(self.ongoing_requests.items()): 
            timeout_str = state.get("timeout_time")
            if timeout_str:
                try:
                    timeout_time = datetime.fromisoformat(timeout_str.replace('Z', '+00:00'))
                    if current_time > timeout_time: 
                        if workflow_id in self.ongoing_requests:
                            timed_out_workflows.append(workflow_id)
                except ValueError: self.logger.warning(f"Invalid timeout format for workflow {workflow_id}: {timeout_str}")
        
        for workflow_id in timed_out_workflows:
            if workflow_id in self.ongoing_requests:
                self.logger.warning(f"Workflow {workflow_id} timed out")
                await self._fail_request(workflow_id, f"Workflow timed out after {self.workflow_timeout_minutes} minutes")

    async def shutdown(self):
        self.logger.info(f"CommanderLogic shutting down for agent {self.agent_id}")
        if self.ongoing_requests:
            self.logger.warning(f"Shutting down with {len(self.ongoing_requests)} ongoing workflows")
            workflow_ids_to_fail = list(self.ongoing_requests.keys())
            for wf_id in workflow_ids_to_fail:
                if wf_id in self.ongoing_requests: await self._fail_request(wf_id, "CommanderAgent shutdown - workflow aborted")
        
        if self.memory_manager and hasattr(self.memory_manager, 'shutdown'):
            self.logger.info("Attempting to shut down MemoryManager...")
            try:
                if asyncio.iscoroutinefunction(self.memory_manager.shutdown): await self.memory_manager.shutdown()
                else: self.memory_manager.shutdown()
                self.logger.info("MemoryManager shutdown successfully.")
            except Exception as e_mm_shutdown: self.logger.error(f"Error during MemoryManager shutdown: {e_mm_shutdown}", exc_info=True)
        
        self.logger.info(f"CommanderLogic shutdown complete for {self.agent_id}")

    def get_status_summary(self) -> Dict[str, Any]:
        status_counts = defaultdict(int)
        for state in self.ongoing_requests.values(): status_counts[state.get("status", "UNKNOWN")] += 1
        
        # Enhanced status summary
        summary = {
            "ongoing_workflows": len(self.ongoing_requests), 
            "archived_workflows": len(self.request_history),
            "status_breakdown": dict(status_counts), 
            "failed_agents": dict(self.agent_failure_counts),
            "agent_id": self.agent_id,
            "memory_manager": {
                "available": self.memory_manager is not None,
                "enhanced_features": self.enhanced_features_available,
                "version": "V2.0 Enhanced" if self.enhanced_features_available else ("MVP-1.4 Standard" if self.memory_manager else "Not Available")
            }
        }
        
        return summary