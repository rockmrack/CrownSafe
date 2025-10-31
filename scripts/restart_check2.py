import subprocess

import redis

# 1. Kill specific agent processes (not all Python)
print("Killing agents...")
for agent in ["commander_agent", "planner_agent", "router_agent"]:
    try:
        subprocess.run(
            f'taskkill /F /FI "WINDOWTITLE eq {agent}*"',
            shell=True,
            capture_output=True,
        )
    except:
        pass

# 2. Clear Redis
print("Clearing Redis...")
r = redis.Redis(host="localhost", port=6379)
r.flushall()
print("Redis cleared")

# 3. Start commander agent in a new window so we can see output
print("Starting commander agent in new window...")
subprocess.Popen("start cmd /k python commander_agent/main.py", shell=True)

print("\nCommander should be running in a new window.")
print("Check what it's printing there.")
