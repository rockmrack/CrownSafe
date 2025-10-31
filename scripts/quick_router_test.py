# scripts/quick_router_test.py

import json
import time

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Check queue is being processed
queue_key = "mcp:queue:router_agent_01"
initial_len = r.llen(queue_key)

print(f"Initial queue length: {initial_len}")

# Add a PING message
test_msg = {
    "mcp_header": {
        "message_type": "PING",
        "sender_id": "test",
        "target_id": "router_agent_01",
        "correlation_id": "test123",
        "timestamp": "2025-01-01T00:00:00Z",
    },
    "payload": {},
}

r.lpush(queue_key, json.dumps(test_msg))
print("Added test message")

time.sleep(2)

final_len = r.llen(queue_key)
print(f"Final queue length: {final_len}")

if final_len < initial_len + 1:
    print("✅ Router is processing messages!")
else:
    print("❌ Router is still stuck!")
