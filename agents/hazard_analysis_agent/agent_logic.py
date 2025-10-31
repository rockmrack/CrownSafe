# agents/hazard_analysis_agent/agent_logic.py
# Version: 1.5-BABYSHIELD (Live OpenAI API Implementation, Test-Compatible)
# Description: Analyzes recall data using a live call to the OpenAI GPT-4o model.

import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Constants ---
API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = "gpt-4o"  # Updated to the latest model


class HazardAnalysisLogic:
    """Handles the logic for analyzing product hazards from recall data by calling an LLM."""

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        if not API_KEY:
            self.logger.critical("OPENAI_API_KEY not found in environment variables. The agent cannot function.")
            raise ValueError("OPENAI_API_KEY is not set.")
        self.logger.info(f"HazardAnalysisLogic initialized for agent {self.agent_id}.")

    def _create_llm_prompt(self, recall_data: list[dict[str, Any]], product_name: str) -> str:
        """Creates a system prompt for the LLM to summarize recall information."""
        recall_details = ""
        for i, recall in enumerate(recall_data):
            # prefer hazard, else reason, else description
            reason = (
                recall.get("hazard")
                or recall.get("hazard_description")
                or recall.get("reason")
                or recall.get("description")
                or "N/A"
            )
            date = recall.get("recall_date") or recall.get("date") or "N/A"
            # normalize date if ISO
            try:
                date = datetime.fromisoformat(date).date().isoformat()
            except Exception:
                pass
            recall_details += f"Recall {i + 1}: Reason: '{reason}', Date: '{date}'.\n"

        return f"""
You are a baby product safety expert named BabyShield. Your task is to analyze recall data for a specific product and provide a clear, concise, and direct summary for a concerned parent.  # noqa: E501

Product Name: {product_name}
Recall Data:
{recall_details}

Based on this data, determine a risk level from this specific list: ["None", "Low", "Medium", "High", "Critical"].

Your response MUST be a single, valid JSON object with exactly two keys: "summary" and
"risk_level". Do not include any other text, explanations, or markdown.

Example of a perfect response:
{{"summary": "This product has an active recall due to a potential contamination risk. It is
advised to stop using this product immediately.", "risk_level": "High"}}
"""

    async def _query_llm(self, prompt: str) -> dict[str, Any] | None:
        """Queries the OpenAI API for analysis using an async HTTPX client with no proxy support."""
        self.logger.info(f"Querying {LLM_MODEL} for hazard analysis…")
        try:
            # Disable environment-based proxies
            async with httpx.AsyncClient(trust_env=False) as http_client:
                client = AsyncOpenAI(api_key=API_KEY, http_client=http_client)
                response = await client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that only responds with valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )

            raw = response.choices[0].message.content
            self.logger.info("Successfully received analysis from LLM.")
            return json.loads(raw)

        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            return None

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent. It receives recall data from the Router
        and returns either a safe default or the LLM analysis.
        """
        self.logger.info(f"Received task with inputs: {inputs}")

        # support recall_data as dict or list
        raw = inputs.get("recall_data", inputs)
        if isinstance(raw, dict) and "recalls" in raw:
            recall_data = raw.get("recalls") or []
        elif isinstance(raw, list):
            recall_data = raw
        else:
            recall_data = []

        # Get product details - check for nested structure
        product_details = inputs.get("product_details", {}) or {}
        product_name = product_details.get("product_name", "the product")

        # Also check if product_name is directly in inputs (fallback)
        if product_name == "the product" and inputs.get("product_name"):
            product_name = inputs.get("product_name")

        # Get visual confidence score if present
        visual_confidence = inputs.get("visual_confidence")

        # No recalls => safe default
        if not recall_data:
            self.logger.info("No recall data provided. Returning safe default status.")
            return {
                "status": "COMPLETED",
                "result": {  # CHANGED FROM "data" to "result"
                    "summary": "No recalls found for this product.",
                    "risk_level": "None",  # CHANGED FROM None to "None" (string)
                },
            }

        try:
            prompt = self._create_llm_prompt(recall_data, product_name)
            analysis = await self._query_llm(prompt)

            if isinstance(analysis, dict) and "summary" in analysis and "risk_level" in analysis:
                # --- START OF NEW CONDITIONAL WARNING LOGIC ---
                if visual_confidence and 0.7 <= visual_confidence < 0.95:
                    warning_text = f"⚠️ Warning: This product was identified from a photo with {int(visual_confidence * 100)}% confidence. Please verify the model number on the product to ensure this information is accurate for your specific item. "  # noqa: E501
                    analysis["summary"] = warning_text + analysis.get("summary", "")
                    self.logger.info(
                        f"Prepended medium-confidence warning to the final summary (confidence: {visual_confidence})",
                    )
                # --- END OF NEW CONDITIONAL WARNING LOGIC ---
                return {
                    "status": "COMPLETED",
                    "result": analysis,  # CHANGED FROM "data" to "result"
                }
            self.logger.error("LLM response was invalid or malformed: %s", analysis)
            return {
                "status": "FAILED",
                "error": "LLM response was invalid or malformed.",
            }

        except Exception as e:
            self.logger.error(
                f"An unexpected error occurred during hazard analysis: {e}",
                exc_info=True,
            )
            return {"status": "FAILED", "error": str(e)}
