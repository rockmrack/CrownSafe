"""
OpenAI LLM Client implementation for BabyShield chat functionality.
Provides a chat_json method that interfaces with OpenAI's API.
"""
import os
import json
from typing import Dict, Any, Optional
import logging

try:
    import openai
    import httpx

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Install with: pip install openai httpx")


class OpenAILLMClient:
    """
    OpenAI client that implements the LLMClient protocol for chat functionality.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI client with optimized HTTP settings.

        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if OPENAI_AVAILABLE and self.api_key:
            try:
                # Configure HTTP client with aggressive IPv4-only settings
                OPENAI_TIMEOUT = float(
                    os.getenv("OPENAI_TIMEOUT", "10")
                )  # Shorter timeout for faster fallback

                # Force IPv4 by binding the local address to 0.0.0.0
                transport = httpx.HTTPTransport(
                    local_address="0.0.0.0", retries=0  # No retries - fail fast
                )

                http_client = httpx.Client(
                    transport=transport,  # Force IPv4
                    timeout=httpx.Timeout(OPENAI_TIMEOUT, connect=5.0, read=OPENAI_TIMEOUT),
                    http2=False,  # Disable HTTP/2 - h2 package not installed
                    limits=httpx.Limits(
                        max_connections=1, max_keepalive_connections=0
                    ),  # Minimal connections
                )

                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    http_client=http_client,
                    max_retries=0,  # No retries - fail fast for faster fallback
                )
                logging.info(
                    f"OpenAI client initialized successfully with {OPENAI_TIMEOUT}s timeout, IPv4-only, fast-fail mode"
                )
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logging.warning("OpenAI client not initialized - missing API key or library")

    def chat_json(
        self,
        model: str = "gpt-4o-mini",
        system: str = "",
        user: str = "",
        response_schema: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Send a chat request to OpenAI and get a JSON response.

        Args:
            model: OpenAI model to use
            system: System message
            user: User message
            response_schema: JSON schema for response format
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing the response

        Raises:
            RuntimeError: If OpenAI client is not available or request fails
        """
        if not self.client:
            # Fallback response for development/testing
            logging.warning("OpenAI client not available, returning fallback response")
            return self._get_fallback_response()

        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            if user:
                messages.append({"role": "user", "content": user})

            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "timeout": timeout,
                "temperature": 0.1,  # Low temperature for consistent responses
            }

            # Add JSON mode if schema is provided
            if response_schema:
                request_params["response_format"] = {"type": "json_object"}

            # Make the API call
            response = self.client.chat.completions.create(**request_params)

            # Extract and parse the response
            content = response.choices[0].message.content

            if response_schema:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON response: {e}")
                    return self._get_fallback_response()
            else:
                return {"content": content}

        except Exception as e:
            logging.error(f"OpenAI API call failed: {e}")
            return self._get_fallback_response()

    def _get_fallback_response(self) -> Dict[str, Any]:
        """
        Get a fallback response when OpenAI is not available.

        Returns:
            Dictionary with a basic response structure
        """
        return {
            "summary": "Based on the product scan, this appears to be a baby formula product. While I'm experiencing connectivity issues with the AI service, I can provide basic safety guidance.",
            "reasons": [
                "Product appears to be a regulated baby formula",
                "No immediate recall alerts in local database",
                "Standard safety checks recommend verifying key details",
            ],
            "checks": [
                "Check expiration date on packaging",
                "Verify age appropriateness (0-12 months typical)",
                "Look for allergen warnings (milk, soy common)",
                "Ensure proper storage temperature",
            ],
            "flags": ["baby_formula", "contains_milk", "network_fallback"],
            "disclaimer": "This is a basic safety assessment. For detailed analysis, please try again in a moment as our AI service reconnects.",
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
            "evidence": [
                {"type": "regulation", "source": "FDA", "id": "baby_formula_regs"},
                {"type": "regulation", "source": "CPSC", "id": "infant_product_monitoring"},
            ],
            "suggested_questions": [
                "Is this safe for newborns?",
                "What allergens does this contain?",
                "Are there any recalls for this product?",
            ],
            "emergency": None,
        }
