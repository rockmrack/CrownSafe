import asyncio
import logging
from core_infra.mcp_client_library.client import MCPClient
from .agent_logic import AlternativesAgentLogic

# ... (Standard logging and agent setup) ...


class AlternativesAgent:
    def __init__(self):
        # ... (Standard __init__) ...
        self.logic = AlternativesAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability(
            "get_alternatives", self.handle_get_alternatives
        )

    async def handle_get_alternatives(self, task_payload: dict) -> dict:
        product_name = task_payload.get("product_name")
        product_category = task_payload.get("product_category")
        if not all([product_name, product_category]):
            return {
                "status": "error",
                "message": "Payload must contain 'product_name' and 'product_category'.",
            }
        return self.logic.get_alternatives(product_name, product_category)

    # ... (Standard run method) ...


# ... (Standard main execution block) ...
