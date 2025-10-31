# scripts/check_message_flow_detailed.py

import json

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Checking message flow...\n")

# 1. Check Commander queue
cmd_queue = "mcp:queue:commander_agent_01"
cmd_len = r.llen(cmd_queue)
print(f"1️⃣ Commander queue: {cmd_len} messages")

if cmd_len > 0:
    # Check the latest message
    msg = r.lindex(cmd_queue, 0)
    try:
        msg_data = json.loads(msg)
        print("\nLatest Commander message:")
        print(f"  Type: {msg_data.get('mcp_header', {}).get('message_type')}")
        print("  Payload structure:")
        payload = msg_data.get("payload", {})
        for key in payload.keys():
            print(f"    - {key}")
            if key == "user_request" and isinstance(payload[key], dict):
                print("      Contents:")
                for subkey in payload[key].keys():
                    print(f"        - {subkey}")
    except:
        print("  Could not parse message")

# 2. Check other queues
for agent in ["planner_agent_01", "router_agent_01"]:
    queue_key = f"mcp:queue:{agent}"
    queue_len = r.llen(queue_key)
    print(f"\n{agent}: {queue_len} messages")

# 3. Look for ANY workflow created recently
print("\n📊 Recent workflows:")
all_workflows = r.keys("rossnet:workflow:*")
if all_workflows:
    # Get the most recent 3
    for key in all_workflows[-3:]:
        try:
            data = json.loads(r.get(key))
            wf_id = key.split(":")[-1]
            print(f"\n  Workflow: {wf_id[:8]}...")
            print(f"    Status: {data.get('status')}")
            print(f"    Created by: {data.get('original_requester_id', 'Unknown')}")
            print(f"    workflow_id field: {data.get('workflow_id', 'MISSING')}")
        except:
            pass
