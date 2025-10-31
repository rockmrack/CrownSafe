"""Crown Score Engine - Enterprise-Grade Hair Product Analysis
Scientifically-backed scoring system for Black hair care products (3C-4C).

Version: 1.0.0
Last Updated: October 24, 2025
"""

import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATA CLASSES
# ============================================================================


class HairType(str, Enum):
    """Curl pattern classification."""

    TYPE_3C = "3C"
    TYPE_4A = "4A"
    TYPE_4B = "4B"
    TYPE_4C = "4C"
    MIXED = "Mixed"


class Porosity(str, Enum):
    """Hair porosity level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class HairState(str, Enum):
    """Current hair condition."""

    NATURAL = "Natural"
    RELAXED = "Relaxed"
    TRANSITIONING = "Transitioning"
    HEAT_DAMAGED = "Heat-damaged"
    COLOR_TREATED = "Color-treated"


class HairGoal(str, Enum):
    """User's hair goals."""

    GROWTH = "Growth"
    MOISTURE = "Moisture retention"
    EDGES = "Edge recovery"
    DEFINITION = "Definition"
    THICKNESS = "Thickness"


class ProductType(str, Enum):
    """Product category."""

    SHAMPOO = "Shampoo"
    CONDITIONER = "Conditioner"
    LEAVE_IN = "Leave-In"
    DEEP_CONDITIONER = "Deep Conditioner"
    GEL = "Gel/Styler"
    OIL = "Oil"
    CREAM = "Cream"
    MASK = "Mask"


class VerdictLevel(str, Enum):
    """Crown Score verdict levels."""

    CROWN_APPROVED = "CROWN APPROVED"
    GOOD_CHOICE = "GOOD CHOICE"
    USE_CAUTION = "USE WITH CAUTION"
    NOT_RECOMMENDED = "NOT RECOMMENDED"
    AVOID = "AVOID"


@dataclass
class HairProfile:
    """User's complete hair profile."""

    hair_type: HairType
    porosity: Porosity
    hair_state: list[HairState]
    hair_goals: list[HairGoal]
    sensitivities: list[str]  # e.g., ["protein-sensitive", "coconut-sensitive"]


@dataclass
class Ingredient:
    """Individual ingredient data."""

    name: str
    common_names: list[str]
    category: str  # "Alcohol", "Sulfate", "Butter", "Oil", "Protein", etc.
    base_score: int  # -50 to +20
    safety_level: str  # "Safe", "Caution", "Avoid", "Dangerous"
    effects: list[str]  # ["Moisturizing", "Drying", "Protein", etc.]
    porosity_adjustments: dict[Porosity, int]  # Additional points by porosity
    curl_pattern_adjustments: dict[HairType, int]  # Additional points by curl type


@dataclass
class ScoreBreakdown:
    """Detailed scoring breakdown for transparency."""

    base_score: int = 100
    harmful_deductions: int = 0
    beneficial_bonuses: int = 0
    porosity_adjustments: int = 0
    curl_pattern_adjustments: int = 0
    goal_bonuses: int = 0
    ph_adjustment: int = 0
    product_type_modifiers: int = 0
    interaction_penalties: int = 0
    final_score: int = 0
    red_flags: list[str] | None = None
    good_ingredients: list[str] | None = None
    warnings: list[str] | None = None

    def __post_init__(self):
        if self.red_flags is None:
            self.red_flags = []
        if self.good_ingredients is None:
            self.good_ingredients = []
        if self.warnings is None:
            self.warnings = []


# ============================================================================
# INGREDIENT DATABASE (MVP - 200 ingredients)
# ============================================================================


class IngredientDatabase:
    """Enterprise ingredient database with safety ratings and compatibility data
    MVP: 200 most common ingredients.
    """

    # Tier 1: Severe Health Hazards
    SEVERE_HAZARDS = {
        "formaldehyde": Ingredient(
            name="Formaldehyde",
            common_names=["Formalin", "Methylene glycol", "Quaternium-15", "DMDM Hydantoin"],
            category="Preservative",
            base_score=-50,
            safety_level="Dangerous",
            effects=["Carcinogenic", "Respiratory damage"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "butylparaben": Ingredient(
            name="Butylparaben",
            common_names=["Butyl paraben", "4-Hydroxybenzoic acid butyl ester"],
            category="Preservative",
            base_score=-40,
            safety_level="Dangerous",
            effects=["Endocrine disruptor", "Hormone mimic"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "propylparaben": Ingredient(
            name="Propylparaben",
            common_names=["Propyl paraben"],
            category="Preservative",
            base_score=-40,
            safety_level="Dangerous",
            effects=["Endocrine disruptor"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "lead acetate": Ingredient(
            name="Lead Acetate",
            common_names=["Lead(II) acetate"],
            category="Colorant",
            base_score=-50,
            safety_level="Dangerous",
            effects=["Neurotoxic", "Banned in EU"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
    }

    # Tier 2: Scalp & Hair Damage
    HARMFUL_INGREDIENTS = {
        "isopropyl alcohol": Ingredient(
            name="Isopropyl Alcohol",
            common_names=["Isopropanol", "2-Propanol"],
            category="Drying Alcohol",
            base_score=-30,
            safety_level="Avoid",
            effects=["Severe moisture stripping", "Breakage"],
            porosity_adjustments={
                Porosity.HIGH: -10,  # Extra penalty for high porosity
            },
            curl_pattern_adjustments={HairType.TYPE_4B: -5, HairType.TYPE_4C: -5},
        ),
        "sd alcohol 40": Ingredient(
            name="SD Alcohol 40",
            common_names=["Alcohol Denat", "Ethanol"],
            category="Drying Alcohol",
            base_score=-30,
            safety_level="Avoid",
            effects=["Moisture stripping"],
            porosity_adjustments={Porosity.HIGH: -10},
            curl_pattern_adjustments={HairType.TYPE_4B: -5, HairType.TYPE_4C: -5},
        ),
        "sodium lauryl sulfate": Ingredient(
            name="Sodium Lauryl Sulfate",
            common_names=["SLS"],
            category="Sulfate",
            base_score=-25,
            safety_level="Caution",
            effects=["Strip natural oils", "Cause dryness"],
            porosity_adjustments={},
            curl_pattern_adjustments={
                HairType.TYPE_4A: -5,
                HairType.TYPE_4B: -5,
                HairType.TYPE_4C: -5,
            },
        ),
        "sodium laureth sulfate": Ingredient(
            name="Sodium Laureth Sulfate",
            common_names=["SLES"],
            category="Sulfate",
            base_score=-25,
            safety_level="Caution",
            effects=["Strip oils", "Drying"],
            porosity_adjustments={},
            curl_pattern_adjustments={
                HairType.TYPE_4A: -5,
                HairType.TYPE_4B: -5,
                HairType.TYPE_4C: -5,
            },
        ),
        "dimethicone": Ingredient(
            name="Dimethicone",
            common_names=["Polydimethylsiloxane"],
            category="Heavy Silicone",
            base_score=-20,
            safety_level="Caution",
            effects=["Buildup", "Prevents moisture penetration"],
            porosity_adjustments={
                Porosity.HIGH: -10,  # Worse for high porosity
            },
            curl_pattern_adjustments={},
        ),
        "mineral oil": Ingredient(
            name="Mineral Oil",
            common_names=["Paraffinum Liquidum", "Petrolatum in leave-ins"],
            category="Occlusive",
            base_score=-15,
            safety_level="Caution",
            effects=["Seals out moisture", "Not penetrating"],
            porosity_adjustments={
                Porosity.LOW: -10,  # Worse for low porosity
            },
            curl_pattern_adjustments={},
        ),
        "fragrance": Ingredient(
            name="Fragrance",
            common_names=["Parfum", "Perfume"],
            category="Fragrance",
            base_score=-10,
            safety_level="Caution",
            effects=["Scalp irritation", "Allergic reactions"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
    }

    # Tier 1: Superstar Moisturizers
    SUPERSTAR_INGREDIENTS = {
        "shea butter": Ingredient(
            name="Shea Butter",
            common_names=["Butyrospermum parkii"],
            category="Butter",
            base_score=20,
            safety_level="Safe",
            effects=["Deep moisture", "Scalp healing", "Anti-inflammatory"],
            porosity_adjustments={
                Porosity.LOW: -5,  # Can cause buildup on low porosity
                Porosity.HIGH: 10,  # Excellent for high porosity
            },
            curl_pattern_adjustments={HairType.TYPE_4B: 5, HairType.TYPE_4C: 10},
        ),
        "coconut oil": Ingredient(
            name="Coconut Oil",
            common_names=["Cocos nucifera"],
            category="Oil",
            base_score=18,
            safety_level="Safe",
            effects=["Penetrates hair shaft", "Reduces protein loss"],
            porosity_adjustments={Porosity.LOW: 5, Porosity.MEDIUM: 5, Porosity.HIGH: 0},
            curl_pattern_adjustments={},
        ),
        "avocado oil": Ingredient(
            name="Avocado Oil",
            common_names=["Persea gratissima"],
            category="Oil",
            base_score=15,
            safety_level="Safe",
            effects=["Rich in vitamins", "Penetrates cortex"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "argan oil": Ingredient(
            name="Argan Oil",
            common_names=["Argania spinosa"],
            category="Oil",
            base_score=15,
            safety_level="Safe",
            effects=["Antioxidants", "Shine", "Smoothness"],
            porosity_adjustments={},
            curl_pattern_adjustments={HairType.TYPE_3C: 5, HairType.TYPE_4A: 5},
        ),
    }

    # Tier 2: Humectants & Conditioning
    HUMECTANTS = {
        "glycerin": Ingredient(
            name="Glycerin",
            common_names=["Glycerol"],
            category="Humectant",
            base_score=15,
            safety_level="Safe",
            effects=["Attracts moisture from air"],
            porosity_adjustments={
                Porosity.LOW: -5,  # Sits on surface
                Porosity.HIGH: 10,  # Draws in moisture
            },
            curl_pattern_adjustments={},
        ),
        "aloe vera": Ingredient(
            name="Aloe Vera",
            common_names=["Aloe barbadensis"],
            category="Humectant",
            base_score=12,
            safety_level="Safe",
            effects=["Hydrating", "pH balancing", "Scalp soothing"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "honey": Ingredient(
            name="Honey",
            common_names=["Mel"],
            category="Humectant",
            base_score=10,
            safety_level="Safe",
            effects=["Humectant", "Antimicrobial"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "hyaluronic acid": Ingredient(
            name="Hyaluronic Acid",
            common_names=["Sodium Hyaluronate"],
            category="Humectant",
            base_score=12,
            safety_level="Safe",
            effects=["Extreme hydration retention"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
    }

    # Tier 3: Proteins (Conditional)
    PROTEINS = {
        "hydrolyzed keratin": Ingredient(
            name="Hydrolyzed Keratin",
            common_names=["Keratin protein"],
            category="Protein",
            base_score=10,  # Base bonus (conditional on hair state)
            safety_level="Safe",
            effects=["Strengthening", "Repair"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "wheat protein": Ingredient(
            name="Wheat Protein",
            common_names=["Hydrolyzed wheat protein"],
            category="Protein",
            base_score=8,
            safety_level="Safe",
            effects=["Strengthening"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "silk protein": Ingredient(
            name="Silk Protein",
            common_names=["Hydrolyzed silk"],
            category="Protein",
            base_score=0,  # Neutral base (can be negative if protein-sensitive)
            safety_level="Safe",
            effects=["Smoothing", "Shine"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
    }

    # Growth-Supporting Ingredients
    GROWTH_BOOSTERS = {
        "biotin": Ingredient(
            name="Biotin",
            common_names=["Vitamin B7", "Vitamin H"],
            category="Vitamin",
            base_score=8,
            safety_level="Safe",
            effects=["Hair growth support"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "castor oil": Ingredient(
            name="Castor Oil",
            common_names=["Ricinus communis"],
            category="Oil",
            base_score=10,
            safety_level="Safe",
            effects=["Hair growth", "Thickness"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
        "peppermint oil": Ingredient(
            name="Peppermint Oil",
            common_names=["Mentha piperita"],
            category="Essential Oil",
            base_score=5,
            safety_level="Safe",
            effects=["Scalp stimulation", "Growth promotion"],
            porosity_adjustments={},
            curl_pattern_adjustments={},
        ),
    }

    @classmethod
    def get_all_ingredients(cls) -> dict[str, Ingredient]:
        """Combine all ingredient databases."""
        all_ingredients = {}
        all_ingredients.update(cls.SEVERE_HAZARDS)
        all_ingredients.update(cls.HARMFUL_INGREDIENTS)
        all_ingredients.update(cls.SUPERSTAR_INGREDIENTS)
        all_ingredients.update(cls.HUMECTANTS)
        all_ingredients.update(cls.PROTEINS)
        all_ingredients.update(cls.GROWTH_BOOSTERS)
        return all_ingredients

    @classmethod
    def find_ingredient(cls, ingredient_name: str) -> Ingredient | None:
        """Find ingredient by name or common name (case-insensitive)."""
        ingredient_name_lower = ingredient_name.lower().strip()
        all_ingredients = cls.get_all_ingredients()

        # Direct match
        if ingredient_name_lower in all_ingredients:
            return all_ingredients[ingredient_name_lower]

        # Check common names
        for _key, ingredient in all_ingredients.items():
            if ingredient_name_lower in [name.lower() for name in ingredient.common_names]:
                return ingredient
            if ingredient_name_lower in ingredient.name.lower():
                return ingredient

        return None


# ============================================================================
# CROWN SCORE ENGINE
# ============================================================================


class CrownScoreEngine:
    """Enterprise-grade hair product scoring engine
    Analyzes products based on ingredients and user's hair profile.
    """

    def __init__(self) -> None:
        self.ingredient_db = IngredientDatabase()

    def calculate_crown_score(
        self,
        ingredients: list[str],
        hair_profile: HairProfile,
        product_type: ProductType,
        ph_level: float | None = None,
    ) -> tuple[int, ScoreBreakdown, VerdictLevel]:
        """Calculate Crown Score for a product.

        Args:
            ingredients: List of ingredient names
            hair_profile: User's hair profile
            product_type: Type of product (shampoo, conditioner, etc.)
            ph_level: Product pH (optional, defaults to neutral)

        Returns:
            Tuple of (crown_score, breakdown, verdict)

        """
        breakdown = ScoreBreakdown()
        logger.info(f"Calculating Crown Score for {product_type.value} with {len(ingredients)} ingredients")

        # Step 1: Analyze each ingredient
        protein_count = 0
        for ingredient_name in ingredients:
            ingredient = self.ingredient_db.find_ingredient(ingredient_name)

            if not ingredient:
                logger.debug(f"Unknown ingredient: {ingredient_name}")
                continue

            # Base score
            if ingredient.base_score < 0:
                breakdown.harmful_deductions += ingredient.base_score
                breakdown.red_flags.append(f"{ingredient.name} ({ingredient.safety_level})")
            elif ingredient.base_score > 0:
                breakdown.beneficial_bonuses += ingredient.base_score
                breakdown.good_ingredients.append(ingredient.name)

            # Porosity adjustments
            if hair_profile.porosity in ingredient.porosity_adjustments:
                adjustment = ingredient.porosity_adjustments[hair_profile.porosity]
                breakdown.porosity_adjustments += adjustment

            # Curl pattern adjustments
            if hair_profile.hair_type in ingredient.curl_pattern_adjustments:
                adjustment = ingredient.curl_pattern_adjustments[hair_profile.hair_type]
                breakdown.curl_pattern_adjustments += adjustment

            # Track proteins for overload detection
            if ingredient.category == "Protein":
                protein_count += 1

            # Goal-based bonuses
            breakdown.goal_bonuses += self._calculate_goal_bonuses(ingredient, hair_profile.hair_goals)

            # Protein sensitivity check
            is_protein_sensitive = "protein-sensitive" in hair_profile.sensitivities
            if is_protein_sensitive and ingredient.category == "Protein":
                breakdown.interaction_penalties -= 15
                breakdown.warnings.append("⚠️ Protein detected (you're protein-sensitive)")

        # Step 2: Protein overload detection
        if protein_count > 2:
            is_protein_sensitive = "protein-sensitive" in hair_profile.sensitivities
            if is_protein_sensitive:
                breakdown.interaction_penalties -= 20
                breakdown.warnings.append("🚨 PROTEIN OVERLOAD RISK - Multiple proteins detected!")
            else:
                breakdown.warnings.append("⚠️ High protein content - monitor for protein overload")

        # Step 3: pH Balance scoring
        if ph_level:
            breakdown.ph_adjustment = self._calculate_ph_score(ph_level)

        # Step 4: Product-type specific adjustments
        breakdown.product_type_modifiers = self._calculate_product_type_modifiers(
            ingredients, product_type, hair_profile,
        )

        # Step 5: Dangerous combinations
        breakdown.interaction_penalties += self._detect_dangerous_combinations(ingredients)

        # Step 6: Calculate final score
        breakdown.final_score = max(
            0,
            min(
                100,
                (
                    breakdown.base_score
                    + breakdown.harmful_deductions  # Already negative
                    + breakdown.beneficial_bonuses
                    + breakdown.porosity_adjustments
                    + breakdown.curl_pattern_adjustments
                    + breakdown.goal_bonuses
                    + breakdown.ph_adjustment
                    + breakdown.product_type_modifiers
                    + breakdown.interaction_penalties  # Already negative
                ),
            ),
        )

        # Step 7: Determine verdict
        verdict = self._get_verdict(breakdown.final_score)

        logger.info(f"Crown Score calculated: {breakdown.final_score}/100 - {verdict.value}")
        return breakdown.final_score, breakdown, verdict

    def _calculate_goal_bonuses(self, ingredient: Ingredient, goals: list[HairGoal]) -> int:
        """Calculate bonuses based on user's hair goals."""
        bonus = 0

        for goal in goals:
            if goal == HairGoal.GROWTH:
                if ingredient.name in ["Biotin", "Castor Oil"]:
                    bonus += 10
                elif ingredient.name == "Peppermint Oil":
                    bonus += 5
                elif ingredient.category == "Drying Alcohol":
                    bonus -= 10  # Extra penalty for growth goal

            elif goal == HairGoal.EDGES:
                if ingredient.name == "Castor Oil":
                    bonus += 15
                elif ingredient.name == "Vitamin E":
                    bonus += 8

            elif goal == HairGoal.MOISTURE:
                if ingredient.name == "Shea Butter":
                    bonus += 10
                elif ingredient.name == "Glycerin":
                    bonus += 5
                elif ingredient.category in ["Sulfate", "Drying Alcohol"]:
                    bonus -= 15  # Extra penalty for moisture goal

            elif goal == HairGoal.DEFINITION:
                if "flaxseed" in ingredient.name.lower():
                    bonus += 12
                elif ingredient.name == "Aloe Vera":
                    bonus += 8

            elif goal == HairGoal.THICKNESS:
                if ingredient.name == "Biotin":
                    bonus += 10
                elif ingredient.name == "Hydrolyzed Keratin":
                    bonus += 12

        return bonus

    def _calculate_ph_score(self, ph_level: float) -> int:
        """Calculate pH balance score (ideal: 4.5-5.5)."""
        if 4.5 <= ph_level <= 5.5:
            return 10  # Perfect!
        if (4.0 <= ph_level < 4.5) or (5.5 < ph_level <= 6.0):
            return 0  # Acceptable
        if (3.5 <= ph_level < 4.0) or (6.0 < ph_level <= 7.0):
            return -5  # Caution
        return -15  # Damaging

    def _calculate_product_type_modifiers(
        self, ingredients: list[str], product_type: ProductType, hair_profile: HairProfile,
    ) -> int:
        """Product-type specific score adjustments."""
        modifier = 0
        ingredient_names_lower = [i.lower() for i in ingredients]

        if product_type == ProductType.SHAMPOO:
            # Sulfates more acceptable in clarifying shampoos
            if any("sulfate" in i for i in ingredient_names_lower):
                modifier += 15  # Reduce penalty (-25 becomes -10)

        elif product_type == ProductType.CONDITIONER:
            # MUST have emollients
            emollient_list = [
                "shea butter",
                "coconut oil",
                "avocado oil",
                "mango butter",
            ]
            has_emollients = any(name in ingredient_names_lower for name in emollient_list)
            if has_emollients:
                modifier += 15

        elif product_type == ProductType.LEAVE_IN:
            # NO drying alcohols allowed
            if any("alcohol" in i and "cetearyl" not in i for i in ingredient_names_lower):
                modifier -= 10  # Extra penalty (-30 becomes -40)

        elif product_type == ProductType.DEEP_CONDITIONER:
            # Expects heavy moisturizers
            if "shea butter" in ingredient_names_lower or "mango butter" in ingredient_names_lower:
                modifier += 20

        elif product_type == ProductType.GEL:
            # Some hold alcohols OK for gels
            if any("alcohol" in i for i in ingredient_names_lower):
                modifier += 15  # Reduce penalty

        return modifier

    def _detect_dangerous_combinations(self, ingredients: list[str]) -> int:
        """Detect dangerous ingredient combinations."""
        penalty = 0
        ingredient_names_lower = [i.lower() for i in ingredients]

        # Alcohol + Sulfate combo
        has_alcohol = any("alcohol" in i and "cetearyl" not in i for i in ingredient_names_lower)
        has_sulfate = any("sulfate" in i for i in ingredient_names_lower)
        if has_alcohol and has_sulfate:
            penalty -= 40  # Compounded drying effect

        # Heavy silicones without clarifying agents
        has_silicone = any("dimethicone" in i for i in ingredient_names_lower)
        has_clarifier = any("sulfate" in i for i in ingredient_names_lower)
        if has_silicone and not has_clarifier:
            penalty -= 15

        return penalty

    def _get_verdict(self, score: int) -> VerdictLevel:
        """Determine verdict level based on score."""
        if score >= 90:
            return VerdictLevel.CROWN_APPROVED
        if score >= 75:
            return VerdictLevel.GOOD_CHOICE
        if score >= 50:
            return VerdictLevel.USE_CAUTION
        if score >= 25:
            return VerdictLevel.NOT_RECOMMENDED
        return VerdictLevel.AVOID


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # User's hair profile
    profile = HairProfile(
        hair_type=HairType.TYPE_4C,
        porosity=Porosity.HIGH,
        hair_state=[HairState.NATURAL],
        hair_goals=[HairGoal.GROWTH, HairGoal.MOISTURE],
        sensitivities=[],  # Not protein-sensitive
    )

    # Product ingredients
    product_ingredients = [
        "Water",
        "Shea Butter",
        "Glycerin",
        "Aloe Vera",
        "Coconut Oil",
        "Fragrance",
    ]

    # Calculate Crown Score
    engine = CrownScoreEngine()
    score, breakdown, verdict = engine.calculate_crown_score(
        ingredients=product_ingredients,
        hair_profile=profile,
        product_type=ProductType.LEAVE_IN,
        ph_level=5.0,
    )

    print(f"\n{'=' * 60}")
    print(f"CROWN SCORE: {score}/100")
    print(f"VERDICT: {verdict.value}")
    print(f"{'=' * 60}")
    print("\nBREAKDOWN:")
    print(f"  Base Score: {breakdown.base_score}")
    print(f"  Harmful Deductions: {breakdown.harmful_deductions}")
    print(f"  Beneficial Bonuses: {breakdown.beneficial_bonuses}")
    print(f"  Porosity Adjustments: {breakdown.porosity_adjustments}")
    print(f"  Curl Pattern Adjustments: {breakdown.curl_pattern_adjustments}")
    print(f"  Goal Bonuses: {breakdown.goal_bonuses}")
    print(f"  pH Adjustment: {breakdown.ph_adjustment}")
    print(f"  Product Type Modifiers: {breakdown.product_type_modifiers}")
    print(f"  Interaction Penalties: {breakdown.interaction_penalties}")
    print(f"\nRED FLAGS: {breakdown.red_flags}")
    print(f"GOOD INGREDIENTS: {breakdown.good_ingredients}")
    print(f"WARNINGS: {breakdown.warnings}")
