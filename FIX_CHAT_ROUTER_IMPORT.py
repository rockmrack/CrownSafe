#!/usr/bin/env python3
"""
Test script to identify chat router import issues
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.getcwd())

def test_imports():
    """Test each import individually to find the failing one"""
    
    print("🔍 Testing chat router imports...")
    
    try:
        print("1. Testing basic imports...")
        from uuid import uuid4, UUID
        import logging
        from typing import Dict, Any, List, Optional, Literal
        from time import perf_counter, monotonic
        print("✅ Basic imports OK")
    except Exception as e:
        print(f"❌ Basic imports failed: {e}")
        return False
    
    try:
        print("2. Testing FastAPI imports...")
        from fastapi import APIRouter, Depends, HTTPException, Request
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
        from sqlalchemy.orm import Session
        print("✅ FastAPI imports OK")
    except Exception as e:
        print(f"❌ FastAPI imports failed: {e}")
        return False
    
    try:
        print("3. Testing core modules...")
        from core.chat_budget import TOTAL_BUDGET_SEC, ROUTER_TIMEOUT_SEC, TOOL_TIMEOUT_SEC, SYNTH_TIMEOUT_SEC
        print("✅ Chat budget OK")
    except Exception as e:
        print(f"❌ Chat budget failed: {e}")
        return False
    
    try:
        from core.resilience import breaker, call_with_timeout
        print("✅ Resilience OK")
    except Exception as e:
        print(f"❌ Resilience failed: {e}")
        return False
    
    try:
        from core.feature_flags import chat_enabled_for
        print("✅ Feature flags OK")
    except Exception as e:
        print(f"❌ Feature flags failed: {e}")
        return False
    
    try:
        from core.metrics import inc_req, obs_total, obs_tool, obs_synth, inc_fallback, inc_blocked, inc_alternatives_shown, inc_unclear, inc_emergency
        print("✅ Metrics OK")
    except Exception as e:
        print(f"❌ Metrics failed: {e}")
        return False
    
    try:
        print("4. Testing chat memory...")
        from api.crud.chat_memory import get_profile, get_or_create_conversation, log_message, upsert_profile, mark_erase_requested, purge_conversations_for_user
        print("✅ Chat memory OK")
    except Exception as e:
        print(f"❌ Chat memory failed: {e}")
        return False
    
    try:
        print("5. Testing chat tools...")
        from api.services.chat_tools import run_tool_for_intent
        print("✅ Chat tools OK")
    except Exception as e:
        print(f"❌ Chat tools failed: {e}")
        return False
    
    try:
        print("6. Testing chat agent logic...")
        from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse
        print("✅ Chat agent logic OK")
    except Exception as e:
        print(f"❌ Chat agent logic failed: {e}")
        return False
    
    try:
        print("7. Testing database...")
        from core_infra.database import get_db
        print("✅ Database OK")
    except Exception as e:
        print(f"❌ Database failed: {e}")
        return False
    
    try:
        print("8. Testing workers...")
        from workers.tasks.chat_cleanup import purge_user_history_task
        print("✅ Workers OK")
    except Exception as e:
        print(f"❌ Workers failed: {e}")
        print(f"   This might be the issue!")
        return False
    
    try:
        print("9. Testing full chat router import...")
        from api.routers.chat import router as chat_router
        print("✅ Chat router import successful!")
        print(f"   Router has {len(chat_router.routes)} routes")
        
        # List the routes
        for route in chat_router.routes:
            if hasattr(route, 'path'):
                print(f"   - {route.methods} {route.path}")
        
        return True
    except Exception as e:
        print(f"❌ Chat router import failed: {e}")
        print(f"   This is the root cause!")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("\n✅ ALL IMPORTS SUCCESSFUL - Chat router should work!")
    else:
        print("\n❌ IMPORT FAILURE IDENTIFIED - This is why chat endpoints are missing!")
