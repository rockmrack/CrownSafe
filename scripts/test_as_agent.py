# scripts/test_as_agent.py

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from core_infra.mcp_client_library.client import MCPClient

async def test_agent_connection():
    """Test connecting as an agent using the MCP Client"""
    print("\n🔍 Testing connection using MCP Client...\n")
    
    # Create a test agent
    test_agent_id = "test_agent_debug"
    mcp_client = MCPClient(
        agent_id=test_agent_id,
        server_url="ws://127.0.0.1:8001"
    )
    
    try:
        print("📡 Connecting to MCP Router...")
        await mcp_client.connect()
        print("✅ Connected successfully!")
        
        # Try to send a test message
        await mcp_client.send_message(
            payload={"test": "message"},
            message_type="TEST",
            target_agent_id="test_target"
        )
        print("✅ Sent test message!")
        
        # Disconnect
        await mcp_client.disconnect()
        print("✅ Disconnected cleanly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_connection())