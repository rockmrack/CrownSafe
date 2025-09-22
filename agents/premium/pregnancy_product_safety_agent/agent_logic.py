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
        if use_mock:
            # Legacy mock data support for development
            try:
                with open(MOCK_INGREDIENTS_PATH, 'r') as f:
                    self.ingredient_db = json.load(f)
                with open(MOCK_SAFETY_DATA_PATH, 'r') as f:
                    self.safety_db = json.load(f).get("unsafe_ingredients", {})
                self.logger.info("Successfully loaded mock ingredient and pregnancy safety databases.")
            except Exception as e:
                self.logger.error(f"CRITICAL: Could not load mock data: {e}")
                self.ingredient_db = {}
                self.safety_db = {}
        else:
            # Use real database for production
            self.logger.info("Using real ingredient and pregnancy safety databases from database")
            # Database connections will be made per-request for better performance
            self.ingredient_db = None  # Will use database queries
            self.safety_db = None      # Will use database queries

    def check_product_safety(self, product_upc: str, trimester: int = 1) -> Dict[str, Any]:
        """
        Checks a product's ingredients against the pregnancy safety database.
        The 'trimester' argument is included for future, more advanced logic.
        """
        self.logger.info(f"Performing pregnancy safety check for UPC {product_upc} (Trimester: {trimester})")

        # Use mock data if available (development mode)
        if self.ingredient_db is not None and self.safety_db is not None:
            return self._check_with_mock_data(product_upc, trimester)
        
        # Use real database (production mode)
        return self._check_with_database(product_upc, trimester)
    
    def _check_with_mock_data(self, product_upc: str, trimester: int) -> Dict[str, Any]:
        """Legacy mock data checking for development"""
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
        
        # Return results
        is_safe = len(unsafe_ingredients_found) == 0
        return {
            "status": "success",
            "product_name": product_name,
            "is_safe": is_safe,
            "unsafe_ingredients": unsafe_ingredients_found,
            "total_ingredients_checked": len(product_ingredients),
            "data_source": "mock"
        }
    
    def _check_with_database(self, product_upc: str, trimester: int) -> Dict[str, Any]:
        """Real database checking for production"""
        from core_infra.database import get_db_session
        from models.product_ingredients import ProductIngredient, IngredientSafety
        
        with get_db_session() as db:
            # 1. Get product ingredients from database
            product = db.query(ProductIngredient).filter(ProductIngredient.upc == product_upc).first()
            if not product:
                return {"status": "error", "message": "Product not found in ingredient database."}
            
            # Check if product is already marked as pregnancy unsafe
            if product.pregnancy_safe is False:
                return {
                    "status": "success",
                    "product_name": product.product_name,
                    "is_safe": False,
                    "unsafe_ingredients": ["Product marked as pregnancy unsafe"],
                    "total_ingredients_checked": len(product.ingredients) if product.ingredients else 0,
                    "data_source": "database",
                    "confidence_score": product.confidence_score
                }
            
            product_ingredients = set(product.ingredients) if product.ingredients else set()
            
            # 2. Cross-reference with unsafe ingredients list
            unsafe_ingredients_found = []
            for ingredient in product_ingredients:
                # Check for exact match or partial match
                safety_records = db.query(IngredientSafety).filter(
                    (IngredientSafety.ingredient_name.ilike(f"%{ingredient}%")) |
                    (IngredientSafety.alternative_names.contains([ingredient]))
                ).all()
                
                for safety_record in safety_records:
                    if safety_record.pregnancy_risk_level:
                        unsafe_ingredients_found.append({
                            "ingredient": ingredient,
                            "matched_name": safety_record.ingredient_name,
                            "risk_level": safety_record.pregnancy_risk_level,
                            "reason": safety_record.pregnancy_risk_reason,
                            "source": safety_record.pregnancy_source
                        })
            
            # Return results
            is_safe = len(unsafe_ingredients_found) == 0
            return {
                "status": "success", 
                "product_name": product.product_name,
                "brand": product.brand,
                "category": product.category,
                "is_safe": is_safe,
                "unsafe_ingredients": unsafe_ingredients_found,
                "total_ingredients_checked": len(product_ingredients),
                "data_source": "database",
                "confidence_score": product.confidence_score,
                "last_updated": product.last_updated.isoformat() if product.last_updated else None
            }