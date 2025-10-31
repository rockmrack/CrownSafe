# scripts/trace_workflow_message_flow.py

import json
import time

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

workflow_id = "97da841b-d39b-4f85-9418-85dd007c4afb"  # From your test

print(f"🔍 Tracing workflow: {workflow_id}\n")

# 1. Check all queues for messages
print("📬 Checking message queues:")
for agent in ["commander_agent_01", "planner_agent_01", "router_agent_01"]:
    queue_key = f"mcp:queue:{agent}"
    queue_len = r.llen(queue_key)
    print(f"   {agent}: {queue_len} messages")

    # Check if workflow ID is in any queued messages
    for i in range(min(queue_len, 5)):
        msg = r.lindex(queue_key, i)
        if workflow_id in msg:
            print(f"   ✅ Found workflow in {agent} queue!")

# 2. Check for any Redis keys with this workflow ID
print("\n🔍 Searching for workflow ID in Redis:")
all_keys = r.keys("*")
found_keys = []

for key in all_keys:
    if workflow_id in key:
        found_keys.append(key)
        print(f"   ✅ Found in key: {key}")

if not found_keys:
    print("   ❌ Workflow ID not found in any Redis keys")

# 3. Check Commander's ongoing requests (if stored)
print("\n📊 Recent workflows created:")
workflow_keys = r.keys("rossnet:workflow:*")
print(f"   Total workflows: {len(workflow_keys)}")

# Show last 3 workflows
for key in workflow_keys[-3:]:
    try:
        data = json.loads(r.get(key))
        wf_id = key.split(":")[-1]
        print(f"\n   Workflow: {wf_id[:8]}...")
        print(f"     Status: {data.get('status')}")
        print(f"     Created by: {data.get('original_requester_id', 'Unknown')}")
        print(f"     workflow_id field: {data.get('workflow_id', 'MISSING')}")
    except (json.JSONDecodeError, TypeError):
        pass  # Could not parse workflow data

# 4. Monitor for new workflows
print("\n⏳ Monitoring for new workflows (10 seconds)...")
initial_count = len(workflow_keys)

for i in range(10):
    time.sleep(1)
    current_keys = r.keys("rossnet:workflow:*")
    if len(current_keys) > initial_count:
        new_keys = set(current_keys) - set(workflow_keys)
        for new_key in new_keys:
            print(f"   ✅ NEW workflow created: {new_key}")
            if workflow_id in new_key:
                print("      This is our workflow!")
