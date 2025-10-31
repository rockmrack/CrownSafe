from typing import Any, Generic, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: dict[str, Any] | None = None


def ok(data: Any = None) -> dict[str, Any]:
    return {"success": True, "data": data}


def fail(
    message: str,
    code: str = "BAD_REQUEST",
    status: int = 400,
    extra: dict[str, Any] | None = None,
):
    payload: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
    }
    if extra:
        payload["error"].update(extra)
    raise HTTPException(status_code=status, detail=payload)
