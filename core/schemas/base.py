"""
Base Schema Classes for BabyShield API
Provides consistent Pydantic configuration across all models
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    Base schema class with consistent configuration for all BabyShield models.

    Key features:
    - protected_namespaces=() allows fields like 'model_number' without warnings
    - extra="forbid" prevents unexpected fields
    - populate_by_name=True allows field aliases
    """

    model_config = ConfigDict(
        protected_namespaces=(),  # allows fields like `model_number` without warnings
        extra="forbid",  # prevent unexpected fields
        populate_by_name=True,  # allows field aliases
        validate_assignment=True,  # validate on assignment
        use_enum_values=True,  # use enum values in serialization
    )


class AppModel(BaseSchema):
    """
    Application model base class.
    Inherits from BaseSchema with additional app-specific configuration.
    """

    model_config = ConfigDict(
        protected_namespaces=(),  # allows fields like `model_number` without warnings
        extra="forbid",  # prevent unexpected fields
        populate_by_name=True,  # allows field aliases
        validate_assignment=True,  # validate on assignment
        use_enum_values=True,  # use enum values in serialization
        # App-specific config
        json_schema_extra={"example": {"message": "This is an example response"}},
    )


class APIResponse(BaseSchema):
    """
    Standard API response wrapper.
    """

    ok: bool = True
    message: str | None = None
    data: Any | None = None
    error: dict[str, Any] | None = None

    model_config = ConfigDict(
        protected_namespaces=(),
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ok": True,
                "message": "Operation successful",
                "data": {"result": "example"},
            }
        },
    )


class ErrorResponse(BaseSchema):
    """
    Standard error response format.
    """

    ok: bool = False
    error: dict[str, Any]
    message: str | None = None

    model_config = ConfigDict(
        protected_namespaces=(),
        extra="forbid",
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "ok": False,
                "error": {"code": "VALIDATION_ERROR", "message": "Invalid input data"},
                "message": "Request validation failed",
            }
        },
    )
