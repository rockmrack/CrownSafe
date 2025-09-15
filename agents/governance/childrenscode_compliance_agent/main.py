import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import ChildrensCode_ComplianceAgentLogic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_ID = "childrenscode_compliance_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class ChildrensCode_ComplianceAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = ChildrensCode_ComplianceAgentLogic(agent_id=self.agent_id)
        
        self.mcp_client.register_capability("verify_uk_defaults", self.handle_verify_defaults)

    async def handle_verify_defaults(self, task_payload: dict) -> dict:
        user_profile = task_payload.get("user_profile")
        if not user_profile:
            return {"status": "error", "message": "Missing 'user_profile' in payload."}
        return self.logic.verify_default_settings(user_profile)

    async def run(self):
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()

async def main():
    agent = ChildrensCode_ComplianceAgent()
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ChildrensCode_ComplianceAgent stopped by user.")