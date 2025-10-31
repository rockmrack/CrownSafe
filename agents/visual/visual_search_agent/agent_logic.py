# agents/visual/visual_search_agent/agent_logic.py

import json
import logging
import os
from typing import Any
from urllib.parse import urlparse

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


def _is_azure_blob_url(url: str) -> bool:
    """Check if URL is an Azure Blob Storage URL"""
    u = urlparse(url)
    return u.scheme == "blob" or ("blob.core.windows.net" in (u.netloc or ""))


async def _fetch_image_bytes(image_url: str) -> tuple[bytes, str]:
    """Validate and download image. Returns (bytes, content_type).
    Raises ValueError on 4xx/5xx or non-image content.
    """
    import httpx

    headers = {"User-Agent": "babyshield-backend/1.0"}

    # For Azure Blob Storage URLs or any external CDN → use HTTP GET
    if _is_azure_blob_url(image_url) and image_url.startswith("blob://"):
        # blob://container/blobname → Azure SDK
        from core_infra.azure_storage import AzureBlobStorageClient

        u = urlparse(image_url)
        container = u.netloc
        blob_name = u.path.lstrip("/")
        storage_client = AzureBlobStorageClient(container_name=container)
        blob_data = storage_client.download_blob(blob_name)
        ctype = "image/jpeg"  # Default, could be enhanced to get from blob properties
        return blob_data, ctype

    # HTTP(S) path
    async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
        r = await client.get(image_url)
        # Fail fast on broken URL
        if r.status_code >= 400:
            raise ValueError(f"http_{r.status_code}")
        ctype = r.headers.get("content-type", "")
        if not ctype.startswith("image/"):
            raise ValueError(f"non_image_content:{ctype}")
        # Basic size guard (optional): reject huge files > 10MB
        if (cl := r.headers.get("content-length")) and cl.isdigit() and int(cl) > 10_000_000:
            raise ValueError("image_too_large")
        return r.content, ctype


class VisualSearchAgentLogic:
    """Uses a multi-modal LLM to identify a product from an image.
    Phase 3: Provides definitive identification with confidence scoring.
    """

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger

        # Check if OpenAI API key is available
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("sk-mock"):
            self.logger.warning("OpenAI API key not configured - visual identification will be unavailable")
            self.llm_client = None
        else:
            self.llm_client = AsyncOpenAI(api_key=api_key)

        self.logger.info("VisualSearchAgentLogic initialized.")

    async def suggest_products_from_image(self, image_url: str) -> dict[str, Any]:
        """Analyzes an image and returns a list of potential product matches.
        (Kept for backward compatibility with Phase 2 endpoints)
        """
        self.logger.info(f"Analyzing image for product suggestions: {image_url}")

        # Check if OpenAI client is available
        if not self.llm_client:
            return {
                "status": "FAILED",
                "error": "Visual identification unavailable - OpenAI API key not configured",
                "error_type": "api_key_missing",
            }

        try:
            # External URL → fetch & base64, do NOT call OpenAI if fetch fails
            try:
                image_bytes, content_type = await _fetch_image_bytes(image_url)
                import base64

                if "png" in content_type:
                    fmt = "png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    fmt = "jpeg"
                else:
                    fmt = "jpeg"
                b64 = base64.b64encode(image_bytes).decode("ascii")
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{fmt};base64,{b64}"},
                }
                self.logger.info(f"Fetched external image for suggestions ({len(image_bytes)} bytes, {content_type})")
            except Exception as fetch_err:
                # Map common fetch errors to clean failures; skip OpenAI entirely
                msg = str(fetch_err)
                self.logger.info(f"Image fetch failed: {msg}")
                if msg.startswith("http_404"):
                    self.logger.info("Returning image_url_not_found error")
                    return {
                        "status": "FAILED",
                        "error": "image_url_not_found",
                        "error_type": "image_fetch_failed",
                    }
                if msg.startswith("non_image_content"):
                    self.logger.info("Returning image_url_not_image error")
                    return {
                        "status": "FAILED",
                        "error": "image_url_not_image",
                        "error_type": "image_fetch_failed",
                    }
                if msg.startswith("image_too_large"):
                    self.logger.info("Returning image_too_large error")
                    return {
                        "status": "FAILED",
                        "error": "image_too_large",
                        "error_type": "image_fetch_failed",
                    }
                self.logger.info("Returning generic image_fetch_failed error")
                return {
                    "status": "FAILED",
                    "error": "image_fetch_failed",
                    "error_type": "image_fetch_failed",
                }

            self.logger.info("Making OpenAI API call for product suggestions")
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze the baby product in this image. Identify the product name, brand, and model number if visible. Provide your top 3 most likely matches as a JSON object with a 'suggestions' array, where each object has 'product_name', 'brand', 'model_number', and a 'confidence' score from 0.0 to 1.0. Return ONLY valid JSON without any markdown formatting or code fences.",  # noqa: E501
                            },
                            image_content,
                        ],
                    },
                ],
                max_tokens=500,
            )
            self.logger.info("OpenAI API call for suggestions completed successfully")
            suggestions_json = response.choices[0].message.content
            self.logger.info(f"OpenAI suggestions response: {suggestions_json[:200]}...")  # Log first 200 chars

            if not suggestions_json or suggestions_json.strip() == "":
                self.logger.warning("OpenAI returned empty suggestions response")
                return {
                    "status": "FAILED",
                    "error": "OpenAI returned empty suggestions response",
                }

            try:
                # Clean up markdown formatting that OpenAI sometimes adds
                cleaned_json = suggestions_json.strip()
                if cleaned_json.startswith("```json"):
                    # Remove markdown code block formatting
                    cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()
                elif cleaned_json.startswith("```"):
                    # Remove generic code block formatting
                    cleaned_json = cleaned_json.replace("```", "").strip()

                suggestions = json.loads(cleaned_json)
                return {"status": "COMPLETED", "result": {"suggestions": suggestions}}
            except json.JSONDecodeError as json_error:
                self.logger.exception(f"Failed to parse OpenAI suggestions JSON: {json_error}")
                self.logger.exception(f"Raw suggestions content: {suggestions_json}")

                return {
                    "status": "FAILED",
                    "error": f"OpenAI suggestions parsing failed: {json_error}",
                    "raw_response": suggestions_json[:500],
                }
        except Exception as e:
            self.logger.error(f"Error during visual analysis: {e}", exc_info=True)

            error_message = str(e)
            # map invalid_image_url to a clean client error
            if "invalid_image_url" in error_message:
                return {
                    "status": "FAILED",
                    "error": "openai_invalid_image_url",
                    "error_type": "image_fetch_failed",
                }

            # Check if this is an OpenAI API key issue
            if "401" in error_message and (
                "api key" in error_message.lower() or "unauthorized" in error_message.lower()
            ):
                self.logger.warning("OpenAI API key is invalid or missing - visual identification unavailable")
                return {
                    "status": "FAILED",
                    "error": "Visual identification unavailable - OpenAI API key not configured",
                    "error_type": "api_key_missing",
                }

            return {"status": "FAILED", "error": "Failed to analyze image."}

    async def identify_product_from_image(self, image_url: str) -> dict[str, Any]:
        """Analyzes an image and returns the single best product match with a confidence score.
        Used for Phase 3 full workflow integration.
        """
        self.logger.info(f"Analyzing image for definitive product identification: {image_url}")

        # Check if OpenAI client is available
        if not self.llm_client:
            return {
                "status": "FAILED",
                "error": "Visual identification unavailable - OpenAI API key not configured",
                "error_type": "api_key_missing",
            }

        try:
            # External URL → fetch & base64, do NOT call OpenAI if fetch fails
            try:
                image_bytes, content_type = await _fetch_image_bytes(image_url)
                import base64

                if "png" in content_type:
                    fmt = "png"
                elif "jpeg" in content_type or "jpg" in content_type:
                    fmt = "jpeg"
                else:
                    fmt = "jpeg"
                b64 = base64.b64encode(image_bytes).decode("ascii")
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{fmt};base64,{b64}"},
                }
                self.logger.info(f"Fetched external image ({len(image_bytes)} bytes, {content_type})")
            except Exception as fetch_err:
                # Map common fetch errors to clean failures; skip OpenAI entirely
                msg = str(fetch_err)
                self.logger.info(f"Image fetch failed: {msg}")
                if msg.startswith("http_404"):
                    self.logger.info("Returning image_url_not_found error")
                    return {
                        "status": "FAILED",
                        "error": "image_url_not_found",
                        "error_type": "image_fetch_failed",
                    }
                if msg.startswith("non_image_content"):
                    self.logger.info("Returning image_url_not_image error")
                    return {
                        "status": "FAILED",
                        "error": "image_url_not_image",
                        "error_type": "image_fetch_failed",
                    }
                if msg.startswith("image_too_large"):
                    self.logger.info("Returning image_too_large error")
                    return {
                        "status": "FAILED",
                        "error": "image_too_large",
                        "error_type": "image_fetch_failed",
                    }
                self.logger.info("Returning generic image_fetch_failed error")
                return {
                    "status": "FAILED",
                    "error": "image_fetch_failed",
                    "error_type": "image_fetch_failed",
                }

            self.logger.info("Making OpenAI API call for product identification")
            response = await self.llm_client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze the baby product in this image. Identify the product name, brand, and model number if visible. Provide your single best guess as a JSON object with the keys 'product_name', 'brand', 'model_number', and a 'confidence' score from 0.0 to 1.0 representing your certainty. Return ONLY valid JSON without any markdown formatting or code fences.",  # noqa: E501
                            },
                            image_content,
                        ],
                    },
                ],
                max_tokens=300,
            )
            self.logger.info("OpenAI API call completed successfully")
            result_json = response.choices[0].message.content
            self.logger.info(f"OpenAI response content: {result_json[:200]}...")  # Log first 200 chars

            if not result_json or result_json.strip() == "":
                self.logger.warning("OpenAI returned empty response")
                return {"status": "FAILED", "error": "OpenAI returned empty response"}

            try:
                # Clean up markdown formatting that OpenAI sometimes adds
                cleaned_json = result_json.strip()
                if cleaned_json.startswith("```json"):
                    # Remove markdown code block formatting
                    cleaned_json = cleaned_json.replace("```json", "").replace("```", "").strip()
                elif cleaned_json.startswith("```"):
                    # Remove generic code block formatting
                    cleaned_json = cleaned_json.replace("```", "").strip()

                best_guess = json.loads(cleaned_json)
                self.logger.info(f"Successfully parsed OpenAI response: {best_guess}")

                # Validate required fields
                if not isinstance(best_guess, dict):
                    self.logger.error("OpenAI response is not a dictionary")
                    return {
                        "status": "FAILED",
                        "error": "Invalid response format from OpenAI",
                    }

                # Ensure all required fields exist
                required_fields = [
                    "product_name",
                    "brand",
                    "model_number",
                    "confidence",
                ]
                for field in required_fields:
                    if field not in best_guess:
                        self.logger.warning(f"Missing field '{field}' in OpenAI response, setting to null")
                        best_guess[field] = None

                # Ensure confidence is a number
                if best_guess.get("confidence") is not None:
                    try:
                        best_guess["confidence"] = float(best_guess["confidence"])
                    except (ValueError, TypeError):
                        self.logger.warning("Invalid confidence value, setting to 0.0")
                        best_guess["confidence"] = 0.0
                else:
                    best_guess["confidence"] = 0.0

                return {"status": "COMPLETED", "result": best_guess}
            except json.JSONDecodeError as json_error:
                self.logger.exception(f"Failed to parse OpenAI JSON response: {json_error}")
                self.logger.exception(f"Raw response content: {result_json}")

                # Try to extract useful information even if JSON parsing fails
                return {
                    "status": "FAILED",
                    "error": f"OpenAI response parsing failed: {json_error}",
                    "raw_response": result_json[:500],  # Include first 500 chars for debugging
                }
        except Exception as e:
            self.logger.error(f"Error during visual identification: {e}", exc_info=True)

            error_message = str(e)
            # map invalid_image_url to a clean client error
            if "invalid_image_url" in error_message:
                return {
                    "status": "FAILED",
                    "error": "openai_invalid_image_url",
                    "error_type": "image_fetch_failed",
                }

            # Check if this is an OpenAI API key issue
            if "401" in error_message and (
                "api key" in error_message.lower() or "unauthorized" in error_message.lower()
            ):
                self.logger.warning("OpenAI API key is invalid or missing - visual identification unavailable")
                return {
                    "status": "FAILED",
                    "error": "Visual identification unavailable - OpenAI API key not configured",
                    "error_type": "api_key_missing",
                }

            return {
                "status": "FAILED",
                "error": "Failed to identify product from image.",
            }

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent."""
        image_url = inputs.get("image_url")
        if not image_url:
            return {"status": "FAILED", "error": "image_url is required."}

        # Check if this is a full workflow call (Phase 3) or suggestion call (Phase 2)
        if inputs.get("mode") == "identify":
            return await self.identify_product_from_image(image_url)
        else:
            return await self.suggest_products_from_image(image_url)
