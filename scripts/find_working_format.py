# scripts/find_working_format.py

import json

import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🔍 Finding what message format actually works...\n")

# Look for any successful workflow
workflows = r.keys("rossnet:workflow:*")
if workflows:
    # Get a recent workflow that was created by commander
    for key in workflows[-5:]:  # Check last 5
        try:
            data = json.loads(r.get(key))
            if data.get("original_requester_id") == "commander_agent_01":
                print(f"✅ Found Commander-created workflow: {key}")
                print(f"   Status: {data.get('status')}")

                # Check the original payload
                if "original_plan_payload" in data:
                    print("\n📋 Original plan payload structure:")
                    plan = data["original_plan_payload"]
                    print(json.dumps(plan, indent=2)[:500] + "...")
                    break
        except:
            pass

# Let's also check what messages Commander IS processing
print("\n🔍 Checking Commander message patterns...")

# The issue might be that Commander expects a specific field structure
# Let's try with the exact format from the logs

test_formats = [
    # Format 1: Direct user_request
    {
        "user_goal": "Test authorization",
        "task_type": "prior_authorization",
        "parameters": {"patient_id": "p1", "drug_name": "d1", "insurer_id": "i1"},
    },
    # Format 2: Wrapped in user_request
    {
        "user_request": {
            "user_goal": "Test authorization",
            "task_type": "prior_authorization",
            "parameters": {"patient_id": "p1", "drug_name": "d1", "insurer_id": "i1"},
        }
    },
    # Format 3: Different structure
    {
        "request": {
            "user_goal": "Test authorization",
            "task_type": "prior_authorization",
            "parameters": {"patient_id": "p1", "drug_name": "d1", "insurer_id": "i1"},
        }
    },
]

print("\n🧪 Which format does Commander accept?")
for i, fmt in enumerate(test_formats):
    print(f"\nFormat {i + 1}: {list(fmt.keys())}")
