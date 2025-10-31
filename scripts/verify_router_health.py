# scripts/verify_router_health.py

import json
import time
import uuid
from datetime import UTC, datetime

import redis


def check_router_health() -> bool:
    """Comprehensive Router Agent health check."""
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    print("🏥 Router Agent Health Check\n")

    # 1. Check if queue is being processed
    print("1️⃣ Checking queue processing...")

    # Add a test message
    test_id = str(uuid.uuid4())[:8]
    test_msg = {
        "mcp_header": {
            "message_type": "PING",
            "sender_id": "health_check",
            "target_id": "router_agent_01",
            "correlation_id": f"health_{test_id}",
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "payload": {},
    }

    queue_key = "mcp:queue:router_agent_01"
    initial_len = r.llen(queue_key)
    r.lpush(queue_key, json.dumps(test_msg))

    print(f"   Added test message to queue (length: {initial_len} -> {initial_len + 1})")

    # Wait and check if processed
    time.sleep(2)
    final_len = r.llen(queue_key)

    if final_len < initial_len + 1:
        print("   ✅ Router is processing messages!")
    else:
        print("   ❌ Router is NOT processing messages")
        print("   Queue length unchanged - Router may be stuck or not running")
        return False

    # 2. Check recent workflows
    print("\n2️⃣ Checking recent workflows...")
    workflow_keys = r.keys("rossnet:workflow:*")

    if workflow_keys:
        # Get most recent
        recent_workflows = []
        for key in workflow_keys[-5:]:  # Last 5
            try:
                data = json.loads(r.get(key))
                wf_id = key.split(":")[-1]
                recent_workflows.append(
                    {
                        "id": wf_id,
                        "status": data.get("status", "UNKNOWN"),
                        "has_workflow_id": "workflow_id" in data,
                        "workflow_id_value": data.get("workflow_id", "MISSING"),
                    },
                )
            except (json.JSONDecodeError, TypeError):
                pass  # Could not parse workflow data

        for wf in recent_workflows:
            status_icon = "✅" if wf["has_workflow_id"] and wf["workflow_id_value"] != "N/A" else "❌"
            print(
                f"   {status_icon} {wf['id'][:8]}... - Status: {wf['status']}, workflow_id: {wf['workflow_id_value']}",
            )

    # 3. Test workflow creation
    print("\n3️⃣ Testing workflow creation...")

    test_workflow_id = str(uuid.uuid4())
    test_plan = {
        "mcp_header": {
            "message_type": "TASK_ASSIGN",
            "sender_id": "health_check",
            "target_id": "router_agent_01",
            "correlation_id": test_workflow_id,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        "payload": {
            "plan": {
                "workflow_goal": "Health check test",
                "steps": [
                    {
                        "step_id": "health_test_1",
                        "agent_capability_required": "HEALTH_TEST",
                        "task_description": "Test task",
                        "inputs": {},
                        "dependencies": [],
                    },
                ],
            },
        },
    }

    r.lpush(queue_key, json.dumps(test_plan))
    print(f"   Sent test workflow: {test_workflow_id[:8]}...")

    # Wait for processing
    for i in range(5):
        time.sleep(1)
        if r.exists(f"rossnet:workflow:{test_workflow_id}"):
            print("   ✅ Router successfully created workflow!")

            # Check if workflow_id field is set
            data = json.loads(r.get(f"rossnet:workflow:{test_workflow_id}"))
            if data.get("workflow_id") == test_workflow_id:
                print("   ✅ workflow_id field is correctly set!")
            else:
                print(f"   ❌ workflow_id field is: {data.get('workflow_id', 'MISSING')}")

            return True

    print("   ❌ Router did not create workflow")
    return False


if __name__ == "__main__":
    if check_router_health():
        print("\n✅ Router Agent is healthy!")
    else:
        print("\n❌ Router Agent has issues!")
        print("\n🔧 To fix:")
        print("1. Make sure agent_logic.py has the workflow_id fix")
        print("2. Restart Router Agent: python -m agents.routing.router_agent.main")
        print("3. Check Router Agent console for errors")
