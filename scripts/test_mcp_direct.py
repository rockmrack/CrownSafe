# scripts/test_mcp_direct.py

import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_http_endpoints():
    """Test if MCP Router has any HTTP endpoints"""
    print("\n🔍 Testing MCP Router HTTP endpoints...\n")
    
    base_url = "http://127.0.0.1:8001"
    
    async with aiohttp.ClientSession() as session:
        # Try different endpoints
        endpoints = ["/", "/health", "/status", "/ws"]
        
        for endpoint in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}") as response:
                    print(f"{endpoint}: {response.status} - {await response.text()}")
            except Exception as e:
                print(f"{endpoint}: Error - {e}")

async def test_websocket_with_headers():
    """Test WebSocket with different headers"""
    print("\n🔍 Testing WebSocket with headers...\n")
    
    import websockets
    
    # Try with different origins and headers
    headers = {
        "Origin": "http://localhost:8000",
        "User-Agent": "RossNet-Client/1.0"
    }
    
    try:
        uri = "ws://127.0.0.1:8001"
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            print("✅ Connected with headers!")
    except Exception as e:
        print(f"❌ Failed with headers: {e}")
    
    # Try without any headers
    try:
        uri = "ws://127.0.0.1:8001"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected without headers!")
    except Exception as e:
        print(f"❌ Failed without headers: {e}")

async def check_mcp_router_logs():
    """Instructions to check MCP Router logs"""
    print("\n📋 Check MCP Router Terminal:\n")
    print("1. Look at the terminal where MCP Router is running")
    print("2. You should see error messages when connections are rejected")
    print("3. Look for messages about:")
    print("   - Authentication failures")
    print("   - CORS issues")
    print("   - Connection rejections")
    print("\nCommon issues:")
    print("- MCP Router might require specific agent IDs")
    print("- WebSocket subprotocols might be required")
    print("- Origin headers might be validated")

if __name__ == "__main__":
    asyncio.run(test_http_endpoints())
    asyncio.run(test_websocket_with_headers())
    check_mcp_router_logs()