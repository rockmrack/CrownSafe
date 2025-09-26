#!/usr/bin/env python3
"""Test script to isolate chat import issues"""

import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing chat imports step by step...")
print("=" * 60)

try:
    print("1. Testing database import...")
    from core_infra.database import Base, engine
    print("   ✅ Database imported")
except Exception as e:
    print(f"   ❌ Database import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("2. Testing chat_memory models import...")
    from api.models.chat_memory import UserProfile, Conversation, ConversationMessage
    print("   ✅ Chat memory models imported")
except Exception as e:
    print(f"   ❌ Chat memory models import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Testing analytics models import...")
    from api.models.analytics import ExplainFeedback
    print("   ✅ Analytics models imported")
except Exception as e:
    print(f"   ❌ Analytics models import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("   ✅ Tables created/verified")
except Exception as e:
    print(f"   ❌ Table creation failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("5. Testing chat budget import...")
    from core.chat_budget import TOTAL_BUDGET_SEC
    print(f"   ✅ Chat budget imported (TOTAL_BUDGET_SEC={TOTAL_BUDGET_SEC})")
except Exception as e:
    print(f"   ❌ Chat budget import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("6. Testing resilience import...")
    from core.resilience import breaker, call_with_timeout
    print("   ✅ Resilience imported")
except Exception as e:
    print(f"   ❌ Resilience import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("7. Testing feature flags import...")
    from core.feature_flags import chat_enabled_for
    print("   ✅ Feature flags imported")
except Exception as e:
    print(f"   ❌ Feature flags import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("8. Testing metrics import...")
    from core.metrics import inc_req
    print("   ✅ Metrics imported")
except Exception as e:
    print(f"   ❌ Metrics import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("9. Testing agent logic import...")
    from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse
    print("   ✅ Chat agent logic imported")
except Exception as e:
    print(f"   ❌ Chat agent logic import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("10. Testing chat tools import...")
    from api.services.chat_tools import run_tool_for_intent
    print("   ✅ Chat tools imported")
except Exception as e:
    print(f"   ❌ Chat tools import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("11. Testing chat memory CRUD import...")
    from api.crud.chat_memory import get_profile, get_or_create_conversation
    print("   ✅ Chat memory CRUD imported")
except Exception as e:
    print(f"   ❌ Chat memory CRUD import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("12. Testing chat router import...")
    from api.routers.chat import router as chat_router
    print("   ✅ Chat router imported")
    print(f"   Routes: {[route.path for route in chat_router.routes if hasattr(route, 'path')]}")
except Exception as e:
    print(f"   ❌ Chat router import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("✅ ALL IMPORTS SUCCESSFUL!")
print("The chat feature should work in production.")
