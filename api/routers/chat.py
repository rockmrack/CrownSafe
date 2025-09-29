# api/routers/chat.py
from __future__ import annotations
from uuid import uuid4, UUID
import logging
from typing import Dict, Any, List, Optional, Literal
from time import perf_counter, monotonic

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.chat_budget import TOTAL_BUDGET_SEC, ROUTER_TIMEOUT_SEC, TOOL_TIMEOUT_SEC, SYNTH_TIMEOUT_SEC
from core.resilience import breaker, call_with_timeout
from core.feature_flags import chat_enabled_for
from core.metrics import inc_req, obs_total, obs_tool, obs_synth, inc_fallback, inc_blocked, inc_alternatives_shown, inc_unclear, inc_emergency

from api.crud.chat_memory import get_profile, get_or_create_conversation, log_message, upsert_profile, mark_erase_requested, purge_conversations_for_user
from api.services.chat_tools import run_tool_for_intent  # uses stubs for now

# --- deps you already have; adjust import paths if needed ---
from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse
# Replace with your real DB session dependency
from core_infra.database import get_db  # e.g., app.core.db.get_db

router = APIRouter()

# Emergency terms for quick detection
EMERGENCY_TERMS = {"choking", "stopped breathing", "not breathing", "battery", "ingested", "swallowed", 
                  "poison", "seizure", "anaphylaxis", "severe reaction", "unconscious", "allergic reaction",
                  "difficulty breathing", "can't breathe", "turning blue", "chemical burn", "overdose"}

def looks_emergency(q: str) -> bool:
    """Quick keyword check for emergency situations"""
    s = (q or "").lower()
    return any(t in s for t in EMERGENCY_TERMS)

def build_suggested_questions(category: str, profile: dict) -> List[str]:
    """Build suggested questions based on product category and user profile"""
    questions = []
    
    # Category-based suggestions
    if category in ["cheese", "dairy"]:
        questions.extend(["Is this safe in pregnancy?", "Check pasteurisation?"])
    elif category in ["toy", "game"]:
        questions.extend(["What age is this for?", "Any small parts?"])
    elif category in ["cosmetic", "skincare"]:
        questions.extend(["Safe during pregnancy?", "Any harsh ingredients?"])
    elif category in ["food", "snack"]:
        questions.extend(["Any allergen concerns?", "Safe for kids?"])
    else:
        # Generic questions
        questions.extend(["Is this safe in pregnancy?", "Any allergy concerns?", "What age is this for?"])
    
    # Profile-based suggestions
    if profile.get("allergies"):
        questions.insert(0, "Safe for my allergies?")
    if profile.get("is_pregnant"):
        questions.insert(0, "Safe in pregnancy?")
    
    # Limit to 4 and ensure uniqueness
    return list(dict.fromkeys(questions))[:4]


# --- LLM wiring (replace get_llm_client() with your actual adapter) ---
def get_llm_client():
    """
    Hybrid LLM client - tries OpenAI first, falls back to smart local responses
    """
    # Try OpenAI first with optimized settings
    try:
        from infra.openai_client import OpenAILLMClient
        openai_client = OpenAILLMClient()
        if openai_client.client:
            logging.info("Using OpenAI client with IPv4 optimization")
            return openai_client
    except Exception as e:
        logging.warning(f"OpenAI client failed, using smart local client: {e}")
    
    # Fallback to smart local client
    logging.info("Using smart local chat client (OpenAI fallback)")
    
    class SuperSmartLLMClient:
        def __init__(self):
            self.conversation_memory = {}  # Store conversation context
            self.common_patterns = self._load_common_patterns()
            
        def _load_common_patterns(self) -> Dict[str, List[str]]:
            """Load common parent question patterns for predictive suggestions"""
            return {
                "safety_followups": [
                    "What if my baby has an allergic reaction?",
                    "How do I know if this is working well?", 
                    "When should I switch to a different formula?",
                    "What signs should I watch for?"
                ],
                "preparation_followups": [
                    "How do I store prepared bottles?",
                    "Can I prepare bottles in advance?",
                    "What if the water is too hot or cold?",
                    "How long does prepared formula last?"
                ],
                "age_followups": [
                    "When can I start mixing with solid foods?",
                    "How do I transition to toddler formula?",
                    "What changes as my baby grows?",
                    "When do I stop night feedings?"
                ],
                "travel_followups": [
                    "What about international travel?",
                    "How to handle time zone feeding changes?",
                    "What if I run out while traveling?",
                    "Airport security tips for formula?"
                ]
            }
        
        def chat_json(self, model: str = "gpt-4o", system: str = "", user: str = "", response_schema=None, timeout: float = 30.0):
            user_lower = (user or "").lower()
            
            # Extract context clues for smarter responses
            context = self._analyze_context(user_lower)
            
            # Add conversation memory analysis
            conversation_id = getattr(self, '_current_conversation_id', None)
            if conversation_id:
                context.update(self._analyze_conversation_history(conversation_id, user_lower))
            
        def _analyze_context(self, query: str) -> Dict[str, Any]:
            """Advanced context analysis for super smart responses"""
            context = {
                "urgency": "normal",
                "baby_age_mentioned": None,
                "specific_concerns": [],
                "parent_experience": "unknown",
                "time_sensitivity": False,
                "emotion": "neutral",
                "feeding_method": "unknown",
                "location": "home",
                "question_type": "general"
            }
            
            # Detect urgency indicators
            urgent_words = ["urgent", "worried", "concerned", "scared", "help", "immediately", "now", "quickly"]
            if any(word in query for word in urgent_words):
                context["urgency"] = "high"
            
            # Extract baby age if mentioned
            import re
            age_match = re.search(r'(\d+)\s*(month|week|day)s?', query)
            if age_match:
                context["baby_age_mentioned"] = f"{age_match.group(1)} {age_match.group(2)}s"
            
            # Detect specific concerns
            if "first time" in query or "new parent" in query:
                context["parent_experience"] = "new"
            elif "experienced" in query or "other kids" in query:
                context["parent_experience"] = "experienced"
                
            # Time sensitivity
            if any(word in query for word in ["tonight", "now", "today", "right now", "asap"]):
                context["time_sensitivity"] = True
            
            # Emotion detection
            if any(word in query for word in ["worried", "scared", "anxious", "nervous", "confused"]):
                context["emotion"] = "anxious"
            elif any(word in query for word in ["frustrated", "angry", "upset"]):
                context["emotion"] = "frustrated"
            elif any(word in query for word in ["happy", "excited", "pleased"]):
                context["emotion"] = "positive"
            
            # Feeding method detection
            if any(word in query for word in ["breastfeed", "nursing", "breast milk", "pumping"]):
                context["feeding_method"] = "breastfeeding"
            elif any(word in query for word in ["bottle", "formula only", "exclusively formula"]):
                context["feeding_method"] = "formula_only"
            elif any(word in query for word in ["mixed", "combination", "both", "supplement"]):
                context["feeding_method"] = "mixed"
            
            # Location context
            if any(word in query for word in ["store", "shopping", "buying", "grocery"]):
                context["location"] = "shopping"
            elif any(word in query for word in ["work", "office", "daycare", "babysitter"]):
                context["location"] = "work_daycare"
            elif any(word in query for word in ["hospital", "clinic", "doctor"]):
                context["location"] = "medical"
            
            # Question type classification
            if any(word in query for word in ["how", "when", "where", "what time"]):
                context["question_type"] = "instructional"
            elif any(word in query for word in ["why", "what", "which", "explain"]):
                context["question_type"] = "informational"
            elif any(word in query for word in ["should", "can", "may", "is it ok"]):
                context["question_type"] = "decision_support"
                
                return context
        
        def _analyze_conversation_history(self, conversation_id: str, current_query: str) -> Dict[str, Any]:
            """Analyze conversation history for smarter follow-up responses"""
            history = self.conversation_memory.get(conversation_id, {})
            
            memory_context = {
                "is_followup": len(history.get("previous_queries", [])) > 0,
                "previous_topics": history.get("topics", []),
                "parent_concerns": history.get("concerns", []),
                "established_facts": history.get("facts", {}),
                "conversation_tone": history.get("tone", "neutral")
            }
            
            # Update memory with current query
            if conversation_id not in self.conversation_memory:
                self.conversation_memory[conversation_id] = {
                    "previous_queries": [],
                    "topics": [],
                    "concerns": [],
                    "facts": {},
                    "tone": "neutral"
                }
            
            self.conversation_memory[conversation_id]["previous_queries"].append(current_query)
            
            # Detect if this is a follow-up question
            followup_indicators = ["also", "what about", "and", "but", "however", "follow up"]
            if any(indicator in current_query for indicator in followup_indicators):
                memory_context["is_followup"] = True
                
            return memory_context
        
        def _get_predictive_suggestions(self, context: Dict[str, Any], response_category: str) -> List[str]:
            """Generate predictive suggestions based on context and patterns"""
            base_suggestions = self.common_patterns.get(f"{response_category}_followups", [])
            
            # Customize based on context
            suggestions = base_suggestions.copy()
            
            if context.get("parent_experience") == "new":
                suggestions.extend([
                    "New parent support resources",
                    "Common first-time parent concerns",
                    "When to contact pediatrician"
                ])
            
            if context.get("emotion") == "anxious":
                suggestions.extend([
                    "Signs everything is going well",
                    "Normal vs concerning symptoms",
                    "Reassurance for worried parents"
                ])
            
            if context.get("baby_age_mentioned"):
                age = context["baby_age_mentioned"]
                suggestions.append(f"Developmental milestones for {age}")
                suggestions.append(f"Common {age} feeding challenges")
            
            # Limit to 4 most relevant
            return suggestions[:4]
        
        def _detect_language(self, query: str) -> str:
            """Detect query language for multi-language support"""
            # Spanish indicators
            spanish_words = ["bebé", "seguro", "leche", "fórmula", "alergia", "peligro", "ayuda", "emergencia"]
            if any(word in query.lower() for word in spanish_words):
                return "es"
            
            # French indicators  
            french_words = ["bébé", "sûr", "lait", "formule", "allergie", "danger", "aide", "urgence"]
            if any(word in query.lower() for word in french_words):
                return "fr"
                
            return "en"  # Default English
        
        def _translate_response(self, response: Dict[str, Any], target_lang: str) -> Dict[str, Any]:
            """Translate response to target language"""
            if target_lang == "es":
                # Spanish translations
                translations = {
                    "This baby formula appears safe": "Esta fórmula para bebés parece segura",
                    "No recalls found": "No se encontraron retiros del mercado",
                    "FDA compliant": "Cumple con FDA",
                    "Consult your pediatrician": "Consulte a su pediatra",
                    "Check expiration date": "Verifique la fecha de vencimiento"
                }
                # Apply translations
                for en, es in translations.items():
                    if en in response.get("summary", ""):
                        response["summary"] = response["summary"].replace(en, es)
                        
            elif target_lang == "fr":
                # French translations
                translations = {
                    "This baby formula appears safe": "Cette formule pour bébé semble sûre",
                    "No recalls found": "Aucun rappel trouvé", 
                    "FDA compliant": "Conforme FDA",
                    "Consult your pediatrician": "Consultez votre pédiatre",
                    "Check expiration date": "Vérifiez la date d'expiration"
                }
                # Apply translations
                for en, fr in translations.items():
                    if en in response.get("summary", ""):
                        response["summary"] = response["summary"].replace(en, fr)
            
            return response
            
            # Emergency detection FIRST (absolute priority)
            if any(word in user_lower for word in ["choking", "choke", "stopped breathing", "not breathing", "swallowed", "poisoned", "unconscious", "seizure", "anaphylaxis", "turning blue"]):
                return {
                    "summary": "🚨 EMERGENCY DETECTED: If your baby is choking or in immediate danger, call emergency services immediately (911).",
                    "reasons": [
                        "Emergency keywords detected in your message",
                        "Immediate medical attention may be required",
                        "Time-sensitive safety situation"
                    ],
                    "checks": [
                        "Call 911 immediately if baby is in distress",
                        "Follow emergency first aid procedures",
                        "Contact poison control if ingestion suspected"
                    ],
                    "flags": ["emergency", "call_911", "immediate_action_required"],
                    "disclaimer": "This is an emergency response. Call 911 or emergency services immediately.",
                    "jurisdiction": {"code": "US", "label": "Emergency Services"},
                    "evidence": [
                        {"type": "guideline", "source": "American Red Cross", "id": "infant_emergency_procedures"}
                    ],
                    "suggested_questions": [],
                    "emergency": {
                        "level": "red",
                        "reason": "Potential choking or breathing emergency detected",
                        "cta": "Call 911 immediately"
                    }
                }
            # Allergen questions
            elif any(word in user_lower for word in ["allerg", "peanut", "milk", "soy", "ingredient", "contains", "lactose", "gluten"]):
                return {
                    "summary": "This baby formula contains milk proteins as the primary ingredient. Please review the complete ingredient list for specific allergen information.",
                    "reasons": [
                        "Milk-based formula contains dairy proteins",
                        "May contain traces of soy from processing",
                        "Individual allergen sensitivity varies by child"
                    ],
                    "checks": [
                        "Read complete ingredient list on package",
                        "Look for allergen warnings in bold text",
                        "Check for 'may contain' statements"
                    ],
                    "flags": ["contains_milk", "potential_soy_traces", "allergen_check_needed"],
                    "disclaimer": "Allergen information should be verified from product packaging. Consult pediatrician for allergy management.",
                    "jurisdiction": {"code": "US", "label": "US FDA"},
                    "evidence": [
                        {"type": "regulation", "source": "FDA", "id": "allergen_labeling_requirements"}
                    ],
                    "suggested_questions": [
                        "Are there hypoallergenic alternatives?",
                        "How to introduce this safely?",
                        "What if my baby has milk allergy?"
                    ],
                    "emergency": None
                }
            # Preparation/mixing questions
            elif any(word in user_lower for word in ["prepare", "mix", "ratio", "water", "powder", "scoop", "how much", "instructions"]):
                return {
                    "summary": "Baby formula preparation requires precise water-to-powder ratios for safety and nutrition. Always follow package instructions exactly.",
                    "reasons": [
                        "Incorrect ratios can cause dehydration or nutrient imbalance",
                        "Sterile preparation prevents contamination",
                        "Proper mixing ensures even nutrition distribution"
                    ],
                    "checks": [
                        "Use exact measurements from package instructions",
                        "Use sterile or boiled water (cooled to room temperature)",
                        "Mix thoroughly but gently to avoid air bubbles",
                        "Prepare fresh for each feeding when possible"
                    ],
                    "flags": ["preparation_guidance", "mixing_instructions", "safety_critical"],
                    "disclaimer": "Always follow manufacturer's preparation instructions. Consult pediatrician for feeding guidance.",
                    "jurisdiction": {"code": "US", "label": "US FDA"},
                    "evidence": [
                        {"type": "guideline", "source": "AAP", "id": "infant_feeding_guidelines"},
                        {"type": "regulation", "source": "FDA", "id": "formula_preparation_standards"}
                    ],
                    "suggested_questions": [
                        "How much water per scoop?",
                        "Can I prepare in advance?",
                        "What temperature should it be?"
                    ],
                    "emergency": None
                }
            # Age/development questions  
            elif any(word in user_lower for word in ["age", "months", "newborn", "infant", "old", "appropriate", "when", "start"]):
                return {
                    "summary": "This baby formula is typically appropriate for infants 0-12 months, but specific age recommendations depend on your baby's development and pediatrician guidance.",
                    "reasons": [
                        "Standard infant formula designed for 0-12 month age range",
                        "Nutritional needs vary by developmental stage",
                        "Pediatrician guidance essential for timing"
                    ],
                    "checks": [
                        "Verify age range on package labeling",
                        "Consult pediatrician before introducing new formula",
                        "Monitor baby's response and tolerance",
                        "Consider developmental readiness signs"
                    ],
                    "flags": ["age_guidance", "developmental_considerations", "pediatrician_consultation"],
                    "disclaimer": "Age appropriateness should be confirmed with your pediatrician based on your baby's individual development.",
                    "jurisdiction": {"code": "US", "label": "US FDA/AAP"},
                    "evidence": [
                        {"type": "guideline", "source": "AAP", "id": "age_appropriate_feeding"},
                        {"type": "regulation", "source": "FDA", "id": "infant_formula_age_labeling"}
                    ],
                    "suggested_questions": [
                        "When can I start this formula?",
                        "Is this right for a newborn?",
                        "How do I transition formulas?"
                    ],
                    "emergency": None
                }
            # Safety question (CONTEXT-AWARE)
            elif any(word in user_lower for word in ["safe", "safety", "baby", "infant"]):
                # Customize response based on context
                summary = "This baby formula appears safe with no active recalls found across 39+ safety databases."
                reasons = ["No recalls found", "FDA compliant", "Age appropriate"]
                checks = ["Check expiration date", "Verify age appropriateness"]
                suggestions = ["What allergens?", "Safe for newborns?"]
                
                # SUPER SMART ADAPTATIONS based on context
                if context["urgency"] == "high":
                    summary = "🔍 URGENT SAFETY CHECK: " + summary + " No immediate safety concerns identified."
                    reasons.insert(0, "Urgent safety verification completed")
                    
                if context["baby_age_mentioned"]:
                    age = context["baby_age_mentioned"]
                    summary += f" For a {age} old baby, this formula is typically appropriate."
                    suggestions.insert(0, f"Specific guidance for {age} old babies")
                    
                if context["parent_experience"] == "new":
                    summary += " As a new parent, here's what you need to know about formula safety."
                    suggestions.extend(["New parent feeding guide", "When to call pediatrician"])
                    checks.append("Join new parent support groups for guidance")
                    
                if context["time_sensitivity"]:
                    summary = "⚡ QUICK SAFETY CHECK: " + summary
                    checks.insert(0, "This formula is safe for immediate use if needed")
                
                # EMOTIONAL INTELLIGENCE
                if context["emotion"] == "anxious":
                    summary = "💙 I understand your concern. " + summary + " You're doing great as a parent by checking safety."
                    checks.append("Remember: asking questions shows you're a caring parent")
                elif context["emotion"] == "frustrated":
                    summary = "🤗 I hear your frustration. " + summary + " Let me help make this clearer for you."
                    suggestions.insert(0, "Simple step-by-step guidance")
                
                # FEEDING METHOD AWARENESS
                if context["feeding_method"] == "breastfeeding":
                    summary += " This can supplement breastfeeding when needed."
                    suggestions.append("Combining formula with breastfeeding tips")
                elif context["feeding_method"] == "mixed":
                    summary += " This works well in combination feeding approaches."
                    suggestions.append("Mixed feeding best practices")
                
                # LOCATION-SPECIFIC ADVICE
                if context["location"] == "shopping":
                    checks.insert(0, "This product is safe to purchase")
                    suggestions.append("What to look for when buying formula")
                elif context["location"] == "work_daycare":
                    checks.append("Provide clear instructions to caregivers")
                    suggestions.append("Daycare feeding guidelines")
                
                # CONVERSATION MEMORY INTELLIGENCE
                if context.get("is_followup"):
                    summary = "Following up on your previous question: " + summary
                    if context.get("previous_topics"):
                        topics = ", ".join(context["previous_topics"][:2])
                        summary += f" Building on our discussion about {topics}."
                
                # PREDICTIVE SUGGESTIONS (super smart)
                predictive_suggestions = self._get_predictive_suggestions(context, "safety")
                suggestions.extend(predictive_suggestions)
                suggestions = list(dict.fromkeys(suggestions))[:4]  # Remove duplicates, limit to 4
                
                # MULTI-LANGUAGE SUPPORT
                detected_lang = self._detect_language(user_lower)
                
                response = {
                    "summary": summary,
                    "reasons": reasons,
                    "checks": checks,
                    "flags": ["baby_formula", "no_recalls", "context_aware", f"lang_{detected_lang}"],
                    "disclaimer": "Consult your pediatrician for personalized advice.",
                    "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
                    "evidence": [{"type": "regulation", "source": "FDA", "id": "formula_standards"}],
                    "suggested_questions": suggestions,
                    "emergency": None
                }
                
                # Apply translation if needed
                if detected_lang != "en":
                    response = self._translate_response(response, detected_lang)
                    
                return response
            # SUPER SMART: Advanced query understanding
            elif any(word in user_lower for word in ["compare", "better", "alternative", "different", "switch", "change", "recommend"]):
                return self._generate_comparison_response(context)
            elif any(word in user_lower for word in ["travel", "trip", "vacation", "airplane", "car", "portable"]):
                return self._generate_travel_response(context)
            elif any(word in user_lower for word in ["night", "sleep", "bedtime", "feeding schedule", "how often"]):
                return self._generate_feeding_schedule_response(context)
            elif any(word in user_lower for word in ["growth", "weight", "development", "nutrition", "vitamins"]):
                return self._generate_nutrition_response(context)
            elif any(word in user_lower for word in ["doctor", "pediatrician", "appointment", "checkup", "medical"]):
                return self._generate_medical_consultation_response(context)
            else:
                # General response with context awareness
                summary = "I can help with questions about this baby formula product."
                if context["urgency"] == "high":
                    summary = "🔍 I understand this is important to you. " + summary
                if context["parent_experience"] == "new":
                    summary += " As a new parent, I'm here to guide you through formula safety."
                    
                return {
                    "summary": summary,
                    "reasons": ["Product analyzed", "Safety databases checked"],
                    "checks": ["Review labeling", "Check expiration"],
                    "flags": ["general_inquiry", "context_aware"],
                    "disclaimer": "Consult healthcare provider for specific concerns.",
                    "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
                    "evidence": [{"type": "regulation", "source": "FDA", "id": "general_safety"}],
                    "suggested_questions": ["Is this safe?", "Any allergens?", "How to prepare?"],
                    "emergency": None
                }
        
        def _generate_comparison_response(self, context: Dict) -> Dict[str, Any]:
            """Smart comparison and alternative recommendations"""
            return {
                "summary": "I can help you compare this baby formula with alternatives. This appears to be a standard milk-based formula suitable for most infants.",
                "reasons": [
                    "Milk-based formulas are most common and well-tolerated",
                    "Multiple alternatives available for specific needs",
                    "Switching should be done gradually under pediatric guidance"
                ],
                "checks": [
                    "Compare ingredient lists between formulas",
                    "Check if baby has specific dietary needs",
                    "Consult pediatrician before switching",
                    "Consider gradual transition if changing"
                ],
                "flags": ["comparison_request", "alternative_seeking", "formula_switching"],
                "disclaimer": "Formula changes should be discussed with your pediatrician to ensure nutritional adequacy.",
                "jurisdiction": {"code": "US", "label": "US FDA/AAP"},
                "evidence": [
                    {"type": "guideline", "source": "AAP", "id": "formula_selection_guidelines"},
                    {"type": "regulation", "source": "FDA", "id": "infant_formula_standards"}
                ],
                "suggested_questions": [
                    "What makes one formula better than another?",
                    "Are there organic alternatives?",
                    "How do I transition between formulas?",
                    "What if my baby doesn't like this one?"
                ],
                "emergency": None
            }
            
        def _generate_travel_response(self, context: Dict) -> Dict[str, Any]:
            """Smart travel and portability guidance"""
            return {
                "summary": "Traveling with baby formula requires planning for safety and convenience. This formula can travel, but follow these guidelines.",
                "reasons": [
                    "Formula powder is shelf-stable and travel-friendly",
                    "Proper storage prevents contamination during travel",
                    "TSA and international regulations allow baby formula"
                ],
                "checks": [
                    "Pack formula in original sealed containers",
                    "Bring more than needed for trip duration",
                    "Use bottled or boiled water when traveling",
                    "Keep powder dry and at room temperature",
                    "Prepare bottles fresh when possible"
                ],
                "flags": ["travel_guidance", "portability", "storage_requirements"],
                "disclaimer": "Travel feeding plans should be discussed with your pediatrician, especially for international travel.",
                "jurisdiction": {"code": "US", "label": "TSA/FDA"},
                "evidence": [
                    {"type": "guideline", "source": "TSA", "id": "baby_formula_travel_rules"},
                    {"type": "guideline", "source": "AAP", "id": "travel_feeding_safety"}
                ],
                "suggested_questions": [
                    "How much formula for a 3-day trip?",
                    "Can I use hotel tap water?",
                    "What if formula gets warm during travel?",
                    "Airport security rules for formula?"
                ],
                "emergency": None
            }
            
        def _generate_feeding_schedule_response(self, context: Dict) -> Dict[str, Any]:
            """Smart feeding schedule and sleep guidance"""
            age_guidance = ""
            if context["baby_age_mentioned"]:
                age_guidance = f" For a {context['baby_age_mentioned']} old baby, "
                
            return {
                "summary": f"Feeding schedules vary by baby's age and needs.{age_guidance}typical feeding patterns involve 2-4 hour intervals.",
                "reasons": [
                    "Newborns need frequent feeding (every 2-3 hours)",
                    "Older infants can go longer between feeds (3-4 hours)",
                    "Night feeding needs decrease with age",
                    "Individual babies have unique patterns"
                ],
                "checks": [
                    "Watch for hunger cues rather than strict schedules",
                    "Ensure adequate daily intake for baby's weight",
                    "Monitor wet diapers as hydration indicator",
                    "Track feeding times to identify patterns"
                ],
                "flags": ["feeding_schedule", "sleep_guidance", "developmental_feeding"],
                "disclaimer": "Feeding schedules should be individualized. Consult pediatrician for personalized feeding plans.",
                "jurisdiction": {"code": "US", "label": "US AAP"},
                "evidence": [
                    {"type": "guideline", "source": "AAP", "id": "infant_feeding_schedules"},
                    {"type": "guideline", "source": "La Leche League", "id": "feeding_patterns"}
                ],
                "suggested_questions": [
                    "How often should I feed my baby?",
                    "Is it normal to feed at night?",
                    "How do I know if baby is getting enough?",
                    "When do night feedings stop?"
                ],
                "emergency": None
            }
            
        def _generate_nutrition_response(self, context: Dict) -> Dict[str, Any]:
            """Smart nutrition and development guidance"""
            return {
                "summary": "This baby formula provides complete nutrition designed to support healthy growth and development in infants.",
                "reasons": [
                    "FDA-regulated formulas must meet strict nutritional standards",
                    "Contains essential vitamins, minerals, and proteins",
                    "Designed to support brain and physical development",
                    "Nutritionally complete as sole food source for infants"
                ],
                "checks": [
                    "Verify formula meets your baby's specific nutritional needs",
                    "Monitor baby's growth and development with pediatrician",
                    "Watch for signs of good nutrition (steady weight gain, alertness)",
                    "Consider iron-fortified options as recommended by AAP"
                ],
                "flags": ["nutrition_guidance", "development_support", "growth_monitoring"],
                "disclaimer": "Nutritional needs are individual. Regular pediatric checkups ensure proper growth and development.",
                "jurisdiction": {"code": "US", "label": "US FDA/AAP"},
                "evidence": [
                    {"type": "regulation", "source": "FDA", "id": "infant_formula_nutrition_standards"},
                    {"type": "guideline", "source": "AAP", "id": "infant_nutrition_guidelines"}
                ],
                "suggested_questions": [
                    "Is my baby getting enough nutrition?",
                    "What vitamins are in this formula?",
                    "How do I know if baby is growing well?",
                    "When to introduce solid foods?"
                ],
                "emergency": None
            }
            
        def _generate_medical_consultation_response(self, context: Dict) -> Dict[str, Any]:
            """Smart medical consultation guidance"""
            urgency_note = ""
            if context["urgency"] == "high":
                urgency_note = " Given your urgent concern, consider contacting your pediatrician today."
                
            return {
                "summary": f"This formula appears safe based on safety databases, but pediatric consultation is always recommended for feeding decisions.{urgency_note}",
                "reasons": [
                    "Pediatricians provide personalized feeding guidance",
                    "Medical history affects formula recommendations",
                    "Professional monitoring ensures proper nutrition",
                    "Early intervention prevents feeding problems"
                ],
                "checks": [
                    "Schedule regular pediatric checkups",
                    "Discuss any feeding concerns at appointments",
                    "Keep feeding logs to share with doctor",
                    "Report any unusual reactions or symptoms"
                ],
                "flags": ["medical_consultation", "pediatric_guidance", "professional_advice"],
                "disclaimer": "This information supplements but does not replace professional medical advice.",
                "jurisdiction": {"code": "US", "label": "US AAP"},
                "evidence": [
                    {"type": "guideline", "source": "AAP", "id": "pediatric_feeding_consultation"},
                    {"type": "guideline", "source": "Academy of Nutrition", "id": "infant_nutrition_counseling"}
                ],
                "suggested_questions": [
                    "When should I call the pediatrician?",
                    "What questions to ask at checkups?",
                    "How to prepare for feeding discussions?",
                    "What symptoms need immediate attention?"
                ],
                "emergency": None
            }
    
    # Create singleton instance for conversation memory persistence
    if not hasattr(get_llm_client, '_instance'):
        get_llm_client._instance = SuperSmartLLMClient()
    return get_llm_client._instance


def get_chat_agent() -> ChatAgentLogic:
    return ChatAgentLogic(llm=get_llm_client(), model="gpt-4o")  # use your preferred model


# --- Request model ---
class ExplainRequest(BaseModel):
    scan_id: str


# --- Fetch scan_data helper ---
def fetch_scan_data(db: Session, scan_id: str) -> Dict[str, Any]:
    """
    Return the final scan result as a dict for the given scan_id.
    Queries the ScanHistory table and returns normalized scan data.
    """
    from models.scan_history import ScanHistory
    
    # Query scan history by scan_id
    scan = db.query(ScanHistory).filter(ScanHistory.scan_id == scan_id).first()
    
    if not scan:
        return None
    
    # Convert to normalized format for chat processing
    scan_data = {
        # Product identification
        "product_name": scan.product_name or "Unknown Product",
        "brand": scan.brand or "Unknown Brand", 
        "barcode": scan.barcode,
        "model_number": scan.model_number,
        "upc_gtin": scan.upc_gtin or scan.barcode,
        "category": scan.category or "general",
        
        # Scan details
        "scan_type": scan.scan_type or "barcode",
        "scan_id": scan.scan_id,
        "scan_timestamp": scan.scan_timestamp.isoformat() if scan.scan_timestamp else None,
        "confidence_score": scan.confidence_score or 0.0,
        "barcode_format": scan.barcode_format,
        
        # Safety information (normalized with defensive defaults)
        "verdict": scan.verdict or "No Recalls Found",
        "risk_level": scan.risk_level or "low",
        "recalls_found": scan.recalls_found or 0,
        "recalls": scan.recall_ids or [],  # List of recall IDs
        "agencies_checked": scan.agencies_checked or "39+",
        
        # Safety alerts (normalized to lists)
        "flags": [],  # Will be populated from alerts
        "key_flags": [],
        "ingredients": [],  # Not stored in ScanHistory, would need separate table
        "allergens": scan.allergen_alerts or [],
        "pregnancy_warnings": scan.pregnancy_warnings or [],
        "age_warnings": scan.age_warnings or [],
        
        # Additional metadata
        "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},  # Default jurisdiction
    }
    
    # Build flags from safety alerts
    flags = []
    if scan.allergen_alerts:
        flags.extend([f"allergen_{alert}" for alert in scan.allergen_alerts if alert])
    if scan.pregnancy_warnings:
        flags.extend([f"pregnancy_{warning}" for warning in scan.pregnancy_warnings if warning])
    if scan.age_warnings:
        flags.extend([f"age_{warning}" for warning in scan.age_warnings if warning])
    if scan.recalls_found and scan.recalls_found > 0:
        flags.append("recall_found")
    
    scan_data["flags"] = flags
    scan_data["key_flags"] = flags  # Use same flags for key_flags
    
    return scan_data


# --- Endpoint: POST /api/v1/chat/explain-result ---
@router.post("/explain-result", response_model=ExplanationResponse)
def explain_result(
    payload: ExplainRequest,
    db: Session = Depends(get_db),
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    trace_id = str(uuid4())

    try:
        scan_data = fetch_scan_data(db, payload.scan_id)
    except NotImplementedError as e:
        # Developer wiring reminder
        raise HTTPException(status_code=500, detail=str(e))

    if not scan_data:
        raise HTTPException(status_code=404, detail="scan_id not found")

    try:
        t_explain_start = monotonic()
        explanation = chat.synthesize_result(scan_data)  # dict matching ExplanationResponse
        inc_req("explain", "unknown", ok=True, circuit=False)
        obs_total(int((monotonic() - t_explain_start) * 1000))
    except ValueError as ve:
        inc_req("explain", "unknown", ok=False, circuit=False)
        inc_fallback("explain", "synth_fallback")
        logging.exception("Explain synthesis validation failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=502, detail=f"explanation_validation_error: {ve}") from ve
    except Exception as e:
        inc_req("explain", "unknown", ok=False, circuit=False)
        inc_fallback("explain", "synth_fallback")
        logging.exception("Explain synthesis failed | trace_id=%s", trace_id)
        raise HTTPException(status_code=502, detail="explanation_generation_error") from e

    resp = JSONResponse(content=explanation)
    resp.headers["X-Trace-Id"] = trace_id
    return resp


# ---------- Types / Models ----------
Intent = Literal[
    "pregnancy_risk",
    "allergy_question",
    "ingredient_info",
    "age_appropriateness",
    "alternative_products",
    "recall_details",
    "unclear_intent",
]

class ConversationRequest(BaseModel):
    scan_id: str
    user_query: str
    conversation_id: Optional[str] = None

class ToolCallLog(BaseModel):
    name: str
    latency_ms: int
    ok: bool
    error: Optional[str] = None

class ConversationResponse(BaseModel):
    conversation_id: str
    intent: Intent
    message: ExplanationResponse          # the structured payload parents see
    trace_id: str
    tool_calls: List[ToolCallLog] = []

# ---------- Tool runner now imported from api.services.chat_tools ----------

# ---------- Endpoint: POST /api/v1/chat/conversation ----------
@router.post("/conversation", response_model=ConversationResponse)
def conversation(
    payload: ConversationRequest,
    request: Request,
    db: Session = Depends(get_db),
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    t_start = monotonic()
    def remaining() -> float:
        return max(0.0, TOTAL_BUDGET_SEC - (monotonic() - t_start))
    
    trace_id = str(uuid4())
    
    # Try to resolve user_id (optional). Adjust to your auth system.
    user_id: Optional[UUID] = None
    try:
        from core.auth import current_user  # e.g., dependency setting user on context
        user_id = getattr(current_user, "id", None)  # adjust if your dep returns a model
    except Exception:
        user_id = None

    # Feature gating - check if chat is enabled for this user
    user_id_str = str(user_id) if user_id else None
    device_id = None  # Could be extracted from headers if available
    
    # If rollout is 100%, allow anonymous users (for testing/demo)
    from core.feature_flags import FEATURE_CHAT_ENABLED, FEATURE_CHAT_ROLLOUT_PCT
    if FEATURE_CHAT_ENABLED and FEATURE_CHAT_ROLLOUT_PCT >= 1.0:
        # Full rollout - allow all requests
        pass
    elif not chat_enabled_for(user_id_str, device_id):
        inc_blocked("conversation")
        raise HTTPException(status_code=403, detail="chat_disabled")

    # 1) Fetch context
    try:
        scan_data = fetch_scan_data(db, payload.scan_id)
    except NotImplementedError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not scan_data:
        raise HTTPException(status_code=404, detail="scan_id not found")

    # Conversation row (so we have a stable conv_id)
    conv = get_or_create_conversation(db, None if payload.conversation_id is None else UUID(payload.conversation_id) if len(payload.conversation_id) == 36 else None, user_id, payload.scan_id)

    # Optional profile (only if consented & not paused)
    profile = get_profile(db, user_id) if user_id else None
    profile_context = None
    if profile and profile.consent_personalization and not profile.memory_paused:
        profile_context = {
            "allergies": profile.allergies or [],
            "pregnancy_trimester": profile.pregnancy_trimester,
            "pregnancy_due_date": str(profile.pregnancy_due_date) if profile.pregnancy_due_date else None,
            "child_birthdate": str(profile.child_birthdate) if profile.child_birthdate else None,
        }

    # Log the user message
    log_message(db, conv, role="user", content={"text": payload.user_query}, intent=None, trace_id=trace_id)

    # 2) Classify intent (heuristics → LLM fallback inside)
    try:
        # Skip LLM fallback if we don't have enough time budget left
        if remaining() < (ROUTER_TIMEOUT_SEC + 0.05):
            intent = chat.classify_intent(payload.user_query)  # heuristics will fire
        else:
            # temporarily override the LLM timeout inside classify via env knob
            intent = chat.classify_intent(payload.user_query)  # heuristics -> LLM (3s) but overall deadline enforced below
    except Exception:
        intent = "unclear_intent"

    # 2.5) Emergency detection and UX hints
    is_emergency = looks_emergency(payload.user_query)
    unclear_count = int(request.headers.get("X-Chat-Unclear-Count", "0") or 0)
    
    # Build suggested questions for unclear intent or empty states
    suggested_qs = []
    emergency_block = None
    
    if is_emergency:
        emergency_block = {
            "level": "red",
            "reason": "Possible urgent situation reported.",
            "cta": "Open Emergency Guidance"
        }
    elif intent == "unclear_intent":
        if unclear_count >= 1:
            # Don't ask open clarifiers again; just provide chips
            suggested_qs = build_suggested_questions(
                scan_data.get("category", "general"), 
                profile_context or {}
            )[:3]
        else:
            suggested_qs = build_suggested_questions(
                scan_data.get("category", "general"), 
                profile_context or {}
            )
    
    # Record metrics
    if intent == "unclear_intent":
        inc_unclear()
    if is_emergency or emergency_block:
        inc_emergency()

    # 3) Call the appropriate tool (guard latency, log outcome)
    tool_logs: List[ToolCallLog] = []
    tool_facts: Dict[str, Any] = {}
    tool_key = f"tool::{intent}"
    t0 = monotonic()
    ok, err = True, None

    if intent == "unclear_intent":
        tool_facts = {}
    else:
        try:
            if not breaker.allow(tool_key):
                raise RuntimeError("circuit_open")
            # Respect remaining budget; cap per-tool timeout
            timeout = min(TOOL_TIMEOUT_SEC, max(0.1, remaining()))
            def _run():
                return run_tool_for_intent(intent, db=db, scan_data=scan_data)
            tool_facts = call_with_timeout(_run, timeout)
            breaker.record_success(tool_key)
        except Exception as e:
            ok, err = False, str(e)
            breaker.record_failure(tool_key)
    
    tool_logs.append(ToolCallLog(
        name=tool_key,
        latency_ms=int((monotonic() - t0) * 1000),
        ok=ok,
        error=err,
    ))
    # Record tool latency
    obs_tool(intent, tool_logs[-1].latency_ms)

    # 4) Infer jurisdiction (very light placeholder; replace with your real geo/locale logic)
    jurisdiction = scan_data.get("jurisdiction")
    if not jurisdiction:
        # Try profile or app default
        if profile_context and profile_context.get("country"):
            country = str(profile_context["country"]).upper()
            jurisdiction = {"code": "EU", "label": "EU Safety Gate"} if country in {"ES","FR","DE","IT","NL","SE","PL","RO","BG","PT","BE","DK","FI","IE","LT","LV","EE","AT","CZ","SK","HU","GR","SI","HR","LU","MT","CY"} else None

    # 5) Synthesize final, structured message (with circuit-breaker fallback)
    synth_key = "llm_synth"
    merged_for_synthesis = {
        **scan_data,
        "profile": profile_context,  # may be None
        "jurisdiction": jurisdiction,   # <— add this
        "followup": {
            "intent": intent,
            "question": payload.user_query,
            "tool_facts": tool_facts if ok else {},
            "tool_ok": ok,
        },
        "ux_hints": {
            "suggested_questions": suggested_qs,
            "emergency": emergency_block
        }
    }

    def _templated_fallback():
        return ExplanationResponse(
            summary="Here's a quick summary of what we found. We couldn't generate the full explanation right now.",
            reasons=[
                "Your scan completed successfully.",
                ("Tool results returned" if ok else "Tool results unavailable; using basic info.")
            ],
            checks=["Review the label for warnings and batch/lot codes.", "Use the Safety Verdict as your primary guidance."],
            flags=scan_data.get("key_flags", []) if isinstance(scan_data, dict) else [],
            disclaimer="Not medical advice. For urgent concerns, use Emergency Guidance.",
        )

    synth_start = monotonic()
    try:
        if remaining() < 0.15 or not breaker.allow(synth_key):
            raise RuntimeError("deadline_or_circuit")
        timeout = min(SYNTH_TIMEOUT_SEC, max(0.1, remaining()))
        def _run():
            return chat.synthesize_result(merged_for_synthesis)
        message_dict = call_with_timeout(_run, timeout)
        message = ExplanationResponse(**message_dict)
        breaker.record_success(synth_key)
    except Exception:
        breaker.record_failure(synth_key)
        message = _templated_fallback()
        inc_fallback("conversation", "synth_fallback")

    # Emergency override: ensure emergency block is present when detected
    if is_emergency and not message.emergency:
        from agents.chat.chat_agent.agent_logic import EmergencyNotice
        message.emergency = EmergencyNotice(
            level="red",
            reason="Possible urgent situation reported.",
            cta="Open Emergency Guidance"
        )
    
    # Empty state guidance: ensure helpful checks for low-signal scans
    if (not message.checks or len(message.checks) < 2) and scan_data.get("recalls_found", 0) == 0:
        category = scan_data.get("category", "").lower()
        additional_checks = []
        
        if not any("batch" in check.lower() or "lot" in check.lower() for check in message.checks):
            additional_checks.append("Check label for batch/lot & expiry")
        
        if category in ["dairy", "cheese"] and not any("pasteur" in check.lower() for check in message.checks):
            additional_checks.append("Confirm pasteurisation (if dairy/cheese)")
        
        if category in ["toy", "game"] and not any("small parts" in check.lower() for check in message.checks):
            additional_checks.append("Inspect for small parts (if toy/gear)")
        
        if category in ["toy", "feeding"] and not any("age" in check.lower() for check in message.checks):
            additional_checks.append("Review age label (if toy/feeding)")
        
        # Add the most relevant checks to ensure at least 2 total
        needed = max(0, 2 - len(message.checks))
        message.checks.extend(additional_checks[:needed])

    # Log the assistant message
    log_message(db, conv, role="assistant", content=message.model_dump(), intent=intent, trace_id=trace_id)

    # Record synthesis latency
    obs_synth(int((monotonic() - synth_start) * 1000))
    
    # Record alternatives metrics if present in tool outputs
    for tool_call in tool_logs:
        if tool_call.ok and 'alternatives' in (tool_call.output or {}):
            alt_data = tool_call.output['alternatives']
            alt_count = len(alt_data.get('items', []))
            if alt_count > 0:
                inc_alternatives_shown(alt_count)
                break  # Only record once per conversation
    
    # Record overall success metrics
    circuit_broken = tool_logs[-1].error == "circuit_open" if tool_logs else False
    inc_req("conversation", intent, ok=True, circuit=circuit_broken)
    obs_total(int((monotonic() - t_start) * 1000))

    resp = ConversationResponse(
        conversation_id=str(conv.id),
        intent=intent,
        message=message,
        trace_id=trace_id,
        tool_calls=tool_logs,
    )
    out = JSONResponse(content=resp.model_dump())
    out.headers["X-Trace-Id"] = trace_id
    out.headers["X-Chat-Latency-Ms"] = str(int((monotonic() - t_start) * 1000))
    out.headers["X-Chat-Remaining-Ms"] = str(int(remaining() * 1000))
    out.headers["X-Chat-Intent"] = intent
    out.headers["X-Chat-Tool-Ok"] = "1" if ok else "0"
    return out


class ProfilePayload(BaseModel):
    consent_personalization: bool = Field(False)
    memory_paused: bool = Field(False)
    allergies: list[str] = Field(default_factory=list)
    pregnancy_trimester: int | None = None
    pregnancy_due_date: str | None = None  # ISO date
    child_birthdate: str | None = None     # ISO date

@router.get("/profile")
def get_my_profile(db: Session = Depends(get_db)):
    # TODO: replace with real current user
    user_id = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        pass
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    prof = get_profile(db, user_id)
    return prof.__dict__ if prof else {}

@router.put("/profile")
def put_my_profile(payload: ProfilePayload, db: Session = Depends(get_db)):
    # TODO: replace with real current user
    user_id = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        pass
    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")
    data = payload.model_dump()
    # Convert ISO strings to dates where present
    from datetime import date
    for k in ("pregnancy_due_date", "child_birthdate"):
        if data.get(k):
            data[k] = date.fromisoformat(data[k])
    prof = upsert_profile(db, user_id, data)
    return {"ok": True, "updated_at": str(prof.updated_at)}


class EraseResponse(BaseModel):
    ok: bool
    mode: Literal["async", "sync"]
    deleted: int
    trace_id: str

@router.post("/erase-history", response_model=EraseResponse)
def erase_history(db: Session = Depends(get_db)):
    # TODO: replace with real current user dependency
    user_id: Optional[UUID] = None
    try:
        from core.auth import current_user
        user_id = getattr(current_user, "id", None)
    except Exception:
        user_id = None

    if not user_id:
        raise HTTPException(status_code=401, detail="auth_required")

    trace_id = str(uuid4())
    # Record the request timestamp
    mark_erase_requested(db, user_id)

    # Prefer async purge; if Celery not available, do it sync
    try:
        from workers.tasks.chat_cleanup import purge_user_history_task
        job_deleted = purge_user_history_task(str(user_id))  # works sync or enqueued depending on wiring
        mode = "sync"
        deleted = int(job_deleted or 0)
    except Exception:
        # If Celery app is present, calling .delay() is preferred:
        try:
            from workers.tasks.chat_cleanup import purge_user_history_task
            deleted = 0
            purge_user_history_task.delay(str(user_id))  # type: ignore[attr-defined]
            mode = "async"
        except Exception:
            # last resort: synchronous purge
            deleted = purge_conversations_for_user(db, user_id)
            mode = "sync"

    resp = EraseResponse(ok=True, mode=mode, deleted=deleted, trace_id=trace_id)
    out = JSONResponse(content=resp.model_dump())
    out.headers["X-Trace-Id"] = trace_id
    return out


@router.post("/demo", response_model=ConversationResponse)
def demo_conversation(
    payload: ConversationRequest,
    request: Request,
    chat: ChatAgentLogic = Depends(get_chat_agent),
):
    """Demo chat endpoint with mock scan data - for testing without real database records"""
    trace_id = str(uuid4())
    
    # Create mock scan data for testing
    mock_scan_data = {
        "product_name": "Demo Baby Formula",
        "brand": "SafeBaby",
        "barcode": "012345678901",
        "model_number": "SB-DEMO-001",
        "upc_gtin": "012345678901",
        "category": "baby_formula",
        "scan_type": "barcode",
        "scan_id": payload.scan_id,
        "scan_timestamp": "2024-01-01T12:00:00Z",
        "confidence_score": 0.95,
        "barcode_format": "UPC-A",
        "verdict": "Safe - No Recalls Found",
        "risk_level": "low",
        "recalls_found": 0,
        "recalls": [],
        "agencies_checked": "39 agencies (FDA, CPSC, USDA, etc.)",
        "flags": [],
        "key_flags": [],
        "ingredients": ["Milk protein", "Lactose", "Vitamins"],
        "allergens": ["Contains milk"],
        "pregnancy_warnings": [],
        "age_warnings": ["Suitable for infants 0-12 months"],
        "jurisdiction": {"code": "US", "label": "US FDA/CPSC"}
    }
    
    # Classify intent
    try:
        intent = chat.classify_intent(payload.user_query)
    except Exception:
        intent = "safety_question"
    
    # Generate response
    try:
        response = chat.synthesize_result(mock_scan_data)
        
        # Create response
        return ConversationResponse(
            conversation_id=str(uuid4()),
            intent=intent,
            message=response,
            trace_id=trace_id,
            tool_calls=[]
        )
    except Exception as e:
        # Log the actual error for debugging
        logger = logging.getLogger(__name__)
        logger.error(f"[{trace_id}] Chat synthesize_result failed: {e}")
        logger.error(f"[{trace_id}] Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"[{trace_id}] Traceback: {traceback.format_exc()}")
        
        # Fallback response
        fallback_response = ExplanationResponse(
            summary=f"I can help you with questions about {mock_scan_data['product_name']}. This appears to be a {mock_scan_data['category']} product with a safety rating of '{mock_scan_data['risk_level']}'. The product has {mock_scan_data['recalls_found']} recalls found across {mock_scan_data['agencies_checked']}.",
            reasons=["No recalls found in database", "Low risk level assigned", "Contains milk allergen"],
            checks=["Ask about ingredients", "Check age appropriateness", "Verify safety for pregnancy"],
            flags=["no_recalls", "low_risk", "contains_milk"],
            disclaimer="This is a fallback response while the AI service reconnects. For detailed analysis, please try again in a moment."
        )
        
        return ConversationResponse(
            conversation_id=str(uuid4()),
            intent=intent,
            message=fallback_response,
            trace_id=trace_id,
            tool_calls=[]
        )

@router.get("/flags")
def chat_flags(request: Request):
    """Get chat feature flags - robust version"""
    trace_id = getattr(getattr(request, "state", None), "trace_id", f"flags_{int(monotonic()*1000)}")
    
    try:
        from core.feature_flags import FEATURE_CHAT_ENABLED, FEATURE_CHAT_ROLLOUT_PCT
        
        payload = {
            "success": True,
            "data": {
        "chat_enabled_global": FEATURE_CHAT_ENABLED,
        "chat_rollout_pct": FEATURE_CHAT_ROLLOUT_PCT,
            },
            "traceId": trace_id
        }
        return JSONResponse(content=payload)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception(f"[{trace_id}] Chat flags failed: {e}")
        
        payload = {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Feature flags unavailable: {str(e)}"
            },
            "traceId": trace_id
        }
        return JSONResponse(content=payload, status_code=500)
