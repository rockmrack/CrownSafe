# scripts/test_api_simple.py

import requests
import json

url = "http://localhost:8000/api/v1/prior-auth/predict"
data = {"patient_id": "test-001", "drug_name": "Metformin", "insurer_id": "UHC"}

print("Sending request to API...")
response = requests.post(url, json=data)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 202:
    workflow_id = response.json()["workflow_id"]
    print(f"\nWorkflow ID: {workflow_id}")
    print(f"Check status at: http://localhost:8000/api/v1/status/{workflow_id}")
