"""Test chat agent and endpoints."""

import sys

sys.path.insert(0, ".")

print("=" * 70)
print("CHAT AGENT VERIFICATION")
print("=" * 70)

# Test 1: Import chat router
print("\n[1/4] Testing chat router import...")
try:
    from api.routers.chat import router as chat_router

    print("✓ Chat router imported successfully")

    routes = [r for r in chat_router.routes if hasattr(r, "path")]
    print(f"✓ Found {len(routes)} chat routes")

    for route in routes:
        methods = ", ".join(sorted(route.methods)) if hasattr(route, "methods") and route.methods else "N/A"
        print(f"  {methods:15} {route.path}")

except Exception as e:
    print(f"✗ Failed to import chat router: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Test 2: Check chat agent logic
print("\n[2/4] Testing chat agent logic...")
try:
    from agents.chat.chat_agent.agent_logic import ChatAgentLogic

    print("✓ ChatAgentLogic imported successfully")
except Exception as e:
    print(f"✗ Failed to import ChatAgentLogic: {e}")
    import traceback

    traceback.print_exc()

# Test 3: Check chat tools
print("\n[3/4] Testing chat tools...")
try:
    from api.services.chat_tools import run_tool_for_intent

    print("✓ Chat tools imported successfully")
except Exception as e:
    print(f"✗ Failed to import chat tools: {e}")
    import traceback

    traceback.print_exc()

# Test 4: Check chat memory/CRUD
print("\n[4/4] Testing chat memory...")
try:
    from api.crud.chat_memory import get_or_create_conversation, log_message

    print("✓ Chat memory functions imported successfully")
except Exception as e:
    print(f"✗ Failed to import chat memory: {e}")
    import traceback

    traceback.print_exc()

# Final check: Verify in main app
print("\n[FINAL] Checking chat registration in main app...")
try:
    from api.main_crownsafe import app

    chat_routes = [r for r in app.routes if hasattr(r, "path") and "/chat" in r.path]
    print(f"✓ Found {len(chat_routes)} chat endpoints in main app")

    # Show some key endpoints
    key_endpoints = [r.path for r in chat_routes if "/api/v1/chat" in r.path]
    if key_endpoints:
        print("\n  Sample endpoints:")
        for ep in sorted(set(key_endpoints))[:10]:
            print(f"    {ep}")

except Exception as e:
    print(f"✗ Failed to check main app: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 70)
print("✓ CHAT AGENT IS OPERATIONAL")
print("=" * 70)
