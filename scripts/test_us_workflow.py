import requests
import time
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"  # The API is now running inside Docker, but the port is mapped to our host


def run_us_mvp_test():
    """
    Tests the full US-focused MVP workflow by making a live API call
    to the containerized backend stack.

    Prerequisite: The entire backend must be running via `docker-compose up --build`.
    """
    print("--- Starting US MVP End-to-End Test ---")

    # 1. Define the request payload for a product safety check
    request_payload = {
        "task_type": "babyshield_safety_check",
        "parameters": {
            "barcode": "123456789012",  # This UPC is in our CPSC mock data
            "image_url": None,
            "country_code": "US",
        },
    }

    print("\nStep 1: Sending Safety Check request to the API Gateway...")
    print(f"Payload: {json.dumps(request_payload, indent=2)}")

    # 2. Make the initial POST request to trigger the workflow
    try:
        # NOTE: We are now calling the main /process endpoint, as the Commander will route it.
        response = requests.post(
            f"{API_BASE_URL}/api/v1/process", json=request_payload, timeout=15
        )
        response.raise_for_status()

        response_data = response.json()
        workflow_id = response_data.get("workflow_id")

        assert response.status_code == 202
        assert workflow_id is not None

        print(
            f"   -> SUCCESS: API Gateway accepted the request. Workflow ID: {workflow_id}"
        )

    except requests.exceptions.RequestException as e:
        print(f"   -> FAILED: Could not connect to the API Gateway at {API_BASE_URL}.")
        print("      Is the Docker stack running? Use 'docker-compose up --build -d'.")
        print(f"      Error: {e}")
        return

    # 3. Poll the status endpoint until the workflow is complete
    print(f"\nStep 2: Polling status for workflow {workflow_id}...")

    max_polls = 25
    poll_interval = 2  # seconds
    final_status = None

    for i in range(max_polls):
        try:
            print(f"   Poll attempt {i + 1}/{max_polls}...")
            status_response = requests.get(
                f"{API_BASE_URL}/api/v1/status/{workflow_id}", timeout=10
            )

            if status_response.status_code == 404:
                print("      -> Workflow not yet found in Redis. Waiting...")
                time.sleep(poll_interval)
                continue

            status_response.raise_for_status()

            status_data = status_response.json()
            current_status = status_data.get("status")
            print(f"      -> Current status: {current_status}")

            if current_status in ["COMPLETED", "FAILED"]:
                final_status = status_data
                break

            time.sleep(poll_interval)

        except requests.exceptions.RequestException as e:
            print("   -> FAILED: Could not poll the status endpoint.")
            print(f"      Error: {e}")
            return

    # 4. Verify the final result
    print("\nStep 3: Verifying the final result...")

    if not final_status:
        print("   -> FAILED: Workflow did not complete within the timeout period.")
        return

    if final_status.get("status") == "FAILED":
        print("   -> FAILED: The workflow completed with a FAILED status.")
        print(f"      Error Message: {final_status.get('error_message')}")
        return

    assert final_status.get("status") == "COMPLETED"
    final_result = final_status.get("result")
    assert final_result is not None

    print("   -> SUCCESS: Workflow completed successfully!")
    print("\n--- FINAL HAZARD ANALYSIS RESULT ---")
    print(json.dumps(final_result, indent=2))

    # Check for a key piece of the result from the HazardAnalysisAgent
    # This will need to be updated once the HazardAnalysisAgent is built
    # assert "risk_score" in final_result

    print("\n--- US MVP End-to-End Test Passed Successfully! ---")


if __name__ == "__main__":
    run_us_mvp_test()
