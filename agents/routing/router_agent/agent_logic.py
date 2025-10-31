# agents/routing/router_agent/agent_logic.py
# Version: 2.4-BABYSHIELD (Fixed to handle both 'result' and 'data' keys from agents)
import asyncio
import json
import logging
from typing import Any, Dict, Optional

# --- Agent Logic Imports ---
AGENT_LOGIC_CLASSES = {}
try:
    from agents.product_identifier_agent.agent_logic import ProductIdentifierLogic

    AGENT_LOGIC_CLASSES["identify_product"] = ProductIdentifierLogic
except ImportError:
    ProductIdentifierLogic = None
try:
    from agents.recall_data_agent.agent_logic import RecallDataAgentLogic

    AGENT_LOGIC_CLASSES["query_recalls_by_product"] = RecallDataAgentLogic
except ImportError:
    RecallDataAgentLogic = None
try:
    from agents.hazard_analysis_agent.agent_logic import HazardAnalysisLogic

    AGENT_LOGIC_CLASSES["analyze_hazards"] = HazardAnalysisLogic
except ImportError:
    HazardAnalysisLogic = None
try:
    from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic

    AGENT_LOGIC_CLASSES["identify_product_from_image"] = VisualSearchAgentLogic
except ImportError:
    VisualSearchAgentLogic = None
# --- End of Imports ---


class BabyShieldRouterLogic:
    """
    Orchestrates the execution of a BabyShieldPlan by calling other agent logic
    classes directly in a dependency-aware manner. Manages the workflow state in-memory.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        self.agent_registry = {}

        # Instantiate only the agent logic classes that were successfully imported.
        for capability, LogicClass in AGENT_LOGIC_CLASSES.items():
            if not LogicClass:
                continue
            instance_id = f"{capability}_instance_001"
            # Special‐case RecallDataAgentLogic (no logger accepted)
            if LogicClass == RecallDataAgentLogic:
                self.agent_registry[capability] = LogicClass(agent_id=instance_id)
                self.logger.info(f"Router registered legacy agent for capability: '{capability}'")
            else:
                self.agent_registry[capability] = LogicClass(agent_id=instance_id, logger_instance=self.logger)
                self.logger.info(f"Router registered agent for capability: '{capability}'")

        self.logger.info(
            "BabyShieldRouterLogic initialized with %d available agents.",
            len(self.agent_registry),
        )

    def _substitute_dependency_placeholders(
        self, inputs: Dict[str, Any], workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replaces placeholders like '.' with actual data
        from the results of completed dependency tasks.
        """
        substituted = json.loads(json.dumps(inputs))  # deep copy

        for key, value in substituted.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                placeholder = value.strip("{}")
                parts = placeholder.split(".")
                if len(parts) < 2:
                    self.logger.warning(f"Invalid placeholder format: {value}")
                    substituted[key] = None
                    continue

                step_id = parts[0]
                # *** HERE'S THE FIX ***: drop the 'result' segment if present
                path = parts[1:]
                if path and path[0] == "result":
                    path = path[1:]

                source = workflow_state["tasks"].get(step_id, {}).get("result")
                if source is None:
                    self.logger.error(f"Could not resolve placeholder '{value}': no result for step '{step_id}'")
                    substituted[key] = None
                    continue

                # drill down the rest of the path
                final = source
                for p in path:
                    if isinstance(final, dict) and p in final:
                        final = final[p]
                    else:
                        final = None
                        break

                if final is not None:
                    substituted[key] = final
                    self.logger.info(f"Successfully resolved '{value}' → {final}")
                else:
                    self.logger.error(f"Could not resolve placeholder '{value}': path {path} missing in {source}")
                    substituted[key] = None

        return substituted

    async def execute_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        wf_id = plan.get("plan_id")
        self.logger.info(f"--- Starting execution for workflow: {wf_id} ---")

        # initialize workflow state
        wf = {
            "workflow_id": wf_id,
            "plan": plan,
            "status": "RUNNING",
            "tasks": {
                s["step_id"]: {"status": "PENDING", "result": None, "error": None} for s in plan.get("steps", [])
            },
            "completed_tasks": set(),
            "failed_tasks": set(),
        }

        # dispatch loop
        for _ in range(len(plan["steps"]) + 1):
            if wf["status"] != "RUNNING":
                break
            dispatched = 0

            for step in plan["steps"]:
                sid = step["step_id"]
                ts = wf["tasks"][sid]
                deps = set(step.get("dependencies", []))
                if ts["status"] == "PENDING" and deps.issubset(wf["completed_tasks"]):
                    dispatched += 1
                    ts["status"] = "RUNNING"
                    cap = step["agent_capability_required"]
                    agent = self.agent_registry.get(cap)
                    if not agent:
                        ts.update({"status": "FAILED", "error": f"No agent for {cap}"})
                        wf["failed_tasks"].add(sid)
                        continue

                    # substitute placeholders
                    inputs = self._substitute_dependency_placeholders(step["inputs"], wf)
                    self.logger.info(f"Dispatching task '{sid}' with inputs: {inputs}")
                    try:
                        res = await agent.process_task(inputs)
                        if res.get("status") == "COMPLETED":
                            # *** CRITICAL FIX: Check for both 'result' and 'data' keys ***
                            agent_result = res.get("result")
                            if agent_result is None:
                                agent_result = res.get("data", {})

                            ts.update({"status": "COMPLETED", "result": agent_result})
                            wf["completed_tasks"].add(sid)
                            self.logger.info(f"Task '{sid}' COMPLETED with result: {agent_result}")

                            # --- START OF NEW CONFIDENCE CHECK LOGIC ---
                            if sid == "step0_visual_search":
                                confidence = agent_result.get("confidence", 0.0) if agent_result else 0.0
                                if confidence < 0.7:
                                    self.logger.warning(
                                        f"Visual search confidence ({confidence}) is below threshold. Halting workflow."
                                    )
                                    wf["status"] = "FAILED"
                                    wf["error_message"] = (
                                        f"Visual search confidence too low ({confidence:.2f}) to proceed with a safety check. Please provide a clearer image or use the barcode scanner."
                                    )
                                    # Mark this as a special failure
                                    ts.update(
                                        {
                                            "status": "FAILED",
                                            "error": f"Confidence too low: {confidence:.2f}",
                                        }
                                    )
                                    wf["failed_tasks"].add(sid)
                                    break
                            # --- END OF NEW CONFIDENCE CHECK LOGIC ---
                        else:
                            err = res.get("error", "Unknown error")
                            ts.update({"status": "FAILED", "error": err})
                            wf["failed_tasks"].add(sid)
                            self.logger.error(f"Task '{sid}' FAILED: {err}")
                    except Exception as e:
                        ts.update({"status": "FAILED", "error": str(e)})
                        wf["failed_tasks"].add(sid)
                        self.logger.exception(f"Critical error in '{sid}': {e}")

            if dispatched == 0:
                break

        # finalize status
        if wf["failed_tasks"]:
            wf["status"] = "FAILED"
            # Collect detailed error information from failed tasks
            failed_task_details = []
            for task_id in wf["failed_tasks"]:
                task_info = wf["tasks"].get(task_id, {})
                task_error = task_info.get("error", "Unknown task error")
                failed_task_details.append(f"Task '{task_id}': {task_error}")

            error_summary = (
                f"Workflow failed with {len(wf['failed_tasks'])} failed task(s): {'; '.join(failed_task_details)}"
            )
            self.logger.error(error_summary)

        elif wf["completed_tasks"] == set(t["step_id"] for t in plan["steps"]):
            wf["status"] = "COMPLETED"
            error_summary = None
        else:
            wf["status"] = "STALLED"
            error_summary = f"Workflow stalled: {len(wf['completed_tasks'])}/{len(plan['steps'])} tasks completed"
            self.logger.warning(error_summary)

        self.logger.info(f"--- Workflow finished for: {wf_id} with status: {wf['status']} ---")
        last = plan["steps"][-1]["step_id"]

        result = {
            "status": wf["status"],
            "workflow_id": wf_id,
            "final_result": wf["tasks"][last]["result"],
            "full_workflow_state": wf,
        }

        # Include error details when workflow fails or stalls
        if error_summary:
            result["error"] = error_summary

        return result
