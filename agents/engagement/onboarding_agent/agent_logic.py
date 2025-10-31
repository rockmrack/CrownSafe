# agents/engagement/onboarding_agent/agent_logic.py
# Version 1.0 - Live Logic Implementation

import asyncio
import logging
from typing import Any

# Import the consolidated database setup
from core_infra.database import User, get_db_session

logger = logging.getLogger(__name__)


class OnboardingAgentLogic:
    """Handles setting initial user profile data after registration."""

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None) -> None:
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"OnboardingAgentLogic initialized for agent {self.agent_id}.")

    async def set_initial_profile(self, user_id: int, is_pregnant: bool) -> bool:
        """Updates a user's record in the database with their pregnancy status."""
        await asyncio.sleep(0.1)  # Simulate I/O delay
        self.logger.info(f"Setting initial profile for user_id: {user_id}. Is Pregnant: {is_pregnant}")
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    self.logger.error(f"User with id {user_id} not found in database.")
                    return False

                user.is_pregnant = is_pregnant
                db.commit()
                self.logger.info(f"Successfully updated profile for user_id: {user_id}.")
                return True
        except Exception as e:
            self.logger.error(f"Database update failed for user {user_id}: {e}", exc_info=True)
            return False

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Main entry point for the agent."""
        self.logger.info(f"Received onboarding task with inputs: {inputs}")
        user_id = inputs.get("user_id")
        is_pregnant = inputs.get("is_pregnant", False)

        if not user_id:
            return {"status": "FAILED", "error": "user_id is required for onboarding."}

        success = await self.set_initial_profile(user_id, is_pregnant)

        if success:
            return {
                "status": "COMPLETED",
                "result": {"message": "User profile updated successfully."},
            }
        else:
            return {
                "status": "FAILED",
                "error": "Failed to update user profile in the database.",
            }
