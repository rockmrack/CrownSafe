# scripts/check_commander_workflow.py

import json

import redis

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Checking all workflow keys in Redis:\n")

# List all keys
all_keys = r.keys("*")
workflow_keys = [k for k in all_keys if "workflow" in k.lower()]

print(f"Found {len(workflow_keys)} workflow-related keys:\n")

for key in workflow_keys[:20]:  # Show first 20
    print(f"Key: {key}")
    try:
        value = r.get(key)
        if value:
            data = json.loads(value)
            print(f"  Status: {data.get('status', 'N/A')}")
            print(f"  Workflow ID: {data.get('workflow_id', 'N/A')}")
    except:
        print("  (Could not parse)")
    print()

# Check specific patterns
print("\n🔍 Checking specific patterns:")
patterns = ["rossnet:workflow:*", "commander:*", "*commander*workflow*"]

for pattern in patterns:
    keys = r.keys(pattern)
    print(f"\nPattern '{pattern}': {len(keys)} keys")
    for key in keys[:5]:
        print(f"  - {key}")
