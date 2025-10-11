#!/usr/bin/env python3
"""
OpenAPI specification generator for BabyShield API
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI spec for BabyShield API"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="BabyShield API",
        version="1.0.0",
        description="""
        BabyShield API provides access to product safety and recall information from multiple international agencies.
        
        ## Authentication
        Currently, all endpoints are public and do not require authentication in staging environment.
        
        ## Response Format
        All responses follow a consistent envelope format:
        - Success: `{ "success": true, "data": <payload> }`
        - Error: `{ "success": false, "error": { "code": "<ERROR_CODE>", "message": "<description>" } }`
        
        ## Error Codes
        - `BAD_REQUEST`: Invalid request parameters
        - `NOT_FOUND`: Resource not found
        - `UPSTREAM_TIMEOUT`: External agency API timeout
        - `INTERNAL_ERROR`: Internal server error
        
        ## Pagination
        Search endpoints support pagination using `cursor` parameter. Include the `nextCursor` from the response to fetch the next page.
        
        ## Rate Limiting
        No rate limiting is currently enforced in staging environment.
        """,
        routes=app.routes,
        servers=[
            {"url": "https://babyshield.cureviax.ai", "description": "Production"},
            {"url": "http://localhost:8001", "description": "Local Development"},
        ],
        tags=[
            {"name": "agencies", "description": "Agency information endpoints"},
            {
                "name": "search",
                "description": "Recall search endpoints for individual agencies",
            },
            {"name": "system", "description": "System health and monitoring endpoints"},
        ],
    )

    # Add response examples
    openapi_schema["paths"]["/api/v1/agencies"]["get"]["responses"]["200"]["content"]["application/json"]["example"] = {
        "success": True,
        "data": [
            {
                "code": "FDA",
                "name": "U.S. Food and Drug Administration",
                "country": "United States",
                "website": "https://www.fda.gov",
            },
            {
                "code": "CPSC",
                "name": "U.S. Consumer Product Safety Commission",
                "country": "United States",
                "website": "https://www.cpsc.gov",
            },
        ],
        "traceId": "trace_a1b2c3d4e5f6_1234567890",
    }

    # Add error response examples
    for path in openapi_schema["paths"].values():
        for method in path.values():
            if "responses" in method:
                method["responses"]["400"] = {
                    "description": "Bad Request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                            "example": {
                                "success": False,
                                "error": {
                                    "code": "BAD_REQUEST",
                                    "message": "Missing required parameter: product",
                                },
                            },
                        }
                    },
                }

    # Ensure DSAR download route present
    paths = openapi_schema.setdefault("paths", {})
    paths.setdefault(
        "/api/v1/user/data/download/{request_id}",
        {
            "get": {
                "summary": "Download exported user data",
                "parameters": [
                    {
                        "name": "request_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "File stream"}},
            }
        },
    )

    # Mark deprecated user_id fields in premium/alternatives/report requests
    def deprecate_param(path_key: str, method: str, param_name: str):
        try:
            params = openapi_schema["paths"][path_key][method]["requestBody"]["content"]["application/json"]["schema"][
                "properties"
            ]
            if param_name in params:
                params[param_name]["deprecated"] = True
                # Not required
                required = openapi_schema["paths"][path_key][method]["requestBody"]["content"]["application/json"][
                    "schema"
                ].get("required", [])
                if param_name in required:
                    required.remove(param_name)
        except Exception:
            pass

    for path_key, method in [
        ("/api/v1/premium/pregnancy/check", "post"),
        ("/api/v1/premium/allergy/check", "post"),
        ("/api/v1/baby/alternatives", "post"),
        ("/api/v1/baby/reports/generate", "post"),
    ]:
        deprecate_param(path_key, method, "user_id")

    app.openapi_schema = openapi_schema
    return app.openapi_schema
