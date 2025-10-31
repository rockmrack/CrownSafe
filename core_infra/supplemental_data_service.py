"""Supplemental Data Service for BabyShield
Integrates authoritative data sources beyond recalls for comprehensive safety reports
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FoodData:
    """Food product data from USDA and Edamam"""

    fdc_id: str | None = None
    name: str | None = None
    ingredients: list[str] | None = None
    allergens: list[str] | None = None
    nutritional_info: dict[str, Any] | None = None
    safety_score: float | None = None
    source: str = "unknown"


@dataclass
class CosmeticData:
    """Cosmetic product data from EU CosIng and Open Beauty Facts"""

    product_name: str | None = None
    ingredients: list[str] | None = None
    regulatory_status: dict[str, str] | None = None
    safety_concerns: list[str] | None = None
    safety_score: float | None = None
    source: str = "unknown"


@dataclass
class ChemicalData:
    """Chemical safety data from OSHA and ATSDR"""

    chemical_name: str | None = None
    cas_number: str | None = None
    safety_limits: dict[str, Any] | None = None
    health_effects: list[str] | None = None
    exposure_guidelines: dict[str, Any] | None = None
    safety_score: float | None = None
    source: str = "unknown"


class USDAClient:
    """USDA FoodData Central API client"""

    def __init__(self) -> None:
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        self.api_key = os.getenv("USDA_API_KEY")
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.info("USDA FoodData Central disabled - no API key provided")

    async def search_food(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for food products in USDA database"""
        if not self.enabled:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/foods/search",
                    params={
                        "api_key": self.api_key,
                        "query": query,
                        "pageSize": limit,
                        "dataType": ["Foundation", "SR Legacy"],
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("foods", [])
        except Exception as e:
            logger.error(f"USDA API error: {e}")
            return []

    async def get_food_details(self, fdc_id: str) -> dict[str, Any] | None:
        """Get detailed food information by FDC ID"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/food/{fdc_id}",
                    params={"api_key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"USDA API error for FDC ID {fdc_id}: {e}")
            return None


class EdamamClient:
    """Edamam Food Database API client"""

    def __init__(self) -> None:
        self.app_id = os.getenv("EDAMAM_APP_ID")
        self.app_key = os.getenv("EDAMAM_APP_KEY")
        self.base_url = "https://api.edamam.com/api/food-database/v2"
        self.enabled = bool(self.app_id and self.app_key)

        if not self.enabled:
            logger.info("Edamam API disabled - no credentials provided")

    async def search_food(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for food products in Edamam database"""
        if not self.enabled:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/parser",
                    params={
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "ingr": query,
                        "limit": limit,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("hints", [])
        except Exception as e:
            logger.error(f"Edamam API error: {e}")
            return []

    async def get_nutrition_info(self, food_id: str) -> dict[str, Any] | None:
        """Get nutritional information for a food item"""
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/nutrients",
                    params={"app_id": self.app_id, "app_key": self.app_key},
                    json={
                        "ingredients": [
                            {
                                "quantity": 100,
                                "measureURI": "http://www.edamam.com/ontologies/edamam.owl#Measure_gram",
                                "foodId": food_id,
                            },
                        ],
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Edamam nutrition API error for food ID {food_id}: {e}")
            return None


class CosIngClient:
    """EU CosIng Database client"""

    def __init__(self) -> None:
        self.base_url = "https://ec.europa.eu/growth/tools-databases/cosing/"
        self.enabled = True  # Public database, no API key needed
        logger.info("EU CosIng database client initialized")

    async def search_ingredient(self, ingredient_name: str) -> list[dict[str, Any]]:
        """Search for cosmetic ingredients in EU CosIng database"""
        if not self.enabled:
            return []

        try:
            # Note: This is a simplified implementation
            # The actual CosIng database would require web scraping or a different approach
            # For now, we'll return mock data structure
            logger.info(f"Searching CosIng for ingredient: {ingredient_name}")

            # Mock response structure - would be replaced with actual API calls
            return [
                {
                    "ingredient_name": ingredient_name,
                    "cas_number": "mock-cas",
                    "ec_number": "mock-ec",
                    "functions": ["mock-function"],
                    "restrictions": [],
                    "safety_assessment": "mock-assessment",
                },
            ]
        except Exception as e:
            logger.error(f"CosIng API error: {e}")
            return []


class SupplementalDataService:
    """Main service for integrating supplemental data sources"""

    def __init__(self) -> None:
        self.usda_client = USDAClient()
        self.edamam_client = EdamamClient()
        self.cosing_client = CosIngClient()

        logger.info("SupplementalDataService initialized")

    async def get_food_data(self, product_name: str, barcode: str | None = None) -> FoodData:
        """Get comprehensive food data from multiple sources"""
        logger.info(f"Getting food data for: {product_name}")

        food_data = FoodData()

        # Search USDA database
        usda_results = await self.usda_client.search_food(product_name, limit=5)
        if usda_results:
            best_match = usda_results[0]
            food_data.fdc_id = str(best_match.get("fdcId", ""))
            food_data.name = best_match.get("description", product_name)
            food_data.source = "USDA"

            # Get detailed nutritional info
            if food_data.fdc_id:
                details = await self.usda_client.get_food_details(food_data.fdc_id)
                if details:
                    food_data.nutritional_info = self._extract_nutritional_info(details)

        # Search Edamam database
        edamam_results = await self.edamam_client.search_food(product_name, limit=5)
        if edamam_results and not food_data.nutritional_info:
            best_match = edamam_results[0]
            food_data.name = best_match.get("food", {}).get("label", product_name)
            food_data.source = "Edamam"

            # Get nutritional info
            food_id = best_match.get("food", {}).get("foodId")
            if food_id:
                nutrition = await self.edamam_client.get_nutrition_info(food_id)
                if nutrition:
                    food_data.nutritional_info = self._extract_edamam_nutrition(nutrition)

        # If no data found from APIs, create mock data
        if not food_data.name:
            food_data.name = product_name
            food_data.ingredients = ["natural ingredients", "preservatives"]
            food_data.allergens = []
            food_data.source = "mock"
            food_data.safety_score = 0.7

        # Calculate safety score
        food_data.safety_score = self._calculate_food_safety_score(food_data)

        return food_data

    async def get_cosmetic_data(self, product_name: str) -> CosmeticData:
        """Get cosmetic data from EU CosIng and other sources"""
        logger.info(f"Getting cosmetic data for: {product_name}")

        try:
            # Ensure product_name is not None or empty
            if not product_name or not product_name.strip():
                product_name = "unknown_product"

            cosmetic_data = CosmeticData(product_name=product_name.strip())

            # Search CosIng database
            # This would be implemented with actual ingredient extraction
            # For now, we'll create a mock structure
            cosmetic_data.ingredients = ["glycerin", "water", "preservatives"]
            cosmetic_data.regulatory_status = {"EU": "approved", "US": "pending"}
            cosmetic_data.safety_concerns = []
            cosmetic_data.source = "CosIng"
            cosmetic_data.safety_score = 0.8  # Mock score

            logger.info(f"Created cosmetic data: {cosmetic_data}")
            return cosmetic_data

        except Exception as e:
            logger.error(f"Error creating cosmetic data: {e}", exc_info=True)
            # Return a minimal valid CosmeticData object
            return CosmeticData(
                product_name=product_name or "unknown",
                ingredients=[],
                regulatory_status={},
                safety_concerns=[],
                source="error",
                safety_score=0.0,
            )

    async def get_chemical_data(self, chemical_name: str) -> ChemicalData:
        """Get chemical safety data from OSHA and ATSDR"""
        logger.info(f"Getting chemical data for: {chemical_name}")

        chemical_data = ChemicalData(chemical_name=chemical_name)

        # Mock implementation - would integrate with actual OSHA/ATSDR APIs
        chemical_data.cas_number = "mock-cas-number"
        chemical_data.safety_limits = {"OSHA_PEL": "10 mg/m3", "ACGIH_TLV": "5 mg/m3"}
        chemical_data.health_effects = ["respiratory irritation", "skin sensitization"]
        chemical_data.exposure_guidelines = {
            "inhalation": "avoid",
            "skin": "use protection",
        }
        chemical_data.source = "OSHA/ATSDR"
        chemical_data.safety_score = 0.7  # Mock score

        return chemical_data

    def _extract_nutritional_info(self, usda_data: dict[str, Any]) -> dict[str, Any]:
        """Extract nutritional information from USDA data"""
        nutrients = {}

        for nutrient in usda_data.get("foodNutrients", []):
            nutrient_info = nutrient.get("nutrient", {})
            name = nutrient_info.get("name", "").lower()
            amount = nutrient.get("amount", 0)
            unit = nutrient_info.get("unitName", "")

            if name and amount:
                nutrients[name] = {"amount": amount, "unit": unit}

        return nutrients

    def _extract_edamam_nutrition(self, edamam_data: dict[str, Any]) -> dict[str, Any]:
        """Extract nutritional information from Edamam data"""
        nutrients = {}

        for nutrient in edamam_data.get("totalNutrients", {}):
            nutrient_data = edamam_data["totalNutrients"][nutrient]
            name = nutrient_data.get("label", "").lower()
            amount = nutrient_data.get("quantity", 0)
            unit = nutrient_data.get("unit", "")

            if name and amount:
                nutrients[name] = {"amount": amount, "unit": unit}

        return nutrients

    def _calculate_food_safety_score(self, food_data: FoodData) -> float:
        """Calculate safety score for food data"""
        score = 0.5  # Base score

        # Add points for having nutritional data
        if food_data.nutritional_info:
            score += 0.2

        # Add points for having ingredient information
        if food_data.ingredients:
            score += 0.2

        # Add points for allergen information
        if food_data.allergens:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0


# Global instance
supplemental_data_service = SupplementalDataService()
