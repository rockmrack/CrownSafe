import logging
import json
import os
from typing import Dict, Any, List
from pathlib import Path

from core_infra.database import get_db_session, User, FamilyMember

logger = logging.getLogger(__name__)

MOCK_INGREDIENTS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mock_product_ingredients.json"


class AllergySensitivityAgentLogic:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logger

        # Check if mock data is allowed in production
        USE_MOCK_INGREDIENT_DB = os.getenv("USE_MOCK_INGREDIENT_DB", "false").lower() == "true"
        ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

        if ENVIRONMENT == "production" and USE_MOCK_INGREDIENT_DB:
            raise RuntimeError("Production environment cannot use mock ingredient database")

        self._load_ingredient_data(USE_MOCK_INGREDIENT_DB)
        self.logger.info("AllergySensitivityAgentLogic initialized.")

    def _load_ingredient_data(self, use_mock: bool = False):
        """Loads the ingredient data."""
        if use_mock:
            # Legacy mock data support for development
            try:
                with open(MOCK_INGREDIENTS_PATH, "r") as f:
                    self.ingredient_db = json.load(f)
                self.logger.info("Successfully loaded mock ingredient database.")
            except Exception as e:
                self.logger.error(f"CRITICAL: Could not load mock data: {e}")
                self.ingredient_db = {}
        else:
            # Use real database for production
            self.logger.info("Using real ingredient database from database")
            # Database connections will be made per-request for better performance
            self.ingredient_db = None  # Will use database queries

    def check_product_for_family(self, user_id: int, product_upc: str) -> Dict[str, Any]:
        """
        Checks a product's ingredients against all members of a user's family.
        """
        self.logger.info(f"Performing allergy check for user {user_id} and UPC {product_upc}")

        # Use mock data if available (development mode)
        if self.ingredient_db is not None:
            return self._check_with_mock_data(user_id, product_upc)

        # Use real database (production mode)
        return self._check_with_database(user_id, product_upc)

    def _check_with_mock_data(self, user_id: int, product_upc: str) -> Dict[str, Any]:
        """Legacy mock data checking for development"""
        # 1. Get product ingredients
        product_info = self.ingredient_db.get(product_upc)
        if not product_info:
            return {
                "status": "error",
                "message": "Product not found in ingredient database.",
            }

        product_ingredients = set(product_info.get("ingredients", []))
        product_name = product_info.get("product_name", "Unknown Product")

        # Continue with existing mock logic...
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.families:
                    return {
                        "status": "error",
                        "message": "User or user's family not found.",
                    }

                # For MVP, assume user belongs to one family
                family = user.families[0]
                family_members = family.members

                if not family_members:
                    return {
                        "status": "success",
                        "product_name": product_name,
                        "is_safe": True,
                        "alerts": [],
                    }

                # 3. Check for allergen conflicts
                alerts = []
                for member in family_members:
                    member_allergies = set([allergy.allergen_name.lower() for allergy in member.allergies])

                    # Check for direct ingredient matches
                    conflicting_ingredients = product_ingredients.intersection(member_allergies)

                    if conflicting_ingredients:
                        alerts.append(
                            {
                                "member_name": member.name,
                                "age_months": member.age_months,
                                "conflicting_ingredients": list(conflicting_ingredients),
                                "severity": "high",  # Default; could be enhanced
                            }
                        )

                is_safe = len(alerts) == 0
                return {
                    "status": "success",
                    "product_name": product_name,
                    "is_safe": is_safe,
                    "alerts": alerts,
                    "total_ingredients_checked": len(product_ingredients),
                    "family_members_checked": len(family_members),
                    "data_source": "mock",
                }

        except Exception as e:
            self.logger.error(f"Database error during allergy check: {e}")
            return {"status": "error", "message": f"Database error: {str(e)}"}

    def _check_with_database(self, user_id: int, product_upc: str) -> Dict[str, Any]:
        """Real database checking for production"""
        from db.models.product_ingredients import ProductIngredient, IngredientSafety

        try:
            with get_db_session() as db:
                # 1. Get product ingredients from database
                product = db.query(ProductIngredient).filter(ProductIngredient.upc == product_upc).first()
                if not product:
                    return {
                        "status": "error",
                        "message": "Product not found in ingredient database.",
                    }

                product_ingredients = set(product.ingredients) if product.ingredients else set()
                known_allergens = set(product.allergens) if product.allergens else set()

                # 2. Get family members and their allergies
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.families:
                    return {
                        "status": "error",
                        "message": "User or user's family not found.",
                    }

                # For MVP, assume user belongs to one family
                family = user.families[0]
                family_members = family.members

                if not family_members:
                    return {
                        "status": "success",
                        "product_name": product.product_name,
                        "is_safe": True,
                        "alerts": [],
                        "data_source": "database",
                    }

                # 3. Check for allergen conflicts
                alerts = []
                for member in family_members:
                    member_allergies = set([allergy.allergen_name.lower() for allergy in member.allergies])

                    # Check for direct ingredient matches
                    conflicting_ingredients = product_ingredients.intersection(member_allergies)

                    # Check for known allergen matches
                    conflicting_allergens = known_allergens.intersection(member_allergies)

                    # Check database for ingredient safety records
                    ingredient_alerts = []
                    for ingredient in product_ingredients:
                        safety_records = (
                            db.query(IngredientSafety)
                            .filter(
                                IngredientSafety.ingredient_name.ilike(f"%{ingredient}%"),
                                IngredientSafety.common_allergen,
                            )
                            .all()
                        )

                        for safety_record in safety_records:
                            if safety_record.allergen_type and safety_record.allergen_type.lower() in member_allergies:
                                ingredient_alerts.append(
                                    {
                                        "ingredient": ingredient,
                                        "allergen_type": safety_record.allergen_type,
                                        "matched_allergen": safety_record.ingredient_name,
                                    }
                                )

                    if conflicting_ingredients or conflicting_allergens or ingredient_alerts:
                        alerts.append(
                            {
                                "member_name": member.name,
                                "age_months": member.age_months,
                                "conflicting_ingredients": list(conflicting_ingredients),
                                "conflicting_allergens": list(conflicting_allergens),
                                "ingredient_alerts": ingredient_alerts,
                                "severity": "high",  # Default; could be enhanced based on member age/sensitivity
                            }
                        )

                is_safe = len(alerts) == 0
                return {
                    "status": "success",
                    "product_name": product.product_name,
                    "brand": product.brand,
                    "category": product.category,
                    "is_safe": is_safe,
                    "alerts": alerts,
                    "total_ingredients_checked": len(product_ingredients),
                    "family_members_checked": len(family_members),
                    "data_source": "database",
                    "confidence_score": product.confidence_score,
                    "last_updated": product.last_updated.isoformat() if product.last_updated else None,
                }

        except Exception as e:
            self.logger.error(f"Database error during allergy check: {e}")
            return {"status": "error", "message": f"Database error: {str(e)}"}
