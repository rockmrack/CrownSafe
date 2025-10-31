# scripts/test_commander_directly.py

import json
import time
import uuid

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Clear Commander queue first
r.delete("mcp:queue:commander_agent_01")
print("Cleared Commander queue")

# Create test message with EXACT format Commander expects
workflow_id = str(uuid.uuid4())
test_msg = {
    "mcp_header": {
        "message_type": "PROCESS_USER_REQUEST",
        "sender_id": f"api_gateway_client_{workflow_id}",
        "target_id": "commander_agent_01",
        "correlation_id": workflow_id,
        "timestamp": "2025-01-01T00:00:00Z",
    },
    "payload": {
        "user_request": {
            "user_goal": "Determine prior authorization for TestDrug",
            "task_type": "prior_authorization",
            "parameters": {
                "patient_id": "test-123",
                "drug_name": "TestDrug",
                "insurer_id": "TestIns",
            },
        },
    },
}

print(f"\nSending test to Commander with workflow ID: {workflow_id}")
r.lpush("mcp:queue:commander_agent_01", json.dumps(test_msg))

# Wait and check
time.sleep(5)

# Check if workflow was created
workflow_key = f"rossnet:workflow:{workflow_id}"
if r.exists(workflow_key):
    print("✅ SUCCESS! Workflow created!")
    data = json.loads(r.get(workflow_key))
    print(f"Status: {data.get('status')}")
    print(f"workflow_id field: {data.get('workflow_id')}")
else:
    print("❌ FAILED - Workflow not created")

    # Check Commander queue
    queue_len = r.llen("mcp:queue:commander_agent_01")
    print(f"Commander queue: {queue_len} messages")

    # Check Commander logs
    print("\nCHECK THE COMMANDER CONSOLE FOR ERRORS!")
