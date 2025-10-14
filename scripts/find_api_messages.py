# scripts/find_api_messages.py

import redis
import json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Looking for API workflow messages...\n")

# Check all messages in Commander queue
cmd_queue = "mcp:queue:commander_agent_01"
queue_len = r.llen(cmd_queue)

print(f"Commander queue has {queue_len} messages:\n")

for i in range(min(queue_len, 10)):  # Check up to 10 messages
    msg = r.lindex(cmd_queue, i)
    try:
        msg_data = json.loads(msg)
        msg_type = msg_data.get("mcp_header", {}).get("message_type")
        sender = msg_data.get("mcp_header", {}).get("sender_id", "")
        corr_id = msg_data.get("mcp_header", {}).get("correlation_id", "")

        print(f"Message {i + 1}:")
        print(f"  Type: {msg_type}")
        print(f"  From: {sender}")
        print(
            f"  Correlation ID: {corr_id[:8]}..."
            if corr_id
            else "  Correlation ID: None"
        )

        if "api_gateway" in sender:
            print("  ✅ This is from API Gateway!")
            payload = msg_data.get("payload", {})
            print(f"  Payload keys: {list(payload.keys())}")
            if "user_request" in payload:
                print("  ✅ Has user_request field!")
        print()

    except:
        print(f"Message {i + 1}: Could not parse\n")

# Also check for workflows with API correlation IDs
print("\n🔍 Checking if any workflows match recent API calls...")

# Get all workflows
all_workflows = r.keys("rossnet:workflow:*")
for key in all_workflows:
    try:
        data = json.loads(r.get(key))
        requester = data.get("original_requester_id", "")
        if "api_gateway" in requester:
            wf_id = key.split(":")[-1]
            print(f"\n✅ Found API-created workflow: {wf_id}")
            print(f"   Status: {data.get('status')}")
            print(f"   workflow_id field: {data.get('workflow_id', 'MISSING')}")
            print(
                f"   controller_correlation_id: {data.get('controller_correlation_id', 'None')}"
            )
    except:
        pass
