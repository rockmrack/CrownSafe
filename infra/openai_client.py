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
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Install with: pip install openai")


class OpenAILLMClient:
    """
    OpenAI client that implements the LLMClient protocol for chat functionality.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key: OpenAI API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if OPENAI_AVAILABLE and self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logging.info("OpenAI client initialized successfully")
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
        timeout: float = 30.0
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
            "summary": "I'm here to help explain your scan results. The system is currently using a fallback response.",
            "reasons": ["System is in fallback mode"],
            "checks": ["Check the product label", "Verify expiration date"],
            "flags": [],
            "disclaimer": "This is a fallback response. Please check with the system administrator.",
            "jurisdiction": {"code": "US", "label": "US FDA/CPSC"},
            "evidence": [],
            "suggested_questions": ["Is this safe to use?", "Any safety concerns?"],
            "emergency": None
        }
