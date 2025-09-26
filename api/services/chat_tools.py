# api/services/chat_tools.py
from __future__ import annotations
import os
from typing import Dict, Any, Literal, Optional

Intent = Literal[
    "pregnancy_risk",
    "allergy_question",
    "ingredient_info",
    "age_appropriateness",
    "alternative_products",
    "recall_details",
    "unclear_intent",
]

# Environment flag to toggle between stub and real tools
USE_REAL = os.getenv("BS_USE_REAL_TOOLS", "false").lower() in {"1","true","yes","on"}

# Toggle between real and stub implementations
if USE_REAL:
    from api.services.chat_tools_real import (
        pregnancy_adapter as _preg, 
        allergy_adapter as _all,
        recall_details_adapter as _recall,
        ingredient_info_adapter as _ingredient,
        age_check_adapter as _age,
        alternatives_adapter as _alts
    )
    def tool_pregnancy(scan): return _preg(scan)
    def tool_allergy(scan):   return _all(scan)
    def tool_recall_details(scan): return _recall(scan)
    def tool_ingredients(scan): return _ingredient(scan)
    def tool_age(scan): return _age(scan)
    def tool_alternatives(scan): return _alts(scan)
else:
    # Stub implementations (original logic)
    def _lower_list(xs): return [str(x).lower() for x in xs or []]

    def tool_pregnancy(scan: Dict[str, Any]) -> Dict[str, Any]:
        flags = set(scan.get("flags", []))
        ingredients = _lower_list(scan.get("ingredients", []))
        risks = []
        if "soft_cheese" in flags or scan.get("category") == "cheese":
            risks.append("soft_cheese_pasteurisation")
        if "raw milk" in ingredients or "unpasteurized" in " ".join(ingredients):
            risks.append("unpasteurised_dairy")
        return {"pregnancy": {"risks": risks, "notes": "Check pasteurisation on label" if risks else ""}}

    def tool_allergy(scan: Dict[str, Any]) -> Dict[str, Any]:
        profile = scan.get("profile") or {}
        allergies = set(_lower_list(profile.get("allergies", [])))
        ingredients = set(_lower_list(scan.get("ingredients", [])))
        hits = sorted(list(allergies.intersection(ingredients)))
        # common alias
        if "peanut" in allergies and any(x in ingredients for x in {"peanut","peanuts","groundnut"}):
            if "contains_peanuts" not in scan.get("flags", []):
                pass
        return {"allergy": {"hits": hits, "allergies": list(allergies)}}

def tool_ingredients(scan: Dict[str, Any]) -> Dict[str, Any]:
    return {"ingredients_info": {"ingredients": scan.get("ingredients", []), "notes": scan.get("ingredients_notes")}}

def tool_age(scan: Dict[str, Any]) -> Dict[str, Any]:
    min_age = scan.get("age_min_months")
    return {"age_fit": {"age_ok": min_age is not None and min_age <= 0, "min_age_months": min_age}}

def tool_alternatives(scan: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder: integrate a recommender later
    return {"alternatives": []}

def tool_recall_details(scan: Dict[str, Any]) -> Dict[str, Any]:
    return {"recalls": scan.get("recalls", []), "recalls_found": scan.get("recalls_found", 0), "batch_check": "Verify batch/lot on label"}

def run_tool_for_intent(intent: Intent, *, scan_data: Dict[str, Any], db=None) -> Dict[str, Any]:
    if intent == "pregnancy_risk":       return tool_pregnancy(scan_data)
    if intent == "allergy_question":     return tool_allergy(scan_data)
    if intent == "ingredient_info":      return tool_ingredients(scan_data)
    if intent == "age_appropriateness":  return tool_age(scan_data)
    if intent == "alternative_products": return tool_alternatives(scan_data)
    if intent == "recall_details":       return tool_recall_details(scan_data)
    return {}
