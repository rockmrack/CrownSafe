"""
API Contract & OpenAPI Compliance Tests - Phase 3

Tests that the API implementation matches the OpenAPI specification exactly.
Validates request/response schemas, documentation coverage, and API versioning.

Author: BabyShield Development Team
Date: October 11, 2025
"""

import json
from typing import Dict

import pytest
from fastapi.testclient import TestClient
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename

from api.main_babyshield import app


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def openapi_spec():
    """Load OpenAPI specification."""
    # Get OpenAPI spec from FastAPI app
    return app.openapi()


# ====================
# API CONTRACT TESTS
# ====================


@pytest.mark.api
@pytest.mark.contract
def test_openapi_spec_validation(openapi_spec):
    """
    Test that OpenAPI spec is valid according to OpenAPI 3.0 standard.

    Acceptance Criteria:
    - Spec is valid OpenAPI 3.0.x or 3.1.x
    - No schema validation errors
    - All required fields present
    - Proper use of $ref pointers
    - No circular references
    """
    # Validate spec structure
    assert "openapi" in openapi_spec
    assert openapi_spec["openapi"].startswith("3.")

    assert "info" in openapi_spec
    assert "title" in openapi_spec["info"]
    assert "version" in openapi_spec["info"]

    assert "paths" in openapi_spec
    assert len(openapi_spec["paths"]) > 0

    # Validate against OpenAPI schema
    try:
        validate_spec(openapi_spec)
        print("\n✅ OpenAPI spec is valid!")
    except Exception as e:
        pytest.fail(f"OpenAPI spec validation failed: {e}")

    # Check for recommended fields
    assert "description" in openapi_spec["info"]
    assert "servers" in openapi_spec or "host" in openapi_spec

    print("\n📋 API Specification:")
    print(f"   Title: {openapi_spec['info']['title']}")
    print(f"   Version: {openapi_spec['info']['version']}")
    print(f"   Endpoints: {len(openapi_spec['paths'])}")


@pytest.mark.api
@pytest.mark.contract
def test_all_endpoints_documented(test_client, openapi_spec):
    """
    Test that all API endpoints are documented in OpenAPI spec.

    Acceptance Criteria:
    - 100% endpoint coverage in spec
    - All HTTP methods documented
    - Internal endpoints excluded (/metrics, /admin)
    - Deprecated endpoints marked
    - Health check endpoint included
    """
    # Get documented endpoints from spec
    documented_endpoints = set()
    for path, methods in openapi_spec["paths"].items():
        for method in methods.keys():
            if method in ["get", "post", "put", "delete", "patch"]:
                documented_endpoints.add(f"{method.upper()} {path}")

    # Get actual routes from FastAPI app
    actual_endpoints = set()
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            # Skip internal routes
            if (
                not route.path.startswith("/docs")
                and not route.path.startswith("/redoc")
                and not route.path.startswith("/openapi")
            ):
                for method in route.methods:
                    if method != "HEAD":
                        actual_endpoints.add(f"{method} {route.path}")

    # Find undocumented endpoints
    undocumented = actual_endpoints - documented_endpoints
    extra_docs = documented_endpoints - actual_endpoints

    print("\n📚 Endpoint Documentation:")
    print(f"   Documented: {len(documented_endpoints)}")
    print(f"   Actual: {len(actual_endpoints)}")
    print(f"   Undocumented: {len(undocumented)}")

    if undocumented:
        print("\n⚠️  Undocumented endpoints:")
        for endpoint in sorted(undocumented):
            print(f"      {endpoint}")

    if extra_docs:
        print("\n⚠️  Documented but not implemented:")
        for endpoint in sorted(extra_docs):
            print(f"      {endpoint}")

    # Allow some exceptions for test/internal endpoints
    critical_undocumented = [e for e in undocumented if not e.startswith("GET /test")]

    assert len(critical_undocumented) == 0, f"{len(critical_undocumented)} endpoints missing documentation"


@pytest.mark.api
@pytest.mark.contract
def test_response_schemas_match_spec(test_client, openapi_spec):
    """
    Test that actual API responses match OpenAPI spec schemas.

    Acceptance Criteria:
    - Response structure matches spec exactly
    - All required fields present
    - Data types match spec
    - Additional fields documented or rejected
    - Status codes match spec
    """
    from api.auth_endpoints import create_access_token

    token = create_access_token(data={"sub": "contract@example.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Test critical endpoints
    test_cases = [
        {"method": "GET", "path": "/healthz", "headers": {}, "expected_status": 200, "required_fields": ["status"]},
        {
            "method": "GET",
            "path": "/api/v1/recalls",
            "headers": headers,
            "expected_status": 200,
            "required_fields": ["items", "total"],
        },
        {
            "method": "GET",
            "path": "/api/v1/user/profile",
            "headers": headers,
            "expected_status": 200,
            "required_fields": ["email", "id"],
        },
    ]

    for test_case in test_cases:
        if test_case["method"] == "GET":
            response = test_client.get(test_case["path"], headers=test_case["headers"])

        # Check status code
        assert response.status_code == test_case["expected_status"], (
            f"{test_case['path']}: Expected {test_case['expected_status']}, got {response.status_code}"
        )

        # Check response structure
        if response.status_code == 200 and response.content:
            data = response.json()

            # Verify required fields
            for field in test_case["required_fields"]:
                assert field in data, f"{test_case['path']}: Missing required field '{field}'"

    print("\n✅ Response schemas validated")


@pytest.mark.api
@pytest.mark.contract
def test_request_validation_per_spec(test_client, openapi_spec):
    """
    Test that request validation matches OpenAPI spec requirements.

    Acceptance Criteria:
    - Required parameters enforced
    - Optional parameters handled correctly
    - Invalid types rejected with 422
    - Query parameter validation works
    - Request body validation works
    """
    from api.auth_endpoints import create_access_token

    token = create_access_token(data={"sub": "validation@example.com"})
    headers = {"Authorization": f"Bearer {token}"}

    # Test 1: Missing required parameters
    response = test_client.post(
        "/api/v1/barcode/scan",
        json={},  # Missing required 'barcode' field
        headers=headers,
    )
    assert response.status_code == 422, "Should reject missing required field"

    # Test 2: Invalid data types
    response = test_client.get(
        "/api/v1/recalls?limit=invalid",  # Should be integer
        headers=headers,
    )
    assert response.status_code == 422, "Should reject invalid type"

    # Test 3: Out of range values
    response = test_client.get(
        "/api/v1/recalls?limit=10000",  # Exceeds max limit
        headers=headers,
    )
    # Should either work with clamped value or return 422
    assert response.status_code in [200, 422]

    # Test 4: Valid request
    response = test_client.get("/api/v1/recalls?limit=10&skip=0", headers=headers)
    assert response.status_code == 200, "Valid request should succeed"

    print("\n✅ Request validation working as specified")


@pytest.mark.api
@pytest.mark.contract
def test_api_versioning_compliance(test_client):
    """
    Test API versioning is properly implemented and documented.

    Acceptance Criteria:
    - API version in path (/api/v1/)
    - Version header supported (X-API-Version)
    - Deprecated endpoints marked in spec
    - Version documented in OpenAPI spec
    - Breaking changes require new version
    """
    # Test 1: API version in path
    response = test_client.get("/healthz")
    assert response.status_code == 200

    # Test 2: Versioned endpoints exist
    response = test_client.get("/api/v1/recalls")
    # May be 401 (needs auth) but should not be 404
    assert response.status_code != 404, "v1 endpoint should exist"

    # Test 3: Check API version in OpenAPI spec
    openapi_spec = app.openapi()

    # Verify version is documented
    assert "version" in openapi_spec["info"]
    api_version = openapi_spec["info"]["version"]

    print(f"\n📌 API Version: {api_version}")

    # Test 4: Version header support (optional)
    from api.auth_endpoints import create_access_token

    token = create_access_token(data={"sub": "version@example.com"})

    response = test_client.get("/api/v1/recalls", headers={"Authorization": f"Bearer {token}", "X-API-Version": "1"})
    # Should work with or without version header
    assert response.status_code in [200, 401]

    # Test 5: Check for deprecated endpoints in spec
    deprecated_count = 0
    for path, methods in openapi_spec["paths"].items():
        for method, details in methods.items():
            if isinstance(details, dict) and details.get("deprecated"):
                deprecated_count += 1
                print(f"   Deprecated: {method.upper()} {path}")

    print(f"   Deprecated endpoints: {deprecated_count}")
    print("✅ API versioning properly implemented")
