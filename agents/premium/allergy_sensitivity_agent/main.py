import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import AllergySensitivityAgentLogic

# Configure standard logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AGENT_ID = "allergy_sensitivity_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class AllergySensitivityAgent:
    """
    The main agent class that connects the agent's logic to the MCP network.
    """

    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = AllergySensitivityAgentLogic(agent_id=self.agent_id)

        # Register the agent's capabilities with the MCP client
        self.mcp_client.register_capability(
            "check_product_for_family_allergies", self.handle_check_allergies
        )

    async def handle_check_allergies(self, task_payload: dict) -> dict:
        """
        Handles incoming tasks for the 'check_product_for_family_allergies' capability.
        It validates the payload and calls the core logic.
        """
        user_id = task_payload.get("user_id")
        product_upc = task_payload.get("product_upc")

        if not all([user_id, product_upc]):
            error_msg = "Payload must contain both 'user_id' and 'product_upc'."
            logger.error(f"Task failed validation: {error_msg}")
            return {"status": "error", "message": error_msg}

        # Call the core logic to perform the check
        return self.logic.check_product_for_family(user_id, product_upc)

    async def run(self):
        """Connects to the MCP and runs the agent's main event loop."""
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()
        # The mcp_client.connect() method contains the main loop
        # that listens for tasks until the connection is closed.


async def main():
    """The main entry point to create and run the agent."""
    agent = AllergySensitivityAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"{AGENT_ID} stopped by user.")
