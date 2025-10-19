import logging
from typing import Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class COPPA_ComplianceAgentLogic:
    """
    The core logic for managing compliance with the US Children's Online Privacy Protection Act (COPPA).
    MVP VERSION: Implements rule-based checks for age verification and consent.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logger
        self.logger.info("COPPA_ComplianceAgentLogic initialized.")

    def check_age_and_get_consent_status(
        self, user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Checks a user's age and determines if parental consent is required and obtained.
        """
        self.logger.info(
            f"Performing COPPA check for user_id: {user_profile.get('user_id')}"
        )

        try:
            birth_date_str = user_profile.get("birth_date")
            if not birth_date_str:
                # If no birth date, we must assume they are a child for safety.
                return self._handle_consent_required("Birth date not provided.")

            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            age = (
                today.year
                - birth_date.year
                - ((today.month, today.day) < (birth_date.month, birth_date.day))
            )

            self.logger.info(f"Calculated age for user is {age}.")

            # The COPPA rule applies to children under 13.
            if age < 13:
                # Check if verifiable parental consent is on file.
                # For the MVP, we'll check for a simple flag in the user profile.
                if user_profile.get("parental_consent_verified") is True:
                    return {
                        "status": "success",
                        "coppa_applies": True,
                        "consent_required": True,
                        "consent_obtained": True,
                        "message": "User is under 13, and verifiable parental consent is on file.",
                    }
                else:
                    return self._handle_consent_required(
                        "User is under 13, but verifiable parental consent is missing."
                    )
            else:
                # User is 13 or older, COPPA does not apply.
                return {
                    "status": "success",
                    "coppa_applies": False,
                    "consent_required": False,
                    "consent_obtained": True,  # Consent is implicit by being over the age limit
                    "message": "User is 13 or older. COPPA does not apply.",
                }

        except Exception as e:
            self.logger.error(
                f"An error occurred during COPPA check: {e}", exc_info=True
            )
            return {"status": "error", "message": f"An unexpected error occurred: {e}"}

    def _handle_consent_required(self, reason: str) -> Dict[str, Any]:
        """Helper function to generate a standardized 'consent required' response."""
        self.logger.warning(f"COPPA consent required: {reason}")
        return {
            "status": "success",
            "coppa_applies": True,
            "consent_required": True,
            "consent_obtained": False,
            "message": reason,
        }

    def generate_data_deletion_plan(self, user_id: str) -> Dict[str, Any]:
        """
        Generates a plan for deleting a user's data upon parental request.
        For the MVP, this returns a list of instructions.
        """
        self.logger.info(f"Generating data deletion plan for user_id: {user_id}")

        # In a real system, this would query a database of all services
        # where the user's data is stored.
        plan = [
            f"DELETE user record from PostgreSQL 'users' table where user_id = '{user_id}'.",
            f"DELETE all entries from PostgreSQL 'audit_trail' table associated with user_id = '{user_id}'.",
            "SCRUB user's product scan history from ChromaDB.",
            "REMOVE user from any push notification subscription lists.",
            "CONFIRM deletion and send confirmation email to parent.",
        ]

        return {"status": "success", "deletion_plan": plan}
