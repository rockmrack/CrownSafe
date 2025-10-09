# scripts/check_mcp_router_status.py

import requests

# Check MCP Router status
response = requests.get("http://127.0.0.1:8001/")
status = response.json()

print("MCP Router Status:")
print(f"Active connections: {status['active_websocket_connections']}")
print(f"Registered agents: {status['registered_agents_in_discovery']}")

# You might need to:
# 1. Restart some agents to free up connections
# 2. Increase the connection limit in MCP Router
# 3. Check if there's a max_connections setting
