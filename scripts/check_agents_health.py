# scripts/check_agents_health.py

import redis
import json
import time
import subprocess

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("🏥 Checking Agent Health...\n")

agents = {
    "commander_agent_01": "Commander",
    "planner_agent_01": "Planner",
    "router_agent_01": "Router",
}

for agent_id, name in agents.items():
    print(f"🔍 {name} Agent:")

    # Check queue
    queue_key = f"mcp:queue:{agent_id}"
    queue_len = r.llen(queue_key)
    print(f"   Queue: {queue_len} messages")

    # Send PING
    ping_msg = {
        "mcp_header": {
            "message_type": "PING",
            "sender_id": "health_check",
            "target_id": agent_id,
            "correlation_id": f"ping_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "payload": {},
    }

    initial_len = queue_len
    r.lpush(queue_key, json.dumps(ping_msg))

    time.sleep(2)

    final_len = r.llen(queue_key)

    if final_len <= initial_len:
        print("   ✅ Processing messages")
    else:
        print("   ❌ NOT processing messages!")
    print()

# Check processes
print("\n🔍 Checking running processes:")
try:
    # Windows
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], capture_output=True, text=True)
    python_processes = result.stdout.count("python.exe")
    print(f"   Found {python_processes} Python processes")
except:
    pass
