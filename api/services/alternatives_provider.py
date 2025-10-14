from __future__ import annotations
from typing import Dict, Any, List
from api.schemas.alternatives import AlternativeItem, AlternativesOut
from api.services.evidence import label_to_evidence, regulatory_to_evidence


def _rules(scan: Dict[str, Any], profile: Dict[str, Any]) -> List[AlternativeItem]:
    """
    Rules-based alternatives engine. Returns safer product suggestions based on
    scan data, flags, and user profile.
    """
    items: List[AlternativeItem] = []
    cat = (scan.get("category") or "").lower()
    flags = set(scan.get("flags") or [])
    ingredients = [str(x).lower() for x in (scan.get("ingredients") or [])]
    allergies = set([a.lower() for a in (profile.get("allergies") or [])])

    # Cheese: suggest pasteurised, hard cheeses
    if cat == "cheese" or "soft_cheese" in flags:
        items.append(
            AlternativeItem(
                id="alt_pasteurised_brie",
                name="Pasteurised Brie (labeled)",
                reason="Same style but pasteurised, lower listeria risk in pregnancy.",
                tags=["pasteurised", "pregnancy"],
                pregnancy_safe=True,
                evidence=label_to_evidence("pasteurisation"),
            )
        )
        items.append(
            AlternativeItem(
                id="alt_hard_cheese",
                name="Hard cheeses (Cheddar, Gruyère)",
                reason="Hard cheeses are lower moisture; generally safer in pregnancy.",
                tags=["pregnancy"],
                pregnancy_safe=True,
                evidence=regulatory_to_evidence("FDA", "Pregnancy food safety guidelines"),
            )
        )

    # Peanut allergy: suggest nut-free alternatives
    if "peanut" in allergies or any("peanut" in ing for ing in ingredients):
        items.append(
            AlternativeItem(
                id="alt_peanut_free_bar",
                name="Nut-free snack bar",
                reason="Avoids peanut exposure for your family allergy profile.",
                tags=["peanut-free", "allergy"],
                allergy_safe_for=["peanut"],
                evidence=label_to_evidence("allergen statement"),
            )
        )
        items.append(
            AlternativeItem(
                id="alt_sunbutter",
                name="SunButter (sunflower seed spread)",
                reason="Peanut-free alternative with similar taste and nutrition.",
                tags=["peanut-free", "allergy", "spread"],
                allergy_safe_for=["peanut"],
                evidence=label_to_evidence("facility information"),
            )
        )

    # Tree nut allergies
    if any(nut in allergies for nut in ["tree_nut", "almond", "walnut", "cashew"]):
        items.append(
            AlternativeItem(
                id="alt_nut_free_granola",
                name="Nut-free granola or oat bars",
                reason="Avoids tree nut cross-contamination risks.",
                tags=["nut-free", "allergy"],
                allergy_safe_for=["tree_nut", "almond", "walnut", "cashew"],
                evidence=label_to_evidence("allergen manufacturing statement"),
            )
        )

    # Sleep products: flat/firm surfaces
    if "infant_sleeper" in flags or "sleep_surface" in flags or cat == "infant_sleeper":
        items.append(
            AlternativeItem(
                id="alt_flat_sleep_surface",
                name="Flat, firm sleep surface (crib/bassinet with fitted sheet)",
                reason="Meets safe sleep guidance; avoids inclined sleepers.",
                tags=["flat-sleep", "safe-sleep"],
                age_min_months=0,
                evidence=regulatory_to_evidence("CPSC", "Safe sleep guidelines"),
            )
        )
        items.append(
            AlternativeItem(
                id="alt_bassinet",
                name="CPSC-compliant bassinet",
                reason="Portable flat sleep surface that meets safety standards.",
                tags=["flat-sleep", "portable", "cpsc-approved"],
                age_min_months=0,
                evidence=regulatory_to_evidence("CPSC", "Bassinet safety standard"),
            )
        )

    # Small parts / choking hazards: age-appropriate alternatives
    if "small_parts" in flags or "choking_hazard" in flags:
        if cat in ["toy", "game"]:
            items.append(
                AlternativeItem(
                    id="alt_large_piece_toy",
                    name="Large-piece version of similar toy",
                    reason="Same play value but with pieces too large to swallow.",
                    tags=["no-small-parts", "age-appropriate"],
                    age_min_months=0,
                    evidence=regulatory_to_evidence("CPSC", "Small parts test guidelines"),
                )
            )

        items.append(
            AlternativeItem(
                id="alt_soft_toy",
                name="Soft fabric toy without detachable parts",
                reason="No small parts risk; safer for younger children.",
                tags=["soft", "no-small-parts"],
                age_min_months=0,
                evidence=label_to_evidence("age recommendation"),
            )
        )

    # Cosmetic ingredients: pregnancy-safe alternatives
    if cat == "cosmetic" and any(ing in ingredients for ing in ["retinol", "salicylic acid", "hydroquinone"]):
        items.append(
            AlternativeItem(
                id="alt_pregnancy_safe_skincare",
                name="Pregnancy-safe skincare (vitamin C, hyaluronic acid)",
                reason="Effective ingredients without pregnancy concerns.",
                tags=["pregnancy-safe", "skincare"],
                pregnancy_safe=True,
                evidence=regulatory_to_evidence("FDA", "Cosmetic ingredient safety"),
            )
        )

    # High-mercury fish: low-mercury alternatives
    if cat == "fish" or any("mercury" in flag for flag in flags):
        items.append(
            AlternativeItem(
                id="alt_low_mercury_fish",
                name="Low-mercury fish (salmon, sardines, anchovies)",
                reason="Omega-3 benefits without mercury concerns in pregnancy.",
                tags=["low-mercury", "pregnancy-safe", "omega-3"],
                pregnancy_safe=True,
                evidence=regulatory_to_evidence("FDA", "Fish consumption guidelines"),
            )
        )

    # Raw/unpasteurized dairy: pasteurized alternatives
    if any("raw" in ing or "unpasteurized" in ing for ing in ingredients):
        items.append(
            AlternativeItem(
                id="alt_pasteurized_dairy",
                name="Pasteurized version of same product",
                reason="Same nutritional benefits without bacterial contamination risk.",
                tags=["pasteurized", "pregnancy-safe"],
                pregnancy_safe=True,
                evidence=label_to_evidence("pasteurization statement"),
            )
        )

    # Limit to top 3 most relevant alternatives
    return items[:3]


def get_alternatives(scan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get safer product alternatives based on scan data and user profile.
    Returns AlternativesOut schema with up to 3 suggestions.
    """
    import os

    # Feature flag check
    if os.getenv("BS_ALTERNATIVES_ENABLED", "true").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return AlternativesOut(items=[]).model_dump()

    profile = scan.get("profile") or {}
    items = _rules(scan, profile)

    # TODO: later swap in a catalog/recommender; keep same shape
    return AlternativesOut(items=items).model_dump()
