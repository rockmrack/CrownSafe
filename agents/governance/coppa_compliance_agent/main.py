import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import COPPA_ComplianceAgentLogic

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_ID = "coppa_compliance_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"

class COPPA_ComplianceAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = COPPA_ComplianceAgentLogic(agent_id=self.agent_id)
        
        self.mcp_client.register_capability("check_coppa_consent", self.handle_check_consent)
        self.mcp_client.register_capability("plan_data_deletion", self.handle_plan_deletion)

    async def handle_check_consent(self, task_payload: dict) -> dict:
        user_profile = task_payload.get("user_profile")
        if not user_profile:
            return {"status": "error", "message": "Missing 'user_profile' in payload."}
        return self.logic.check_age_and_get_consent_status(user_profile)

    async def handle_plan_deletion(self, task_payload: dict) -> dict:
        user_id = task_payload.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Missing 'user_id' in payload."}
        return self.logic.generate_data_deletion_plan(user_id)

    async def run(self):
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()

async def main():
    agent = COPPA_ComplianceAgent()
    await agent.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("COPPA_ComplianceAgent stopped by user.")