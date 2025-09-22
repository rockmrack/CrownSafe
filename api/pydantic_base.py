"""
Legacy pydantic base - now imports from core.schemas.base
Maintained for backward compatibility
"""

from core.schemas.base import AppModel, BaseSchema, APIResponse, ErrorResponse

# Re-export for backward compatibility
__all__ = ["AppModel", "BaseSchema", "APIResponse", "ErrorResponse"]
