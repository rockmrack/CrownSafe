# scripts/check_stuck_messages.py

import json

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Checking stuck messages in queues:\n")

agents = ["commander_agent_01", "planner_agent_01", "router_agent_01"]

for agent in agents:
    queue_key = f"mcp:queue:{agent}"
    queue_len = r.llen(queue_key)

    print(f"📬 {agent}: {queue_len} messages")

    if queue_len > 0:
        # Show first message
        first_msg = r.lindex(queue_key, 0)
        try:
            msg_data = json.loads(first_msg)
            msg_type = msg_data.get("mcp_header", {}).get("message_type")
            sender = msg_data.get("mcp_header", {}).get("sender_id", "Unknown")
            corr_id = msg_data.get("mcp_header", {}).get("correlation_id", "")

            print("   First message:")
            print(f"     Type: {msg_type}")
            print(f"     From: {sender}")
            print(f"     Correlation ID: {corr_id[:20]}..." if len(corr_id) > 20 else f"     Correlation ID: {corr_id}")

            # Check payload for API messages
            if "api_gateway" in sender:
                payload = msg_data.get("payload", {})
                print(f"     Payload: {payload}")

        except Exception as e:
            print(f"   Error parsing message: {e}")
    print()
