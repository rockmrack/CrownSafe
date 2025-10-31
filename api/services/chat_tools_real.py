from __future__ import annotations

from typing import Any, Dict

# Import your existing agents
from agents.premium.pregnancy_product_safety_agent.main import (
    PregnancyProductSafetyAgent,
)

from api.schemas.tools import (
    AgeCheckIn,
    AgeCheckOut,
    AllergyCheckIn,
    AllergyCheckOut,
    AllergyHit,
    IngredientInfoIn,
    IngredientInfoOut,
    PregnancyCheckIn,
    PregnancyCheckOut,
    RecallDetailsOut,
    RiskItem,
)
from api.services.alternatives_provider import get_alternatives
from api.services.evidence import label_to_evidence, recalls_to_evidence


def pregnancy_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for PregnancyProductSafetyAgent that converts between chat format and agent format.
    """
    # Create typed input (reserved for future type validation)
    _ = PregnancyCheckIn(
        product_name=scan.get("product_name"),
        category=scan.get("category"),
        ingredients=scan.get("ingredients") or [],
        flags=scan.get("flags") or [],
        jurisdiction=scan.get("jurisdiction"),
    )

    # Call the real agent
    agent = PregnancyProductSafetyAgent()

    # The real agent expects UPC-based calls, so we need to adapt
    # For now, we'll use a simplified approach based on ingredients and flags
    raw_result = _check_pregnancy_safety_from_scan(agent, scan)

    # Map to typed output
    risks = []
    if raw_result and raw_result.get("unsafe_ingredients"):
        for ingredient, details in raw_result["unsafe_ingredients"].items():
            risks.append(
                RiskItem(
                    code=f"ingredient_{ingredient.lower().replace(' ', '_')}",
                    reason=details.get(
                        "reason",
                        f"Contains {ingredient} which may pose pregnancy risks",
                    ),
                    severity=details.get("severity", "moderate"),
                )
            )

    # Check for specific flag-based risks
    flags = scan.get("flags", [])
    if "soft_cheese" in flags or any("cheese" in flag for flag in flags):
        risks.append(
            RiskItem(
                code="soft_cheese_pasteurisation",
                reason="Soft cheese may contain listeria unless pasteurised",
                severity="moderate",
            )
        )

    out = PregnancyCheckOut(
        risks=risks,
        notes=raw_result.get("notes")
        if raw_result
        else "Check product labeling for pasteurisation and safety warnings",
    )

    return {"pregnancy": out.model_dump()}


def allergy_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for AllergySensitivityAgent that converts between chat format and agent format.
    """
    profile = scan.get("profile") or {}

    # Create typed input (reserved for future type validation)
    _ = AllergyCheckIn(
        ingredients=[str(i) for i in (scan.get("ingredients") or [])],
        profile_allergies=[str(a).lower() for a in (profile.get("allergies") or [])],
        product_name=scan.get("product_name"),
    )

    # Call the real agent - simplified approach since agent expects user_id + UPC
    raw_result = _check_allergy_from_scan(scan, profile.get("allergies", []))

    # Map to typed output
    hits = []
    if raw_result and raw_result.get("allergen_matches"):
        for match in raw_result["allergen_matches"]:
            hits.append(
                AllergyHit(
                    allergen=match.get("allergen", ""),
                    present=bool(match.get("present", False)),
                    evidence=match.get("evidence", "ingredient_list"),
                )
            )

    out = AllergyCheckOut(hits=hits, summary=raw_result.get("summary") if raw_result else None)

    return {"allergy": out.model_dump()}


def _check_pregnancy_safety_from_scan(agent: PregnancyProductSafetyAgent, scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to check pregnancy safety based on scan data rather than UPC.
    This is a simplified adapter until we have full ingredient database integration.
    """
    try:
        # Get the agent logic (reserved for future agent integration)
        _ = agent.logic

        # For now, create a mock result based on common pregnancy safety patterns
        ingredients = scan.get("ingredients", [])
        category = scan.get("category", "")
        flags = scan.get("flags", [])

        unsafe_ingredients = {}

        # Check for common pregnancy-unsafe ingredients
        pregnancy_unsafe = {
            "alcohol": {
                "reason": "Alcohol consumption during pregnancy can cause birth defects",
                "severity": "high",
            },
            "caffeine": {
                "reason": "High caffeine intake should be limited during pregnancy",
                "severity": "low",
            },
            "raw_milk": {
                "reason": "Raw milk may contain harmful bacteria",
                "severity": "high",
            },
            "unpasteurized": {
                "reason": "Unpasteurized products may contain listeria",
                "severity": "moderate",
            },
            "mercury": {
                "reason": "Mercury can harm fetal development",
                "severity": "high",
            },
            "high_sodium": {
                "reason": "Excessive sodium can contribute to pregnancy complications",
                "severity": "low",
            },
        }

        for ingredient in ingredients:
            ingredient_lower = str(ingredient).lower()
            for unsafe, details in pregnancy_unsafe.items():
                if unsafe in ingredient_lower:
                    unsafe_ingredients[ingredient] = details

        # Check category-based risks
        if category.lower() in ["cheese", "dairy"] and any("soft" in flag for flag in flags):
            unsafe_ingredients["soft_cheese"] = {
                "reason": "Soft cheeses may contain listeria unless pasteurised",
                "severity": "moderate",
            }

        return {
            "status": "success",
            "unsafe_ingredients": unsafe_ingredients,
            "notes": "Always consult with healthcare provider for pregnancy-specific dietary advice"
            if unsafe_ingredients
            else None,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_allergy_from_scan(scan: Dict[str, Any], profile_allergies: list) -> Dict[str, Any]:
    """
    Helper to check allergies based on scan data and profile.
    This is a simplified adapter until we have full user profile integration.
    """
    try:
        ingredients = [str(i).lower() for i in scan.get("ingredients", [])]
        allergies = [str(a).lower() for a in profile_allergies]

        allergen_matches = []

        # Direct ingredient matches
        for allergen in allergies:
            for ingredient in ingredients:
                if allergen in ingredient or ingredient in allergen:
                    allergen_matches.append(
                        {
                            "allergen": allergen,
                            "present": True,
                            "evidence": "ingredient_list",
                        }
                    )

        # Common allergen aliases
        allergen_aliases = {
            "peanut": ["peanuts", "groundnut", "arachis"],
            "tree_nut": [
                "almond",
                "walnut",
                "cashew",
                "pecan",
                "hazelnut",
                "brazil_nut",
            ],
            "dairy": ["milk", "lactose", "casein", "whey"],
            "egg": ["eggs", "albumin", "ovalbumin"],
            "soy": ["soya", "soybean", "lecithin"],
            "wheat": ["gluten", "flour", "semolina"],
            "shellfish": ["shrimp", "crab", "lobster", "prawns"],
            "fish": ["salmon", "tuna", "cod", "mackerel"],
        }

        for allergen in allergies:
            if allergen in allergen_aliases:
                for alias in allergen_aliases[allergen]:
                    for ingredient in ingredients:
                        if alias in ingredient:
                            allergen_matches.append(
                                {
                                    "allergen": allergen,
                                    "present": True,
                                    "evidence": f"contains_{alias}",
                                }
                            )

        # Remove duplicates
        seen = set()
        unique_matches = []
        for match in allergen_matches:
            key = match["allergen"]
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        summary = None
        if unique_matches:
            allergen_names = [m["allergen"] for m in unique_matches]
            summary = f"Detected allergens: {', '.join(allergen_names)}"

        return {
            "status": "success",
            "allergen_matches": unique_matches,
            "summary": summary,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def recall_details_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for recall lookups using the enhanced RecallDB.
    REMOVED FOR CROWN SAFE: Recall lookups no longer applicable (hair products, not baby recalls)
    """
    # Return empty recalls for backward compatibility
    recalls_data = []

    out = RecallDetailsOut(
        recalls=recalls_data,
        recalls_found=0,
        batch_check="Crown Safe focuses on hair product ingredients, not baby product recalls.",
        message="Recall lookup deprecated for Crown Safe",
    )
    return out.model_dump()

    # Original recall lookup removed (~60 lines):
    # from core_infra.database import get_db_session, RecallDB
    # with get_db_session() as db:
    #     query = db.query(RecallDB)
    #     Build search conditions and query recalls
    #     for r in results:
    #         recalls_data.append(RecallRecord(...).model_dump())

    # Add evidence for each recall found (now empty)
    facts = out.model_dump()
    facts["evidence"] = recalls_to_evidence(recalls_data)
    return facts


def ingredient_info_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for ingredient analysis. Uses simple highlighting rules for now.
    """
    inp = IngredientInfoIn(
        ingredients=[str(x) for x in (scan.get("ingredients") or [])],
        product_name=scan.get("product_name"),
        category=scan.get("category"),
    )

    # Simple highlighting rules for common concerns
    highlighted = []
    notes = []
    recommend_label_check = False

    for ingredient in inp.ingredients:
        ingredient_lower = ingredient.lower()

        # Pregnancy concerns
        if any(term in ingredient_lower for term in ["retinol", "salicylic acid", "hydroquinone", "tretinoin"]):
            highlighted.append(ingredient)
            notes.append(f"{ingredient}: Check with healthcare provider during pregnancy")

        # Common allergens
        if any(term in ingredient_lower for term in ["fragrance", "parfum", "sulfate", "paraben"]):
            highlighted.append(ingredient)

        # Preservatives
        if any(term in ingredient_lower for term in ["formaldehyde", "methylisothiazolinone", "benzalkonium"]):
            highlighted.append(ingredient)
            notes.append(f"{ingredient}: Potential skin sensitizer")

    # Check if we should recommend label verification
    if scan.get("category") in ["food", "cosmetic", "pharmaceutical"] or highlighted:
        recommend_label_check = True

    out = IngredientInfoOut(
        ingredients=inp.ingredients,
        highlighted=list(set(highlighted)),  # Remove duplicates
        notes="; ".join(notes) if notes else None,
    )

    facts = out.model_dump()
    if recommend_label_check:
        facts.setdefault("evidence", []).extend(label_to_evidence("ingredient verification"))

    return facts


# Age appropriateness rules based on common safety standards
AGE_RULES = {
    "teether": 3,  # 3+ months
    "pacifier": 0,  # 0+ months
    "bottle": 0,  # 0+ months
    "toy": 36,  # 36+ months (default for toys with small parts)
    "rattle": 3,  # 3+ months
    "infant_sleeper": 0,  # 0+ months
    "car_seat": 0,  # 0+ months
    "high_chair": 6,  # 6+ months
    "walker": 6,  # 6+ months
    "stroller": 0,  # 0+ months
    "crib": 0,  # 0+ months
    "playpen": 0,  # 0+ months
}


def age_check_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for age appropriateness checks using safety rules.
    """
    inp = AgeCheckIn(
        category=scan.get("category"),
        min_age_months=scan.get("age_min_months"),
        flags=scan.get("flags") or [],
    )

    # Determine minimum age
    min_age = inp.min_age_months
    if min_age is None and inp.category:
        min_age = AGE_RULES.get(inp.category.lower())

    # Check flags for safety concerns
    reasons = []
    if "small_parts" in inp.flags:
        reasons.append("Contains small parts; not suitable for under 36 months.")
        min_age = max(min_age or 0, 36)

    if "choking_hazard" in inp.flags:
        reasons.append("Choking hazard; requires adult supervision.")
        min_age = max(min_age or 0, 36)

    if "sharp_edges" in inp.flags:
        reasons.append("Sharp edges present; not suitable for young children.")
        min_age = max(min_age or 0, 36)

    # Check category-specific concerns
    if inp.category and inp.category.lower() in ["toy", "game"]:
        if not min_age:
            min_age = 36  # Default for unspecified toys
            reasons.append("Age recommendation based on product category.")

    out = AgeCheckOut(
        age_ok=(min_age is not None and min_age <= 0),
        min_age_months=min_age,
        reasons=reasons,
    )

    return out.model_dump()


def alternatives_adapter(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapter for alternatives provider that suggests safer product swaps.
    """
    return {"alternatives": get_alternatives(scan)}
