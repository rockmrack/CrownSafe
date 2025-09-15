# agents/visual/visual_search_agent/agent_logic.py

import logging
import json
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
import os

logger = logging.getLogger(__name__)

class VisualSearchAgentLogic:
    """
    Uses a multi-modal LLM to identify a product from an image.
    Phase 3: Provides definitive identification with confidence scoring.
    """
    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.llm_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.logger.info("VisualSearchAgentLogic initialized.")

    async def suggest_products_from_image(self, image_url: str) -> Dict[str, Any]:
        """
        Analyzes an image and returns a list of potential product matches.
        (Kept for backward compatibility with Phase 2 endpoints)
        """
        self.logger.info(f"Analyzing image for product suggestions: {image_url}")
        try:
            response = await self.llm_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze the baby product in this image. Identify the product name, brand, and model number if visible. Provide your top 3 most likely matches as a JSON array of objects, where each object has 'product_name', 'brand', 'model_number', and a 'confidence' score from 0.0 to 1.0. Respond with ONLY the JSON array."},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=500,
            )
            suggestions_json = response.choices[0].message.content
            suggestions = json.loads(suggestions_json)
            return {"status": "COMPLETED", "result": {"suggestions": suggestions}}
        except Exception as e:
            self.logger.error(f"Error during visual analysis: {e}", exc_info=True)
            return {"status": "FAILED", "error": "Failed to analyze image."}

    async def identify_product_from_image(self, image_url: str) -> Dict[str, Any]:
        """
        Analyzes an image and returns the single best product match with a confidence score.
        Used for Phase 3 full workflow integration.
        """
        self.logger.info(f"Analyzing image for definitive product identification: {image_url}")
        try:
            response = await self.llm_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze the baby product in this image. Identify the product name, brand, and model number if visible. Provide your single best guess as a JSON object with the keys 'product_name', 'brand', 'model_number', and a 'confidence' score from 0.0 to 1.0 representing your certainty. Respond with ONLY the single, valid JSON object."},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=300,
            )
            result_json = response.choices[0].message.content
            best_guess = json.loads(result_json)
            return {"status": "COMPLETED", "result": best_guess}
        except Exception as e:
            self.logger.error(f"Error during visual identification: {e}", exc_info=True)
            return {"status": "FAILED", "error": "Failed to identify product from image."}

    async def process_task(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for the agent."""
        image_url = inputs.get("image_url")
        if not image_url:
            return {"status": "FAILED", "error": "image_url is required."}
        
        # Check if this is a full workflow call (Phase 3) or suggestion call (Phase 2)
        if inputs.get("mode") == "identify":
            return await self.identify_product_from_image(image_url)
        else:
            return await self.suggest_products_from_image(image_url)
