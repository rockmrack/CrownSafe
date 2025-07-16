# scripts/test_commander_formats.py

import redis
import json
import uuid
import time

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("🧪 Testing different message formats for Commander...\n")

# Clear Commander queue
r.delete("mcp:queue:commander_agent_01")

formats_to_test = [
    # Format 1: What we've been sending
    {
        "name": "Current format",
        "payload": {
            "user_request": {
                "user_goal": "Determine prior authorization for Metformin",
                "task_type": "prior_authorization",
                "parameters": {
                    "patient_id": "test-patient-001",
                    "drug_name": "Metformin",
                    "insurer_id": "TEST-INS"
                }
            }
        }
    },
    # Format 2: Try without wrapper
    {
        "name": "Direct format",
        "payload": {
            "user_goal": "Determine prior authorization for Metformin",
            "task_type": "prior_authorization",
            "parameters": {
                "patient_id": "test-patient-001",
                "drug_name": "Metformin",
                "insurer_id": "TEST-INS"
            }
        }
    },
    # Format 3: Try as a list (based on "pool" error)
    {
        "name": "List format",
        "payload": {
            "user_request": [{
                "user_goal": "Determine prior authorization for Metformin",
                "task_type": "prior_authorization",
                "parameters": {
                    "patient_id": "test-patient-001",
                    "drug_name": "Metformin",
                    "insurer_id": "TEST-INS"
                }
            }]
        }
    },
    # Format 4: Try with user_request_pool
    {
        "name": "Pool format",
        "payload": {
            "user_request_pool": [{
                "user_goal": "Determine prior authorization for Metformin",
                "task_type": "prior_authorization",
                "parameters": {
                    "patient_id": "test-patient-001",
                    "drug_name": "Metformin",
                    "insurer_id": "TEST-INS"
                }
            }]
        }
    }
]

for i, test_format in enumerate(formats_to_test):
    workflow_id = str(uuid.uuid4())
    print(f"Test {i+1}: {test_format['name']}")
    
    msg = {
        "mcp_header": {
            "message_type": "PROCESS_USER_REQUEST",
            "sender_id": f"api_gateway_client_{workflow_id}",
            "target_id": "commander_agent_01",
            "correlation_id": workflow_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        },
        "payload": test_format["payload"]
    }
    
    # Send to Commander
    r.lpush("mcp:queue:commander_agent_01", json.dumps(msg))
    print(f"   Sent with workflow_id: {workflow_id[:8]}...")
    
    # Wait
    time.sleep(3)
    
    # Check if workflow was created
    if r.exists(f"rossnet:workflow:{workflow_id}"):
        print(f"   ✅ SUCCESS! This format works!\n")
        print(f"   Winning payload structure:")
        print(json.dumps(test_format["payload"], indent=4))
        break
    else:
        # Check queue
        queue_len = r.llen("mcp:queue:commander_agent_01")
        print(f"   ❌ Failed - Queue: {queue_len} messages\n")

print("\n💡 Check the Commander console to see which format it accepts!")