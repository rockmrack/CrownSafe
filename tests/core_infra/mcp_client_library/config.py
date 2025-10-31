# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_client_library\config.py

import logging

# Configure logging for the client library
logger = logging.getLogger("MCPClientLibrary")


class Settings:
    """Configuration settings for the MCP Client Library"""

    # Connection settings
    DEFAULT_ROUTER_URL = "ws://127.0.0.1:8001/ws/{agent_id}"
    HEARTBEAT_INTERVAL = 30.0  # seconds
    RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 5.0  # seconds

    # Message settings
    DEFAULT_TIMEOUT = 30.0  # seconds

    # Add any other settings as needed


# Create a global settings instance
settings = Settings()
