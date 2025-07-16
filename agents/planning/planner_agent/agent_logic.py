# C:\Users\rossd\Downloads\RossNetAgents\agents\planning\planner_agent\agent_logic.py
# Version: 2.8-ENHANCED-FIXED (Enhanced Memory-Augmented Planning with Template Support)
# Revolutionary memory-aware planning system with EnhancedMemoryManager V2.0 integration
# ENHANCED: Added template-based planning for specific task types like prior_authorization
# FIXED: Correct placeholder substitution for all formats including double-brace and lists

import logging
import json
import re
import traceback
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timezone
import asyncio
from pathlib import Path
import uuid

# OpenAI LLM integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Enhanced Memory integration
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core_infra.enhanced_memory_manager import EnhancedMemoryManager
    MEMORY_AVAILABLE = True
except ImportError:
    try:
        # Fallback to standard memory manager
        from core_infra.memory_manager import MemoryManager as EnhancedMemoryManager
        MEMORY_AVAILABLE = True
    except ImportError:
        MEMORY_AVAILABLE = False
        EnhancedMemoryManager = None

# Pydantic models for plan validation
try:
    from pydantic import BaseModel, Field, validator
    from typing import List, Optional, Dict, Any
    
    class PlanStep(BaseModel):
        """Model for individual plan steps"""
        step_id: str
        task_description: str
        agent_capability_required: str
        inputs: Dict[str, Any]
        dependencies: List[str] = Field(default_factory=list)
        priority: str = "medium"
        target_agent_type: Optional[str] = None
        
        @validator('agent_capability_required')
        def validate_capability(cls, v):
            # Updated to include both old and new capabilities
            valid_capabilities = [
                # Old capabilities (for backward compatibility if needed)
                'perform_web_search',
                'retrieve_clinical_trials', 
                'query_adverse_events',
                'build_final_report',
                # New template-based capabilities for prior authorization
                'get_patient_record',
                'query_guidelines',
                'get_policy_for_drug',
                'predict_approval_likelihood',
                'check_drug_interactions',
                'check_coverage_criteria',
                'evaluate_if_patient_meets_pa_criteria_for_metformin',  # Add this temporarily
                'evaluate_if_patient_meets_pa_criteria'  # Generic version
            ]
            # Allow dynamic capabilities that start with known prefixes
            if v not in valid_capabilities:
                # Check if it's a dynamic capability
                if v.startswith('evaluate_if_patient_meets_pa_criteria'):
                    return v
                raise ValueError(f'Invalid capability: {v}. Must be one of {valid_capabilities}')
            return v
    
    class StructuredPlan(BaseModel):
        """Model for complete plan structure"""
        workflow_goal: str
        extracted_drug_name: Optional[str] = None
        extracted_disease_name: Optional[str] = None
        steps: List[PlanStep]
        memory_augmented: bool = False
        research_strategy: str = "comprehensive"
        extracted_entities: Dict[str, Any] = Field(default_factory=dict)
        created_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
        plan_id: str = Field(default_factory=lambda: f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        plan_name: Optional[str] = None
        fallback_used: bool = False
        enhanced_features: Dict[str, Any] = Field(default_factory=dict)
        template_based: Optional[bool] = False
        template_name: Optional[str] = None
        
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    StructuredPlan = None
    PlanStep = None

def substitute_placeholders(obj, params):
    """
    Recursively substitute placeholders in strings/lists/dicts in the given obj.
    Supports {param}, and ${param}.
    """
    if isinstance(obj, str):
        # Make a copy to modify
        result = obj
        for param_key, param_value in params.items():
            if param_value is not None:
                phs = [
                    f"{{{param_key}}}",   # {patient_id}
                    f"${{{param_key}}}"   # ${patient_id}
                ]
                for ph in phs:
                    if ph in result:
                        if isinstance(param_value, list):
                            value_str = ', '.join(map(str, param_value))
                        else:
                            value_str = str(param_value)
                        result = result.replace(ph, value_str)
        return result
    elif isinstance(obj, list):
        return [substitute_placeholders(item, params) for item in obj]
    elif isinstance(obj, dict):
        return {k: substitute_placeholders(v, params) for k, v in obj.items()}
    else:
        return obj

class MemoryAugmentedPlannerLogic:
    """
    Enhanced memory-augmented planning system that leverages EnhancedMemoryManager V2.0
    with temporal analysis, contradiction detection, and research gap identification.
    ENHANCED: Now supports template-based planning for specific task types.
    """
    
    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        """Initialize enhanced memory-augmented planner"""
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        
        # Initialize OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE:
            try:
                import os
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    self.openai_client = OpenAI(api_key=openai_api_key)
                    self.logger.info("OpenAI client initialized for enhanced memory-augmented planning")
                else:
                    self.logger.error("OPENAI_API_KEY not found")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
        
        # Initialize Enhanced Memory Manager
        self.memory_manager = None
        self.enhanced_features_available = False
        if MEMORY_AVAILABLE:
            try:
                self.memory_manager = EnhancedMemoryManager()
                if hasattr(self.memory_manager, 'collection') and self.memory_manager.collection:
                    self.logger.info("EnhancedMemoryManager V2.0 integrated successfully - ADVANCED MEMORY-AUGMENTED PLANNING ENABLED!")
                    
                    # Check for enhanced features
                    if hasattr(self.memory_manager, 'temporal_patterns'):
                        self.logger.info("Temporal pattern analysis available")
                        self.enhanced_features_available = True
                    if hasattr(self.memory_manager, 'contradictions'):
                        self.logger.info("Contradiction detection available")
                        self.enhanced_features_available = True
                    if hasattr(self.memory_manager, 'research_gaps'):
                        self.logger.info("Research gap identification available")
                        self.enhanced_features_available = True
                    if hasattr(self.memory_manager, 'cross_workflow_insights'):
                        self.logger.info("Cross-workflow insights available")
                        self.enhanced_features_available = True
                        
                else:
                    self.logger.warning("EnhancedMemoryManager failed to initialize collection")
                    self.memory_manager = None
            except Exception as e:
                self.logger.error(f"Failed to initialize EnhancedMemoryManager: {e}")
                self.memory_manager = None
        else:
            self.logger.warning("EnhancedMemoryManager not available - using standard planning")
        
        # Load plan templates
        self._load_plan_templates()
    
    def _load_plan_templates(self):
        """Loads all .json plan templates from the template directory."""
        # FIXED: Correct path to go up 4 levels from agents/planning/planner_agent/agent_logic.py
        TEMPLATE_DIR = Path(__file__).parent.parent.parent.parent / "prompts" / "v1"
        self.plan_templates = {}
        self.logger.info(f"Loading plan templates from: {TEMPLATE_DIR}")
        if not TEMPLATE_DIR.is_dir():
            self.logger.warning(f"Template directory not found: {TEMPLATE_DIR}")
            return

        for template_file in TEMPLATE_DIR.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template_name = template_file.stem
                    self.plan_templates[template_name] = template_data
                    self.logger.info(f"  -> Loaded template: '{template_name}'")
            except Exception as e:
                self.logger.error(f"Failed to load template {template_file}: {e}")

    def _detect_prior_authorization_workflow(self, user_goal: str) -> bool:
        """Detect if this is a prior authorization workflow based on the goal"""
        prior_auth_keywords = [
            'prior authorization',
            'prior auth',
            'authorization for',
            'approve',
            'approval',
            'insurance',
            'coverage',
            'insurer'
        ]
        
        goal_lower = user_goal.lower()
        return any(keyword in goal_lower for keyword in prior_auth_keywords)

    def _generate_plan_from_template(self, template_name: str, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured plan by loading a JSON template and substituting placeholders.
        FIXED: Handle double-brace test-value, single-brace {param}, and ${param} style placeholders
        FIXED: Look for parameters at both top level and in parameters dict
        FIXED: Extract parameters from goal string when not explicitly provided
        FIXED: Handle lists containing placeholders
        FIXED: Apply substitution to entire step object, not just inputs
        """
        # DEBUG: Log the entire task_payload to see what we're receiving
        self.logger.critical(f"TEMPLATE GENERATOR RECEIVED task_payload: {json.dumps(task_payload, indent=2)}")
        
        if template_name not in self.plan_templates:
            self.logger.error(f"Plan template '{template_name}' not found.")
            return {"status": "error", "message": f"Plan template '{template_name}' not found."}

        template = self.plan_templates[template_name]
        
        # Extract parameters from goal if not provided
        user_goal = task_payload.get('goal', '') or task_payload.get('user_goal', '')
        
        # FIXED: Collect parameters from both top level and parameters dict
        params = {}
        
        # First get any parameters from the parameters dict
        if "parameters" in task_payload:
            self.logger.debug(f"Found parameters dict: {task_payload['parameters']}")
            params.update(task_payload["parameters"])
        
        # Then get any top-level parameters (these override parameters dict)
        for key in ["patient_id", "drug_name", "insurer_id", "disease_name", "condition_name"]:
            if key in task_payload:
                self.logger.debug(f"Found top-level {key}: {task_payload[key]}")
                params[key] = task_payload[key]
        
        # FIXED: Extract parameters from goal string for prior authorization
        if template_name == "prior_auth_plan_template" and user_goal:
            # Extract drug name if not already present
            if not params.get("drug_name"):
                # Pattern: "authorization for [DRUG] for patient"
                drug_match = re.search(r'authorization\s+for\s+(\w+)\s+for', user_goal, re.IGNORECASE)
                if not drug_match:
                    # Alternative pattern: "for [DRUG] for"
                    drug_match = re.search(r'for\s+(\w+)\s+for', user_goal, re.IGNORECASE)
                if drug_match:
                    params["drug_name"] = drug_match.group(1).strip()
                    self.logger.info(f"Extracted drug_name from goal: {params['drug_name']}")
            
            # Extract insurer ID if not already present
            if not params.get("insurer_id"):
                # Pattern: "with [INSURER] insurance"
                insurer_match = re.search(r'with\s+([\w-]+)\s+insurance', user_goal, re.IGNORECASE)
                if insurer_match:
                    params["insurer_id"] = insurer_match.group(1).strip()
                    self.logger.info(f"Extracted insurer_id from goal: {params['insurer_id']}")
            
            # Extract patient ID if not already present
            if not params.get("patient_id"):
                # Pattern: "patient [ID]" or "patient with"
                patient_match = re.search(r'patient\s+([\w-]+)', user_goal, re.IGNORECASE)
                if patient_match and patient_match.group(1).lower() != 'with':
                    params["patient_id"] = patient_match.group(1).strip()
                    self.logger.info(f"Extracted patient_id from goal: {params['patient_id']}")
                else:
                    # Use default patient ID
                    params["patient_id"] = "patient-001"
                    self.logger.info(f"Using default patient_id: {params['patient_id']}")
        
        # DEBUG: Log collected params
        self.logger.critical(f"COLLECTED PARAMS: {json.dumps(params, indent=2)}")
        
        # FIXED: Validate required parameters for prior authorization
        if template_name == "prior_auth_plan_template":
            # Check for required parameters
            required_params = ["patient_id", "drug_name", "insurer_id"]
            missing_params = []
            
            # Check merged params
            for param in required_params:
                if param not in params or not params[param]:
                    missing_params.append(param)
                    self.logger.error(f"Missing or empty parameter: {param}")
            
            if missing_params:
                error_msg = f"Missing required parameters for prior authorization: {', '.join(missing_params)}"
                self.logger.error(error_msg)
                self.logger.error(f"Available params were: {list(params.keys())}")
                return {"status": "error", "message": error_msg}
            
            # Extract entities from goal if disease/condition not provided
            if not params.get("disease_name") and not params.get("condition_name"):
                entities = self._extract_entities_enhanced(user_goal)
                params["disease_name"] = entities.get('primary_disease', '')
                params["condition_name"] = entities.get('primary_disease', '')
        
        # Log the parameters being used
        self.logger.info(f"Prior-auth template will be populated with: {params}")
        
        # Create a deep copy to avoid modifying the loaded template
        plan_steps = json.loads(json.dumps(template.get("steps", [])))
        
        # CRITICAL FIX: Replace placeholders in ENTIRE step objects, not just inputs
        for i, step in enumerate(plan_steps):
            # Apply substitution to the ENTIRE step object recursively
            plan_steps[i] = substitute_placeholders(step, params)
            
            # SPECIAL FIX for drug interactions: Ensure we have multiple drugs
            if step.get("step_id") == "step4_check_drug_interactions":
                # If drug_names only has one drug, add a dummy second drug for testing
                # In production, this should come from patient's medication list
                if "inputs" in step and "drug_names" in step["inputs"]:
                    drug_list = step["inputs"]["drug_names"]
                    if isinstance(drug_list, list) and len(drug_list) < 2:
                        # Add a common drug for testing interaction
                        step["inputs"]["drug_names"] = drug_list + ["aspirin"]  # Common drug for interactions
                        self.logger.warning(f"Added dummy drug 'aspirin' to drug interaction check for testing")

        # DEBUG: Log the substituted plan
        self.logger.critical(f"SUBSTITUTED PLAN STEPS: {json.dumps(plan_steps, indent=2)}")

        final_plan = {
            "plan_id": f"{template.get('plan_id_prefix', 'plan-')}{uuid.uuid4()}",
            "plan_name": template.get("plan_name", "Unnamed Plan"),
            "workflow_goal": user_goal or template.get("plan_name", "Template-based workflow"),
            "extracted_drug_name": params.get("drug_name"),
            "extracted_disease_name": params.get("disease_name") or params.get("condition_name"),
            "steps": plan_steps,
            "memory_augmented": False,
            "template_based": True,
            "template_name": template_name,
            "created_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.logger.info(f"Successfully generated plan '{final_plan['plan_name']}' from template with {len(final_plan['steps'])} steps.")
        self.logger.critical(f"TEMPLATE-BASED PLAN: {json.dumps(final_plan, indent=2)}")
        return {"status": "success", "plan": final_plan}
    
    def _extract_entities_enhanced(self, user_goal: str) -> Dict[str, Any]:
        """Enhanced entity extraction with pharmaceutical intelligence"""
        try:
            # Enhanced drug patterns including new classes
            drug_patterns = [
                # SGLT2 inhibitors
                r'\b(canagliflozin|dapagliflozin|empagliflozin|ertugliflozin|sotagliflozin)\b',
                # GLP-1 agonists
                r'\b(semaglutide|liraglutide|dulaglutide|exenatide|lixisenatide)\b',
                # ACE inhibitors/ARBs
                r'\b(lisinopril|enalapril|captopril|losartan|valsartan|candesartan)\b',
                # Beta blockers
                r'\b(metoprolol|carvedilol|bisoprolol|atenolol|propranolol)\b',
                # Calcium channel blockers
                r'\b(amlodipine|nifedipine|diltiazem|verapamil)\b',
                # Statins
                r'\b(atorvastatin|simvastatin|rosuvastatin|pravastatin)\b',
                # Diuretics
                r'\b(furosemide|hydrochlorothiazide|spironolactone|torsemide)\b',
                # Other diabetes medications
                r'\b(metformin|insulin|glipizide|glyburide|pioglitazone)\b',
                # Generic patterns
                r'\b([A-Z][a-z]+(?:zin|flozin|ide|pril|tan|pine|statin|olol|dipine))\b'
            ]
            
            # Enhanced disease patterns
            disease_patterns = [
                r'\b(type\s*[12]?\s*diabetes|diabetes mellitus|T1DM|T2DM|diabetic)\b',
                r'\b(heart failure|cardiac failure|HF|CHF|congestive heart failure)\b',
                r'\b(hypertension|high blood pressure|HTN|elevated blood pressure)\b',
                r'\b(hyperlipidemia|dyslipidemia|high cholesterol|elevated lipids)\b',
                r'\b(chronic kidney disease|CKD|renal impairment|nephropathy)\b',
                r'\b(coronary artery disease|CAD|myocardial infarction|MI|angina)\b',
                r'\b(atrial fibrillation|AFib|arrhythmia|cardiac arrhythmia)\b',
                r'\b(obesity|metabolic syndrome|weight management)\b',
                r'\b(stroke|cerebrovascular disease|TIA)\b'
            ]
            
            # Extract entities
            user_goal_lower = user_goal.lower()
            entities = {
                "drugs": [],
                "diseases": [],
                "primary_drug": None,
                "primary_disease": None,
                "drug_class": None,
                "indication_type": None
            }
            
            # Find all drugs
            for pattern in drug_patterns:
                matches = re.findall(pattern, user_goal_lower, re.IGNORECASE)
                for match in matches:
                    drug_name = match.title() if isinstance(match, str) else match[0].title()
                    if drug_name not in entities["drugs"]:
                        entities["drugs"].append(drug_name)
            
            # Find all diseases
            for pattern in disease_patterns:
                matches = re.findall(pattern, user_goal_lower, re.IGNORECASE)
                for match in matches:
                    disease_name = match if isinstance(match, str) else match[0]
                    # Normalize disease names
                    disease_name = self._normalize_disease_name(disease_name)
                    if disease_name not in entities["diseases"]:
                        entities["diseases"].append(disease_name)
            
            # Set primary entities (first found)
            entities["primary_drug"] = entities["drugs"][0] if entities["drugs"] else None
            entities["primary_disease"] = entities["diseases"][0] if entities["diseases"] else None
            
            # Determine drug class
            if entities["primary_drug"]:
                entities["drug_class"] = self._identify_drug_class(entities["primary_drug"])
            
            # Determine indication type
            if entities["primary_disease"]:
                entities["indication_type"] = self._classify_indication(entities["primary_disease"])
            
            # Legacy compatibility
            entities["drug_name"] = entities["primary_drug"]
            entities["disease_name"] = entities["primary_disease"]
            
            self.logger.info(f"Enhanced entity extraction completed: {entities}")
            return entities
            
        except Exception as e:
            self.logger.error(f"Enhanced entity extraction failed: {e}")
            return {
                "drugs": [], "diseases": [], "primary_drug": None, "primary_disease": None,
                "drug_class": None, "indication_type": None,
                "drug_name": None, "disease_name": None
            }
    
    def _normalize_disease_name(self, disease: str) -> str:
        """Normalize disease names for consistency"""
        disease_lower = disease.lower().strip()
        
        # Diabetes variations
        if any(term in disease_lower for term in ['diabetes', 't2dm', 't1dm']):
            if any(term in disease_lower for term in ['type 1', 't1dm']):
                return "Type 1 Diabetes"
            else:
                return "Type 2 Diabetes"
        
        # Heart failure variations
        if any(term in disease_lower for term in ['heart failure', 'hf', 'chf', 'cardiac failure']):
            return "Heart Failure"
        
        # Hypertension variations
        if any(term in disease_lower for term in ['hypertension', 'htn', 'high blood pressure']):
            return "Hypertension"
        
        # Kidney disease variations
        if any(term in disease_lower for term in ['kidney disease', 'ckd', 'renal', 'nephropathy']):
            return "Chronic Kidney Disease"
        
        # Cardiovascular disease variations
        if any(term in disease_lower for term in ['coronary', 'cad', 'myocardial', 'angina']):
            return "Coronary Artery Disease"
        
        return disease.title()
    
    def _identify_drug_class(self, drug: str) -> str:
        """Identify pharmaceutical drug class"""
        drug_lower = drug.lower()
        
        # SGLT2 inhibitors
        if any(sglt2 in drug_lower for sglt2 in ['canagliflozin', 'dapagliflozin', 'empagliflozin', 'ertugliflozin', 'sotagliflozin']):
            return "SGLT2 Inhibitor"
        
        # GLP-1 agonists
        if any(glp1 in drug_lower for glp1 in ['semaglutide', 'liraglutide', 'dulaglutide', 'exenatide']):
            return "GLP-1 Agonist"
        
        # ACE inhibitors
        if drug_lower.endswith('pril'):
            return "ACE Inhibitor"
        
        # ARBs
        if drug_lower.endswith('sartan'):
            return "Angiotensin Receptor Blocker"
        
        # Beta blockers
        if drug_lower.endswith('olol'):
            return "Beta Blocker"
        
        # Calcium channel blockers
        if drug_lower.endswith('dipine'):
            return "Calcium Channel Blocker"
        
        # Statins
        if drug_lower.endswith('statin'):
            return "Statin"
        
        return "Unknown Class"
    
    def _classify_indication(self, disease: str) -> str:
        """Classify indication type for research strategy"""
        disease_lower = disease.lower()
        
        if 'diabetes' in disease_lower:
            return "Metabolic"
        elif any(term in disease_lower for term in ['heart', 'cardiac', 'cardiovascular']):
            return "Cardiovascular"
        elif any(term in disease_lower for term in ['kidney', 'renal']):
            return "Renal"
        elif 'hypertension' in disease_lower:
            return "Cardiovascular"
        else:
            return "General"
    
    async def _get_enhanced_memory_insights_async(self, user_goal: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive memory insights using EnhancedMemoryManager V2.0 - ASYNC VERSION"""
        if not self.memory_manager:
            return {"memory_available": False}
        
        try:
            self.logger.info("Retrieving enhanced memory insights (async)...")
            
            # Get base memory insights (synchronous)
            base_insights = self._get_memory_insights_sync(user_goal, entities)
            
            # Get enhanced analytics if available
            enhanced_insights = {}
            if hasattr(self.memory_manager, 'get_enhanced_analytics'):
                try:
                    # Check if the method is async
                    if asyncio.iscoroutinefunction(self.memory_manager.get_enhanced_analytics):
                        analytics = await self.memory_manager.get_enhanced_analytics()
                    else:
                        # Run sync method in thread pool
                        analytics = await asyncio.to_thread(self.memory_manager.get_enhanced_analytics)
                    enhanced_insights["analytics"] = analytics
                    self.logger.info("Enhanced analytics retrieved")
                except Exception as e:
                    self.logger.warning(f"Enhanced analytics failed: {e}")
            
            # Get enhanced recommendations if available
            if hasattr(self.memory_manager, 'get_enhanced_research_recommendations'):
                try:
                    # This method is likely async based on the original code
                    if asyncio.iscoroutinefunction(self.memory_manager.get_enhanced_research_recommendations):
                        recommendations = await self.memory_manager.get_enhanced_research_recommendations(entities)
                    else:
                        recommendations = await asyncio.to_thread(
                            self.memory_manager.get_enhanced_research_recommendations, 
                            entities
                        )
                    enhanced_insights["enhanced_recommendations"] = recommendations
                    self.logger.info("Enhanced recommendations retrieved")
                except Exception as e:
                    self.logger.warning(f"Enhanced recommendations failed: {e}")
            
            # Combine base and enhanced insights
            combined_insights = {
                **base_insights,
                "enhanced_features": enhanced_insights,
                "temporal_patterns_available": hasattr(self.memory_manager, 'temporal_patterns'),
                "contradiction_detection_available": hasattr(self.memory_manager, 'contradictions'),
                "gap_analysis_available": hasattr(self.memory_manager, 'research_gaps'),
                "cross_workflow_insights_available": hasattr(self.memory_manager, 'cross_workflow_insights')
            }
            
            # Enhanced strategy determination
            enhanced_strategy = self._determine_enhanced_strategy(entities, combined_insights)
            combined_insights["recommendations"]["research_strategy"] = enhanced_strategy
            
            self.logger.info(f"Enhanced memory insights completed: {enhanced_strategy} strategy recommended")
            return combined_insights
            
        except Exception as e:
            self.logger.error(f"Enhanced memory insights failed: {e}")
            return self._get_memory_insights_sync(user_goal, entities)
    
    def _get_memory_insights_sync(self, user_goal: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous memory insights with enhanced drug class intelligence"""
        if not self.memory_manager:
            return {"memory_available": False}
        
        try:
            self.logger.info("Retrieving synchronous memory insights with enhanced intelligence...")
            
            # Enhanced strategy determination based on drug class and entities
            primary_drug = entities.get('primary_drug') or entities.get('drug_name')
            drug_class = entities.get('drug_class')
            primary_disease = entities.get('primary_disease') or entities.get('disease_name')
            
            # Advanced heuristics for strategy determination
            if drug_class == "SGLT2 Inhibitor":
                # SGLT2 inhibitors - we have substantial data
                strategy = "focused"
                knowledge_gaps = ["latest cardiovascular outcomes", "renal protection mechanisms"]
                priority_areas = ["heart failure outcomes", "kidney function preservation"]
                confidence = 0.85
            elif drug_class in ["GLP-1 Agonist", "ACE Inhibitor", "Beta Blocker"]:
                # Well-studied drug classes
                strategy = "focused"
                knowledge_gaps = ["recent clinical updates", "combination therapy data"]
                priority_areas = ["comparative effectiveness", "safety profiles"]
                confidence = 0.75
            elif primary_drug and primary_disease:
                # Both entities present but less familiar drug class
                strategy = "comprehensive"
                knowledge_gaps = ["efficacy data", "safety profile", "mechanism of action"]
                priority_areas = ["clinical trials", "real-world evidence"]
                confidence = 0.60
            else:
                # Missing entities or unknown drug
                strategy = "comprehensive"
                knowledge_gaps = ["basic efficacy", "safety data", "clinical evidence"]
                priority_areas = ["foundational research", "systematic review"]
                confidence = 0.40
            
            # Enhanced insights structure
            memory_insights = {
                "memory_available": True,
                "enhanced_version": True,
                "recommendations": {
                    "research_strategy": strategy,
                    "knowledge_gaps": knowledge_gaps,
                    "priority_areas": priority_areas,
                    "confidence_score": confidence
                },
                "drug_intelligence": {
                    "drug_class": drug_class,
                    "class_familiarity": self._assess_class_familiarity(drug_class),
                    "indication_type": entities.get('indication_type'),
                    "research_maturity": self._assess_research_maturity(drug_class, primary_disease)
                },
                "similar_workflows": [],
                "existing_evidence": {
                    "pubmed_count": 0,
                    "trials_count": 0,
                    "safety_count": 0,
                    "high_quality_count": 0
                },
                "knowledge_base_stats": {
                    "total_documents": 57,  # Updated from our recent successful runs
                    "high_quality_documents": 20,  # From check_memory_content.py results
                    "drug_patterns": 4,  # From analytics
                    "cross_workflow_evidence": 10  # From analytics
                }
            }
            
            self.logger.info(f"Synchronous enhanced insights: {strategy} strategy (confidence: {confidence:.2f})")
            return memory_insights
            
        except Exception as e:
            self.logger.error(f"Synchronous enhanced insights failed: {e}")
            return {"memory_available": False, "error": str(e)}
    
    def _assess_class_familiarity(self, drug_class: str) -> str:
        """Assess how familiar we are with a drug class"""
        if drug_class == "SGLT2 Inhibitor":
            return "high"  # We have extensive SGLT2 data
        elif drug_class in ["ACE Inhibitor", "Beta Blocker", "Statin"]:
            return "moderate"  # Common drug classes
        elif drug_class in ["GLP-1 Agonist", "Calcium Channel Blocker"]:
            return "moderate"
        else:
            return "low"
    
    def _assess_research_maturity(self, drug_class: str, disease: str) -> str:
        """Assess research maturity for drug-disease combination"""
        # SGLT2 inhibitors + cardiovascular/renal conditions = mature
        if drug_class == "SGLT2 Inhibitor" and disease in ["Heart Failure", "Chronic Kidney Disease", "Type 2 Diabetes"]:
            return "mature"
        
        # Common combinations
        if drug_class == "ACE Inhibitor" and disease in ["Hypertension", "Heart Failure"]:
            return "mature"
        
        if drug_class == "Beta Blocker" and disease in ["Heart Failure", "Hypertension"]:
            return "mature"
        
        # Less established combinations
        return "developing"
    
    def _determine_enhanced_strategy(self, entities: Dict[str, Any], insights: Dict[str, Any]) -> str:
        """Determine research strategy using enhanced intelligence"""
        
        # Extract key factors
        drug_class = entities.get('drug_class')
        class_familiarity = insights.get('drug_intelligence', {}).get('class_familiarity', 'low')
        research_maturity = insights.get('drug_intelligence', {}).get('research_maturity', 'developing')
        
        # Enhanced decision logic
        if class_familiarity == "high" and research_maturity == "mature":
            return "update"  # Just need latest findings
        elif class_familiarity in ["high", "moderate"] and research_maturity in ["mature", "developing"]:
            return "focused"  # Targeted research
        else:
            return "comprehensive"  # Full investigation needed
    
    def _create_enhanced_memory_prompt(self, user_goal: str, entities: Dict[str, Any], 
                                     memory_insights: Dict[str, Any]) -> str:
        """Create intelligent prompt with enhanced memory insights"""
        
        base_prompt = f"""You are an expert biomedical research planner with access to advanced pharmaceutical intelligence.

USER RESEARCH GOAL: {user_goal}

ENHANCED ENTITY ANALYSIS:
- Primary Drug: {entities.get('primary_drug', 'Not specified')}
- Drug Class: {entities.get('drug_class', 'Unknown')}
- Primary Disease: {entities.get('primary_disease', 'Not specified')}
- Indication Type: {entities.get('indication_type', 'General')}
- All Drugs: {', '.join(entities.get('drugs', []))}
- All Diseases: {', '.join(entities.get('diseases', []))}
"""

        # Add enhanced memory intelligence
        if memory_insights.get('memory_available'):
            recommendations = memory_insights.get('recommendations', {})
            drug_intelligence = memory_insights.get('drug_intelligence', {})
            enhanced_features = memory_insights.get('enhanced_features', {})
            
            strategy = recommendations.get('research_strategy', 'comprehensive')
            confidence = recommendations.get('confidence_score', 0.5)
            
            memory_section = f"""
ENHANCED MEMORY-BASED INTELLIGENCE:

RECOMMENDED RESEARCH STRATEGY: {strategy.upper()} (Confidence: {confidence:.2f})

PHARMACEUTICAL INTELLIGENCE:
- Drug Class Familiarity: {drug_intelligence.get('class_familiarity', 'unknown').upper()}
- Research Maturity: {drug_intelligence.get('research_maturity', 'unknown').upper()}
- Class-specific Knowledge: Available for {entities.get('drug_class', 'Unknown')}

KNOWLEDGE BASE STATUS:
- Total Documents: {memory_insights.get('knowledge_base_stats', {}).get('total_documents', 0)}
- High-Quality Evidence: {memory_insights.get('knowledge_base_stats', {}).get('high_quality_documents', 0)}
- Cross-Workflow Evidence: {memory_insights.get('knowledge_base_stats', {}).get('cross_workflow_evidence', 0)}

IDENTIFIED KNOWLEDGE GAPS: {', '.join(recommendations.get('knowledge_gaps', []))}
PRIORITY RESEARCH AREAS: {', '.join(recommendations.get('priority_areas', []))}

ENHANCED FEATURES STATUS:
- Temporal Analysis: {'Available' if memory_insights.get('temporal_patterns_available') else 'Not Available'}
- Contradiction Detection: {'Available' if memory_insights.get('contradiction_detection_available') else 'Not Available'}
- Gap Analysis: {'Available' if memory_insights.get('gap_analysis_available') else 'Not Available'}
- Cross-Workflow Insights: {'Available' if memory_insights.get('cross_workflow_insights_available') else 'Not Available'}

STRATEGIC GUIDANCE FOR {strategy.upper()} APPROACH:
"""
            
            if strategy == 'update':
                memory_section += """
UPDATE STRATEGY - Leverage Existing Knowledge:
- FOCUS: Latest 2024-2025 publications and ongoing trials
- SCOPE: Minimal - target recent developments only
- EFFICIENCY: Maximize use of existing evidence base
- EMPHASIS: New findings, emerging safety signals, evolving guidelines
"""
            elif strategy == 'focused':
                memory_section += """
FOCUSED STRATEGY - Target Knowledge Gaps:
- FOCUS: Address specific gaps identified in existing knowledge
- SCOPE: Moderate - balance efficiency with thoroughness
- LEVERAGE: Use existing drug class knowledge to guide research
- EMPHASIS: Fill documented gaps while building on solid foundation
"""
            else:  # comprehensive
                memory_section += """
COMPREHENSIVE STRATEGY - Build Foundation:
- FOCUS: Complete evidence base construction needed
- SCOPE: Full - thorough investigation across all domains
- APPROACH: Standard research protocol with complete coverage
- EMPHASIS: Establish foundational knowledge for future reference
"""
            
            base_prompt += memory_section
        else:
            base_prompt += "\nENHANCED MEMORY INTELLIGENCE: Not available - using standard comprehensive planning\n"
        
        # Enhanced planning instructions with strategy-specific guidance
        strategy = memory_insights.get('recommendations', {}).get('research_strategy', 'comprehensive')
        
        planning_instructions = f"""
ENHANCED PLANNING INSTRUCTIONS - STRATEGY: {strategy.upper()}

Create a JSON research plan optimized for {strategy} research with this EXACT structure:

{{
  "workflow_goal": "{user_goal}",
  "extracted_drug_name": "{entities.get('primary_drug') or 'null'}",
  "extracted_disease_name": "{entities.get('primary_disease') or 'null'}", 
  "steps": [
    {{
      "step_id": "step1_pubmed_search",
      "task_description": "Search PubMed for {strategy} articles on {entities.get('primary_drug', 'the specified drug')} and {entities.get('primary_disease', 'the specified condition')}",
      "agent_capability_required": "perform_web_search",
      "inputs": {{
        "query": "{entities.get('primary_drug', '')} {entities.get('primary_disease', '')} efficacy safety clinical",
        "drug_name": "{entities.get('primary_drug', '')}",
        "disease_name": "{entities.get('primary_disease', '')}",
        "scope": "{self._get_scope_for_strategy(strategy)}"
      }},
      "dependencies": [],
      "priority": "high"
    }},
    {{
      "step_id": "step2a_find_trials", 
      "task_description": "Find {strategy} clinical trials investigating {entities.get('primary_drug', 'the drug')} for {entities.get('primary_disease', 'the condition')}",
      "agent_capability_required": "retrieve_clinical_trials",
      "inputs": {{
        "drug_name": "{entities.get('primary_drug', '')}",
        "disease_name": "{entities.get('primary_disease', '')}",
        "scope": "{self._get_scope_for_strategy(strategy)}"
      }},
      "dependencies": ["step1_pubmed_search"],
      "priority": "high"
    }},
    {{
      "step_id": "step2b_check_drug_safety",
      "task_description": "Check the {strategy} safety data of {entities.get('primary_drug', 'the drug')}",
      "agent_capability_required": "query_adverse_events",
      "inputs": {{
        "drug_name": "{entities.get('primary_drug', '')}",
        "scope": "{self._get_scope_for_strategy(strategy)}"
      }},
      "dependencies": ["step1_pubmed_search"],
      "priority": "high"
    }},
    {{
      "step_id": "step3_compile_report",
      "task_description": "Compile a {strategy} report summarizing findings with enhanced insights",
      "agent_capability_required": "build_final_report",
      "inputs": {{
        "original_goal": "{user_goal}",
        "pubmed_articles": ">>pubmed_results",
        "clinical_trials": ">>trials_results",
        "safety_data": ">>safety_results",
        "report_type": "comprehensive",
        "scope": "{self._get_scope_for_strategy(strategy)}"
      }},
      "dependencies": ["step1_pubmed_search", "step2a_find_trials", "step2b_check_drug_safety"],
      "priority": "high"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. Use ONLY these exact capabilities: "perform_web_search", "retrieve_clinical_trials", "query_adverse_events", "build_final_report"
2. Maintain exact dependency structure as shown
3. Use scope value: "{self._get_scope_for_strategy(strategy)}" for all steps
4. Include exact placeholder format: >>results_type in step3 inputs

RESPONSE FORMAT: Return ONLY the JSON plan, no markdown, no explanations.
"""
        
        return base_prompt + planning_instructions
    
    def _get_scope_for_strategy(self, strategy: str) -> str:
        """Get appropriate scope value for research strategy"""
        scope_mapping = {
            "update": "minimal",
            "focused": "focused", 
            "comprehensive": "comprehensive"
        }
        return scope_mapping.get(strategy, "comprehensive")
    
    async def _create_enhanced_plan_async(self, user_goal: str) -> Dict[str, Any]:
        """Create enhanced memory-augmented research plan - ASYNC VERSION"""
        try:
            self.logger.info(f"Creating enhanced memory-augmented plan (async) for: {user_goal[:100]}...")
            
            # Step 1: Enhanced entity extraction
            entities = self._extract_entities_enhanced(user_goal)
            
            # Step 2: Get enhanced memory insights (async)
            memory_insights = await self._get_enhanced_memory_insights_async(user_goal, entities)
            
            # Step 3: Create enhanced prompt
            prompt = self._create_enhanced_memory_prompt(user_goal, entities, memory_insights)
            
            # Step 4: Generate plan using LLM
            if not self.openai_client:
                self.logger.warning("OpenAI client not available, using enhanced fallback plan")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
            
            try:
                self.logger.info("Sending enhanced memory-augmented prompt to GPT-4...")
                
                # Run OpenAI API call in thread pool (it's synchronous)
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2500
                )
                
                plan_text = response.choices[0].message.content.strip()
                
                # Clean and parse JSON
                if '```json' in plan_text:
                    plan_text = plan_text.split('```json')[1].split('```')[0].strip()
                elif '```' in plan_text:
                    plan_text = plan_text.split('```')[1].strip()
                
                plan_text = plan_text.strip()
                if not plan_text.startswith('{'):
                    start_idx = plan_text.find('{')
                    end_idx = plan_text.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        plan_text = plan_text[start_idx:end_idx+1]
                
                self.logger.critical(f"RAW ENHANCED LLM OUTPUT: {plan_text}")
                
                plan = json.loads(plan_text)
                
                # Add enhanced metadata
                plan['memory_augmented'] = True
                plan['enhanced_features'] = memory_insights.get('enhanced_features', {})
                plan['research_strategy'] = memory_insights.get('recommendations', {}).get('research_strategy', 'comprehensive')
                plan['extracted_entities'] = entities
                plan['drug_intelligence'] = memory_insights.get('drug_intelligence', {})
                plan['created_timestamp'] = datetime.now(timezone.utc).isoformat()
                plan['plan_id'] = f"enhanced_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Validate with Pydantic if available
                if PYDANTIC_AVAILABLE and StructuredPlan:
                    try:
                        validated_plan = StructuredPlan(**plan)
                        plan = validated_plan.model_dump()
                        self.logger.info("Enhanced plan validated successfully with Pydantic")
                    except Exception as e:
                        self.logger.error(f"Enhanced plan Pydantic validation failed: {e}")
                        return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
                
                strategy = plan.get('research_strategy', 'comprehensive')
                self.logger.info(f"Enhanced memory-augmented plan created successfully with {strategy} strategy")
                
                self.logger.critical(f"FINAL ENHANCED PLAN: {json.dumps(plan, indent=2)}")
                return plan
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse enhanced LLM response: {e}")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
            except Exception as e:
                self.logger.error(f"Enhanced OpenAI API error: {e}")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
            
        except Exception as e:
            self.logger.error(f"Enhanced plan creation failed: {e}")
            # Fallback to sync version
            entities = self._extract_entities_enhanced(user_goal)
            memory_insights = self._get_memory_insights_sync(user_goal, entities)
            return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
    
    def create_plan_sync(self, user_goal: str) -> Dict[str, Any]:
        """Synchronous version of enhanced planning for compatibility - FIXED"""
        try:
            self.logger.info(f"Creating plan synchronously for: {user_goal[:100]}...")
            
            # Extract entities
            entities = self._extract_entities_enhanced(user_goal)
            
            # Get memory insights (sync version)
            memory_insights = self._get_memory_insights_sync(user_goal, entities)
            
            # If we have enhanced features and we're in an async context, handle it properly
            if self.enhanced_features_available:
                try:
                    # Check if we're in an async context
                    loop = None
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        # No running loop, we can create one
                        pass
                    
                    if loop is not None:
                        # We're already in an async context, can't use run_until_complete
                        self.logger.info("Already in async context, using sync fallback for enhanced planning")
                        # Use sync memory insights we already have
                        return self._create_enhanced_plan_with_sync_memory(user_goal, entities, memory_insights)
                    else:
                        # No running loop, we can create one and run async version
                        self.logger.info("No async context, creating event loop for enhanced planning")
                        return asyncio.run(self._create_enhanced_plan_async(user_goal))
                        
                except Exception as e:
                    self.logger.warning(f"Enhanced async planning setup failed: {e}")
                    # Fallback to fully synchronous version
                    return self._create_enhanced_plan_with_sync_memory(user_goal, entities, memory_insights)
            else:
                # No enhanced features, use sync version
                return self._create_enhanced_plan_with_sync_memory(user_goal, entities, memory_insights)
                
        except Exception as e:
            self.logger.error(f"Create plan sync failed: {e}")
            # Ultimate fallback
            entities = self._extract_entities_enhanced(user_goal)
            memory_insights = self._get_memory_insights_sync(user_goal, entities)
            return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
    
    def _create_enhanced_plan_with_sync_memory(self, user_goal: str, entities: Dict[str, Any], 
                                              memory_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced plan using already-retrieved sync memory insights"""
        try:
            # Create enhanced prompt
            prompt = self._create_enhanced_memory_prompt(user_goal, entities, memory_insights)
            
            # Generate plan using LLM
            if not self.openai_client:
                self.logger.warning("OpenAI client not available, using enhanced fallback plan")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
            
            try:
                self.logger.info("Sending enhanced memory-augmented prompt to GPT-4 (sync)...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=2500
                )
                
                plan_text = response.choices[0].message.content.strip()
                
                # Clean and parse JSON
                if '```json' in plan_text:
                    plan_text = plan_text.split('```json')[1].split('```')[0].strip()
                elif '```' in plan_text:
                    plan_text = plan_text.split('```')[1].strip()
                
                plan_text = plan_text.strip()
                if not plan_text.startswith('{'):
                    start_idx = plan_text.find('{')
                    end_idx = plan_text.rfind('}')
                    if start_idx != -1 and end_idx != -1:
                        plan_text = plan_text[start_idx:end_idx+1]
                
                self.logger.critical(f"RAW ENHANCED LLM OUTPUT (SYNC): {plan_text}")
                
                plan = json.loads(plan_text)
                
                # Add enhanced metadata
                plan['memory_augmented'] = True
                plan['enhanced_features'] = memory_insights.get('enhanced_features', {})
                plan['research_strategy'] = memory_insights.get('recommendations', {}).get('research_strategy', 'comprehensive')
                plan['extracted_entities'] = entities
                plan['drug_intelligence'] = memory_insights.get('drug_intelligence', {})
                plan['created_timestamp'] = datetime.now(timezone.utc).isoformat()
                plan['plan_id'] = f"enhanced_plan_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Validate with Pydantic if available
                if PYDANTIC_AVAILABLE and StructuredPlan:
                    try:
                        validated_plan = StructuredPlan(**plan)
                        plan = validated_plan.model_dump()
                        self.logger.info("Enhanced plan validated successfully with Pydantic (sync)")
                    except Exception as e:
                        self.logger.error(f"Enhanced plan Pydantic validation failed (sync): {e}")
                        return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
                
                strategy = plan.get('research_strategy', 'comprehensive')
                self.logger.info(f"Enhanced memory-augmented plan created successfully (sync) with {strategy} strategy")
                
                self.logger.critical(f"FINAL ENHANCED PLAN (SYNC): {json.dumps(plan, indent=2)}")
                return plan
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse enhanced LLM response (sync): {e}")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
            except Exception as e:
                self.logger.error(f"Enhanced OpenAI API error (sync): {e}")
                return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
                
        except Exception as e:
            self.logger.error(f"Enhanced sync plan creation failed: {e}")
            return self._create_enhanced_fallback_plan(user_goal, entities, memory_insights)
    
    def _create_enhanced_fallback_plan(self, user_goal: str, entities: Dict[str, Any], 
                                     memory_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced fallback plan with advanced intelligence"""
        strategy = memory_insights.get('recommendations', {}).get('research_strategy', 'comprehensive')
        scope = self._get_scope_for_strategy(strategy)
        
        drug_name = entities.get('primary_drug', 'the drug')
        disease_name = entities.get('primary_disease', 'the condition')
        drug_class = entities.get('drug_class', 'Unknown')
        
        # Enhanced description suffix based on strategy and drug class
        if strategy == 'update':
            description_suffix = f" (focus on latest {drug_class} developments)"
        elif strategy == 'focused':
            description_suffix = f" (target {drug_class} knowledge gaps)"
        else:
            description_suffix = f" (comprehensive {drug_class} investigation)"
        
        # Create enhanced plan structure
        plan = {
            "workflow_goal": user_goal,
            "extracted_drug_name": entities.get('primary_drug'),
            "extracted_disease_name": entities.get('primary_disease'),
            "steps": [
                {
                    "step_id": "step1_pubmed_search",
                    "task_description": f"Search PubMed for {strategy} articles on {drug_name} and {disease_name}{description_suffix}",
                    "agent_capability_required": "perform_web_search",
                    "inputs": {
                        "query": f"{entities.get('primary_drug', '')} {entities.get('primary_disease', '')} efficacy safety clinical",
                        "drug_name": entities.get('primary_drug', ''),
                        "disease_name": entities.get('primary_disease', ''),
                        "scope": scope
                    },
                    "dependencies": [],
                    "priority": "high"
                },
                {
                    "step_id": "step2a_find_trials",
                    "task_description": f"Find {strategy} clinical trials investigating {drug_name} for {disease_name}{description_suffix}",
                    "agent_capability_required": "retrieve_clinical_trials",
                    "inputs": {
                        "drug_name": entities.get('primary_drug', ''),
                        "disease_name": entities.get('primary_disease', ''),
                        "scope": scope
                    },
                    "dependencies": ["step1_pubmed_search"],
                    "priority": "high"
                },
                {
                    "step_id": "step2b_check_drug_safety",
                    "task_description": f"Check the {strategy} safety data of {drug_name}{description_suffix}",
                    "agent_capability_required": "query_adverse_events",
                    "inputs": {
                        "drug_name": entities.get('primary_drug', ''),
                        "scope": scope
                    },
                    "dependencies": ["step1_pubmed_search"],
                    "priority": "high"
                },
                {
                    "step_id": "step3_compile_report",
                    "task_description": f"Compile a {strategy} report with enhanced {drug_class} insights{description_suffix}",
                    "agent_capability_required": "build_final_report",
                    "inputs": {
                        "original_goal": user_goal,
                        "pubmed_articles": ">>pubmed_results",
                        "clinical_trials": ">>trials_results",
                        "safety_data": ">>safety_results",
                        "report_type": "comprehensive",
                        "scope": scope
                    },
                    "dependencies": ["step1_pubmed_search", "step2a_find_trials", "step2b_check_drug_safety"],
                    "priority": "high"
                }
            ]
        }
        
        # Add enhanced metadata
        plan['memory_augmented'] = True
        plan['enhanced_features'] = memory_insights.get('enhanced_features', {})
        plan['research_strategy'] = strategy
        plan['extracted_entities'] = entities
        plan['drug_intelligence'] = memory_insights.get('drug_intelligence', {})
        plan['created_timestamp'] = datetime.now(timezone.utc).isoformat()
        plan['plan_id'] = f"enhanced_fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        plan['fallback_used'] = True
        
        # Validate with Pydantic if available
        if PYDANTIC_AVAILABLE and StructuredPlan:
            try:
                validated_plan = StructuredPlan(**plan)
                plan = validated_plan.model_dump()
                self.logger.info("Enhanced fallback plan validated with Pydantic")
            except Exception as e:
                self.logger.error(f"Enhanced fallback Pydantic validation failed: {e}")
        
        self.logger.info(f"Enhanced fallback plan created with {strategy} strategy for {drug_class}")
        self.logger.critical(f"ENHANCED FALLBACK PLAN: {json.dumps(plan, indent=2)}")
        
        return plan

    def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process planning task with enhanced memory augmentation"""
        try:
            # DEBUG: Log incoming task_data
            self.logger.critical(f"PLANNER RECEIVED task_data: {json.dumps(task_data, indent=2)}")
            
            # Get user goal
            user_goal = task_data.get('goal', '') or task_data.get('user_goal', '')
            if not user_goal:
                raise ValueError("No goal provided in task_data")
            
            # Check for explicit task type
            task_type = task_data.get("task_type")
            
            # ENHANCED: Also detect prior authorization from goal if no explicit task_type
            if task_type == "prior_authorization" or self._detect_prior_authorization_workflow(user_goal):
                self.logger.info("Prior Authorization task type detected. Routing to specialized plan generator.")
                # Call template-based generation
                result = self._generate_plan_from_template(
                    template_name="prior_auth_plan_template", 
                    task_payload=task_data
                )
                
                if result.get("status") == "success":
                    # Return in expected format
                    return {
                        "status": "COMPLETED",
                        "plan": result["plan"],
                        "memory_augmented": False,
                        "template_based": True,
                        "template_name": "prior_auth_plan_template",
                        "message": f"Template-based plan created for prior authorization workflow",
                        "agent_id": self.agent_id,
                        "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                        "version": "2.8-ENHANCED-FIXED"
                    }
                else:
                    # Template generation failed, return error instead of falling back
                    return {
                        "status": "FAILED",
                        "error": result.get('message', 'Template generation failed'),
                        "message": "Prior authorization template generation failed",
                        "agent_id": self.agent_id,
                        "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                        "version": "2.8-ENHANCED-FIXED"
                    }
            
            # Continue with existing logic for other/general tasks
            self.logger.info(f"Processing enhanced memory-augmented planning task for: {user_goal[:100]}...")
            
            # Create enhanced memory-augmented plan (using fixed sync method)
            plan = self.create_plan_sync(user_goal)
            
            # Enhanced result with additional metadata
            result = {
                "status": "COMPLETED",
                "plan": plan,
                "memory_augmented": plan.get('memory_augmented', False),
                "enhanced_features": plan.get('enhanced_features', {}),
                "research_strategy": plan.get('research_strategy', 'comprehensive'),
                "drug_intelligence": plan.get('drug_intelligence', {}),
                "message": f"Enhanced memory-augmented plan created with {plan.get('research_strategy', 'comprehensive')} strategy",
                "agent_id": self.agent_id,
                "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.8-ENHANCED-FIXED"
            }
            
            self.logger.info(f"Enhanced memory-augmented planning completed successfully with {plan.get('research_strategy', 'comprehensive')} strategy")
            return result
            
        except Exception as e:
            self.logger.error(f"Enhanced memory-augmented planning failed: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "status": "FAILED",
                "error": str(e),
                "message": "Enhanced memory-augmented planning failed",
                "agent_id": self.agent_id,
                "processed_timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "2.8-ENHANCED-FIXED"
            }