# scripts/test_router_final_success.py

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import redis.asyncio as redis  # noqa: E402

from agents.routing.router_agent.agent_logic import RouterLogic  # noqa: E402

# Setup logging to see router messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global counters
STATS = {
    "discoveries": 0,
    "task_assigns": 0,
    "task_completes": 0,
    "messages_to_commander": 0,
}


class InstrumentedMockClient:
    """Mock that counts all operations."""

    def __init__(self) -> None:
        self.discoveries = {}

    async def send_message(self, payload, message_type, target_agent_id, correlation_id) -> None:
        """Count messages by type."""
        if message_type == "TASK_ASSIGN":
            STATS["task_assigns"] += 1
        elif message_type == "TASK_COMPLETE":
            STATS["task_completes"] += 1
            if target_agent_id == "test_commander":
                STATS["messages_to_commander"] += 1

        print(f"📤 {message_type} → {target_agent_id}")

    async def query_discovery(self, capabilities_list):
        """Count discoveries."""
        STATS["discoveries"] += 1
        corr_id = f"disc_{uuid.uuid4().hex[:8]}"
        self.discoveries[corr_id] = capabilities_list
        print(f"🔍 Discovery query #{STATS['discoveries']}: {capabilities_list}")
        return corr_id


async def test_router_success() -> int | None:
    print("\n" + "=" * 60)
    print("🎉 ROUTER v1.5.2 VALIDATION TEST")
    print("=" * 60 + "\n")

    # Reset stats
    for key in STATS:
        STATS[key] = 0

    # Test data - 4 tasks (3 parallel, 1 dependent)
    workflow_id = str(uuid.uuid4())
    plan = {
        "workflow_goal": "Complete prior authorization",
        "steps": [
            {
                "step_id": "step1_patient_data",
                "agent_capability_required": "medical_records",
                "task_description": "Get patient data",
                "inputs": {"patient_id": "P123"},
                "dependencies": [],
            },
            {
                "step_id": "step2_guidelines",
                "agent_capability_required": "clinical_guidelines",
                "task_description": "Get guidelines",
                "inputs": {"drug": "Empagliflozin"},
                "dependencies": [],
            },
            {
                "step_id": "step3_policy",
                "agent_capability_required": "insurance_policy",
                "task_description": "Get policy",
                "inputs": {"insurer": "UHC"},
                "dependencies": [],
            },
            {
                "step_id": "step4_predict",
                "agent_capability_required": "ml_prediction",
                "task_description": "Predict approval",
                "inputs": {},
                "dependencies": [
                    "step1_patient_data",
                    "step2_guidelines",
                    "step3_policy",
                ],
            },
        ],
    }

    # Connect to Redis
    try:
        redis_conn = await redis.Redis(host="localhost", port=6379, decode_responses=False)
        await redis_conn.ping()
        print("✅ Redis connected\n")
    except (redis.ConnectionError, redis.TimeoutError):
        print("❌ Redis not running. Start with: redis-server")
        return 1

    # Create router
    client = InstrumentedMockClient()
    router = RouterLogic("test_router", client, logger)
    router.redis_conn = redis_conn

    try:
        # PHASE 1: Submit plan
        print("📋 PHASE 1: Submitting plan with 4 tasks...")
        await router.process_message(
            {
                "mcp_header": {
                    "message_type": "TASK_ASSIGN",
                    "correlation_id": workflow_id,
                    "sender_id": "test_commander",
                },
                "payload": {"plan": plan},
            },
        )
        await asyncio.sleep(0.5)

        print(f"\n✓ Discoveries made: {STATS['discoveries']}")
        print(f"✓ Tasks assigned: {STATS['task_assigns']}")

        # PHASE 2: Send discovery responses
        print("\n📋 PHASE 2: Sending discovery responses...")
        for corr_id, caps in client.discoveries.items():
            await router.process_message(
                {
                    "mcp_header": {
                        "message_type": "DISCOVERY_RESPONSE",
                        "correlation_id": corr_id,
                        "sender_id": "discovery_service",
                    },
                    "payload": {
                        "status": "success",
                        "results": [
                            {
                                "agent_id": f"worker_{caps[0]}",
                                "capabilities": caps,
                                "status": "active",
                            },
                        ],
                    },
                },
            )
        await asyncio.sleep(0.5)

        print(f"\n✓ Total tasks assigned: {STATS['task_assigns']}")

        # PHASE 3: Simulate worker completions
        print("\n📋 PHASE 3: Simulating worker completions...")

        # Complete the first 3 parallel tasks
        for i, task_id in enumerate(["step1_patient_data", "step2_guidelines", "step3_policy"]):
            await router.process_message(
                {
                    "mcp_header": {
                        "message_type": "TASK_COMPLETE",
                        "correlation_id": f"subtask_{workflow_id}_{task_id}_mock",
                        "sender_id": f"worker_mock_{i}",
                    },
                    "payload": {
                        "workflow_id": workflow_id,
                        "task_id": task_id,
                        "result": {"status": "success", "data": f"Data for {task_id}"},
                    },
                },
            )
            await asyncio.sleep(0.2)

        # Wait for dependent task to be dispatched
        await asyncio.sleep(1.0)

        # Complete the dependent task
        await router.process_message(
            {
                "mcp_header": {
                    "message_type": "TASK_COMPLETE",
                    "correlation_id": f"subtask_{workflow_id}_step4_predict_mock",
                    "sender_id": "worker_ml_prediction",
                },
                "payload": {
                    "workflow_id": workflow_id,
                    "task_id": "step4_predict",
                    "result": {
                        "status": "success",
                        "data": "APPROVED - 85% confidence",
                    },
                },
            },
        )

        await asyncio.sleep(0.5)

        # FINAL RESULTS
        print("\n" + "=" * 60)
        print("📊 FINAL VALIDATION RESULTS")
        print("=" * 60)

        print(f"\n✅ Discovery queries: {STATS['discoveries']} (Expected: 4)")
        print(f"✅ Tasks assigned: {STATS['task_assigns']} (Expected: 4)")
        print(f"✅ Task completions: {STATS['task_completes']} (Expected: 1+)")
        print(f"✅ Messages to commander: {STATS['messages_to_commander']} (Expected: 1)")

        # Validation
        success = (
            STATS["discoveries"] >= 4
            and STATS["task_assigns"] >= 4
            and STATS["task_completes"] >= 1
            and STATS["messages_to_commander"] >= 1
        )

        print("\n" + "=" * 60)
        if success:
            print("🎉 ALL VALIDATIONS PASSED!")
            print("✅ Router v1.5.2 with enhanced dependency handling")
            print("✅ is working PERFECTLY!")
        else:
            print("⚠️  Some validations failed")
            print("   Check the statistics above")
        print("=" * 60 + "\n")

        await router.shutdown()
        await redis_conn.close()

        return 0 if success else 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        await redis_conn.close()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_router_success())
    sys.exit(exit_code)
