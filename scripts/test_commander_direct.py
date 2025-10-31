# scripts/test_commander_direct.py

import asyncio

from core_infra.mcp_client_library.client import MCPClient
from core_infra.mcp_client_library.models import MCPMessage


async def message_handler(message: MCPMessage):
    print(f"Received: {message.mcp_header.message_type}")


async def test_commander_direct():
    """Test sending directly to commander"""

    client = MCPClient(
        agent_id="test_direct_client",
        agent_name="Test Direct Client",
        agent_type="test",
        mcp_server_url="ws://127.0.0.1:8001",
        message_handler=message_handler,
    )

    try:
        print("Connecting to MCP Router...")
        await client.connect()
        print("✅ Connected")

        # Check if commander is registered
        print("\nChecking for commander agent...")
        await client.send_message(
            payload={"capabilities": ["commander"]},
            message_type="DISCOVERY_QUERY",
            target_agent_id="discovery_agent_01",
        )

        await asyncio.sleep(2)

        # Send test message to commander
        print("\nSending test message to commander...")
        test_workflow_id = "test_direct_123"

        await client.send_message(
            payload={
                "user_goal": "Test direct message",
                "task_type": "prior_authorization",
                "parameters": {
                    "patient_id": "direct-test",
                    "drug_name": "TestDrug",
                    "insurer_id": "TEST",
                },
            },
            message_type="PROCESS_USER_REQUEST",
            target_agent_id="commander_agent_01",
            correlation_id=test_workflow_id,
        )

        print(f"✅ Sent test message with workflow ID: {test_workflow_id}")

        await asyncio.sleep(2)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_commander_direct())
