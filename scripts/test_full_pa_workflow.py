# scripts/test_api_diagnostic.py

import json
import logging
import time
from typing import Any, Dict, Optional

import redis
import requests


# Setup colored logging
class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        record.msg = f"{log_color}{record.msg}{self.RESET}"
        return super().format(record)


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

API_BASE_URL = "http://127.0.0.1:8000"


def check_endpoint(method: str, endpoint: str, data: Optional[Dict] = None, expected_status: int = 200) -> tuple:
    """Check a single endpoint and return (success, response_data, error_message)"""
    url = f"{API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            return False, None, f"Unsupported method: {method}"

        # Log full response for debugging
        logger.debug(f"Response Status: {response.status_code}")
        logger.debug(f"Response Headers: {dict(response.headers)}")

        try:
            response_data = response.json()
        except:
            response_data = {"text": response.text}

        logger.debug(f"Response Body: {json.dumps(response_data, indent=2)}")

        if response.status_code == expected_status:
            return True, response_data, None
        else:
            return (
                False,
                response_data,
                f"Expected {expected_status}, got {response.status_code}",
            )

    except requests.exceptions.ConnectionError:
        return False, None, "Connection refused - is the API running?"
    except requests.exceptions.Timeout:
        return False, None, "Request timed out"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def check_redis_for_workflow(workflow_id: str) -> Dict[str, Any]:
    """Check Redis directly for workflow information"""
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Check the expected key
        expected_key = f"rossnet:workflow:{workflow_id}"

        # Also check for any keys containing the workflow ID
        all_workflow_keys = r.keys("*workflow*")
        matching_keys = [k for k in all_workflow_keys if workflow_id in k]

        result = {
            "expected_key_exists": r.exists(expected_key),
            "expected_key": expected_key,
            "matching_keys": matching_keys,
            "workflow_data": None,
            "workflow_id_field": None,
        }

        # Try to get the workflow data
        if r.exists(expected_key):
            workflow_json = r.get(expected_key)
            if workflow_json:
                workflow_data = json.loads(workflow_json)
                result["workflow_data"] = workflow_data
                result["workflow_id_field"] = workflow_data.get("workflow_id", "MISSING")
                result["status"] = workflow_data.get("status", "UNKNOWN")

        # Check other matching keys
        for key in matching_keys[:5]:  # Limit to 5 to avoid spam
            if key != expected_key:
                try:
                    data = json.loads(r.get(key))
                    logger.debug(f"Found related key {key} with status: {data.get('status')}")
                except:
                    pass

        return result

    except Exception as e:
        return {"error": str(e)}


def diagnose_api():
    """Run diagnostic checks on the API"""
    logger.info("=" * 70)
    logger.info("🔍 RossNet API Diagnostic Tool")
    logger.info("=" * 70 + "\n")

    # 1. Check if API is reachable
    logger.info("1️⃣ Checking API connectivity...")
    success, data, error = check_endpoint("GET", "/")

    if not success:
        logger.error(f"   ❌ Cannot reach API: {error}")
        logger.error("   Make sure the API Gateway is running:")
        logger.error("   python api_gateway/main.py")
        return

    logger.info("   ✅ API is reachable")

    # 2. Check health endpoint
    logger.info("\n2️⃣ Checking health endpoint...")
    success, data, error = check_endpoint("GET", "/health")

    if success:
        logger.info("   ✅ Health check passed")
        if data:
            logger.info(f"   Status: {data.get('status', 'unknown')}")
    else:
        logger.warning(f"   ⚠️  Health check issue: {error}")

    # 3. Check if endpoints exist
    logger.info("\n3️⃣ Checking API endpoints...")

    # Test various endpoints
    endpoints_to_check = [
        ("GET", "/api/v1/", 404),  # Might not exist
        (
            "POST",
            "/api/v1/prior-auth/predict",
            422,
        ),  # Should fail with validation error
        ("GET", "/api/v1/status/test-id", 404),  # Non-existent workflow
    ]

    for method, endpoint, expected in endpoints_to_check:
        success, data, error = check_endpoint(method, endpoint, expected_status=expected)
        if success or "Expected" in str(error):
            logger.info(f"   ✅ {method} {endpoint} - Accessible")
        else:
            logger.error(f"   ❌ {method} {endpoint} - {error}")

    # 4. Test workflow submission with detailed error checking
    logger.info("\n4️⃣ Testing workflow submission...")

    test_payload = {
        "patient_id": "test-patient-001",
        "drug_name": "Metformin",
        "insurer_id": "TEST-INS",
    }

    logger.info(f"   Payload: {json.dumps(test_payload, indent=6)}")

    url = f"{API_BASE_URL}/api/v1/prior-auth/predict"

    try:
        response = requests.post(url, json=test_payload, timeout=10)

        logger.info(f"   Response Status: {response.status_code}")
        logger.info(f"   Response Headers: {dict(response.headers)}")

        try:
            response_data = response.json()
            logger.info(f"   Response Body: {json.dumps(response_data, indent=6)}")
        except:
            logger.error(f"   Response Text: {response.text}")

        if response.status_code == 202:
            logger.info("   ✅ Workflow submission successful!")
            workflow_id = response_data.get("workflow_id")
            if workflow_id:
                logger.info(f"   Workflow ID: {workflow_id}")

                # Check Redis directly first
                logger.info("\n4.5️⃣ Checking Redis for workflow...")
                time.sleep(1)  # Give it a moment to be created

                redis_check = check_redis_for_workflow(workflow_id)

                if redis_check.get("expected_key_exists"):
                    logger.info(f"   ✅ Workflow found in Redis at: {redis_check['expected_key']}")
                    if redis_check.get("workflow_id_field") == "MISSING":
                        logger.error("   ❌ ISSUE DETECTED: workflow_id field is missing in the stored data!")
                        logger.error("   This is why the API returns 404 when checking status.")
                        logger.error("   FIX: Restart the Router Agent with the updated agent_logic.py")
                    elif redis_check.get("workflow_id_field") == workflow_id:
                        logger.info("   ✅ workflow_id field is correctly set")
                    else:
                        logger.warning(f"   ⚠️  workflow_id mismatch: {redis_check.get('workflow_id_field')}")
                else:
                    logger.warning("   ⚠️  Workflow not found at expected Redis key")
                    if redis_check.get("matching_keys"):
                        logger.info(f"   Found {len(redis_check['matching_keys'])} related keys:")
                        for key in redis_check["matching_keys"][:3]:
                            logger.info(f"     - {key}")

                # Try to check status via API
                logger.info("\n5️⃣ Checking workflow status via API...")
                time.sleep(2)

                status_url = f"{API_BASE_URL}/api/v1/status/{workflow_id}"
                status_response = requests.get(status_url, timeout=5)

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    logger.info("   ✅ Status check successful!")
                    logger.info(f"   Workflow Status: {status_data.get('status')}")
                    logger.info(f"   Full Status: {json.dumps(status_data, indent=6)}")
                elif status_response.status_code == 404:
                    logger.error("   ❌ Status check failed: 404 - Workflow not found")
                    logger.error("   This typically means:")
                    logger.error("   1. The workflow_id field is missing in Redis (most common)")
                    logger.error("   2. The workflow hasn't been created yet")
                    logger.error("   3. The workflow key uses a different format")
                else:
                    logger.error(f"   ❌ Status check failed: {status_response.status_code}")

        elif response.status_code == 500:
            logger.error("   ❌ Internal Server Error (500)")
            logger.error("   This usually means:")
            logger.error("   1. The API cannot connect to Redis")
            logger.error("   2. The API cannot connect to the agents")
            logger.error("   3. There's an error in the API code")
            logger.error("\n   Troubleshooting steps:")
            logger.error("   1. Check if Redis is running: redis-cli ping")
            logger.error("   2. Check if all agents are running")
            logger.error("   3. Check API Gateway logs for detailed error")

        else:
            logger.error(f"   ❌ Unexpected status code: {response.status_code}")

    except Exception as e:
        logger.error(f"   ❌ Error during workflow submission: {str(e)}")

    # 6. Check system dependencies
    logger.info("\n6️⃣ Checking system dependencies...")

    # Check Redis
    try:
        import redis

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        logger.info("   ✅ Redis is running")

        # Count workflows in Redis
        workflow_keys = r.keys("rossnet:workflow:*")
        logger.info(f"   📊 Total workflows in Redis: {len(workflow_keys)}")

    except:
        logger.error("   ❌ Redis is not accessible")
        logger.error("   Start Redis with: redis-server")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 Diagnostic Summary")
    logger.info("=" * 70)

    logger.info("\nIf status checks are returning 404:")
    logger.info("1. The workflow_id field might be missing (we just fixed this)")
    logger.info("2. Restart the Router Agent with the updated agent_logic.py")
    logger.info("3. New workflows created after the restart should work correctly")
    logger.info("\nIf you're getting 500 errors:")
    logger.info("1. All agents must be running (Commander, Planner, Router, Workers)")
    logger.info("2. Redis must be running")
    logger.info("3. Check the API Gateway console for error messages")
    logger.info("\nTo restart the Router Agent:")
    logger.info("1. Stop the current Router Agent (Ctrl+C)")
    logger.info("2. Start it again: python -m agents.routing.router_agent.main")


def test_minimal_workflow():
    """Test the absolute minimum workflow"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 Minimal Workflow Test")
    logger.info("=" * 70 + "\n")

    # Super simple request
    url = f"{API_BASE_URL}/api/v1/prior-auth/predict"
    payload = {"patient_id": "p1", "drug_name": "d1", "insurer_id": "i1"}

    logger.info("Sending minimal request...")

    try:
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 202:
            data = response.json()
            workflow_id = data.get("workflow_id")
            logger.info(f"✅ Success! Workflow ID: {workflow_id}")

            # Check Redis immediately
            logger.info("\n🔍 Checking Redis directly...")
            redis_info = check_redis_for_workflow(workflow_id)

            if redis_info.get("expected_key_exists"):
                logger.info("✅ Workflow exists in Redis")
                if redis_info.get("workflow_id_field") == workflow_id:
                    logger.info("✅ workflow_id field is correctly set")
                else:
                    logger.error(f"❌ workflow_id field issue: {redis_info.get('workflow_id_field')}")
            else:
                logger.warning("⚠️  Workflow not yet in Redis")

            # Poll status
            logger.info("\n📊 Polling status...")
            for i in range(10):
                time.sleep(3)
                status_response = requests.get(f"{API_BASE_URL}/api/v1/status/{workflow_id}")

                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status")
                    logger.info(f"   Poll {i + 1}: {status}")

                    if status in ["COMPLETED", "FAILED"]:
                        logger.info(f"\n✅ Final Result: {json.dumps(status_data, indent=2)}")
                        break
                elif status_response.status_code == 404:
                    logger.error(f"   Poll {i + 1}: 404 - Workflow not found")

                    # Re-check Redis
                    redis_recheck = check_redis_for_workflow(workflow_id)
                    if redis_recheck.get("expected_key_exists"):
                        logger.info("      → Workflow IS in Redis but API can't find it")
                        logger.info("      → This confirms the workflow_id field issue")
                        logger.info("      → Solution: Restart Router Agent with the fix")
                        break
                else:
                    logger.error(f"   Poll {i + 1}: Error {status_response.status_code}")

            else:
                logger.warning("\n⚠️  Workflow did not complete within timeout")

        else:
            logger.error(f"❌ Failed with status: {response.status_code}")
            try:
                logger.error(f"Response: {response.json()}")
            except:
                logger.error(f"Response text: {response.text}")

    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")


def check_workflow_id_fix():
    """Check if the workflow_id fix is needed"""
    logger.info("\n" + "=" * 70)
    logger.info("🔧 Checking for workflow_id issue")
    logger.info("=" * 70 + "\n")

    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Get a few workflow keys
        workflow_keys = r.keys("rossnet:workflow:*")[:5]

        if not workflow_keys:
            logger.info("No workflows found in Redis")
            return

        logger.info(f"Checking {len(workflow_keys)} workflows...\n")

        missing_id_count = 0

        for key in workflow_keys:
            _ = key.split(":")[-1]  # workflow_id_from_key

            try:
                data = json.loads(r.get(key))
                stored_id = data.get("workflow_id", "MISSING")

                if stored_id == "MISSING" or stored_id == "N/A":
                    missing_id_count += 1
                    logger.error(f"❌ {key}")
                    logger.error(f"   workflow_id field: {stored_id}")
                else:
                    logger.info(f"✅ {key}")
                    logger.info(f"   workflow_id field: {stored_id}")

            except Exception as e:
                logger.error(f"Error checking {key}: {e}")

        if missing_id_count > 0:
            logger.error(f"\n❌ Found {missing_id_count} workflows with missing/invalid workflow_id field")
            logger.error("This is why the API returns 404 when checking status")
            logger.error("\nTO FIX:")
            logger.error("1. We've already updated the router agent code")
            logger.error("2. Now restart the Router Agent")
            logger.error("3. New workflows will have the correct workflow_id field")
        else:
            logger.info("\n✅ All checked workflows have proper workflow_id fields")

    except Exception as e:
        logger.error(f"Error checking workflows: {e}")


if __name__ == "__main__":
    import sys

    # Add debug flag
    if "--debug" in sys.argv:
        logger.setLevel(logging.DEBUG)

    # Check for workflow_id issue
    if "--check-fix" in sys.argv:
        check_workflow_id_fix()
    # Run diagnostic
    else:
        diagnose_api()

        # Run minimal test if requested
        if "--test" in sys.argv:
            test_minimal_workflow()
