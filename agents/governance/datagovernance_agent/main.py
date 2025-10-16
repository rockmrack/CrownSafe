import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import DataGovernanceAgentLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AGENT_ID = "datagovernance_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class DataGovernanceAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = DataGovernanceAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability("check_data_minimization", self.handle_check_minimization)
        self.mcp_client.register_capability("determine_data_residency", self.handle_determine_residency)

    async def handle_check_minimization(self, task_payload: dict) -> dict:
        data_payload = task_payload.get("data_payload")
        required_fields = task_payload.get("required_fields")
        if not data_payload or not required_fields:
            return {
                "status": "error",
                "message": "Missing 'data_payload' or 'required_fields'.",
            }
        return self.logic.check_data_minimization(data_payload, required_fields)

    async def handle_determine_residency(self, task_payload: dict) -> dict:
        country_code = task_payload.get("country_code")
        if not country_code:
            return {"status": "error", "message": "Missing 'country_code'."}
        return self.logic.determine_data_residency(country_code)

    async def run(self):
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()


async def main():
    agent = DataGovernanceAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("DataGovernanceAgent stopped by user.")
