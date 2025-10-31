

from .agent_logic import MetricsAgentLogic

# ... (Standard logging and agent setup) ...


class MetricsAgent:
    def __init__(self):
        # ... (Standard __init__) ...
        self.logic = MetricsAgentLogic(agent_id=self.agent_id)

        self.mcp_client.register_capability("track_event", self.handle_track_event)

    async def handle_track_event(self, task_payload: dict) -> dict:
        user_id = task_payload.get("user_id")
        event_name = task_payload.get("event_name")
        properties = task_payload.get("properties", {})
        if not all([user_id, event_name]):
            return {
                "status": "error",
                "message": "Payload must contain 'user_id' and 'event_name'.",
            }
        return self.logic.track_event(user_id, event_name, properties)

    # ... (Standard run method) ...


# ... (Standard main execution block) ...
