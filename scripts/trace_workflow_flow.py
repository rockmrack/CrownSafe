# scripts/trace_workflow_flow.py

import redis
import json
import time
import asyncio

async def trace_workflow(workflow_id: str):
    """Trace where a workflow ID appears in the system"""
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    print(f"🔍 Tracing workflow: {workflow_id}\n")
    
    # 1. Check for workflow in different patterns
    patterns = [
        f"rossnet:workflow:{workflow_id}",
        f"rossnet:workflow:*{workflow_id}*",
        f"commander:*{workflow_id}*",
        f"planner:*{workflow_id}*",
        f"*{workflow_id}*"
    ]
    
    for pattern in patterns:
        keys = r.keys(pattern)
        if keys:
            print(f"✅ Found keys matching pattern '{pattern}':")
            for key in keys[:5]:  # Limit output
                print(f"   - {key}")
                try:
                    value = r.get(key)
                    if value:
                        data = json.loads(value)
                        print(f"     Type: {data.get('message_type', 'N/A')}")
                        print(f"     Status: {data.get('status', 'N/A')}")
                except:
                    pass
        else:
            print(f"❌ No keys found for pattern: {pattern}")
    
    # 2. Check message queues for this workflow
    print("\n📬 Checking message queues...")
    agents = ["commander_agent_01", "planner_agent_01", "router_agent_01"]
    
    for agent in agents:
        queue_key = f"mcp:queue:{agent}"
        queue_len = r.llen(queue_key)
        
        if queue_len > 0:
            print(f"\n{agent} queue ({queue_len} messages):")
            # Check first few messages
            for i in range(min(3, queue_len)):
                msg = r.lindex(queue_key, i)
                try:
                    msg_data = json.loads(msg)
                    corr_id = msg_data.get("mcp_header", {}).get("correlation_id", "")
                    if workflow_id in corr_id:
                        print(f"   ✅ Found message with workflow ID!")
                        print(f"      Type: {msg_data.get('mcp_header', {}).get('message_type')}")
                except:
                    pass

# Run it
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(trace_workflow(sys.argv[1]))
    else:
        print("Usage: python trace_workflow_flow.py <workflow_id>")