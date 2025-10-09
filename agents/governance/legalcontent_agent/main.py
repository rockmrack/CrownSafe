import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import LegalContentAgentLogic

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

AGENT_ID = "legalcontent_agent_01"
MCP_SERVER_URL = "ws://127.0.0.1:8001"


class LegalContentAgent:
    def __init__(self):
        self.agent_id = AGENT_ID
        self.mcp_client = MCPClient(agent_id=self.agent_id, server_url=MCP_SERVER_URL)
        self.logic = LegalContentAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability("get_legal_document", self.handle_get_document)

    async def handle_get_document(self, task_payload: dict) -> dict:
        doc_type = task_payload.get("doc_type")
        language = task_payload.get("language")
        country = task_payload.get("country")
        if not all([doc_type, language, country]):
            return {
                "status": "error",
                "message": "Payload must contain 'doc_type', 'language', and 'country'.",
            }
        return self.logic.get_legal_document(doc_type, language, country)

    async def run(self):
        logger.info(f"Starting {self.agent_id}...")
        await self.mcp_client.connect()


async def main():
    agent = LegalContentAgent()
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("LegalContentAgent stopped by user.")
