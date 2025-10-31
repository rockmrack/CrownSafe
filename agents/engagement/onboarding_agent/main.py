import asyncio
import logging

from core_infra.mcp_client_library.client import MCPClient

from .agent_logic import OnboardingAgentLogic

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AGENT_ID = "onboarding_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class OnboardingAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = OnboardingAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability("create_user_profile", self.handle_create_profile)
        self.mcp_client.register_capability("update_onboarding_info", self.handle_update_info)

    async def handle_create_profile(self, task_payload: dict) -> dict:
        email = task_payload.get("email")
        password = task_payload.get("password")
        country_code = task_payload.get("country_code")
        if not all([email, password, country_code]):
            return {
                "status": "error",
                "message": "Payload must contain 'email', 'password', and 'country_code'.",
            }
        return self.logic.create_user_profile(email, password, country_code)

    async def handle_update_info(self, task_payload: dict) -> dict:
        user_id = task_payload.get("user_id")
        parent_status = task_payload.get("parent_status")
        due_date = task_payload.get("due_date")  # Optional
        if not all([user_id, parent_status]):
            return {
                "status": "error",
                "message": "Payload must contain 'user_id' and 'parent_status'.",
            }
        return self.logic.update_onboarding_info(user_id, parent_status, due_date)

    async def run(self):
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()


async def main():
    agent = OnboardingAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("OnboardingAgent stopped by user.")
