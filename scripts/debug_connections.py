# scripts/debug_connections.py

import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_mcp_connection():
    """Test if we can connect to MCP Router and check registered agents"""
    
    print("\n🔍 Testing MCP Router Connection...\n")
    
    try:
        # Connect to MCP Router
        uri = "ws://127.0.0.1:8001"
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to MCP Router")
            
            # Send a discovery query to see what agents are available
            test_message = {
                "mcp_header": {
                    "message_type": "DISCOVERY_QUERY",
                    "sender_id": "debug_client",
                    "correlation_id": "debug_" + str(datetime.now().timestamp())
                },
                "payload": {
                    "capabilities": ["commander"]
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent discovery query for commander capability")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print("📥 Received response:")
                print(json.dumps(response_data, indent=2))
                
                # Check if commander agent is registered
                if response_data.get("mcp_header", {}).get("message_type") == "DISCOVERY_RESPONSE":
                    results = response_data.get("payload", {}).get("results", [])
                    if results:
                        print("\n✅ Found registered agents:")
                        for agent in results:
                            print(f"   - {agent.get('agent_id')} with capabilities: {agent.get('capabilities')}")
                    else:
                        print("\n❌ No commander agent found! Make sure commander_agent is running and connected.")
                        
            except asyncio.TimeoutError:
                print("❌ No response received - discovery service might not be running")
                
    except Exception as e:
        print(f"❌ Could not connect to MCP Router: {e}")
        print("   Make sure MCP Router is running on port 8001")

async def test_workflow_submission():
    """Test submitting a workflow directly via WebSocket"""
    
    print("\n🔍 Testing Direct Workflow Submission...\n")
    
    try:
        uri = "ws://127.0.0.1:8001"
        async with websockets.connect(uri) as websocket:
            
            # Register as a test client
            register_msg = {
                "mcp_header": {
                    "message_type": "REGISTER",
                    "sender_id": "test_api_client"
                },
                "payload": {
                    "agent_id": "test_api_client",
                    "capabilities": ["api_gateway"]
                }
            }
            
            await websocket.send(json.dumps(register_msg))
            print("📤 Registered as test client")
            
            # Send workflow request
            workflow_msg = {
                "mcp_header": {
                    "message_type": "PROCESS_USER_REQUEST",
                    "sender_id": "test_api_client",
                    "target_agent_id": "commander_agent_01",
                    "correlation_id": "test_workflow_123"
                },
                "payload": {
                    "user_goal": "Test prior authorization",
                    "task_type": "prior_authorization",
                    "parameters": {
                        "patient_id": "test-001",
                        "drug_name": "TestDrug",
                        "insurer_id": "TEST"
                    }
                }
            }
            
            await websocket.send(json.dumps(workflow_msg))
            print("📤 Sent workflow request to commander")
            
            # Listen for responses
            print("\n📥 Listening for responses (10 seconds)...")
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < 10:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    msg_type = response_data.get("mcp_header", {}).get("message_type")
                    sender = response_data.get("mcp_header", {}).get("sender_id")
                    print(f"   Received: {msg_type} from {sender}")
                    
                    if msg_type == "ERROR":
                        print(f"   ❌ Error: {response_data.get('payload', {}).get('error_message')}")
                        
                except asyncio.TimeoutError:
                    continue
                    
    except Exception as e:
        print(f"❌ Error during workflow submission: {e}")

async def check_agent_registrations():
    """Check which agents are registered"""
    
    print("\n🔍 Checking Agent Registrations...\n")
    
    required_agents = [
        ("commander_agent_01", ["commander"]),
        ("planner_agent_01", ["planning"]),
        ("router_agent_01", ["routing"]),
        ("discovery_agent_01", ["discovery"])
    ]
    
    try:
        uri = "ws://127.0.0.1:8001"
        async with websockets.connect(uri) as websocket:
            
            for agent_id, capabilities in required_agents:
                # Query for each capability
                query_msg = {
                    "mcp_header": {
                        "message_type": "DISCOVERY_QUERY",
                        "sender_id": "debug_client",
                        "correlation_id": f"check_{agent_id}"
                    },
                    "payload": {
                        "capabilities": capabilities
                    }
                }
                
                await websocket.send(json.dumps(query_msg))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("mcp_header", {}).get("message_type") == "DISCOVERY_RESPONSE":
                        results = response_data.get("payload", {}).get("results", [])
                        if results:
                            print(f"✅ {agent_id}: FOUND")
                        else:
                            print(f"❌ {agent_id}: NOT FOUND - Make sure this agent is running")
                            
                except asyncio.TimeoutError:
                    print(f"❌ {agent_id}: NO RESPONSE")
                    
    except Exception as e:
        print(f"❌ Error checking registrations: {e}")

async def main():
    print("="*70)
    print("🔧 RossNet Connection Debugger")
    print("="*70)
    
    # Test MCP connection
    await test_mcp_connection()
    
    # Check agent registrations
    await check_agent_registrations()
    
    # Test workflow submission
    await test_workflow_submission()
    
    print("\n" + "="*70)
    print("Debug complete. Check the output above for issues.")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())