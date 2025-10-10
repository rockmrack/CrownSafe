# scripts/test_full_workflow.py

import requests
import time
import json

print("🚀 Full Workflow Test\n")

# Step 1: Submit workflow
print("1️⃣ Submitting workflow...")
response = requests.post(
    "http://localhost:8000/api/v1/prior-auth/predict",
    json={
        "patient_id": "test-patient-123",
        "drug_name": "Metformin",
        "insurer_id": "BlueCross",
    },
)

if response.status_code != 202:
    print(f"❌ Failed to submit: {response.status_code}")
    print(response.text)
    exit(1)

workflow_id = response.json()["workflow_id"]
print(f"✅ Workflow submitted: {workflow_id}")

# Step 2: Poll for completion
print("\n2️⃣ Polling for completion...")
max_attempts = 30
attempt = 0

while attempt < max_attempts:
    time.sleep(3)
    attempt += 1

    print(f"\n  Attempt {attempt}/{max_attempts}")

    # Check status
    status_response = requests.get(f"http://localhost:8000/api/v1/status/{workflow_id}")

    if status_response.status_code == 404:
        # Try direct Redis check
        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Check if workflow exists with different format
        possible_keys = [
            f"rossnet:workflow:{workflow_id}",
            f"commander:workflow:{workflow_id}",
            f"workflow:{workflow_id}",
        ]

        found = False
        for key in possible_keys:
            if r.exists(key):
                print(f"  📍 Found in Redis at: {key}")
                data = json.loads(r.get(key))
                print(f"  Status in Redis: {data.get('status')}")
                found = True
                break

        if not found:
            # List all workflows to debug
            all_workflows = r.keys("*workflow*")
            print(f"  🔍 Total workflows in Redis: {len(all_workflows)}")
            if workflow_id in str(all_workflows):
                print("  ⚠️  Workflow ID found in some key")

        continue

    elif status_response.status_code == 200:
        status_data = status_response.json()
        print(f"  ✅ Status: {status_data['status']}")

        if status_data["status"] in ["COMPLETED", "FAILED"]:
            print("\n3️⃣ Final Result:")
            print(json.dumps(status_data, indent=2))

            if status_data["status"] == "COMPLETED":
                print("\n✅ Workflow completed successfully!")
            else:
                print(f"\n❌ Workflow failed: {status_data.get('error_message')}")
            break

    else:
        print(f"  ❌ Error: {status_response.status_code}")

if attempt >= max_attempts:
    print("\n❌ Workflow did not complete in time")
