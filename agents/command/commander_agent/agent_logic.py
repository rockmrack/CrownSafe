# agents/command/commander_agent/agent_logic.py

import asyncio
import logging
import traceback
from typing import Dict, Any, Optional

# Adjust imports to your actual folder structure:
try:
    from agents.planning.planner_agent.agent_logic import BabyShieldPlannerLogic
except ImportError:

    class BabyShieldPlannerLogic:
        def __init__(self, *args, **kwargs):
            pass

        def process_task(self, user_request):
            # Always returns a fake "plan" for stub testing
            return {
                "status": "COMPLETED",
                "plan": {
                    "plan_id": "stub_plan_1",
                    "steps": [
                        {
                            "step_id": "step1",
                            "task_description": "Dummy step",
                            "agent_capability_required": "query_recalls_by_product",
                            "inputs": {"product_name": "Test Product", "upc": "123"},
                            "dependencies": [],
                        }
                    ],
                },
            }


try:
    from agents.routing.router_agent.agent_logic import BabyShieldRouterLogic
except ImportError:

    class BabyShieldRouterLogic:
        def __init__(self, *args, **kwargs):
            pass

        async def execute_plan(self, plan):
            # Always returns a fake result for stub testing
            return {
                "status": "COMPLETED",
                "final_result": {"recalls_found": 1, "summary": "Stub result"},
            }


class BabyShieldCommanderLogic:
    """
    The main entry point for the BabyShield "Safety Check" workflow.
    It orchestrates the Planner and Router to execute a full safety check in-memory
    within a single API request lifecycle.
    """

    def __init__(
        self,
        agent_id: str = "commander_001",
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initializes the Commander and the orchestration agents it controls.
        """
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        self.planner = BabyShieldPlannerLogic(
            agent_id="planner_for_commander", logger_instance=self.logger
        )
        self.router = BabyShieldRouterLogic(
            agent_id="router_for_commander", logger_instance=self.logger
        )
        self.logger.info(
            "BabyShieldCommanderLogic initialized. It now directly controls the Planner and Router."
        )

    async def start_safety_check_workflow(
        self, user_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        The primary method that executes the entire end-to-end safety check.

        Args:
            user_request: A dictionary containing the product identifier,
                          e.g., {"barcode": "12345", "image_url": null}

        Returns:
            A dictionary with the final result of the workflow.
        """
        self.logger.info("--- New Safety Check Workflow Started ---")
        self.logger.info(f"User Request: {user_request}")

        try:
            # --- Step 1: Delegate to Planner ---
            self.logger.info("Step 1: Calling Planner to create an execution plan...")
            planner_result = self.planner.process_task(user_request)

            if planner_result.get("status") != "COMPLETED":
                error_msg = f"Planner failed: {planner_result.get('error', 'Unknown planning error')}"
                self.logger.error(error_msg)
                return {"status": "FAILED", "error": error_msg}

            plan = planner_result.get("plan")
            self.logger.info(
                f"Step 1 Complete. Plan '{plan.get('plan_id')}' created successfully."
            )

            # --- Step 2: Delegate to Router ---
            self.logger.info(
                f"Step 2: Calling Router to execute plan '{plan.get('plan_id')}'..."
            )
            router_result = await self.router.execute_plan(plan)

            if router_result.get("status") != "COMPLETED":
                error_msg = f"Router failed: {router_result.get('error', 'Unknown execution error')}"
                self.logger.error(error_msg)

                # --------- ADD DB FALLBACK HERE -----------
                try:
                    from core_infra.database import SessionLocal, RecallDB

                    db = SessionLocal()

                    # Try model number first (highest precision), then barcode/UPC
                    model_number = user_request.get("model_number")
                    barcode = user_request.get("barcode")

                    recall = None
                    if model_number:
                        self.logger.info(
                            f"Attempting DB fallback with model_number: {model_number}"
                        )
                        recall = (
                            db.query(RecallDB)
                            .filter(RecallDB.model_number.ilike(model_number))
                            .first()
                        )

                    if not recall and barcode:
                        self.logger.info(
                            f"Attempting DB fallback with barcode: {barcode}"
                        )
                        recall = (
                            db.query(RecallDB).filter(RecallDB.upc == barcode).first()
                        )

                    db.close()
                    if recall:
                        self.logger.info("Recall found directly in DB fallback!")
                        try:
                            recall_data = recall.to_dict()
                        except AttributeError:
                            # Fallback if to_dict() doesn't exist
                            recall_data = {
                                "recall_id": recall.recall_id,
                                "product_name": recall.product_name,
                                "model_number": recall.model_number,
                                "recall_date": recall.recall_date.isoformat()
                                if recall.recall_date
                                else None,
                                "source_agency": recall.source_agency,
                                "description": recall.description,
                                "hazard": recall.hazard,
                                "remedy": recall.remedy,
                                "upc": recall.upc,
                                "url": recall.url,
                            }
                        return {"status": "COMPLETED", "data": recall_data}
                    else:
                        self.logger.error(
                            "Recall not found even with direct DB fallback."
                        )
                except Exception as fallback_exc:
                    self.logger.error(f"DB fallback failed: {fallback_exc}")
                # --------- END DB FALLBACK -----------

                return {"status": "FAILED", "error": error_msg}

            final_result = router_result.get("final_result")
            self.logger.info("Step 2 Complete. Router executed the plan successfully.")

            # --- START OF NEW LOGIC ---
            # Check if the workflow completed but produced an empty or inconclusive result.
            # This happens if a product isn't identified or no recalls are found.
            if router_result.get("status") == "COMPLETED" and (
                not final_result or not final_result.get("risk_level")
            ):
                self.logger.warning(
                    "Workflow completed but resulted in an inconclusive analysis. Returning an 'UNKNOWN' status."
                )
                return {
                    "status": "INCONCLUSIVE",
                    "data": {
                        "summary": "Could not definitively identify this product or find matching recall data.",
                        "risk_level": "Unknown",
                        "note": "This does not mean the product is safe. It means we could not find it in our system using the provided identifier. Please try searching by the model number found on the product label or use the photo scan feature.",
                    },
                }
            # --- END OF NEW LOGIC ---

            # --- Step 3: Return Final Result ---
            self.logger.info("--- Workflow Completed Successfully ---")
            return {"status": "COMPLETED", "data": final_result}

        except Exception as e:
            self.logger.error(
                f"An unexpected exception occurred in the Commander workflow: {e}",
                exc_info=True,
            )
            return {
                "status": "FAILED",
                "error": f"A critical error occurred in the Commander: {traceback.format_exc()}",
            }
