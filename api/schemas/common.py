from typing import Any, Dict, Generic, Optional, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None


def ok(data: Any = None) -> Dict[str, Any]:
    return {"success": True, "data": data}


def fail(
    message: str,
    code: str = "BAD_REQUEST",
    status: int = 400,
    extra: Optional[Dict[str, Any]] = None,
):
    payload: Dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
    }
    if extra:
        payload["error"].update(extra)
    raise HTTPException(status_code=status, detail=payload)
