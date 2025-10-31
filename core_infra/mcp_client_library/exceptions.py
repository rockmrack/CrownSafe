# C:\Users\rossd\Downloads\RossNetAgents\core_infra\mcp_client_library\exceptions.py

"""Custom exceptions for the MCP Client Library."""


class MCPClientError(Exception):
    """Base exception class for MCP Client Library errors."""



class MCPError(MCPClientError):  # <<< ADDED THIS CLASS
    """Generic error raised for MCP client operations that don't fit a more specific category."""



class MCPConnectionError(MCPClientError):
    """Raised when a connection to the MCP Router cannot be established or is lost."""



class NotConnectedError(MCPClientError):
    """Raised when trying to send a message while not connected to the MCP Router."""



class MCPMessageError(MCPClientError):
    """Raised when a message has invalid format or content."""



class AuthenticationError(MCPClientError):
    """Raised when authentication with the MCP Router fails."""



class TimeoutError(MCPClientError):  # Note: This might conflict with built-in TimeoutError if not careful with imports
    """Raised when an operation times out."""



class DiscoveryError(MCPClientError):
    """Raised when there's an error during discovery operations."""



class TaskError(MCPClientError):
    """Raised when there's an error during task execution."""



# Aliases for backward compatibility or common usage
# ConnectionError = MCPConnectionError # Be cautious with aliasing built-in names
# MessageFormatError = MCPMessageError
