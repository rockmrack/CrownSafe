# scripts/check_commander_health.py

import redis
import json
import time
import uuid


def check_commander():
    r = redis.Redis(host="localhost", port=6379, decode_responses=True)

    print("🏥 Commander Agent Health Check\n")

    # 1. Check queue length
    queue_key = "mcp:queue:commander_agent_01"
    queue_len = r.llen(queue_key)
    print(f"1️⃣ Commander queue length: {queue_len}")

    if queue_len > 0:
        print("   ⚠️  Messages are stuck in queue!")
        # Peek at first message
        first_msg = r.lindex(queue_key, 0)
        try:
            msg_data = json.loads(first_msg)
            msg_type = msg_data.get("mcp_header", {}).get("message_type")
            timestamp = msg_data.get("mcp_header", {}).get("timestamp")
            print(f"   First message type: {msg_type}")
            print(f"   Timestamp: {timestamp}")
        except:
            print("   Could not parse first message")

    # 2. Send a PING and see if it's processed
    print("\n2️⃣ Sending PING to Commander...")
    ping_id = str(uuid.uuid4())[:8]
    ping_msg = {
        "mcp_header": {
            "message_type": "PING",
            "sender_id": "health_check",
            "target_id": "commander_agent_01",
            "correlation_id": f"ping_{ping_id}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "payload": {},
    }

    initial_len = r.llen(queue_key)
    r.lpush(queue_key, json.dumps(ping_msg))
    print(f"   Queue length before: {initial_len}, after: {initial_len + 1}")

    # Wait a bit
    time.sleep(3)

    final_len = r.llen(queue_key)
    if final_len < initial_len + 1:
        print("   ✅ Commander processed the PING!")
    else:
        print("   ❌ Commander is NOT processing messages!")
        print("\n   🔧 Solutions:")
        print("   1. Check if Commander Agent is running")
        print("   2. Check Commander Agent console for errors")
        print("   3. Restart Commander Agent")
        return False

    # 3. Check for recent Commander activity
    print("\n3️⃣ Checking for recent Commander activity...")
    # Look for any keys that might indicate Commander activity
    patterns = ["commander:*", "*commander*workflow*", "mcp:ack:commander*"]

    found_activity = False
    for pattern in patterns:
        keys = r.keys(pattern)
        if keys:
            print(f"   Found {len(keys)} keys matching '{pattern}'")
            found_activity = True

    if not found_activity:
        print("   ⚠️  No recent Commander activity found")

    return True


if __name__ == "__main__":
    check_commander()
