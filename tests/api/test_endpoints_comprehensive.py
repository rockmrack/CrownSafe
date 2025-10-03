"""
Comprehensive API Endpoint Tests
Demonstrates testing patterns for BabyShield API
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestAuthenticationEndpoints:
    """Test authentication endpoints"""
    
    def test_register_new_user(self, test_app, test_helper):
        """Test user registration"""
        response = test_app.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
            }
        )
        
        data = test_helper.assert_success_response(response)
        assert "user_id" in data.get("data", {})
    
    def test_register_duplicate_email(self, test_app, test_user, test_helper):
        """Test registration with duplicate email"""
        response = test_app.post(
            "/api/v1/auth/register",
            json={
                "email": test_user["email"],
                "password": "SecurePassword123!",
            }
        )
        
        test_helper.assert_error_response(response, expected_status=409)
    
    def test_login_valid_credentials(self, test_app, test_user, test_helper):
        """Test login with valid credentials"""
        response = test_app.post(
            "/api/v1/auth/token",
            data={  # OAuth2 uses form data
                "username": test_user["email"],
                "password": test_user["password"],
            }
        )
        
        data = test_helper.assert_success_response(response)
        assert "access_token" in data
        assert "token_type" in data
    
    def test_login_invalid_credentials(self, test_app, test_helper):
        """Test login with invalid credentials"""
        response = test_app.post(
            "/api/v1/auth/token",
            data={
                "username": "nonexistent@example.com",
                "password": "WrongPassword123!",
            }
        )
        
        test_helper.assert_unauthorized(response)


@pytest.mark.api
class TestBarcodeEndpoints:
    """Test barcode scanning endpoints"""
    
    def test_scan_valid_barcode(self, test_app, test_user, auth_headers, test_helper):
        """Test scanning a valid barcode"""
        response = test_app.post(
            "/api/v1/barcode/scan",
            json={
                "barcode": "012345678905",
                "user_id": test_user["id"],
            },
            headers=auth_headers,
        )
        
        data = test_helper.assert_success_response(response)
        assert "scan_results" in data.get("data", {})
    
    def test_scan_invalid_barcode(self, test_app, test_user, auth_headers, test_helper):
        """Test scanning an invalid barcode"""
        response = test_app.post(
            "/api/v1/barcode/scan",
            json={
                "barcode": "INVALID",
                "user_id": test_user["id"],
            },
            headers=auth_headers,
        )
        
        test_helper.assert_error_response(response)
    
    def test_scan_without_auth(self, test_app, test_user, test_helper):
        """Test scanning without authentication"""
        response = test_app.post(
            "/api/v1/barcode/scan",
            json={
                "barcode": "012345678905",
                "user_id": test_user["id"],
            },
        )
        
        test_helper.assert_unauthorized(response)
    
    @pytest.mark.security
    def test_scan_sql_injection_attempt(self, test_app, test_user, auth_headers, test_helper):
        """Test that SQL injection is prevented"""
        response = test_app.post(
            "/api/v1/barcode/scan",
            json={
                "barcode": "'; DROP TABLE users; --",
                "user_id": test_user["id"],
            },
            headers=auth_headers,
        )
        
        # Should return validation error, not crash
        test_helper.assert_error_response(response)


@pytest.mark.api
class TestSearchEndpoints:
    """Test search endpoints"""
    
    def test_search_recalls(self, test_app, test_recall, auth_headers, test_helper):
        """Test searching for recalls"""
        response = test_app.post(
            "/api/v1/search/advanced",
            json={
                "query": "baby product",
                "limit": 20,
                "offset": 0,
            },
            headers=auth_headers,
        )
        
        data = test_helper.assert_success_response(response)
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_search_with_filters(self, test_app, auth_headers, test_helper):
        """Test search with filters"""
        response = test_app.post(
            "/api/v1/search/advanced",
            json={
                "query": "stroller",
                "agencies": ["CPSC"],
                "risk_level": "high",
                "limit": 10,
                "offset": 0,
            },
            headers=auth_headers,
        )
        
        data = test_helper.assert_success_response(response)
        assert "data" in data
    
    def test_search_pagination(self, test_app, auth_headers, test_helper):
        """Test search pagination"""
        # First page
        response1 = test_app.post(
            "/api/v1/search/advanced",
            json={"query": "product", "limit": 5, "offset": 0},
            headers=auth_headers,
        )
        data1 = test_helper.assert_success_response(response1)
        
        # Second page
        response2 = test_app.post(
            "/api/v1/search/advanced",
            json={"query": "product", "limit": 5, "offset": 5},
            headers=auth_headers,
        )
        data2 = test_helper.assert_success_response(response2)
        
        # Results should be different
        assert data1["data"] != data2["data"]
    
    def test_search_query_too_long(self, test_app, auth_headers, test_helper):
        """Test that overly long queries are rejected"""
        long_query = "a" * 300  # Exceeds max length
        
        response = test_app.post(
            "/api/v1/search/advanced",
            json={"query": long_query, "limit": 20, "offset": 0},
            headers=auth_headers,
        )
        
        test_helper.assert_error_response(response)


@pytest.mark.api
class TestSubscriptionEndpoints:
    """Test subscription endpoints"""
    
    def test_check_subscription_status(self, test_app, test_subscriber, auth_headers, test_helper):
        """Test checking subscription status"""
        response = test_app.get(
            f"/api/v1/subscription/status?user_id={test_subscriber['id']}",
            headers=auth_headers,
        )
        
        data = test_helper.assert_success_response(response)
        assert data["data"]["is_subscribed"] is True
    
    def test_access_premium_feature_without_subscription(self, test_app, test_user, auth_headers, test_helper):
        """Test that premium features require subscription"""
        response = test_app.post(
            "/api/v1/premium/pregnancy-check",
            json={
                "user_id": test_user["id"],
                "product_name": "Test Product",
            },
            headers=auth_headers,
        )
        
        test_helper.assert_forbidden(response)
    
    def test_access_premium_feature_with_subscription(self, test_app, test_subscriber, auth_headers, test_helper):
        """Test that subscribers can access premium features"""
        response = test_app.post(
            "/api/v1/premium/pregnancy-check",
            json={
                "user_id": test_subscriber["id"],
                "product_name": "Test Product",
            },
            headers=auth_headers,
        )
        
        # Should succeed or return valid response (not 403)
        assert response.status_code in [200, 404]  # 404 if product not found


@pytest.mark.security
class TestSecurityHeaders:
    """Test security headers are properly set"""
    
    def test_security_headers_present(self, test_app):
        """Test that security headers are present"""
        response = test_app.get("/api/v1/health")
        
        # Check for important security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "Content-Security-Policy" in response.headers
    
    def test_rate_limiting(self, test_app):
        """Test that rate limiting is enforced"""
        # Make many requests rapidly
        responses = []
        for _ in range(150):  # Exceed rate limit
            response = test_app.get("/api/v1/health")
            responses.append(response)
        
        # At least one should be rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Rate limiting not enforced"


@pytest.mark.slow
@pytest.mark.integration
class TestEndToEndFlows:
    """Test complete end-to-end user flows"""
    
    def test_complete_scan_flow(self, test_app, test_helper):
        """Test complete barcode scan flow from registration to result"""
        # 1. Register user
        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "SecurePassword123!",
            }
        )
        register_data = test_helper.assert_success_response(register_response)
        user_id = register_data["data"]["user_id"]
        
        # 2. Login
        login_response = test_app.post(
            "/api/v1/auth/token",
            data={
                "username": "flowtest@example.com",
                "password": "SecurePassword123!",
            }
        )
        login_data = test_helper.assert_success_response(login_response)
        token = login_data["access_token"]
        
        # 3. Scan barcode
        scan_response = test_app.post(
            "/api/v1/barcode/scan",
            json={
                "barcode": "012345678905",
                "user_id": user_id,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        scan_data = test_helper.assert_success_response(scan_response)
        
        # 4. Check scan history
        history_response = test_app.get(
            f"/api/v1/scan-history?user_id={user_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        history_data = test_helper.assert_success_response(history_response)
        
        # Verify scan is in history
        assert len(history_data["data"]) > 0


@pytest.mark.unit
class TestInputValidation:
    """Test input validation"""
    
    def test_validate_email(self):
        """Test email validation"""
        from utils.security.input_validator import InputValidator
        
        # Valid emails
        assert InputValidator.validate_email("test@example.com") == "test@example.com"
        assert InputValidator.validate_email("user+tag@domain.co.uk") == "user+tag@domain.co.uk"
        
        # Invalid emails
        with pytest.raises(ValueError):
            InputValidator.validate_email("invalid-email")
        
        with pytest.raises(ValueError):
            InputValidator.validate_email("@example.com")
    
    def test_validate_barcode(self):
        """Test barcode validation"""
        from utils.security.input_validator import InputValidator
        
        # Valid barcodes
        assert InputValidator.validate_barcode("012345678905") == "012345678905"
        assert InputValidator.validate_barcode("4006381333931") == "4006381333931"
        
        # Invalid barcodes
        with pytest.raises(ValueError):
            InputValidator.validate_barcode("'; DROP TABLE users; --")
        
        with pytest.raises(ValueError):
            InputValidator.validate_barcode("<script>alert('xss')</script>")
    
    def test_validate_pagination(self):
        """Test pagination validation"""
        from utils.security.input_validator import InputValidator
        
        # Valid pagination
        limit, offset = InputValidator.validate_pagination(20, 0)
        assert limit == 20
        assert offset == 0
        
        # Limit too high (should cap at 100)
        limit, offset = InputValidator.validate_pagination(500, 0)
        assert limit == 100
        
        # Offset too high (should raise error)
        with pytest.raises(ValueError):
            InputValidator.validate_pagination(20, 20000)


@pytest.mark.slow
class TestPerformance:
    """Test performance characteristics"""
    
    def test_search_performance(self, test_app, auth_headers, performance_tracker):
        """Test that search completes within acceptable time"""
        performance_tracker.start()
        
        response = test_app.post(
            "/api/v1/search/advanced",
            json={"query": "baby", "limit": 20, "offset": 0},
            headers=auth_headers,
        )
        
        performance_tracker.stop()
        
        assert response.status_code == 200
        performance_tracker.assert_faster_than(2.0)  # Should complete in < 2 seconds
    
    def test_bulk_operations_performance(self, test_app, test_admin, auth_headers, performance_tracker):
        """Test bulk operations performance"""
        # This would test bulk insert/update operations
        pass

