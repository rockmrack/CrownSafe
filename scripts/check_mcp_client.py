# scripts/check_mcp_client.py

import sys
import os

sys.path.insert(0, os.path.abspath("."))

# Import and inspect MCPClient
try:
    from core_infra.mcp_client_library.client import MCPClient
    import inspect

    print("MCPClient constructor signature:")
    print(inspect.signature(MCPClient.__init__))

    # Try to see the docstring
    print("\nMCPClient docstring:")
    print(MCPClient.__doc__)

    # Check if there's a connect method
    if hasattr(MCPClient, "connect"):
        print("\nConnect method signature:")
        print(inspect.signature(MCPClient.connect))

except Exception as e:
    print(f"Error: {e}")
