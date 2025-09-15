import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import PregnancyProductSafetyAgentLogic

# Configure standard logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_ID = "pregnancy_product_safety_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class PregnancyProductSafetyAgent:
    """
    The main agent class that connects pregnancy product safety logic to the MCP network.
    """
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = PregnancyProductSafetyAgentLogic(agent_id=self.agent_id)
        
        # Register the agent's capabilities with the MCP client
        self.mcp_client.register_capability(
            "check_pregnancy_safety",
            self.handle_check_safety
        )

    async def handle_check_safety(self, task_payload: dict) -> dict:
        """
        Handles incoming tasks for the 'check_pregnancy_safety' capability.
        Validates the payload and calls the product safety logic.
        """
        product_upc = task_payload.get("product_upc")
        trimester = task_payload.get("trimester", 1)  # Default to 1 if not provided

        if not product_upc:
            error_msg = "Payload must contain 'product_upc'."
            logger.error(f"Task failed validation: {error_msg}")
            return {"status": "error", "message": error_msg}

        # Call the core logic to perform the check
        return self.logic.check_product_safety(product_upc, trimester)

    async def run(self):
        """Connects to the MCP and runs the agent's main event loop."""
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()
        # The mcp_client.connect() method contains the main loop
        # that listens for tasks until the connection is closed.

async def main():
    """The main entry point to create and run the agent."""
    agent = PregnancyProductSafetyAgent()
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"{AGENT_ID} stopped by user.")
