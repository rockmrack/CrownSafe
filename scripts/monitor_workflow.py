# scripts/monitor_workflow.py

import asyncio
import redis.asyncio as aioredis
import json
import time
from datetime import datetime


async def monitor_workflow(workflow_id: str):
    """Monitor a workflow in Redis"""
    print(f"\n🔍 Monitoring workflow: {workflow_id}\n")

    # Use the new Redis API
    redis = aioredis.Redis(host="localhost", port=6379, decode_responses=True)

    # Check multiple possible keys
    keys_to_check = [
        f"rossnet:workflow:{workflow_id}",
        f"workflow:{workflow_id}",
        f"commander:workflow:{workflow_id}",
        f"rossnet:commander:workflow:{workflow_id}",
        f"commander_agent_01:workflow:{workflow_id}",
    ]

    print("Checking Redis keys:")
    for key in keys_to_check:
        exists = await redis.exists(key)
        print(f"  {key}: {'EXISTS' if exists else 'NOT FOUND'}")

        if exists:
            value = await redis.get(key)
            try:
                data = json.loads(value)
                print(f"\n  Content: {json.dumps(data, indent=2)}")
            except:
                print(f"  Raw content: {value}")

    # List all keys matching workflow pattern
    print("\n\nAll workflow-related keys in Redis:")
    async for key in redis.scan_iter(match="*workflow*"):
        print(f"  - {key}")

    # Also check for the specific workflow ID anywhere
    print(f"\n\nAll keys containing workflow ID {workflow_id}:")
    async for key in redis.scan_iter(match=f"*{workflow_id}*"):
        print(f"  - {key}")

    await redis.close()


async def trace_workflow_creation():
    """Submit a workflow and trace its creation"""
    import requests

    # Submit a new workflow
    print("📤 Submitting new workflow...")
    response = requests.post(
        "http://localhost:8000/api/v1/prior-auth/predict",
        json={
            "patient_id": "trace-test-001",
            "drug_name": "TestDrug",
            "insurer_id": "TEST",
        },
    )

    if response.status_code == 202:
        workflow_id = response.json()["workflow_id"]
        print(f"✅ Workflow created: {workflow_id}")

        # Monitor it immediately
        for i in range(10):
            print(f"\n⏱️  Check {i+1}/10 (after {i*2} seconds)")
            await monitor_workflow(workflow_id)

            # Also check status endpoint
            status_response = requests.get(f"http://localhost:8000/api/v1/status/{workflow_id}")
            print(f"\nAPI Status endpoint: {status_response.status_code}")
            if status_response.status_code == 200:
                print(f"Status data: {json.dumps(status_response.json(), indent=2)}")
                break

            await asyncio.sleep(2)
    else:
        print(f"❌ Failed to create workflow: {response.status_code}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Monitor specific workflow
        asyncio.run(monitor_workflow(sys.argv[1]))
    else:
        # Create and trace new workflow
        asyncio.run(trace_workflow_creation())
