# C:\Users\rossd\Downloads\RossNetAgents\agents\routing\router_agent\agent_logic.py
# MODIFIED: Enhanced dependency handling and message correlation as per Gemini report
# Version: 1.5.3 - Production Ready with workflow_id fix

import asyncio
import json
import uuid
import time
import signal
import sys
import traceback
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, List, Tuple

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPHeader
from core_infra.redis_manager import get_redis_connection
from redis import asyncio as redis

WORKFLOW_STATE_PREFIX = "rossnet:workflow:"
WORKFLOW_TTL_SECONDS = 3600
MAX_RESTART_ATTEMPTS = 5
RESTART_DELAY_BASE = 5  # seconds

# PRODUCTION SETTINGS - Dependencies enabled, debug reduced
DEBUG_MODE = False  # Set to True only for debugging
BYPASS_DEPENDENCIES = False  # FIXED: Dependencies enabled for proper workflow

class RouterLogic:
    def __init__(self, agent_id: str, mcp_client: MCPClient, logger: logging.Logger):
        self.agent_id = agent_id
        self.mcp_client = mcp_client
        self.logger = logger
        self.redis_conn: Optional[redis.Redis] = None
        self.pending_discovery_map: Dict[str, Dict[str, str]] = {}
        self.is_shutting_down = False
        self.restart_count = 0
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 300  # 5 minutes
        
        # Message tracking for debugging
        self.message_counters = {
            "TASK_ASSIGN_SENT": 0,
            "TASK_COMPLETE_RECEIVED": 0,
            "TASK_FAIL_RECEIVED": 0,
            "DISCOVERY_QUERIES_SENT": 0,
            "DISCOVERY_RESPONSES_RECEIVED": 0
        }
        
        # Correlation tracking for better message handling
        self.active_correlations: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info(f"RouterLogic for {self.agent_id} initialized (Production v1.5.3 - Dependencies: {not BYPASS_DEPENDENCIES}).")
        
        asyncio.create_task(self._initialize_redis())
        asyncio.create_task(self._start_health_monitor())

    async def _start_health_monitor(self):
        """Monitor health and restart if needed"""
        while not self.is_shutting_down:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                current_time = time.time()
                
                # Debug: Log message counters periodically
                if DEBUG_MODE and self.message_counters["TASK_ASSIGN_SENT"] > 0:
                    self.logger.info(f"DEBUG_COUNTERS: {self.message_counters}")
                
                # Check if we've been silent too long
                if current_time - self.last_heartbeat > self.connection_timeout:
                    self.logger.error(f"RouterLogic: No heartbeat for {current_time - self.last_heartbeat}s. Connection may be lost.")
                    await self._handle_connection_loss()
                
                # Update heartbeat
                self.last_heartbeat = current_time
                
                # Health check Redis connection
                if self.redis_conn:
                    try:
                        await asyncio.wait_for(self.redis_conn.ping(), timeout=5)
                    except asyncio.TimeoutError:
                        self.logger.error("RouterLogic: Redis ping timeout - attempting reconnection")
                        await self._reconnect_redis()
                    except Exception as e:
                        self.logger.error(f"RouterLogic: Redis health check failed: {e}")
                        await self._reconnect_redis()
                
            except Exception as e:
                self.logger.error(f"RouterLogic: Health monitor error: {e}", exc_info=True)

    async def _handle_connection_loss(self):
        """Handle detected connection loss"""
        if self.is_shutting_down:
            return
            
        self.logger.warning("RouterLogic: Handling connection loss - attempting recovery")
        try:
            await self._reconnect_redis()
            
            if hasattr(self.mcp_client, 'reconnect'):
                await self.mcp_client.reconnect()
            
            self.last_heartbeat = time.time()
            self.logger.info("RouterLogic: Connection recovery successful")
            
        except Exception as e:
            self.logger.error(f"RouterLogic: Connection recovery failed: {e}", exc_info=True)

    async def _reconnect_redis(self):
        """Reconnect to Redis with retry logic"""
        for attempt in range(3):
            try:
                if self.redis_conn:
                    try:
                        await self.redis_conn.close()
                    except:
                        pass
                
                self.redis_conn = await get_redis_connection()
                await self.redis_conn.ping()
                self.logger.info(f"RouterLogic: Redis reconnection successful (attempt {attempt + 1})")
                return
                
            except Exception as e:
                self.logger.error(f"RouterLogic: Redis reconnection attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        
        self.logger.error("RouterLogic: All Redis reconnection attempts failed")
        self.redis_conn = None

    async def _initialize_redis(self):
        """Initialize Redis connection with enhanced error handling"""
        for attempt in range(3):
            try:
                self.redis_conn = await get_redis_connection()
                await self.redis_conn.ping()
                
                test_key = f"router_agent_startup_check:{self.agent_id}:{int(time.time())}"
                test_value = datetime.now(timezone.utc).isoformat()
                await self.redis_conn.set(test_key, test_value)
                
                retrieved_value = await self.redis_conn.get(test_key)
                if retrieved_value:
                    await self.redis_conn.delete(test_key)
                
                self.logger.info(f"RouterLogic: Redis connection fully verified (attempt {attempt + 1})")
                return
                
            except redis.ConnectionError as e:
                self.logger.error(f"RouterLogic: Redis connection failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                self.logger.error(f"RouterLogic: Unexpected Redis error (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
        
        self.logger.error("RouterLogic: Failed to initialize Redis after all attempts")
        self.redis_conn = None

    async def _get_workflow_state(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow state with enhanced error handling"""
        if not self.redis_conn:
            self.logger.error("Cannot get workflow state: Redis unavailable.")
            return None
            
        redis_key = f"{WORKFLOW_STATE_PREFIX}{workflow_id}"
        
        for attempt in range(2):
            try:
                state_json = await asyncio.wait_for(self.redis_conn.get(redis_key), timeout=10)
                
                if state_json:
                    return json.loads(state_json.decode('utf-8') if isinstance(state_json, bytes) else state_json)
                else:
                    self.logger.warning(f"REDIS_GET: Workflow state not found: {redis_key}")
                    return None
                    
            except asyncio.TimeoutError:
                self.logger.error(f"REDIS_GET: Timeout getting key {redis_key} (attempt {attempt + 1})")
                if attempt == 0:
                    await self._reconnect_redis()
            except Exception as e:
                self.logger.error(f"REDIS_GET: Error (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt == 0:
                    await self._reconnect_redis()
        
        return None

    async def _save_workflow_state(self, workflow_id: str, state_dict: Dict[str, Any], set_ttl: bool = False) -> bool:
        """Save workflow state with enhanced error handling"""
        if not self.redis_conn:
            self.logger.error("Cannot save workflow state: Redis unavailable.")
            return False
            
        redis_key = f"{WORKFLOW_STATE_PREFIX}{workflow_id}"
        
        for attempt in range(2):
            try:
                state_json = json.dumps(state_dict)
                
                if set_ttl:
                    await asyncio.wait_for(
                        self.redis_conn.setex(redis_key, WORKFLOW_TTL_SECONDS, state_json), 
                        timeout=10
                    )
                else:
                    await asyncio.wait_for(
                        self.redis_conn.set(redis_key, state_json), 
                        timeout=10
                    )
                
                self.logger.info(f"REDIS_SAVE: Success for workflow {workflow_id}")
                return True
                
            except asyncio.TimeoutError:
                self.logger.error(f"REDIS_SAVE: Timeout saving {workflow_id} (attempt {attempt + 1})")
                if attempt == 0:
                    await self._reconnect_redis()
            except Exception as e:
                self.logger.error(f"REDIS_SAVE: Error (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt == 0:
                    await self._reconnect_redis()
        
        return False

    async def process_message(self, message_data: Dict[str, Any]) -> None:
        """Process message with enhanced error handling and correlation tracking"""
        self.last_heartbeat = time.time()
        
        header_dict = message_data.get("mcp_header", {})
        payload = message_data.get("payload", {})
        message_type = header_dict.get("message_type", "UNKNOWN")
        correlation_id = header_dict.get("correlation_id")

        if message_type not in ["PING", "PONG"]:
            self.logger.info(f"RouterLogic process_message: Type='{message_type}', CorrID='{correlation_id}'")

        try:
            if message_type == "TASK_ASSIGN":
                await self._handle_new_plan(header_dict, payload)
            elif message_type in ["TASK_COMPLETE", "TASK_FAIL"]:
                if message_type == "TASK_COMPLETE":
                    self.message_counters["TASK_COMPLETE_RECEIVED"] += 1
                else:
                    self.message_counters["TASK_FAIL_RECEIVED"] += 1
                await self._handle_subtask_result(message_data)
            elif message_type == "DISCOVERY_RESPONSE":
                self.message_counters["DISCOVERY_RESPONSES_RECEIVED"] += 1
                await self.handle_discovery_result(message_data)
            elif message_type not in ["PING", "PONG", "DISCOVERY_ACK"]:
                self.logger.warning(f"PROCESS_MESSAGE: Unhandled type '{message_type}'")
                
        except Exception as e:
            self.logger.error(f"PROCESS_MESSAGE: Critical error processing {message_type}: {e}", exc_info=True)

    async def _handle_new_plan(self, mcp_header: Dict[str, Any], task_assign_mcp_payload: Dict[str, Any]) -> None:
        """Handle new plan with enhanced validation"""
        self.logger.info("HANDLE_NEW_PLAN: Processing new plan from Commander.")
        
        try:
            plan_data = task_assign_mcp_payload.get("plan")
            workflow_id = mcp_header.get("correlation_id")
            original_requester_id = mcp_header.get("sender_id")

            if not all([plan_data, workflow_id, original_requester_id, isinstance(plan_data, dict)]):
                error_msg = "Invalid/incomplete TASK_ASSIGN - missing required fields"
                self.logger.error(f"HANDLE_NEW_PLAN: {error_msg}")
                
                if workflow_id and original_requester_id:
                    fail_payload = {
                        "workflow_id": workflow_id,
                        "status": "FAILED",
                        "message": error_msg,
                        "task_summary": {}
                    }
                    await self._send_response_to_agent(original_requester_id, "TASK_FAIL", fail_payload, correlation_id=workflow_id)
                return

            self.logger.info(f"HANDLE_NEW_PLAN: Workflow {workflow_id} - Goal: {plan_data.get('workflow_goal')}")
            
            # Initialize workflow state - FIXED: Added workflow_id field
            initial_state = {
                "workflow_id": workflow_id,  # <-- FIX: Added this line
                "original_plan_payload": task_assign_mcp_payload,
                "plan_details": plan_data,
                "status": "RECEIVED",
                "tasks": {},
                "completed_tasks": [],
                "failed_tasks": [],
                "original_requester_id": original_requester_id,
                "controller_correlation_id": workflow_id,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "router_version": "1.5.3"
            }

            # Process plan steps
            plan_steps = plan_data.get("steps", [])
            if not plan_steps:
                error_msg = "Plan contains no executable steps"
                self.logger.error(f"HANDLE_NEW_PLAN: {error_msg}")
                initial_state["status"] = "FAILED"
                initial_state["error_message"] = error_msg
                await self._save_workflow_state(workflow_id, initial_state, set_ttl=True)
                await self._notify_workflow_completion(workflow_id, initial_state)
                return

            # Parse steps
            valid_tasks_count = 0
            for i, step_data in enumerate(plan_steps):
                try:
                    task_id = step_data.get("step_id")
                    capability_required = step_data.get("agent_capability_required")
                    task_description = step_data.get("task_description")
                    parameters = step_data.get("inputs", {})
                    dependencies = step_data.get("dependencies", []) or []

                    if not task_id or not capability_required:
                        self.logger.warning(f"HANDLE_NEW_PLAN: Step {i+1} missing required fields. Skipping.")
                        continue

                    initial_state["tasks"][task_id] = {
                        "task_description": task_description,
                        "capability_required": capability_required,
                        "parameters": parameters,
                        "depends_on": dependencies,
                        "status": "PENDING",
                        "assigned_agent": None,
                        "result": None,
                        "error": None,
                        "retries": 0,
                        "created_time": datetime.now(timezone.utc).isoformat()
                    }
                    valid_tasks_count += 1
                    self.logger.info(f"HANDLE_NEW_PLAN: Added task '{task_id}' with dependencies: {dependencies}")
                    
                except Exception as e:
                    self.logger.error(f"HANDLE_NEW_PLAN: Error processing step {i+1}: {e}")

            if valid_tasks_count == 0:
                error_msg = "No valid tasks could be parsed from the plan"
                self.logger.error(f"HANDLE_NEW_PLAN: {error_msg}")
                initial_state["status"] = "FAILED"
                initial_state["error_message"] = error_msg
            else:
                initial_state["status"] = "RUNNING"
                self.logger.info(f"HANDLE_NEW_PLAN: Parsed {valid_tasks_count} valid tasks")

            # Save initial state
            if not await self._save_workflow_state(workflow_id, initial_state):
                self.logger.error(f"HANDLE_NEW_PLAN: Failed to save initial state for {workflow_id}")
                return

            task_list = list(initial_state['tasks'].keys())
            self.logger.info(f"HANDLE_NEW_PLAN: Workflow {workflow_id} initialized with tasks: {task_list}")
            
            # Start workflow execution
            if initial_state["status"] == "RUNNING":
                await self._check_and_dispatch_pending(workflow_id)
            else:
                await self._notify_workflow_completion(workflow_id, initial_state)

        except Exception as e:
            self.logger.error(f"HANDLE_NEW_PLAN: Critical error: {e}", exc_info=True)

    async def _handle_subtask_result(self, worker_response_message_data: Dict[str, Any]) -> None:
        """Handle subtask result with enhanced correlation tracking"""
        try:
            header = worker_response_message_data.get("mcp_header", {})
            actual_payload = worker_response_message_data.get("payload", {})
            message_type = header.get("message_type")
            subtask_correlation_id = header.get("correlation_id")
            sender_agent_id = header.get("sender_id")
            workflow_id = actual_payload.get("workflow_id")
            task_id = actual_payload.get("task_id")

            self.logger.critical(f"HANDLE_SUBTASK_RESULT: {message_type} for Task='{task_id}', Workflow='{workflow_id}' from Agent='{sender_agent_id}'")

            if not task_id or not workflow_id:
                self.logger.error(f"Missing task/workflow ID in payload: {actual_payload}")
                return

            workflow_state = await self._get_workflow_state(workflow_id)
            if not workflow_state:
                self.logger.error(f"Workflow {workflow_id} not found for subtask result")
                return

            task_state = workflow_state.get("tasks", {}).get(task_id)
            if not task_state:
                self.logger.error(f"Task {task_id} not found in workflow {workflow_id}")
                return

            # Validate correlation ID matches expected
            expected_correlation = task_state.get("sub_task_correlation_id")
            if expected_correlation and expected_correlation != subtask_correlation_id:
                self.logger.warning(f"Correlation ID mismatch for task {task_id}. Expected: {expected_correlation}, Got: {subtask_correlation_id}")

            # Update task state based on result
            if message_type == "TASK_COMPLETE":
                task_state["status"] = "COMPLETED"
                task_state["result"] = actual_payload.get("result")
                task_state["error"] = None
                task_state["completion_time"] = datetime.now(timezone.utc).isoformat()
                
                completed_tasks = workflow_state.setdefault("completed_tasks", [])
                if task_id not in completed_tasks:
                    completed_tasks.append(task_id)
                    
                self.logger.critical(f"TASK_COMPLETED: Task {task_id} completed successfully")

            elif message_type == "TASK_FAIL":
                task_state["status"] = "FAILED"
                task_state["error"] = actual_payload.get("error_message", "Unknown worker error")
                task_state["result"] = None
                task_state["failure_time"] = datetime.now(timezone.utc).isoformat()
                
                failed_tasks = workflow_state.setdefault("failed_tasks", [])
                if task_id not in failed_tasks:
                    failed_tasks.append(task_id)
                    
                self.logger.error(f"TASK_FAILED: Task {task_id} failed: {task_state['error']}")

            # Save state and continue workflow
            if await self._save_workflow_state(workflow_id, workflow_state):
                # Check for more tasks to dispatch
                await self._check_and_dispatch_pending(workflow_id)
                # Check if workflow is complete
                await self._check_workflow_completion(workflow_id)
            else:
                self.logger.error(f"Failed to save state after task result for {workflow_id}")

        except Exception as e:
            self.logger.error(f"HANDLE_SUBTASK_RESULT: Critical error: {e}", exc_info=True)

    async def handle_discovery_result(self, discovery_response_message_data: Dict[str, Any]) -> None:
        """Handle discovery result with enhanced error handling"""
        try:
            header = discovery_response_message_data.get("mcp_header", {})
            discovery_payload = discovery_response_message_data.get("payload", {})
            discovery_query_correlation_id = header.get("correlation_id")

            self.logger.info(f"HANDLE_DISCOVERY_RESULT: Processing discovery response (QueryCorrID: {discovery_query_correlation_id})")

            if not discovery_query_correlation_id:
                self.logger.error("Missing correlation_id in DISCOVERY_RESPONSE header")
                return

            pending_info = self.pending_discovery_map.pop(discovery_query_correlation_id, None)
            if not pending_info:
                self.logger.warning(f"No pending discovery task for QueryCorrID {discovery_query_correlation_id}")
                return

            workflow_id = pending_info["workflow_id"]
            task_id = pending_info["task_id"]
            
            self.logger.info(f"Matched discovery response to Workflow='{workflow_id}', Task='{task_id}'")

            status = discovery_payload.get("status")
            results = discovery_payload.get("results", [])

            if status != "success" or not results:
                error_msg = f"Discovery failed or no results (Status: {status})"
                self.logger.error(f"{error_msg} for task {task_id}")
                await self._update_task_status(workflow_id, task_id, "FAILED", error=error_msg)
                return

            target_agent_info = self._select_target_agent(results)
            if not target_agent_info:
                error_msg = "Discovery successful but no active agent found"
                self.logger.error(f"{error_msg} for task {task_id}")
                await self._update_task_status(workflow_id, task_id, "FAILED", error=error_msg)
                return

            await self._update_and_dispatch_task(workflow_id, task_id, target_agent_info)

        except Exception as e:
            self.logger.error(f"HANDLE_DISCOVERY_RESULT: Critical error: {e}", exc_info=True)

    async def _check_workflow_completion(self, workflow_id: str) -> None:
        """Check workflow completion with enhanced logging"""
        try:
            workflow_state = await self._get_workflow_state(workflow_id)
            if not workflow_state:
                self.logger.error(f"CHECK_WORKFLOW_COMPLETION: Workflow state {workflow_id} is None")
                return

            if workflow_state.get("status") != "RUNNING":
                return

            all_tasks = workflow_state.get("tasks", {})
            total_tasks = len(all_tasks)
            completed_count = len(workflow_state.get("completed_tasks", []))
            failed_count = len(workflow_state.get("failed_tasks", []))

            self.logger.critical(f"CHECK_WORKFLOW_COMPLETION: Workflow {workflow_id} - Total: {total_tasks}, Completed: {completed_count}, Failed: {failed_count}")

            # Handle edge case of no tasks
            if total_tasks == 0:
                final_status = "FAILED" if workflow_state.get("error_message") else "COMPLETED"
                workflow_state["status"] = final_status
                workflow_state["completion_time"] = datetime.now(timezone.utc).isoformat()
                
                await self._save_workflow_state(workflow_id, workflow_state, set_ttl=True)
                await self._notify_workflow_completion(workflow_id, workflow_state)
                return

            # Check if all tasks are done
            if completed_count + failed_count >= total_tasks:
                final_status = "FAILED" if failed_count > 0 else "COMPLETED"
                workflow_state["status"] = final_status
                workflow_state["completion_time"] = datetime.now(timezone.utc).isoformat()
                
                if final_status == "FAILED" and not workflow_state.get("error_message"):
                    workflow_state["error_message"] = f"Workflow failed - {failed_count} of {total_tasks} tasks failed"

                self.logger.critical(f"CHECK_WORKFLOW_COMPLETION: Workflow {workflow_id} {final_status}")

                await self._save_workflow_state(workflow_id, workflow_state, set_ttl=True)
                await self._notify_workflow_completion(workflow_id, workflow_state)
            else:
                remaining = total_tasks - (completed_count + failed_count)
                self.logger.info(f"CHECK_WORKFLOW_COMPLETION: Workflow {workflow_id} ongoing - {remaining} tasks remaining")

        except Exception as e:
            self.logger.error(f"CHECK_WORKFLOW_COMPLETION: Error checking workflow {workflow_id}: {e}", exc_info=True)

    async def _notify_workflow_completion(self, workflow_id: str, workflow_state: Dict[str, Any]) -> None:
        """Notify workflow completion with enhanced error handling"""
        try:
            self.logger.critical(f"NOTIFY_WORKFLOW_COMPLETION: Workflow {workflow_id} status: {workflow_state.get('status')}")

            original_requester_id = workflow_state.get("original_requester_id")
            reply_correlation_id = workflow_state.get("controller_correlation_id", workflow_id)

            if not original_requester_id:
                self.logger.error(f"No original_requester_id for workflow {workflow_id}")
                return

            status_type = "TASK_COMPLETE" if workflow_state["status"] == "COMPLETED" else "TASK_FAIL"
            
            if workflow_state["status"] == "FAILED":
                message = workflow_state.get("error_message", f"Workflow {workflow_id} failed")
            else:
                message = "Workflow completed successfully"

            # Build task summary
            task_summary = {}
            for task_id, task_data in workflow_state.get("tasks", {}).items():
                task_summary[task_id] = {
                    "status": task_data.get("status"),
                    "result": task_data.get("result"),
                    "error": task_data.get("error")
                }

            final_payload = {
                "workflow_id": workflow_id,
                "status": workflow_state["status"],
                "message": message,
                "task_summary": task_summary
            }

            # Include report result if available
            if (workflow_state["status"] == "COMPLETED" and 
                "step3_compile_report" in task_summary and 
                task_summary["step3_compile_report"].get("status") == "COMPLETED"):
                final_payload["result"] = task_summary["step3_compile_report"].get("result")

            success = await self._send_response_to_agent(
                original_requester_id, status_type, final_payload, correlation_id=reply_correlation_id
            )
            
            if success:
                self.logger.info(f"NOTIFY_WORKFLOW_COMPLETION: Successfully notified {original_requester_id}")
            else:
                self.logger.error(f"NOTIFY_WORKFLOW_COMPLETION: Failed to notify {original_requester_id}")

        except Exception as e:
            self.logger.error(f"NOTIFY_WORKFLOW_COMPLETION: Error: {e}", exc_info=True)

    async def _send_response_to_agent(self, target_agent_id: str, message_type: str, payload: Dict[str, Any], correlation_id: Optional[str] = None) -> bool:
        """Send response with enhanced error handling"""
        if message_type == "TASK_ASSIGN":
            self.message_counters["TASK_ASSIGN_SENT"] += 1
            self.logger.critical(f"ROUTER_AGENT_LOGIC (SEND_RESPONSE): SENDING TASK_ASSIGN: Target='{target_agent_id}', CorrID='{correlation_id}'")
        else:
            self.logger.info(f"SEND_RESPONSE: Sending {message_type} to {target_agent_id} (CorrID: {correlation_id})")

        for attempt in range(2):
            try:
                await asyncio.wait_for(
                    self.mcp_client.send_message(
                        payload=payload, 
                        message_type=message_type, 
                        target_agent_id=target_agent_id, 
                        correlation_id=correlation_id
                    ),
                    timeout=30
                )
                
                self.logger.info(f"SEND_RESPONSE: Successfully sent {message_type} to {target_agent_id}")
                return True
                
            except asyncio.TimeoutError:
                self.logger.error(f"SEND_RESPONSE: Timeout sending {message_type} to {target_agent_id} (attempt {attempt + 1})")
            except Exception as e:
                self.logger.error(f"SEND_RESPONSE: Error sending {message_type} to {target_agent_id} (attempt {attempt + 1}): {e}")
            
            if attempt == 0:
                await asyncio.sleep(2)

        self.logger.error(f"SEND_RESPONSE: Failed to send {message_type} to {target_agent_id} after all attempts")
        return False

    def _select_target_agent(self, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select target agent with enhanced validation"""
        try:
            active_agents = [
                agent for agent in results 
                if isinstance(agent, dict) and agent.get("status", "").lower() == "active"
            ]
            
            if not active_agents:
                self.logger.warning("_select_target_agent: No active agents found")
                return None
                
            selected = active_agents[0]
            self.logger.info(f"_select_target_agent: Selected '{selected.get('agent_id')}' from {len(active_agents)} active agents")
            return selected
            
        except Exception as e:
            self.logger.error(f"_select_target_agent: Error selecting agent: {e}")
            return None

    async def _update_and_dispatch_task(self, workflow_id: str, task_id: str, target_agent_info: Dict[str, Any]) -> None:
        """Update and dispatch task with proper dependency handling - ENHANCED AS PER GEMINI REPORT"""
        try:
            target_agent_id = target_agent_info.get("agent_id")
            self.logger.critical(f"DISPATCH_TASK: Preparing '{task_id}' for '{target_agent_id}' (Workflow: {workflow_id})")

            workflow_state = await self._get_workflow_state(workflow_id)
            if not workflow_state:
                self.logger.error(f"Workflow {workflow_id} not found during dispatch")
                return

            task_info = workflow_state.get("tasks", {}).get(task_id)
            if not task_info:
                self.logger.error(f"Task {task_id} not found during dispatch")
                return

            if task_info.get("status") != "PENDING_DISCOVERY":
                self.logger.warning(f"Task {task_id} not in PENDING_DISCOVERY state: {task_info.get('status')}")
                return

            if not target_agent_id:
                await self._update_task_status(workflow_id, task_id, "FAILED", error="Missing target agent ID")
                return

            # Update task status
            task_info["status"] = "DISPATCHING"
            task_info["assigned_agent"] = target_agent_id
            task_info["dispatch_time"] = datetime.now(timezone.utc).isoformat()

            # --- ENHANCED DEPENDENCY GATHERING LOGIC AS PER GEMINI REPORT ---
            dependency_results = {}
            dependencies = task_info.get("depends_on", [])
            self.logger.info(f"DISPATCH_TASK: Task '{task_id}' requires dependencies: {dependencies}")

            for dep_id in dependencies:
                dep_task_state = workflow_state.get("tasks", {}).get(dep_id)
                if not dep_task_state or dep_task_state.get("status") != "COMPLETED":
                    error_msg = f"Dependency '{dep_id}' not completed. Current status: {dep_task_state.get('status', 'UNKNOWN') if dep_task_state else 'UNKNOWN'}"
                    self.logger.error(f"Cannot dispatch '{task_id}': {error_msg}")
                    await self._update_task_status(workflow_id, task_id, "BLOCKED", error=error_msg)
                    return  # Stop dispatching this task

                # The result from a worker is often nested. We extract the core data.
                worker_result = dep_task_state.get("result", {})
                if isinstance(worker_result, dict) and "data" in worker_result:
                    dependency_results[dep_id] = worker_result["data"]
                    self.logger.info(f"DISPATCH_TASK: Added result from '{dep_id}' to dependency context.")
                else:
                    dependency_results[dep_id] = worker_result  # Fallback for simple results
                    self.logger.warning(f"DISPATCH_TASK: Result from '{dep_id}' has no 'data' field. Using entire result.")
            # --- END OF ENHANCED LOGIC ---

            # Save state before dispatch
            await self._save_workflow_state(workflow_id, workflow_state)

            # Create unique correlation ID for this task assignment
            sub_task_correlation_id = f"subtask_{workflow_id}_{task_id}_{str(uuid.uuid4())[:8]}"
            
            # Store correlation for tracking
            task_info["sub_task_correlation_id"] = sub_task_correlation_id
            self.active_correlations[sub_task_correlation_id] = {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "target_agent_id": target_agent_id,
                "dispatch_time": time.time()
            }
            
            # Include dependency results in parameters
            parameters = dict(task_info.get("parameters", {}))  # Make a copy
            parameters["dependency_results"] = dependency_results
            
            # --- GPT RECOMMENDED FIX: UNPACK PARAMETERS AT TOP LEVEL ---
            assign_payload = {
                "task_id": task_id,
                "task_name": task_info.get("task_description"),
                "workflow_id": workflow_id,
                **parameters  # UNPACK parameters at the top level instead of nesting
            }

            self.logger.critical(f"DISPATCH_TASK: Sending TASK_ASSIGN to {target_agent_id} with {len(dependency_results)} dependencies")

            send_success = await self._send_response_to_agent(
                target_agent_id, "TASK_ASSIGN", assign_payload, correlation_id=sub_task_correlation_id
            )

            # Update task status based on send result
            if send_success:
                task_info["status"] = "RUNNING"
                self.logger.critical(f"DISPATCH_TASK: Successfully dispatched {task_id} to {target_agent_id}")
            else:
                task_info["status"] = "FAILED"
                task_info["error"] = f"Failed to send TASK_ASSIGN to {target_agent_id}"
                task_info["retries"] = task_info.get("retries", 0) + 1
                self.logger.error(f"DISPATCH_TASK: Failed to dispatch {task_id} to {target_agent_id}")

            await self._save_workflow_state(workflow_id, workflow_state)
            
            if task_info["status"] == "FAILED":
                await self._check_workflow_completion(workflow_id)

        except Exception as e:
            self.logger.error(f"_update_and_dispatch_task: Error dispatching task {task_id}: {e}", exc_info=True)

    async def _check_and_dispatch_pending(self, workflow_id: str) -> None:
        """Check and dispatch pending tasks with proper dependency handling"""
        try:
            self.logger.info(f"CHECK_AND_DISPATCH: Checking workflow {workflow_id} for pending tasks")
            
            workflow_state = await self._get_workflow_state(workflow_id)
            if not workflow_state or workflow_state.get("status") != "RUNNING":
                return

            tasks_for_discovery: List[Tuple[str, List[str]]] = []
            state_modified = False

            # First pass: Propagate failures from dependencies (if not bypassed)
            if not BYPASS_DEPENDENCIES:
                if self._propagate_dependency_failures(workflow_state):
                    state_modified = True
            
            # Second pass: Find tasks ready for discovery
            for task_id, task_info in workflow_state.get("tasks", {}).items():
                if task_info.get("status") == "PENDING":
                    dependencies = set(task_info.get("depends_on", []))
                    completed_set = set(workflow_state.get("completed_tasks", []))
                    
                    # Check if dependencies are met (or if bypassing)
                    can_dispatch = BYPASS_DEPENDENCIES or dependencies.issubset(completed_set)
                    
                    if can_dispatch:
                        capability = task_info.get("capability_required")
                        if capability:
                            self.logger.critical(f"CHECK_AND_DISPATCH: Task {task_id} ready for discovery")
                            task_info["status"] = "PENDING_DISCOVERY"
                            tasks_for_discovery.append((task_id, [capability]))
                            state_modified = True
                        else:
                            self.logger.error(f"Task {task_id} missing capability_required")
                            task_info["status"] = "FAILED"
                            task_info["error"] = "Missing capability_required"
                            state_modified = True

            # Save state if modified
            if state_modified:
                await self._save_workflow_state(workflow_id, workflow_state)
                
                # Re-check completion in case tasks failed
                await self._check_workflow_completion(workflow_id)
                
                # Re-fetch state if workflow completed
                updated_state = await self._get_workflow_state(workflow_id)
                if not updated_state or updated_state.get("status") != "RUNNING":
                    return

            # Initiate discovery for ready tasks
            if tasks_for_discovery:
                self.logger.critical(f"CHECK_AND_DISPATCH: Initiating discovery for {len(tasks_for_discovery)} tasks: {[t[0] for t in tasks_for_discovery]}")
                
                discovery_tasks = [
                    self._send_discovery_for_task(workflow_id, task_id, capabilities)
                    for task_id, capabilities in tasks_for_discovery
                ]
                
                results = await asyncio.gather(*discovery_tasks, return_exceptions=True)
                
                # Log any discovery failures
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        task_id = tasks_for_discovery[i][0]
                        self.logger.error(f"Discovery failed for task {task_id}: {result}")

                # Final completion check
                await self._check_workflow_completion(workflow_id)

        except Exception as e:
            self.logger.error(f"_check_and_dispatch_pending: Error processing workflow {workflow_id}: {e}", exc_info=True)

    def _propagate_dependency_failures(self, workflow_state: Dict[str, Any]) -> bool:
        """Propagate dependency failures through the workflow"""
        changes_made = True
        total_changes = False
        
        while changes_made:
            changes_made = False
            failed_tasks = set(workflow_state.get("failed_tasks", []))
            
            for task_id, task_info in workflow_state.get("tasks", {}).items():
                if task_info.get("status") == "PENDING":
                    dependencies = set(task_info.get("depends_on", []))
                    
                    if dependencies.intersection(failed_tasks):
                        self.logger.warning(f"Task {task_id} failed due to failed dependencies")
                        task_info["status"] = "FAILED"
                        task_info["error"] = "Failed due to dependency failure"
                        
                        if task_id not in workflow_state.get("failed_tasks", []):
                            workflow_state.setdefault("failed_tasks", []).append(task_id)
                        
                        changes_made = True
                        total_changes = True
        
        return total_changes

    async def _send_discovery_for_task(self, workflow_id: str, task_id: str, capabilities_list: List[str]):
        """Send discovery request for task with enhanced error handling"""
        try:
            self.message_counters["DISCOVERY_QUERIES_SENT"] += 1
            self.logger.critical(f"SEND_DISCOVERY: Task '{task_id}' capabilities {capabilities_list} (Workflow: {workflow_id})")
            
            query_correlation_id = await asyncio.wait_for(
                self.mcp_client.query_discovery(capabilities_list),
                timeout=15
            )
            
            if query_correlation_id:
                self.pending_discovery_map[query_correlation_id] = {
                    "workflow_id": workflow_id,
                    "task_id": task_id,
                    "timestamp": time.time()
                }
                self.logger.info(f"SEND_DISCOVERY: Query sent for task '{task_id}' (QueryCorrID: {query_correlation_id})")
            else:
                error_msg = "Discovery query failed - no correlation ID returned"
                self.logger.error(f"SEND_DISCOVERY: {error_msg} for task {task_id}")
                await self._update_task_status(workflow_id, task_id, "FAILED", error=error_msg)
                
        except asyncio.TimeoutError:
            error_msg = "Discovery query timeout"
            self.logger.error(f"SEND_DISCOVERY: {error_msg} for task {task_id}")
            await self._update_task_status(workflow_id, task_id, "FAILED", error=error_msg)
        except Exception as e:
            error_msg = f"Discovery exception: {str(e)[:100]}"
            self.logger.error(f"SEND_DISCOVERY: {error_msg} for task {task_id}", exc_info=True)
            await self._update_task_status(workflow_id, task_id, "FAILED", error=error_msg)

    async def _update_task_status(self, workflow_id: str, task_id: str, new_status: str, result: Any = None, error: Optional[str] = None):
        """Update task status with enhanced validation"""
        try:
            workflow_state = await self._get_workflow_state(workflow_id)
            if not workflow_state:
                self.logger.error(f"UPDATE_TASK_STATUS: Workflow {workflow_id} not found")
                return

            task_state = workflow_state.get("tasks", {}).get(task_id)
            if not task_state:
                self.logger.error(f"UPDATE_TASK_STATUS: Task {task_id} not found")
                return

            current_status = task_state.get("status")
            
            # Prevent invalid status transitions
            if current_status in ["COMPLETED", "FAILED"] and new_status not in ["COMPLETED", "FAILED"]:
                self.logger.warning(f"UPDATE_TASK_STATUS: Ignoring transition from {current_status} to {new_status} for task {task_id}")
                return

            # Update task state
            task_state["status"] = new_status
            task_state["updated_time"] = datetime.now(timezone.utc).isoformat()
            
            if result is not None:
                task_state["result"] = result
                task_state["error"] = None
                
            if error is not None:
                task_state["error"] = error
                task_state["status"] = "FAILED"
                task_state["result"] = None

            # Update workflow tracking lists
            completed_list = workflow_state.setdefault("completed_tasks", [])
            failed_list = workflow_state.setdefault("failed_tasks", [])

            # Clean up tracking lists
            if task_id in completed_list:
                completed_list.remove(task_id)
            if task_id in failed_list:
                failed_list.remove(task_id)

            # Add to appropriate list
            if task_state["status"] == "COMPLETED":
                completed_list.append(task_id)
            elif task_state["status"] == "FAILED":
                failed_list.append(task_id)

            self.logger.critical(f"UPDATE_TASK_STATUS: Task {task_id} -> {new_status}")

            # Save and check completion
            if await self._save_workflow_state(workflow_id, workflow_state):
                await self._check_workflow_completion(workflow_id)
            else:
                self.logger.error(f"UPDATE_TASK_STATUS: Failed to save state for workflow {workflow_id}")

        except Exception as e:
            self.logger.error(f"UPDATE_TASK_STATUS: Error updating task {task_id}: {e}", exc_info=True)

    async def shutdown(self):
        """Enhanced shutdown with cleanup"""
        self.logger.info(f"RouterLogic {self.agent_id} shutting down...")
        self.is_shutting_down = True
        
        try:
            # Log final statistics
            self.logger.info(f"FINAL_STATS: {self.message_counters}")
                
            # Clean up pending discoveries and correlations
            if self.pending_discovery_map:
                self.logger.info(f"Cleaning up {len(self.pending_discovery_map)} pending discoveries")
                self.pending_discovery_map.clear()
                
            if self.active_correlations:
                self.logger.info(f"Cleaning up {len(self.active_correlations)} active correlations")
                self.active_correlations.clear()

            # Close Redis connection
            if self.redis_conn:
                await self.redis_conn.close()
                self.logger.info("Redis connection closed")

        except Exception as e:
            self.logger.error(f"Error during RouterLogic shutdown: {e}", exc_info=True)
        
        self.logger.info(f"RouterLogic {self.agent_id} shutdown complete")


# RouterAgent Manager remains the same
class RouterAgentManager:
    def __init__(self):
        self.restart_count = 0
        self.should_restart = True
        self.shutdown_requested = False
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\nReceived signal {signum}. Initiating graceful shutdown...")
        self.shutdown_requested = True
        self.should_restart = False
    
    async def run_with_restart(self):
        """Run RouterAgent with auto-restart capability"""
        self.setup_signal_handlers()
        
        while self.should_restart and not self.shutdown_requested:
            try:
                self.restart_count += 1
                print(f"\n=== Starting RouterAgent (Attempt {self.restart_count}) ===")
                
                if self.restart_count > MAX_RESTART_ATTEMPTS:
                    print(f"Maximum restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Stopping.")
                    break
                
                # Run the main RouterAgent logic
                await self._run_router_agent()
                
                # If we get here, it was a clean shutdown
                print("RouterAgent stopped cleanly")
                break
                
            except KeyboardInterrupt:
                print("Keyboard interrupt received. Stopping restart loop.")
                self.should_restart = False
                break
                
            except Exception as e:
                print(f"RouterAgent crashed (attempt {self.restart_count}): {e}")
                print(f"Full traceback:\n{traceback.format_exc()}")
                
                if self.restart_count < MAX_RESTART_ATTEMPTS and not self.shutdown_requested:
                    delay = RESTART_DELAY_BASE * self.restart_count
                    print(f"Restarting in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    print("Not restarting due to shutdown request or max attempts reached")
                    break
        
        print("RouterAgent restart loop ended")
    
    async def _run_router_agent(self):
        """Run the actual RouterAgent - replace this with your existing main logic"""
        # Import your existing RouterAgent main logic here
        from agents.routing.router_agent.main import main as router_main
        await router_main()


# If this file is run directly, start the enhanced RouterAgent
if __name__ == "__main__":
    async def main():
        manager = RouterAgentManager()
        await manager.run_with_restart()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("RouterAgent manager stopped by user")
    except Exception as e:
        print(f"RouterAgent manager failed: {e}")
        sys.exit(1)