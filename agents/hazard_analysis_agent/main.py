# agents/hazard_analysis_agent/main.py
# Version: 1.0-BABYSHIELD
# Description: Main entry point for running the HazardAnalysisAgent as a service.

import logging
import time

from .agent_logic import HazardAnalysisLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AGENT_ID = "hazard_analysis_agent_01"


class HazardAnalysisAgent:
    """
    A service-oriented agent that waits for hazard analysis tasks.
    Like the ProductIdentifierAgent, its logic is called directly by the Router
    in our current architecture.
    """

    def __init__(self):
        self.agent_id = AGENT_ID
        self.logic = HazardAnalysisLogic(agent_id=self.agent_id)
        self.is_running = False
        logger.info(f"HazardAnalysisAgent initialized: {self.agent_id}")

    def start(self):
        """Starts the agent service."""
        self.is_running = True
        logger.info(f"{self.agent_id} started and is ready for tasks.")
        while self.is_running:
            time.sleep(10)

    def stop(self):
        """Stops the agent service."""
        self.is_running = False
        logger.info(f"Stopping {self.agent_id}...")


def main():
    """Main function to run the agent."""
    agent = HazardAnalysisAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
