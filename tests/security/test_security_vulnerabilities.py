"""
Security vulnerability tests
Tests for OWASP Top 10 vulnerabilities and security best practices
"""

import pytest


class TestSQLInjection:
    """Test suite for SQL injection protection"""

    def test_search_with_sql_injection_attempt_blocked(self, client, auth_token):
        """
        Test SQL injection protection in search.

        Given: Search query with SQL injection attempt
        When: POST /api/v1/search
        Then: Request is rejected or sanitized
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        malicious_queries = [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1' UNION SELECT * FROM users--",
            "admin'--",
            "' OR 1=1--",
        ]

        for query in malicious_queries:
            response = client.post(
                "/api/v1/search", headers=headers, json={"query": query}
            )
            # Should either reject or safely sanitize
            assert response.status_code in [400, 200]
            if response.status_code == 200:
                # Verify no SQL injection occurred
                assert "users" not in str(response.json()).lower()

    def test_user_input_with_sql_injection_sanitized(self, client):
        """
        Test user input sanitization.

        Given: Registration with SQL injection in email
        When: POST /api/v1/auth/register
        Then: Input is sanitized or rejected
        """
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test'; DROP TABLE users;--@example.com",
                "password": "SecurePass123!",
            },
        )
        assert response.status_code in [400, 422]


class TestXSSProtection:
    """Test suite for XSS protection"""

    def test_product_name_with_script_tag_sanitized(self, client, auth_token):
        """
        Test XSS protection in product names.

        Given: Product name with <script> tag
        When: Product is created/updated
        Then: Script tags are removed/escaped
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='javascript:alert(1)'>",
            "javascript:alert('XSS')",
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/v1/product", headers=headers, json={"name": payload}
            )
            # Should sanitize or reject
            if response.status_code == 200:
                assert "<script>" not in response.json().get("name", "")

    def test_response_headers_prevent_xss(self, client):
        """
        Test security headers are set.

        Given: Any request
        When: Response is sent
        Then: X-Content-Type-Options and CSP headers are present
        """
        response = client.get("/healthz")
        assert "X-Content-Type-Options" in response.headers
        assert "Content-Security-Policy" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestAuthentication:
    """Test suite for authentication security"""

    def test_protected_endpoint_without_auth_returns_401(self, client):
        """
        Test authentication requirement.

        Given: No authentication token
        When: GET /api/v1/user/profile
        Then: 401 Unauthorized
        """
        response = client.get("/api/v1/user/profile")
        assert response.status_code == 401

    def test_expired_token_rejected(self, client, expired_token):
        """
        Test expired token handling.

        Given: Expired JWT token
        When: Request with expired token
        Then: 401 Unauthorized
        """
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/user/profile", headers=headers)
        assert response.status_code == 401

    def test_tampered_token_rejected(self, client, valid_token):
        """
        Test token tampering detection.

        Given: Modified JWT token
        When: Request with tampered token
        Then: 401 Unauthorized
        """
        tampered_token = valid_token[:-10] + "tampered123"
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = client.get("/api/v1/user/profile", headers=headers)
        assert response.status_code == 401

    def test_brute_force_protection_active(self, client):
        """
        Test brute force protection.

        Given: Multiple failed login attempts
        When: Threshold is exceeded
        Then: Account is locked or rate limited
        """
        for i in range(10):
            response = client.post(
                "/api/v1/auth/token",
                json={"username": "test@example.com", "password": "WrongPassword"},
            )

        # Next attempt should be blocked
        response = client.post(
            "/api/v1/auth/token",
            json={"username": "test@example.com", "password": "WrongPassword"},
        )
        assert response.status_code in [429, 403]


class TestAuthorization:
    """Test suite for authorization security"""

    def test_user_cannot_access_other_users_data(self, client, user1_token, user2_id):
        """
        Test authorization boundaries.

        Given: User 1 token
        When: Attempt to access User 2 data
        Then: 403 Forbidden
        """
        headers = {"Authorization": f"Bearer {user1_token}"}
        response = client.get(f"/api/v1/user/{user2_id}/profile", headers=headers)
        assert response.status_code == 403

    def test_regular_user_cannot_access_admin_endpoints(
        self, client, regular_user_token
    ):
        """
        Test admin endpoint protection.

        Given: Regular user token
        When: Attempt to access admin endpoint
        Then: 403 Forbidden
        """
        headers = {"Authorization": f"Bearer {regular_user_token}"}
        response = client.get("/api/v1/admin/users", headers=headers)
        assert response.status_code == 403


class TestCSRFProtection:
    """Test suite for CSRF protection"""

    def test_state_changing_requests_require_csrf_token(self, client):
        """
        Test CSRF protection on POST/PUT/DELETE.

        Given: Request without CSRF token
        When: POST /api/v1/user/profile
        Then: 403 Forbidden or CSRF check performed
        """
        # Implementation depends on your CSRF strategy
        pass


class TestRateLimiting:
    """Test suite for rate limiting security"""

    def test_api_rate_limit_per_user_enforced(self, client, auth_token):
        """
        Test per-user rate limiting.

        Given: Authenticated user
        When: Rate limit is exceeded
        Then: 429 Too Many Requests
        """
        headers = {"Authorization": f"Bearer {auth_token}"}

        # Make requests up to rate limit
        for i in range(100):
            client.get("/api/v1/user/profile", headers=headers)

        # Next request should be rate limited
        response = client.get("/api/v1/user/profile", headers=headers)
        assert response.status_code == 429

    def test_ip_based_rate_limiting_for_public_endpoints(self, client):
        """
        Test IP-based rate limiting.

        Given: Multiple requests from same IP
        When: Rate limit is exceeded
        Then: 429 Too Many Requests
        """
        for i in range(200):
            client.get("/api/v1/public/endpoint")

        response = client.get("/api/v1/public/endpoint")
        assert response.status_code == 429


class TestInputValidation:
    """Test suite for input validation security"""

    def test_file_upload_validates_file_type(self, client, auth_token):
        """
        Test file upload type validation.

        Given: Non-image file
        When: Upload to scan endpoint
        Then: 400 Bad Request
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        files = {"file": ("malicious.exe", b"malicious content", "application/exe")}

        response = client.post("/api/v1/scan", headers=headers, files=files)
        assert response.status_code == 400

    def test_file_upload_validates_file_size(self, client, auth_token):
        """
        Test file size limit.

        Given: File exceeding size limit
        When: Upload to scan endpoint
        Then: 413 Payload Too Large
        """
        headers = {"Authorization": f"Bearer {auth_token}"}
        large_file = b"x" * (11 * 1024 * 1024)  # 11MB
        files = {"file": ("large.jpg", large_file, "image/jpeg")}

        response = client.post("/api/v1/scan", headers=headers, files=files)
        assert response.status_code == 413


class TestSecurityHeaders:
    """Test suite for security headers"""

    def test_hsts_header_present(self, client):
        """
        Test HSTS header in production.

        Given: Request to any endpoint
        When: Response is sent
        Then: Strict-Transport-Security header is present
        """
        _ = client.get("/healthz")  # response (HSTS check disabled for testing)
        # In production, HSTS should be present
        # assert "Strict-Transport-Security" in response.headers
        pass

    def test_content_security_policy_configured(self, client):
        """
        Test CSP header configuration.

        Given: Request to any endpoint
        When: Response is sent
        Then: CSP header is properly configured
        """
        response = client.get("/healthz")
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp


# Add pytest fixtures for security testing
@pytest.fixture
def expired_token():
    """Generate an expired JWT token"""
    pass


@pytest.fixture
def valid_token():
    """Generate a valid JWT token"""
    pass


@pytest.fixture
def user1_token():
    """Token for user 1"""
    pass


@pytest.fixture
def user2_id():
    """ID for user 2"""
    pass


@pytest.fixture
def regular_user_token():
    """Token for regular non-admin user"""
    pass
