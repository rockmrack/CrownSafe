# scripts/test_skip_commander.py

import json
import time
import uuid

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

workflow_id = str(uuid.uuid4())
print(f"🚀 Testing by sending directly to Planner with workflow ID: {workflow_id}")

# Create a plan message for Router (via Planner)
plan_msg = {
    "mcp_header": {
        "message_type": "PLAN_GENERATED",
        "sender_id": "planner_agent_01",
        "target_id": "router_agent_01",
        "correlation_id": workflow_id,
        "timestamp": "2025-01-01T00:00:00Z",
    },
    "payload": {
        "plan": {
            "workflow_goal": "Test direct to router",
            "steps": [
                {
                    "step_id": "test_step_1",
                    "agent_capability_required": "TEST_CAPABILITY",
                    "task_description": "Test task",
                    "inputs": {},
                    "dependencies": [],
                },
            ],
        },
    },
}

# Send directly to Router
r.lpush("mcp:queue:router_agent_01", json.dumps(plan_msg))
print("📤 Sent plan directly to Router")

# Wait and check
time.sleep(3)

# Check if workflow was created
workflow_key = f"rossnet:workflow:{workflow_id}"
if r.exists(workflow_key):
    print("✅ SUCCESS! Router created workflow!")
    data = json.loads(r.get(workflow_key))
    print(f"   Status: {data.get('status')}")
    print(f"   workflow_id field: {data.get('workflow_id')}")

    # Now check via API
    import requests

    resp = requests.get(f"http://localhost:8000/api/v1/status/{workflow_id}")
    if resp.status_code == 200:
        print("✅ API can retrieve it!")
    else:
        print(f"❌ API returns: {resp.status_code}")
else:
    print("❌ Workflow not created")
