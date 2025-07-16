# scripts/debug_workflow_flow.py

import redis
import json
import time
import asyncio
from datetime import datetime

def check_all_redis_keys(pattern="*"):
    """Check all Redis keys matching pattern"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    keys = r.keys(pattern)
    return keys

def monitor_redis_for_workflow(workflow_id, duration=30):
    """Monitor Redis for any appearance of the workflow ID"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print(f"🔍 Monitoring Redis for workflow: {workflow_id}")
    print(f"   Duration: {duration} seconds\n")
    
    start_time = time.time()
    found_keys = set()
    
    while time.time() - start_time < duration:
        # Check for any key containing the workflow ID
        all_keys = r.keys("*")
        
        for key in all_keys:
            if workflow_id in key:
                if key not in found_keys:
                    found_keys.add(key)
                    print(f"✅ Found new key: {key}")
                    try:
                        value = r.get(key)
                        data = json.loads(value) if value else {}
                        print(f"   Status: {data.get('status', 'N/A')}")
                        print(f"   Type: {data.get('message_type', 'N/A')}")
                    except:
                        print(f"   (Could not parse value)")
        
        # Also check specific expected keys
        expected_keys = [
            f"rossnet:workflow:{workflow_id}",
            f"commander:workflow:{workflow_id}",
            f"pending_workflow:{workflow_id}",
            f"mcp:messages:*{workflow_id}*"
        ]
        
        for pattern in expected_keys:
            keys = r.keys(pattern)
            for key in keys:
                if key not in found_keys:
                    found_keys.add(key)
                    print(f"✅ Found expected key: {key}")
        
        time.sleep(0.5)
    
    print(f"\n📊 Summary: Found {len(found_keys)} keys related to workflow")
    return found_keys

def check_commander_to_router_flow():
    """Check if messages are flowing from Commander to Router"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("🔍 Checking message flow...\n")
    
    # Check for recent messages
    message_patterns = [
        "mcp:messages:commander_agent_*",
        "mcp:messages:planner_agent_*", 
        "mcp:messages:router_agent_*",
        "mcp:ack:*",
        "rossnet:workflow:*"
    ]
    
    for pattern in message_patterns:
        keys = r.keys(pattern)
        print(f"📬 {pattern}: {len(keys)} keys")
        
        # Show recent ones
        if keys:
            recent_keys = sorted(keys)[-3:]  # Last 3
            for key in recent_keys:
                ttl = r.ttl(key)
                print(f"   - {key} (TTL: {ttl}s)")

def check_agent_queues():
    """Check agent message queues"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print("\n🔍 Checking agent queues...\n")
    
    agents = ["commander_agent_01", "planner_agent_01", "router_agent_01"]
    
    for agent in agents:
        queue_key = f"mcp:queue:{agent}"
        queue_length = r.llen(queue_key)
        print(f"📨 {agent} queue: {queue_length} messages")
        
        if queue_length > 0:
            # Peek at first message without removing
            message = r.lindex(queue_key, 0)
            try:
                msg_data = json.loads(message)
                msg_type = msg_data.get("mcp_header", {}).get("message_type", "Unknown")
                print(f"   First message type: {msg_type}")
            except:
                print(f"   (Could not parse message)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Monitor mode - watch for a specific workflow
        if len(sys.argv) > 2:
            workflow_id = sys.argv[2]
            monitor_redis_for_workflow(workflow_id, duration=30)
        else:
            print("Usage: python debug_workflow_flow.py monitor <workflow_id>")
    else:
        # Check current state
        print("="*60)
        print("🔍 RossNet Message Flow Debugger")
        print("="*60)
        
        check_commander_to_router_flow()
        check_agent_queues()
        
        print("\n💡 To monitor a specific workflow:")
        print("   python debug_workflow_flow.py monitor <workflow_id>")