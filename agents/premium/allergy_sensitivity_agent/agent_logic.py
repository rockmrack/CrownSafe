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
        if not use_mock:
            self.logger.info("Mock ingredient database disabled by config")
            self.ingredient_db = {}
            return
            
        try:
            with open(MOCK_INGREDIENTS_PATH, 'r') as f:
                self.ingredient_db = json.load(f)
            self.logger.info("Successfully loaded mock ingredient database.")
        except Exception as e:
            self.logger.error(f"CRITICAL: Could not load ingredient data: {e}")
            self.ingredient_db = {}

    def check_product_for_family(self, user_id: int, product_upc: str) -> Dict[str, Any]:
        """
        Checks a product's ingredients against all members of a user's family.
        """
        self.logger.info(f"Performing allergy check for user {user_id} and UPC {product_upc}")

        # 1. Get product ingredients
        product_info = self.ingredient_db.get(product_upc)
        if not product_info:
            return {"status": "error", "message": "Product not found in ingredient database."}
        
        product_ingredients = set(product_info.get("ingredients", []))
        product_name = product_info.get("product_name", "Unknown Product")

        # 2. Get family members and their allergies from the database
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user or not user.families:
                    return {"status": "error", "message": "User or user's family not found."}
                
                # For MVP, assume user belongs to one family
                family = user.families[0]
                family_members = family.members

                if not family_members:
                    return {"status": "success", "product_name": product_name, "is_safe": True, "alerts": []}

                # 3. Cross-reference and find matches
                alerts = []
                for member in family_members:
                    member_allergies = set(member.allergies or [])
                    
                    # Find the intersection of the two sets
                    found_allergens = product_ingredients.intersection(member_allergies)
                    
                    if found_allergens:
                        alerts.append({
                            "member_name": member.name,
                            "found_allergens": list(found_allergens),
                            "risk_level": "high"
                        })
                
                if alerts:
                    self.logger.warning(f"Found {len(alerts)} allergy alerts for product '{product_name}'.")
                    return {"status": "success", "product_name": product_name, "is_safe": False, "alerts": alerts}
                else:
                    self.logger.info(f"Product '{product_name}' is safe for all family members.")
                    return {"status": "success", "product_name": product_name, "is_safe": True, "alerts": []}

        except Exception as e:
            self.logger.error(f"Database error during allergy check: {e}", exc_info=True)
            return {"status": "error", "message": "An unexpected database error occurred."}