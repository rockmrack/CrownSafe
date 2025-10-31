from .agent_logic import MonetizationAgentLogic

# ... (Standard logging and agent setup) ...


class MonetizationAgent:
    def __init__(self):
        # ... (Standard __init__) ...
        self.logic = MonetizationAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability("create_subscription", self.handle_create_subscription)
        self.mcp_client.register_capability("get_subscription_status", self.handle_get_status)

    async def handle_create_subscription(self, task_payload: dict) -> dict:
        user_id = task_payload.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Missing 'user_id' in payload."}
        return self.logic.create_customer_and_subscription(user_id)

    async def handle_get_status(self, task_payload: dict) -> dict:
        user_id = task_payload.get("user_id")
        if not user_id:
            return {"status": "error", "message": "Missing 'user_id' in payload."}
        return self.logic.get_subscription_status(user_id)

    # ... (Standard run method) ...


# ... (Standard main execution block) ...
