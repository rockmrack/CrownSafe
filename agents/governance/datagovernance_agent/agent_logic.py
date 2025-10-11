# agents/governance/datagovernance_agent/agent_logic.py
# Version 1.0 - Live Logic Implementation

import logging
from typing import Dict, Any, Optional
import asyncio

# Import the consolidated database setup
from core_infra.database import get_db_session, User

logger = logging.getLogger(__name__)


class DataGovernanceAgentLogic:
    """
    Handles data privacy tasks, such as user data deletion, to comply with regulations.
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        self.agent_id = agent_id
        self.logger = logger_instance or logger
        self.logger.info(f"DataGovernanceAgentLogic initialized for agent {self.agent_id}.")

    async def delete_user_data(self, user_id: int) -> bool:
        """
        Finds a user in the database and deletes their entire record.
        This is a destructive action and should be handled with care.
        """
        await asyncio.sleep(0.1)  # Simulate I/O delay
        self.logger.info(f"Processing data deletion request for user_id: {user_id}")
        try:
            with get_db_session() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    self.logger.warning(f"User with id {user_id} not found for deletion.")
                    # In this case, the goal is achieved (no data exists), so we return success.
                    return True

                db.delete(user)
                db.commit()
                self.logger.info(f"Successfully deleted all data for user_id: {user_id}.")
                return True
        except Exception as e:
            self.logger.error(f"Database deletion failed for user {user_id}: {e}", exc_info=True)
            return False

    async def process_task(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        """
        self.logger.info(f"Received data governance task with inputs: {inputs}")
        action = inputs.get("action")
        payload = inputs.get("payload", {})

        if action == "delete_user_data":
            user_id = payload.get("user_id")
            if not user_id:
                return {
                    "status": "FAILED",
                    "error": "user_id is required for data deletion.",
                }

            success = await self.delete_user_data(user_id)

            if success:
                return {
                    "status": "COMPLETED",
                    "result": {
                        "message": f"Data deletion process completed for user_id: {user_id}."
                    },
                }
            else:
                return {
                    "status": "FAILED",
                    "error": "Failed to process data deletion request.",
                }
        else:
            return {"status": "FAILED", "error": f"Unknown action: {action}"}
