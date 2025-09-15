"""
API versioning system for BabyShield
Enables backward compatibility and smooth transitions
"""

from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime
import logging
import warnings

logger = logging.getLogger(__name__)

class APIVersion:
    """
    Represents an API version
    """
    
    def __init__(self, version: str, deprecated: bool = False, sunset_date: str = None):
        self.version = version
        self.deprecated = deprecated
        self.sunset_date = sunset_date
        self.major, self.minor, self.patch = self._parse_version(version)
    
    def _parse_version(self, version: str) -> tuple:
        """Parse version string like 'v1.2.3' into components"""
        version = version.lstrip('v')
        parts = version.split('.')
        
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        
        return major, minor, patch
    
    def is_compatible_with(self, other: 'APIVersion') -> bool:
        """Check if this version is compatible with another"""
        # Same major version = compatible
        return self.major == other.major
    
    def __str__(self):
        return f"v{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class VersionedAPI:
    """
    Manages API versioning
    """
    
    SUPPORTED_VERSIONS = {
        "v1": APIVersion("v1.0.0", deprecated=True, sunset_date="2025-01-01"),
        "v2": APIVersion("v2.0.0", deprecated=False),
        "v3": APIVersion("v3.0.0", deprecated=False),  # Latest
    }
    
    CURRENT_VERSION = "v3"
    DEFAULT_VERSION = "v2"  # For backward compatibility
    
    @classmethod
    def get_version_from_request(cls, request: Request) -> str:
        """
        Extract API version from request
        Priority: URL path > Header > Query param > Default
        """
        # 1. Check URL path (e.g., /api/v2/...)
        path = request.url.path
        for version in cls.SUPPORTED_VERSIONS:
            if f"/api/{version}/" in path:
                return version
        
        # 2. Check header (API-Version or X-API-Version)
        api_version = request.headers.get("API-Version") or \
                     request.headers.get("X-API-Version")
        if api_version and api_version in cls.SUPPORTED_VERSIONS:
            return api_version
        
        # 3. Check query parameter
        api_version = request.query_params.get("api_version")
        if api_version and api_version in cls.SUPPORTED_VERSIONS:
            return api_version
        
        # 4. Default version
        return cls.DEFAULT_VERSION
    
    @classmethod
    def validate_version(cls, version: str) -> bool:
        """Check if version is supported"""
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def get_deprecation_warning(cls, version: str) -> Optional[Dict[str, str]]:
        """Get deprecation warning for a version"""
        ver = cls.SUPPORTED_VERSIONS.get(version)
        if ver and ver.deprecated:
            return {
                "warning": f"API version {version} is deprecated",
                "sunset_date": ver.sunset_date,
                "recommended_version": cls.CURRENT_VERSION
            }
        return None


def versioned_endpoint(
    versions: list = None,
    deprecated_in: str = None,
    removed_in: str = None
):
    """
    Decorator for versioned endpoints
    
    Usage:
        @versioned_endpoint(versions=["v1", "v2"])
        async def get_users():
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get API version from request
            version = VersionedAPI.get_version_from_request(request)
            
            # Check if endpoint supports this version
            if versions and version not in versions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint not available in API {version}"
                )
            
            # Check if removed
            if removed_in and version >= removed_in:
                raise HTTPException(
                    status_code=410,  # Gone
                    detail=f"Endpoint removed in API {removed_in}"
                )
            
            # Add deprecation warning
            response = await func(request, *args, **kwargs)
            
            if deprecated_in and version >= deprecated_in:
                if isinstance(response, dict):
                    response["_deprecation_warning"] = {
                        "message": f"This endpoint is deprecated in {deprecated_in}",
                        "removed_in": removed_in
                    }
            
            return response
        
        return wrapper
    return decorator


class VersionedRouter:
    """
    Router that handles multiple API versions
    """
    
    def __init__(self):
        self.routers = {}
        for version in VersionedAPI.SUPPORTED_VERSIONS:
            self.routers[version] = APIRouter(prefix=f"/api/{version}")
    
    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: list,
        versions: list = None
    ):
        """Add route to specific versions"""
        versions = versions or list(self.routers.keys())
        
        for version in versions:
            if version in self.routers:
                router = self.routers[version]
                for method in methods:
                    router.add_api_route(
                        path,
                        endpoint,
                        methods=[method],
                        tags=[f"{version}"]
                    )
    
    def get_routers(self):
        """Get all version routers"""
        return list(self.routers.values())


# Version-specific response transformers
class ResponseTransformer:
    """
    Transform responses based on API version
    """
    
    @staticmethod
    def transform_v1_to_v2(data: Dict) -> Dict:
        """Transform v1 response to v2 format"""
        # Example transformation
        if "user_name" in data:
            data["username"] = data.pop("user_name")
        if "created" in data:
            data["created_at"] = data.pop("created")
        return data
    
    @staticmethod
    def transform_v2_to_v3(data: Dict) -> Dict:
        """Transform v2 response to v3 format"""
        # Example transformation
        if "id" in data:
            data["uuid"] = f"uuid_{data['id']}"
        if "status" in data and data["status"] == "active":
            data["status"] = {"code": 1, "label": "active"}
        return data
    
    @classmethod
    def transform_response(cls, data: Dict, from_version: str, to_version: str) -> Dict:
        """Transform response between versions"""
        if from_version == to_version:
            return data
        
        # Apply transformations in sequence
        if from_version == "v1" and to_version == "v2":
            data = cls.transform_v1_to_v2(data)
        elif from_version == "v1" and to_version == "v3":
            data = cls.transform_v1_to_v2(data)
            data = cls.transform_v2_to_v3(data)
        elif from_version == "v2" and to_version == "v3":
            data = cls.transform_v2_to_v3(data)
        
        return data


# Middleware for API versioning
async def api_version_middleware(request: Request, call_next):
    """
    Middleware to handle API versioning
    """
    # Get requested version
    version = VersionedAPI.get_version_from_request(request)
    
    # Validate version
    if not VersionedAPI.validate_version(version):
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported API version: {version}",
                "supported_versions": list(VersionedAPI.SUPPORTED_VERSIONS.keys()),
                "current_version": VersionedAPI.CURRENT_VERSION
            }
        )
    
    # Store version in request state
    request.state.api_version = version
    
    # Process request
    response = await call_next(request)
    
    # Resolve API version from the OpenAPI spec once, then reuse
    v = getattr(request.app.state, "_openapi_version", None)
    if not v:
        try:
            v = request.app.openapi().get("info", {}).get("version", "unknown")
        except Exception:
            v = "unknown"
        request.app.state._openapi_version = v
    
    # Add version headers
    response.headers["X-API-Version"] = v
    response.headers["X-API-Deprecated"] = "false"
    
    # Add deprecation warning if needed
    warning = VersionedAPI.get_deprecation_warning(version)
    if warning:
        response.headers["X-API-Deprecated"] = "true"
        response.headers["X-API-Sunset"] = warning["sunset_date"]
        response.headers["Warning"] = f'299 - "{warning["warning"]}"'
    
    return response


# Backward compatibility helpers
class BackwardCompatibility:
    """
    Helpers for maintaining backward compatibility
    """
    
    @staticmethod
    def deprecated_field(old_name: str, new_name: str):
        """
        Mark a field as deprecated
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                
                # Add both old and new field names
                if isinstance(result, dict) and new_name in result:
                    result[old_name] = result[new_name]
                    result["_field_deprecations"] = {
                        old_name: {
                            "new_name": new_name,
                            "message": f"Field '{old_name}' is deprecated, use '{new_name}'"
                        }
                    }
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def removed_endpoint(version: str, alternative: str = None):
        """
        Mark an endpoint as removed
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                message = f"This endpoint was removed in {version}"
                if alternative:
                    message += f". Use {alternative} instead"
                
                raise HTTPException(
                    status_code=410,  # Gone
                    detail=message
                )
            return wrapper
        return decorator


# Version migration helpers
class VersionMigration:
    """
    Help users migrate between API versions
    """
    
    @staticmethod
    def generate_migration_guide(from_version: str, to_version: str) -> Dict:
        """
        Generate migration guide between versions
        """
        guide = {
            "from_version": from_version,
            "to_version": to_version,
            "changes": []
        }
        
        if from_version == "v1" and to_version == "v2":
            guide["changes"] = [
                {
                    "type": "field_rename",
                    "old": "user_name",
                    "new": "username"
                },
                {
                    "type": "endpoint_change",
                    "old": "/api/v1/get_user",
                    "new": "/api/v2/users/{id}"
                },
                {
                    "type": "response_format",
                    "description": "Error responses now include error codes"
                }
            ]
        
        return guide


# Example usage
"""
# In your main app:

from core_infra.api_versioning import (
    VersionedRouter, 
    api_version_middleware,
    versioned_endpoint
)

app = FastAPI()

# Add versioning middleware
app.middleware("http")(api_version_middleware)

# Create versioned routers
versioned_router = VersionedRouter()

# Add endpoints to specific versions
@versioned_endpoint(versions=["v2", "v3"])
async def get_users(request: Request):
    # Version-specific logic
    if request.state.api_version == "v2":
        return {"users": [...]}
    else:  # v3
        return {"data": {"users": [...]}, "meta": {...}}

# Register routers
for router in versioned_router.get_routers():
    app.include_router(router)

# Migration endpoint
@app.get("/api/migration-guide")
async def get_migration_guide(from_version: str, to_version: str):
    return VersionMigration.generate_migration_guide(from_version, to_version)
"""
