import subprocess
import time

import redis

# 1. Kill all agent processes
print("Killing all agents...")
try:
    subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
except:
    print("Failed to kill processes")

# 2. Clear Redis
print("Clearing Redis...")
r = redis.Redis(host="localhost", port=6379)
r.flushall()
print("Redis cleared")

# 3. Start ONLY commander agent
print("Starting commander agent...")
process = subprocess.Popen(
    ["python", "commander_agent/main.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

# 4. Watch output for 10 seconds
print("\nCommander output:")
print("-" * 50)
start_time = time.time()
while time.time() - start_time < 10:
    output = process.stdout.readline()
    if output:
        print(output.strip())
