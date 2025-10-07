import pytest
import sys

def pytest_collection_modifyitems(config, items):
    """Skip tests that require unavailable dependencies"""
    skip_locust = pytest.mark.skip(reason="locust not installed")
    skip_mcp = pytest.mark.skip(reason="mcp_client_library not available")
    
    for item in items:
        # Skip performance tests if locust not available
        if "performance" in item.keywords:
            try:
                import locust
            except ImportError:
                item.add_marker(skip_locust)
        
        # Skip tests that need mcp_client_library
        if "mcp" in str(item.fspath).lower():
            try:
                from core_infra.mcp_client_library import client
            except ImportError:
                item.add_marker(skip_mcp)