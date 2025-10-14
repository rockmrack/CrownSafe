from fastapi import APIRouter, HTTPException, Request
from typing import Optional, Any

router = APIRouter(prefix="/api/v1", tags=["account-legacy"])


@router.post("/user/data/delete", include_in_schema=False)
async def legacy_delete(request: Request, body: Optional[Any] = None):
    """
    Legacy endpoint - returns 410 Gone to force client migration.
    Accepts any request format to avoid validation errors.
    """
    # Explicit deprecation to force client upgrade
    raise HTTPException(
        status_code=410, detail="Endpoint removed. Use DELETE /api/v1/account"
    )
