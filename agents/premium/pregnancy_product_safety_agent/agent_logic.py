import logging
import json
import os
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

MOCK_INGREDIENTS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mock_product_ingredients.json"
MOCK_SAFETY_DATA_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mock_pregnancy_safety_data.json"

class PregnancyProductSafetyAgentLogic:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logger
        
        # Check if mock data is allowed in production
        USE_MOCK_INGREDIENT_DB = os.getenv("USE_MOCK_INGREDIENT_DB", "false").lower() == "true"
        ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        
        if ENVIRONMENT == "production" and USE_MOCK_INGREDIENT_DB:
            raise RuntimeError("Production environment cannot use mock ingredient database")
        
        self._load_data(USE_MOCK_INGREDIENT_DB)
        self.logger.info("PregnancyProductSafetyAgentLogic initialized.")

    def _load_data(self, use_mock: bool = False):
        """Loads both the ingredient and safety databases."""
        if not use_mock:
            self.logger.info("Mock ingredient and pregnancy safety databases disabled by config")
            self.ingredient_db = {}
            self.safety_db = {}
            return
            
        try:
            with open(MOCK_INGREDIENTS_PATH, 'r') as f:
                self.ingredient_db = json.load(f)
            with open(MOCK_SAFETY_DATA_PATH, 'r') as f:
                self.safety_db = json.load(f).get("unsafe_ingredients", {})
            self.logger.info("Successfully loaded mock ingredient and pregnancy safety databases.")
        except Exception as e:
            self.logger.error(f"CRITICAL: Could not load data: {e}")
            self.ingredient_db = {}
            self.safety_db = {}

    def check_product_safety(self, product_upc: str, trimester: int = 1) -> Dict[str, Any]:
        """
        Checks a product's ingredients against the pregnancy safety database.
        The 'trimester' argument is included for future, more advanced logic.
        """
        self.logger.info(f"Performing pregnancy safety check for UPC {product_upc} (Trimester: {trimester})")

        # 1. Get product ingredients
        product_info = self.ingredient_db.get(product_upc)
        if not product_info:
            return {"status": "error", "message": "Product not found in ingredient database."}
        
        product_ingredients = set(product_info.get("ingredients", []))
        product_name = product_info.get("product_name", "Unknown Product")

        # 2. Cross-reference with unsafe ingredients list
        unsafe_ingredients_found = []
        for ingredient in product_ingredients:
            if ingredient in self.safety_db:
                unsafe_info = self.safety_db[ingredient]
                unsafe_ingredients_found.append({
                    "ingredient": ingredient,
                    "risk_level": unsafe_info.get("risk_level"),
                    "reason": unsafe_info.get("reason")
                })

        if unsafe_ingredients_found:
            self.logger.warning(f"Found {len(unsafe_ingredients_found)} unsafe ingredients in '{product_name}'.")
            return {
                "status": "success",
                "product_name": product_name,
                "is_safe": False,
                "alerts": unsafe_ingredients_found
            }
        else:
            self.logger.info(f"Product '{product_name}' is considered safe based on our database.")
            return {
                "status": "success",
                "product_name": product_name,
                "is_safe": True,
                "alerts": []
            }