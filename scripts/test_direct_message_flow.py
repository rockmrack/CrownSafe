# scripts/test_direct_message_flow.py

import redis
import json
import uuid
import asyncio
import time
from datetime import datetime


async def test_router_directly():
    """Test sending a message directly to the Router"""
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    workflow_id = str(uuid.uuid4())
    print(f"🧪 Testing Router directly with workflow: {workflow_id}")

    # Create a test plan message
    test_plan = {
        "mcp_header": {
            "message_type": "TASK_ASSIGN",
            "sender_id": "test_commander",
            "target_id": "router_agent_01",
            "correlation_id": workflow_id,
            "timestamp": datetime.utcnow().isoformat(),
        },
        "payload": {
            "plan": {
                "workflow_id": workflow_id,
                "workflow_goal": "Test direct router message",
                "steps": [
                    {
                        "step_id": "test_step_1",
                        "agent_capability_required": "TEST_CAPABILITY",
                        "task_description": "Test task",
                        "inputs": {},
                        "dependencies": [],
                    }
                ],
            }
        },
    }

    # Send directly to router queue
    router_queue = "mcp:queue:router_agent_01"

    print(f"\n📤 Sending test plan to Router queue: {router_queue}")
    r.lpush(router_queue, json.dumps(test_plan))

    print("⏳ Waiting for Router to process...")

    # Monitor for workflow creation
    for i in range(10):
        time.sleep(1)
        workflow_key = f"rossnet:workflow:{workflow_id}"
        if r.exists(workflow_key):
            print("✅ Workflow created in Redis!")
            data = json.loads(r.get(workflow_key))
            print(f"   Status: {data.get('status')}")
            print(f"   workflow_id field: {data.get('workflow_id', 'MISSING')}")
            return True
        else:
            print(f"   Attempt {i + 1}: Not found yet...")

    print("❌ Workflow was not created by Router")
    return False


async def check_router_logs():
    """Check if router is processing messages"""
    print("\n📋 Recent Router activity:")
    print("Check the Router Agent console for these message types:")
    print("- TASK_ASSIGN received")
    print("- HANDLE_NEW_PLAN processing")
    print("- Workflow state saved")


def verify_router_is_running():
    """Check if Router Agent is actually running"""
    import subprocess

    try:
        # Check for router process
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        router_running = "router_agent" in result.stdout.lower()

        if router_running:
            print("✅ Router Agent process found")
        else:
            print("❌ Router Agent process NOT found")
            print("   Start it with: python -m agents.routing.router_agent.main")

        return router_running
    except:
        # Windows
        try:
            result = subprocess.run(["tasklist"], capture_output=True, text=True)
            router_running = "python" in result.stdout and "router" in result.stdout.lower()

            if router_running:
                print("✅ Router Agent likely running")
            else:
                print("⚠️  Cannot confirm Router Agent is running")
                print("   Check manually and start with: python -m agents.routing.router_agent.main")

            return True  # Can't be sure on Windows
        except:
            print("⚠️  Cannot check if Router is running")
            return True


async def main():
    print("=" * 60)
    print("🔧 Direct Router Testing")
    print("=" * 60)

    # First check if router is running
    if not verify_router_is_running():
        return

    # Test router directly
    await test_router_directly()

    # Check logs
    await check_router_logs()


if __name__ == "__main__":
    asyncio.run(main())
