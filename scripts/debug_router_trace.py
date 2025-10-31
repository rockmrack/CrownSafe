# scripts/debug_router_trace.py

import asyncio
import functools
import inspect
import json
import logging
import sys
import uuid
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.routing.router_agent.agent_logic import RouterLogic

# TRACE EVERYTHING
TRACE_LOG = []


def trace_calls(obj):
    """Wrap all methods of an object to trace calls"""
    for name in dir(obj):
        if name.startswith("_"):
            continue
        attr = getattr(obj, name)
        if callable(attr) and not isinstance(attr, type):
            wrapped = trace_wrapper(attr, name)
            setattr(obj, name, wrapped)
    return obj


def trace_wrapper(func, name):
    """Wrapper that logs all calls"""

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        TRACE_LOG.append(f"CALL: {name}({args[1:] if args else ''}, {kwargs})")
        result = await func(*args, **kwargs)
        TRACE_LOG.append(f"RETURN: {name} -> {result}")
        return result

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        TRACE_LOG.append(f"CALL: {name}({args[1:] if args else ''}, {kwargs})")
        result = func(*args, **kwargs)
        TRACE_LOG.append(f"RETURN: {name} -> {result}")
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


# CAPTURE EVERYTHING
MESSAGES_SENT = []


class DebugMockClient:
    def __init__(self):
        self.discoveries = {}
        print("🔍 DebugMockClient created")

    async def send_message(self, payload, message_type, target_agent_id, correlation_id):
        msg = {
            "payload": payload,
            "message_type": message_type,
            "target_agent_id": target_agent_id,
            "correlation_id": correlation_id,
        }
        MESSAGES_SENT.append(msg)
        print(f"🟢 MOCK SEND_MESSAGE CALLED: {message_type} → {target_agent_id}")
        return True

    async def query_discovery(self, capabilities_list):
        corr_id = f"disc_{uuid.uuid4().hex[:8]}"
        self.discoveries[corr_id] = capabilities_list
        print(f"🔵 MOCK QUERY_DISCOVERY CALLED: {capabilities_list}")
        return corr_id


class DebugRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        val = self.data.get(key)
        if val and isinstance(val, str):
            return val.encode()
        return val

    async def set(self, key, value):
        if isinstance(value, bytes):
            value = value.decode()
        self.data[key] = value
        return True

    async def setex(self, key, ttl, value):
        return await self.set(key, value)

    async def ping(self):
        return True

    async def close(self):
        pass


async def debug_router():
    print("\n" + "=" * 70)
    print("🔍 ROUTER DEBUGGING - TRACING ALL CALLS")
    print("=" * 70 + "\n")

    # Clear everything
    TRACE_LOG.clear()
    MESSAGES_SENT.clear()

    # Setup
    workflow_id = str(uuid.uuid4())
    plan = {
        "workflow_goal": "Debug test",
        "steps": [
            {
                "step_id": "task1",
                "agent_capability_required": "cap1",
                "task_description": "Task 1",
                "inputs": {},
                "dependencies": [],
            }
        ],
    }

    # Create mocks
    client = DebugMockClient()
    redis = DebugRedis()

    # Trace the client
    trace_calls(client)

    # Create router
    print("Creating router...")
    router = RouterLogic("debug_router", client, logger)
    router.redis_conn = redis

    # Verify client is set correctly
    print(f"\nRouter's mcp_client: {router.mcp_client}")
    print(f"Is our mock: {router.mcp_client is client}")
    print(f"Has send_message: {hasattr(router.mcp_client, 'send_message')}")
    print(f"send_message is: {router.mcp_client.send_message}")

    # Monkey patch the _send_response_to_agent to see if it's called
    original_send_response = router._send_response_to_agent

    async def debug_send_response(*args, **kwargs):
        print("\n🎯 _send_response_to_agent CALLED!")
        print(f"   Args: {args}")
        print(f"   Kwargs: {kwargs}")
        result = await original_send_response(*args, **kwargs)
        print(f"   Result: {result}")
        return result

    router._send_response_to_agent = debug_send_response

    # Submit plan
    print("\n📤 Submitting plan...")
    await router.process_message(
        {
            "mcp_header": {
                "message_type": "TASK_ASSIGN",
                "correlation_id": workflow_id,
                "sender_id": "commander",
            },
            "payload": {"plan": plan},
        }
    )

    await asyncio.sleep(0.5)

    # Send discovery response
    print("\n📡 Sending discovery response...")
    if client.discoveries:
        corr_id = list(client.discoveries.keys())[0]
        await router.process_message(
            {
                "mcp_header": {
                    "message_type": "DISCOVERY_RESPONSE",
                    "correlation_id": corr_id,
                    "sender_id": "discovery",
                },
                "payload": {
                    "status": "success",
                    "results": [
                        {
                            "agent_id": "worker_cap1",
                            "capabilities": ["cap1"],
                            "status": "active",
                        }
                    ],
                },
            }
        )

    await asyncio.sleep(0.5)

    # Results
    print("\n" + "=" * 70)
    print("📊 DEBUG RESULTS")
    print("=" * 70)

    print(f"\nMessages captured: {len(MESSAGES_SENT)}")
    print(f"Discoveries: {len(client.discoveries)}")

    if MESSAGES_SENT:
        print("\nCaptured messages:")
        for msg in MESSAGES_SENT:
            print(f"  - {msg['message_type']} → {msg['target_agent_id']}")
    else:
        print("\n❌ NO MESSAGES CAPTURED!")

    # Show trace of client calls
    print("\n📜 Client method calls:")
    client_calls = [log for log in TRACE_LOG if "send_message" in log or "query_discovery" in log]
    for call in client_calls:
        print(f"  {call}")

    # Check router state
    print("\n🔍 Checking workflow state...")
    state_key = f"rossnet:workflow:{workflow_id}"
    state_data = redis.data.get(state_key)
    if state_data:
        state = json.loads(state_data)
        print(f"Workflow status: {state.get('status')}")
        tasks = state.get("tasks", {})
        for task_id, task_info in tasks.items():
            print(f"  Task {task_id}: {task_info.get('status')}")

    await router.shutdown()


async def simple_trace_test():
    """Even simpler test to trace what's happening"""
    print("\n🔬 SIMPLE TRACE TEST\n")

    # Track ALL method calls on mcp_client
    call_log = []

    class TrackedClient:
        def __getattribute__(self, name):
            if name.startswith("_"):
                return object.__getattribute__(self, name)

            attr = object.__getattribute__(self, name)
            if callable(attr):

                def wrapper(*args, **kwargs):
                    call_log.append(f"CLIENT.{name} called with args={args}, kwargs={kwargs}")
                    if asyncio.iscoroutinefunction(attr):
                        return attr(*args, **kwargs)
                    return attr(*args, **kwargs)

                return wrapper
            return attr

        async def send_message(self, *args, **kwargs):
            print(f"✅ send_message called! args={args}, kwargs={kwargs}")
            MESSAGES_SENT.append({"args": args, "kwargs": kwargs})

        async def query_discovery(self, capabilities):
            print(f"✅ query_discovery called! {capabilities}")
            return "test_corr_id"

    client = TrackedClient()

    # Test direct call
    print("Testing direct call...")
    await client.send_message("test", "TEST", "target", "corr")
    print(f"Messages captured: {len(MESSAGES_SENT)}")

    # Test with router
    print("\nTesting with router...")
    router = RouterLogic("test", client, logger)

    # Check if client is still our mock
    print(f"Router client is TrackedClient: {isinstance(router.mcp_client, TrackedClient)}")
    print(f"Router client: {router.mcp_client}")

    print("\nCall log:")
    for call in call_log:
        print(f"  {call}")


if __name__ == "__main__":
    # Configure logging to see router internals
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    print("Running debug trace...")
    asyncio.run(debug_router())

    print("\n" + "=" * 70)
    print("\nRunning simple trace...")
    MESSAGES_SENT.clear()
    asyncio.run(simple_trace_test())
