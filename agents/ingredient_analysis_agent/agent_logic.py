"""Crown Safe - Ingredient Analysis Agent
Replaces: recall_data_agent (baby recalls) → ingredient safety analysis.

This agent analyzes hair product ingredients using the Crown Score engine
to provide personalized safety and compatibility assessments.
"""

import logging

from core.crown_score_engine import (
    CrownScoreEngine,
    HairGoal,
    HairProfile,
    HairState,
    HairType,
    Porosity,
    ProductType,
    VerdictLevel,
)

logger = logging.getLogger(__name__)


class IngredientAnalysisAgent:
    """Intelligent agent for analyzing hair product ingredients.

    Capabilities:
    - Analyze ingredient safety for specific hair types
    - Calculate personalized Crown Scores
    - Identify harmful ingredients and interactions
    - Recommend safer alternatives
    """

    def __init__(self) -> None:
        self.crown_engine = CrownScoreEngine()
        logger.info("✅ Ingredient Analysis Agent initialized")

    async def analyze_product(
        self,
        ingredients: list[str],
        hair_profile: dict,
        product_type: str,
        ph_level: float | None = None,
    ) -> dict:
        """Analyze a hair product's ingredients.

        Args:
            ingredients: List of ingredient names
            hair_profile: User's hair profile (dict)
            product_type: Type of product (Shampoo, Conditioner, etc.)
            ph_level: Product pH (optional)

        Returns:
            Analysis results with Crown Score and recommendations

        """
        try:
            # Convert dict to HairProfile object
            profile = HairProfile(
                hair_type=HairType(hair_profile.get("hair_type", "4C")),
                porosity=Porosity(hair_profile.get("porosity", "High")),
                hair_state=[HairState(s) for s in hair_profile.get("hair_state", ["Natural"])],
                hair_goals=[HairGoal(g) for g in hair_profile.get("hair_goals", ["Moisture"])],
                sensitivities=hair_profile.get("sensitivities", []),
            )

            # Convert product type string to enum
            product_type_enum = ProductType(product_type)

            # Calculate Crown Score
            crown_score, breakdown, verdict = self.crown_engine.calculate_crown_score(
                ingredients=ingredients,
                hair_profile=profile,
                product_type=product_type_enum,
                ph_level=ph_level,
            )

            logger.info(f"✅ Product analyzed: Crown Score {crown_score}/100 - {verdict.value}")

            return {
                "success": True,
                "crown_score": crown_score,
                "verdict": verdict.value,
                "verdict_color": self._get_verdict_color(verdict),
                "verdict_icon": self._get_verdict_icon(verdict),
                "breakdown": {
                    "base_score": breakdown.base_score,
                    "harmful_deductions": breakdown.harmful_deductions,
                    "beneficial_bonuses": breakdown.beneficial_bonuses,
                    "porosity_adjustments": breakdown.porosity_adjustments,
                    "curl_pattern_adjustments": breakdown.curl_pattern_adjustments,
                    "goal_bonuses": breakdown.goal_bonuses,
                    "ph_adjustment": breakdown.ph_adjustment,
                    "product_type_modifiers": breakdown.product_type_modifiers,
                    "interaction_penalties": breakdown.interaction_penalties,
                },
                "red_flags": breakdown.red_flags,
                "good_ingredients": breakdown.good_ingredients,
                "warnings": breakdown.warnings,
                "recommendation": self._generate_recommendation(crown_score, verdict, breakdown),
            }

        except Exception as e:
            logger.error(f"❌ Product analysis failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "crown_score": 0, "verdict": "ERROR"}

    def _get_verdict_color(self, verdict: VerdictLevel) -> str:
        """Get color code for verdict."""
        mapping = {
            VerdictLevel.CROWN_APPROVED: "green",
            VerdictLevel.GOOD_CHOICE: "yellow",
            VerdictLevel.USE_CAUTION: "orange",
            VerdictLevel.NOT_RECOMMENDED: "red",
            VerdictLevel.AVOID: "red",
        }
        return mapping.get(verdict, "gray")

    def _get_verdict_icon(self, verdict: VerdictLevel) -> str:
        """Get icon for verdict."""
        mapping = {
            VerdictLevel.CROWN_APPROVED: "👑",
            VerdictLevel.GOOD_CHOICE: "✓",
            VerdictLevel.USE_CAUTION: "⚠️",
            VerdictLevel.NOT_RECOMMENDED: "⛔",
            VerdictLevel.AVOID: "🚫",
        }
        return mapping.get(verdict, "?")

    def _generate_recommendation(self, crown_score: int, verdict: VerdictLevel, breakdown) -> str:
        """Generate human-readable recommendation."""
        if verdict == VerdictLevel.CROWN_APPROVED:
            return (
                f"Excellent choice for your hair! This product scored {crown_score}/100 "
                "and is ideal for your hair type and goals."
            )

        if verdict == VerdictLevel.GOOD_CHOICE:
            recommendation = f"Good product (scored {crown_score}/100) with minor concerns. "
            if breakdown.red_flags:
                recommendation += f"Watch out for: {', '.join(breakdown.red_flags[:2])}."
            return recommendation

        if verdict == VerdictLevel.USE_CAUTION:
            recommendation = f"Use with caution (scored {crown_score}/100). "
            if breakdown.red_flags:
                recommendation += f"Contains: {', '.join(breakdown.red_flags[:3])}. "
            recommendation += "Consider patch testing before full use."
            return recommendation

        if verdict == VerdictLevel.NOT_RECOMMENDED:
            recommendation = f"Not recommended (scored {crown_score}/100). "
            if breakdown.red_flags:
                flags = ", ".join(breakdown.red_flags[:3])
                recommendation += f"Multiple concerning ingredients: {flags}. "
            recommendation += "Consider safer alternatives."
            return recommendation

        # AVOID
        recommendation = f"AVOID this product (scored {crown_score}/100). "
        if breakdown.red_flags:
            flags = ", ".join(breakdown.red_flags)
            recommendation += f"Dangerous ingredients detected: {flags}. "
        recommendation += "This product could damage your hair."
        return recommendation

    async def find_alternatives(self, product_name: str, category: str, min_crown_score: int = 75) -> list[dict]:
        """Find safer alternative products.

        Args:
            product_name: Name of the product to replace
            category: Product category (Shampoo, Conditioner, etc.)
            min_crown_score: Minimum acceptable Crown Score

        Returns:
            List of alternative products

        """
        # TODO: Implement database query for alternatives
        # For now, return placeholder
        logger.info(f"🔍 Finding alternatives for {product_name} (category: {category})")

        return [
            {
                "product_name": "Mielle Organics Pomegranate & Honey Moisturizing Conditioner",
                "brand": "Mielle Organics",
                "crown_score": 92,
                "price": 10.99,
                "available_at": ["Target", "Amazon", "Walmart"],
            },
            {
                "product_name": ("SheaMoisture Jamaican Black Castor Oil Strengthen & Restore Leave-In"),
                "brand": "SheaMoisture",
                "crown_score": 88,
                "price": 9.99,
                "available_at": ["Target", "CVS", "Walgreens"],
            },
        ]


# Create global instance
ingredient_analysis_agent = IngredientAnalysisAgent()
