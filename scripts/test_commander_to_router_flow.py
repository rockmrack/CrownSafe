# scripts/test_commander_to_router_flow.py

import asyncio
import json
import redis
import uuid
from datetime import datetime


async def test_flow():
    """Test the complete flow from API to Router"""
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    # Create a unique workflow ID
    workflow_id = str(uuid.uuid4())
    print(f"🧪 Testing flow with workflow ID: {workflow_id}")

    # 1. Simulate what API does - send to Commander
    commander_msg = {
        "mcp_header": {
            "message_type": "PROCESS_USER_REQUEST",
            "sender_id": "test_api_gateway",
            "target_id": "commander_agent_01",
            "correlation_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
        "payload": {
            "user_goal": "Test workflow flow",
            "task_type": "prior_authorization",
            "parameters": {
                "patient_id": "test-123",
                "drug_name": "TestDrug",
                "insurer_id": "TestInsurer",
            },
        },
    }

    print("\n1️⃣ Sending to Commander queue...")
    r.lpush("mcp:queue:commander_agent_01", json.dumps(commander_msg))

    # 2. Monitor for workflow creation
    print("\n2️⃣ Monitoring for workflow creation...")

    for i in range(20):  # Check for 20 seconds
        await asyncio.sleep(1)

        # Check if workflow exists
        workflow_key = f"rossnet:workflow:{workflow_id}"
        if r.exists(workflow_key):
            print(f"\n✅ Workflow created at: {workflow_key}")
            data = json.loads(r.get(workflow_key))
            print(f"   Status: {data.get('status')}")
            print(f"   workflow_id field: {data.get('workflow_id')}")
            return True

        # Also check for any workflow with this correlation_id
        all_workflows = r.keys("rossnet:workflow:*")
        for key in all_workflows:
            try:
                data = json.loads(r.get(key))
                if data.get("controller_correlation_id") == workflow_id:
                    print(f"\n⚠️  Found workflow at DIFFERENT key: {key}")
                    print("   This means Commander/Planner changed the workflow ID!")
                    print(f"   Original: {workflow_id}")
                    print(f"   Actual: {key.split(':')[-1]}")
                    return False
            except:
                pass

        print(f"   Attempt {i+1}: Not found yet...")

    print("\n❌ Workflow was never created!")

    # Check if messages are stuck
    print("\n📬 Checking queues...")
    for agent in ["commander_agent_01", "planner_agent_01", "router_agent_01"]:
        queue_len = r.llen(f"mcp:queue:{agent}")
        print(f"   {agent}: {queue_len} messages")


asyncio.run(test_flow())
