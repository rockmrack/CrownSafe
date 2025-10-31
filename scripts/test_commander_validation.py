# scripts/test_commander_validation.py

import json
import time
import uuid

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🧪 Testing different message content to bypass Commander validation...\n")

# Try different drug names and parameters that might pass validation
test_cases = [
    {
        "drug_name": "Canagliflozin",
        "disease": "Heart Failure",
    },  # From the working example
    {"drug_name": "Empagliflozin", "disease": "Type 2 Diabetes"},  # SGLT2 inhibitor
    {"drug_name": "Ozempic", "disease": "Diabetes"},  # Popular drug
]

for i, test in enumerate(test_cases):
    workflow_id = str(uuid.uuid4())
    print(f"Test {i + 1}: {test['drug_name']} for {test['disease']}")

    msg = {
        "mcp_header": {
            "message_type": "PROCESS_USER_REQUEST",
            "sender_id": f"api_gateway_client_{workflow_id}",
            "target_id": "commander_agent_01",
            "correlation_id": workflow_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "payload": {
            "user_request": {
                "user_goal": f"Determine prior authorization for {test['drug_name']}",
                "task_type": "prior_authorization",
                "parameters": {
                    "patient_id": "test-patient-001",
                    "drug_name": test["drug_name"],
                    "insurer_id": "BlueCross",
                    "diagnosis": test["disease"],
                    "patient_age": 45,
                },
            }
        },
    }

    # Send to Commander
    r.lpush("mcp:queue:commander_agent_01", json.dumps(msg))

    # Wait
    time.sleep(3)

    # Check
    if r.exists(f"rossnet:workflow:{workflow_id}"):
        print("   ✅ SUCCESS! Workflow created\n")
        break
    else:
        # Check if still in queue
        queue_len = r.llen("mcp:queue:commander_agent_01")
        print(f"   ❌ Failed - Queue has {queue_len} messages\n")
