# scripts/check_services.py

import socket
import requests
import redis


def check_port(host, port, service_name):
    """Check if a port is open"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()

    if result == 0:
        print(f"✅ {service_name} is running on port {port}")
        return True
    else:
        print(f"❌ {service_name} is NOT running on port {port}")
        return False


def check_services():
    print("🔍 Checking RossNet Services...\n")

    all_good = True

    # Check Redis
    try:
        r = redis.Redis(host="localhost", port=6379)
        r.ping()
        print("✅ Redis is running on port 6379")
    except:
        print("❌ Redis is NOT running")
        all_good = False

    # Check MCP Router
    if not check_port("localhost", 8001, "MCP Router"):
        print("   Start with: python core_infra/mcp_router/server.py")
        all_good = False

    # Check API Gateway
    try:
        resp = requests.get("http://localhost:8000/health", timeout=1)
        if resp.status_code == 200:
            print("✅ API Gateway is running on port 8000")
        else:
            print("❌ API Gateway is not healthy")
            all_good = False
    except:
        print("❌ API Gateway is NOT running on port 8000")
        print("   Start with: python api_gateway/main.py")
        all_good = False

    print("\n" + "=" * 50)
    if all_good:
        print("✅ All core services are running!")
    else:
        print("❌ Some services are missing. Start them before running tests.")
        print("\nStartup order:")
        print("1. redis-server")
        print("2. python core_infra/mcp_router/server.py")
        print("3. python agents/commander_agent/main.py")
        print("4. python agents/planning/planner_agent/main.py")
        print("5. python agents/routing/router_agent/main.py")
        print("6. python agents/discovery_agent/main.py")
        print("7. python agents/worker_agents/data_retrieval_agent/main.py")
        print("8. python api_gateway/main.py")


if __name__ == "__main__":
    check_services()
