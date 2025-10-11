# scripts/check_workflow_details.py

import redis
import json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Checking workflow details...\n")

# Get a few workflow keys
workflow_keys = r.keys("rossnet:workflow:*")[:5]

for key in workflow_keys:
    print(f"\nKey: {key}")
    value = r.get(key)
    if value:
        try:
            data = json.loads(value)
            print(f"  Status: {data.get('status')}")
            print(f"  Workflow ID in data: {data.get('workflow_id')}")
            print(
                f"  Controller Correlation ID: {data.get('controller_correlation_id')}"
            )
            print(f"  Original Requester: {data.get('original_requester_id')}")

            # Extract workflow ID from key
            workflow_id_from_key = key.split(":")[-1]
            print(f"  Workflow ID from key: {workflow_id_from_key}")

            if workflow_id_from_key != data.get("workflow_id"):
                print("  ⚠️  MISMATCH: Key ID doesn't match stored ID!")
        except:
            print("  Error parsing data")
