"""Health and System Endpoints for App Store Readiness"""

import os
import platform
from datetime import datetime, timezone, UTC
from typing import Any

from fastapi import APIRouter, Request, Response

router = APIRouter(prefix="/api/v1", tags=["health"])

API_VERSION = "1.2.0"


@router.get("/healthz")
async def healthz(request: Request, response: Response) -> dict[str, Any]:
    """Health check endpoint for monitoring
    Returns 200 if service is healthy
    """
    # Get once per process, then reuse
    v = getattr(request.app.state, "_openapi_version", None)
    if not v:
        try:
            v = request.app.openapi().get("info", {}).get("version", "unknown")
        except Exception:
            v = "unknown"
        request.app.state._openapi_version = v

    response.headers["X-API-Version"] = v

    return {
        "ok": True,
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": API_VERSION,
        "service": "babyshield-api",
    }


@router.get("/version")
async def version_info(request: Request, response: Response) -> dict[str, Any]:
    """Get API version information"""
    # Get once per process, then reuse
    v = getattr(request.app.state, "_openapi_version", None)
    if not v:
        try:
            v = request.app.openapi().get("info", {}).get("version", "unknown")
        except Exception:
            v = "unknown"
        request.app.state._openapi_version = v

    response.headers["X-API-Version"] = v

    return {
        "ok": True,
        "api_version": API_VERSION,
        "python_version": platform.python_version(),
        "environment": os.getenv("ENVIRONMENT", "production"),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/docs")
async def api_docs_redirect():
    """Redirect to Swagger UI documentation"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/docs", status_code=302)


@router.get("/redoc")
async def api_redoc_redirect():
    """Redirect to ReDoc documentation"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/redoc", status_code=302)


@router.get("/openapi.json")
async def api_openapi_redirect():
    """Redirect to OpenAPI JSON schema"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/openapi.json", status_code=302)
