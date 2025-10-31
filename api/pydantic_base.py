"""Legacy pydantic base - now imports from core.schemas.base
Maintained for backward compatibility.
"""

from core.schemas.base import APIResponse, AppModel, BaseSchema, ErrorResponse

# Re-export for backward compatibility
__all__ = ["APIResponse", "AppModel", "BaseSchema", "ErrorResponse"]
