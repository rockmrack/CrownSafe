# core_infra/__init__.py
"""Core Infrastructure Package for BabyShield Backend
This package provides essential infrastructure components.
"""

# Make submodules available for imports
# This allows: from core_infra.cache_manager import get_cache_stats
from . import cache_manager, database, sqlite_jsonb_shim

# Optional modules - import if available
# Only add to __all__ if successfully imported
optional_modules = []

# Explicitly import optional modules if available
try:
    from . import async_optimizer

    optional_modules.append("async_optimizer")
except ImportError:
    async_optimizer = None

try:
    from . import connection_pool_optimizer

    optional_modules.append("connection_pool_optimizer")
except ImportError:
    connection_pool_optimizer = None

try:
    from . import smart_cache_warmer

    optional_modules.append("smart_cache_warmer")
except ImportError:
    smart_cache_warmer = None

try:
    from . import mobile_hot_path

    optional_modules.append("mobile_hot_path")
except ImportError:
    mobile_hot_path = None
# Only export modules that actually exist
__all__ = [
    "cache_manager",
    "database",
    "sqlite_jsonb_shim",
] + optional_modules
