# scripts/clear_and_test.py

import redis
import requests
import time
import json

r = redis.Redis(host='localhost', port=6379, decode_responses=True)

print("🧹 Clearing old messages...\n")

# Clear all queues
for agent in ["commander_agent_01", "planner_agent_01", "router_agent_01"]:
    queue_key = f"mcp:queue:{agent}"
    r.delete(queue_key)
    print(f"Cleared {agent} queue")

print("\n🚀 Sending fresh test...\n")

# Send new request
response = requests.post("http://localhost:8000/api/v1/prior-auth/predict", json={
    "patient_id": "fresh-test-123",
    "drug_name": "TestDrug",
    "insurer_id": "TestInsurer"
})

if response.status_code == 202:
    workflow_id = response.json()["workflow_id"]
    print(f"✅ Workflow submitted: {workflow_id}")
    
    # Wait a bit
    time.sleep(3)
    
    # Check if it was created
    workflow_key = f"rossnet:workflow:{workflow_id}"
    if r.exists(workflow_key):
        print(f"✅ Workflow created in Redis!")
    else:
        print(f"❌ Workflow NOT found in Redis")
        
        # Check Commander queue
        cmd_len = r.llen("mcp:queue:commander_agent_01")
        print(f"\nCommander queue: {cmd_len} messages")
        
        if cmd_len > 0:
            # Check first message
            msg = r.lindex("mcp:queue:commander_agent_01", 0)
            msg_data = json.loads(msg)
            print(f"First message type: {msg_data.get('mcp_header', {}).get('message_type')}")