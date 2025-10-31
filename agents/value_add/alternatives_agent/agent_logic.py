# agents/value_add/alternatives_agent/agent_logic.py
# Version 1.0 - Live Logic Implementation

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# This is a mock database of "safe" products. In a real system, this could
# be a curated list in your database or an API call to a trusted partner.
SAFE_PRODUCTS_DB = {
    "Infant Formula": [
        {
            "product_name": "Similac Pro-Advance Infant Formula",
            "upc": "070074649547",
            "reason": "Top-rated for safety and nutrition.",
        },
        {
            "product_name": "Enfamil Enspire Infant Formula",
            "upc": "0300875118228",
            "reason": "Highly recommended by pediatricians.",
        },
    ],
    "Baby Toys": [
        {
            "product_name": "Fisher-Price Rock-a-Stack",
            "upc": "0887961820120",
            "reason": "Classic, non-toxic, and age-appropriate.",
        },
    ],
}


class AlternativesAgentLogic:
    """Suggests safer alternative products based on the category of a recalled item.
    """

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"AlternativesAgentLogic initialized for agent {self.agent_id}.")

    async def find_alternatives(self, category: str) -> list[dict[str, str]]:
        """Simulates searching for safe alternatives in a given category."""
        await asyncio.sleep(0.2)  # Simulate processing time

        # Find a matching category, ignoring case
        for key, value in SAFE_PRODUCTS_DB.items():
            if key.lower() in category.lower():
                return value

        return []  # Return an empty list if no matching category is found

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent.
        """
        self.logger.info(f"Received task to find alternatives with inputs: {inputs}")
        product_category = inputs.get("product_category")

        if not product_category:
            return {
                "status": "FAILED",
                "error": "product_category is required to find alternatives.",
            }

        try:
            alternatives = await self.find_alternatives(product_category)

            return {
                "status": "COMPLETED",
                "result": {
                    "alternatives_found": len(alternatives),
                    "alternatives": alternatives,
                },
            }
        except Exception as e:
            self.logger.error(f"An error occurred while finding alternatives: {e}", exc_info=True)
            return {"status": "FAILED", "error": str(e)}
