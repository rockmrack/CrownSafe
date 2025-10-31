# scripts/test_router_with_correct_format.py

import json
import time
import uuid

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

workflow_id = str(uuid.uuid4())
print(f"🚀 Testing Router with correct message format: {workflow_id}")

# Create a TASK_ASSIGN message (what Commander sends to Router)
task_assign_msg = {
    "mcp_header": {
        "message_type": "TASK_ASSIGN",
        "sender_id": "commander_agent_01",
        "target_id": "router_agent_01",
        "correlation_id": workflow_id,
        "timestamp": "2025-01-01T00:00:00Z",
    },
    "payload": {
        "plan": {
            "workflow_goal": "Test router directly",
            "steps": [
                {
                    "step_id": "test_step_1",
                    "agent_capability_required": "data_extraction",
                    "task_description": "Test task",
                    "inputs": {},
                    "dependencies": [],
                }
            ],
        }
    },
}

# Clear router queue first
r.delete("mcp:queue:router_agent_01")

# Send to Router
r.lpush("mcp:queue:router_agent_01", json.dumps(task_assign_msg))
print("📤 Sent TASK_ASSIGN to Router")

# Wait
time.sleep(5)

# Check if workflow was created
workflow_key = f"rossnet:workflow:{workflow_id}"
if r.exists(workflow_key):
    print("✅ SUCCESS! Router created workflow!")
    data = json.loads(r.get(workflow_key))
    print(f"   Status: {data.get('status')}")
    print(f"   workflow_id field: {data.get('workflow_id')}")

    if data.get("workflow_id") == workflow_id:
        print("   ✅ workflow_id is correctly set!")
    else:
        print("   ❌ workflow_id is NOT set correctly")
else:
    print("❌ Workflow not created")

    # Check if message is still in queue
    queue_len = r.llen("mcp:queue:router_agent_01")
    print(f"   Router queue: {queue_len} messages")
