# scripts/check_specific_workflow.py

import json

import redis

workflow_id = "f7a1c54a-d011-437c-9559-3357eec16a75"  # From your test
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print(f"🔍 Looking for workflow: {workflow_id}\n")

# Check exact key
exact_key = f"rossnet:workflow:{workflow_id}"
if r.exists(exact_key):
    print(f"✅ Found at expected key: {exact_key}")
    data = json.loads(r.get(exact_key))
    print(f"Status: {data.get('status')}")
    print(f"workflow_id field: {data.get('workflow_id', 'MISSING')}")
else:
    print(f"❌ Not found at expected key: {exact_key}")

    # Search for it
    print("\n🔍 Searching all workflows...")
    all_workflows = r.keys("rossnet:workflow:*")
    found = False

    for key in all_workflows:
        try:
            data = json.loads(r.get(key))
            # Check if this workflow matches by correlation_id
            if data.get("controller_correlation_id") == workflow_id:
                print(f"\n✅ Found workflow with matching correlation_id at: {key}")
                print(f"Status: {data.get('status')}")
                print(f"workflow_id field: {data.get('workflow_id', 'MISSING')}")
                print("This is why API can't find it - wrong key!")
                found = True
                break
        except:
            pass

    if not found:
        print("❌ Workflow not found anywhere in Redis")
