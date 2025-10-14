# agents/product_identifier_agent/main.py
# Version: 1.0-BABYSHIELD
# Description: Main entry point for running the ProductIdentifierAgent as a service.

import logging
import time

from .agent_logic import ProductIdentifierLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AGENT_ID = "product_identifier_agent_01"


class ProductIdentifierAgent:
    """
    A service-oriented agent that waits for product identification tasks.
    In a real distributed system, this 'start' method would connect to a message
    queue (like RabbitMQ or Kafka) and listen for 'TASK_ASSIGN' messages.
    For our monolithic app, the logic is called directly by the Router.
    """

    def __init__(self):
        self.agent_id = AGENT_ID
        self.logic = ProductIdentifierLogic(agent_id=self.agent_id)
        self.is_running = False
        logger.info(f"ProductIdentifierAgent initialized: {self.agent_id}")

    def start(self):
        """Starts the agent service."""
        self.is_running = True
        logger.info(f"{self.agent_id} started and is ready for tasks.")
        # In a real system, a message consumer loop would start here.
        # For this project, we just keep the process alive.
        while self.is_running:
            time.sleep(10)

    def stop(self):
        """Stops the agent service."""
        self.is_running = False
        logger.info(f"Stopping {self.agent_id}...")


def main():
    """Main function to run the agent."""
    agent = ProductIdentifierAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
