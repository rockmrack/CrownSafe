# agents/business/metrics_agent/agent_logic.py
# Version: 1.0-BABYSHIELD (Mixpanel Implementation)
# Description: Handles sending analytics events to Mixpanel.

import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from mixpanel import Mixpanel

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# --- Mixpanel Configuration ---
TOKEN = os.getenv("MIXPANEL_PROJECT_TOKEN")


class MetricsAgentLogic:
    """Handles the logic for tracking user events using Mixpanel."""

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        if not TOKEN:
            self.logger.critical(
                "MIXPANEL_PROJECT_TOKEN not found in environment variables. The agent cannot function.",
            )
            raise ValueError("MIXPANEL_PROJECT_TOKEN is not set.")

        # Initialize the Mixpanel client
        self.mixpanel_client = Mixpanel(TOKEN)
        self.logger.info(f"MetricsAgentLogic initialized for agent {self.agent_id}.")

    def track_event(self, user_id: str, event_name: str, properties: dict | None = None) -> bool:
        """Sends a single event to Mixpanel."""
        self.logger.info(f"Tracking event '{event_name}' for user: {user_id}")
        try:
            self.mixpanel_client.track(distinct_id=user_id, event_name=event_name, properties=properties or {})
            self.logger.info(f"Successfully sent event '{event_name}' to Mixpanel.")
            return True
        except Exception as e:
            self.logger.error(f"Mixpanel API call failed: {e}", exc_info=True)
            return False

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent."""
        self.logger.info(f"Received task with inputs: {inputs}")

        user_id = inputs.get("user_id")
        event_name = inputs.get("event_name")
        properties = inputs.get("properties")

        if not all([user_id, event_name]):
            return {"status": "FAILED", "error": "user_id and event_name are required."}

        # The mixpanel library is synchronous, so we run it in an executor
        # to avoid blocking the asyncio event loop.
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(None, self.track_event, user_id, event_name, properties)

        if success:
            return {
                "status": "COMPLETED",
                "result": {"message": "Event tracked successfully."},
            }
        else:
            return {"status": "FAILED", "error": "Failed to track Mixpanel event."}
