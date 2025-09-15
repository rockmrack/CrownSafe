# C:\Users\rossd\Downloads\RossNetAgents\agents\planning\planner_agent\agent_logic.py
# Version: 3.1-BABYSHIELD (Adapted for user-provided template)
# Description: A streamlined, template-based planner for the BabyShield project.
# This version is specifically adapted to work with the existing 'babyshield_safety_check_plan.json'
# and its triple-brace placeholder syntax.

import logging
import json
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path
import uuid

# Pydantic models for plan validation and structure.
try:
    from pydantic import BaseModel, Field, validator

    class PlanStep(BaseModel):
        """Model for a single step in the BabyShield safety check plan."""
        step_id: str
        task_description: str
        agent_capability_required: str
        target_agent_type: Optional[str] = None # Added to match your template
        inputs: Dict[str, Any]
        dependencies: List[str] = Field(default_factory=list)
        priority: str = "medium"

        @validator('agent_capability_required')
        def validate_capability(cls, v):
            """Ensures that the plan only uses capabilities defined for BabyShield."""
            # UPDATED to match your template's capabilities
            valid_capabilities = [
                'identify_product',
                'identify_product_from_image',  # Phase 3: Visual search capability
                'query_recalls_by_product',
                'analyze_hazards',
                'notify_user' # Kept for future use
            ]
            if v not in valid_capabilities:
                raise ValueError(f"Invalid capability: '{v}'. Must be one of {valid_capabilities}")
            return v

    class BabyShieldPlan(BaseModel):
        """Model for the complete BabyShield safety check plan."""
        plan_id: str = Field(default_factory=lambda: f"bsp_{uuid.uuid4()}")
        workflow_goal: str
        # These fields are no longer needed at the top level as they are in the inputs
        # product_identifier_type: str
        # product_identifier_value: str
        steps: List[PlanStep]
        template_name: str
        created_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BabyShieldPlan = None
    PlanStep = None

def substitute_placeholders(obj: Any, params: Dict[str, Any]) -> Any:
    """
    Recursively substitutes placeholders like {{{key}}} in a nested object.
    UPDATED to handle triple-brace syntax and None values properly.
    """
    if isinstance(obj, str):
        # First check if the entire string is a placeholder
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"
            if obj == placeholder:
                # If the whole string is just the placeholder, return the actual value
                # This preserves None values instead of converting to string
                return value
                
        # Otherwise, do string substitution
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in obj:
                # Convert None to empty string for substitution
                sub_value = "" if value is None else str(value)
                obj = obj.replace(placeholder, sub_value)
        return obj
    elif isinstance(obj, list):
        return [substitute_placeholders(item, params) for item in obj]
    elif isinstance(obj, dict):
        return {k: substitute_placeholders(v, params) for k, v in obj.items()}
    else:
        return obj

class BabyShieldPlannerLogic:
    """
    Generates a static, step-by-step execution plan for the BabyShield
    "Safety Check" workflow by loading and populating a predefined JSON template.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        """Initializes the planner."""
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        if not PYDANTIC_AVAILABLE:
            self.logger.critical("Pydantic is not installed. The Planner Agent cannot function without it.")
            raise ImportError("Pydantic is required for the Planner Agent to operate.")
        self._load_plan_templates()

    def _load_plan_templates(self):
        """Loads all .json plan templates from the prompts directory."""
        template_dir = Path(__file__).parent.parent.parent.parent / "prompts" / "v1"
        self.plan_templates = {}
        self.logger.info(f"Loading BabyShield plan templates from: {template_dir}")

        if not template_dir.is_dir():
            self.logger.warning(f"Template directory not found: {template_dir}")
            return

        # Assuming your file is named 'babyshield_safety_check_plan.json'
        for template_file in template_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template_name = template_file.stem
                    self.plan_templates[template_name] = template_data
                    self.logger.info(f"  -> Loaded template: '{template_name}'")
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")

    def _generate_plan_from_template(self, template_name: str, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured plan by loading a JSON template and substituting placeholders.
        """
        self.logger.info(f"Generating plan from template '{template_name}'...")

        if template_name not in self.plan_templates:
            msg = f"Plan template '{template_name}' not found."
            self.logger.error(msg)
            raise FileNotFoundError(msg)

        template = self.plan_templates[template_name]

        # UPDATED: Extract parameters based on your template's structure.
        # It expects 'barcode' and 'image_url', one of which can be null.
        params = {
            "barcode": task_payload.get("barcode"),
            "model_number": task_payload.get("model_number"),
            "image_url": task_payload.get("image_url")
        }

        # Validate that at least one identifier was provided.
        if not params["barcode"] and not params["model_number"] and not params["image_url"]:
            msg = "Missing required parameters for planning. Need 'barcode', 'model_number', or 'image_url'."
            self.logger.error(f"{msg} - Received: {task_payload}")
            raise ValueError(msg)

        # Create a deep copy of the template steps.
        plan_steps_template = json.loads(json.dumps(template.get("steps", [])))

        # Substitute placeholders in the plan steps.
        substituted_steps = substitute_placeholders(plan_steps_template, params)
        
        # Clean up any remaining empty curly braces that weren't substituted
        for step in substituted_steps:
            if "inputs" in step:
                for key, value in step["inputs"].items():
                    if isinstance(value, str):
                        # Remove curly braces from values like "{850016249012}" to "850016249012"
                        if value.startswith("{") and value.endswith("}") and not value.startswith("{{"):
                            step["inputs"][key] = value.strip("{}")
                        # Also handle empty placeholders
                        elif value in ["{}", ""]:
                            step["inputs"][key] = None
        
        # NOTE: The inter-step placeholders like {{step_id.result.field}}
        # are NOT replaced here. That is the job of the ROUTER AGENT after a step completes.
        # This planner's only job is to set the initial inputs.

        # Construct the final plan object.
        final_plan_data = {
            "workflow_goal": task_payload.get("goal", "Perform BabyShield Product Safety Check"),
            "steps": substituted_steps,
            "template_name": template_name
        }

        # Validate the final plan against our Pydantic model.
        try:
            # We use the template's plan_name as the workflow_goal if not provided
            final_plan_data["workflow_goal"] = final_plan_data.get("workflow_goal") or template.get("plan_name")
            validated_plan = BabyShieldPlan(**final_plan_data)
            self.logger.info(f"Successfully generated and validated plan '{validated_plan.plan_id}' from template.")
            return validated_plan.model_dump()
        except Exception as e:
            self.logger.error(f"Pydantic validation failed for the generated plan: {e}")
            self.logger.debug(f"Data that failed validation: {final_plan_data}")
            raise

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent. It receives a task and returns a completed plan.
        """
        self.logger.info(f"Planner agent received task: {task_data}")
        try:
            # The name of your file, without the .json extension
            plan_template_name = "babyshield_safety_check_plan" 

            generated_plan = self._generate_plan_from_template(plan_template_name, task_data)

            return {
                "status": "COMPLETED",
                "plan": generated_plan,
                "message": f"Plan created successfully using template: '{plan_template_name}'.",
                "agent_id": self.agent_id,
                "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "3.1-BABYSHIELD"
            }

        except Exception as e:
            self.logger.error(f"Planning process failed: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "status": "FAILED",
                "error": str(e),
                "message": "Planning process failed.",
                "agent_id": self.agent_id,
                "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "3.1-BABYSHIELD"
            }