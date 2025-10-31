# scripts/test_api_quick.py

import json
import time

import requests

# Test the API
url = "http://localhost:8000/api/v1/prior-auth/predict"
data = {"patient_id": "test-001", "drug_name": "Metformin", "insurer_id": "UHC"}

print("🚀 Sending request to API...")
response = requests.post(url, json=data)

print(f"📋 Status: {response.status_code}")

if response.status_code == 202:
    result = response.json()
    print(f"✅ Response: {json.dumps(result, indent=2)}")

    workflow_id = result["workflow_id"]
    print(f"\n🔍 Workflow ID: {workflow_id}")

    # Check status
    print("\n⏳ Checking status...")
    for i in range(5):
        time.sleep(2)
        status_response = requests.get(f"http://localhost:8000/api/v1/status/{workflow_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"   Status: {status_data['status']}")
            if status_data["status"] in ["COMPLETED", "FAILED"]:
                print("\n📊 Final result:")
                print(json.dumps(status_data, indent=2))
                break
else:
    print(f"❌ Error: {response.text}")
