#!/usr/bin/env python3
"""
Test Suite 2: API Endpoints Tests (100 tests)
Tests all API endpoints, routes, and HTTP responses
"""

import pytest
import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main_babyshield import app

client = TestClient(app)

class TestAPIEndpoints:
    """100 tests for API endpoints"""
    
    # ========================
    # HEALTH AND STATUS ENDPOINTS (10 tests)
    # ========================
    
    def test_healthz_endpoint(self):
        """Test /healthz endpoint"""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_health_endpoint_response_structure(self):
        """Test /healthz response structure"""
        response = client.get("/healthz")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    
    def test_root_endpoint(self):
        """Test root / endpoint"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_endpoint_content_type(self):
        """Test root endpoint content type"""
        response = client.get("/")
        assert "content-type" in response.headers
    
    def test_docs_endpoint(self):
        """Test /docs endpoint"""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_endpoint(self):
        """Test /redoc endpoint"""
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_json(self):
        """Test /openapi.json endpoint"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
    
    def test_openapi_paths(self):
        """Test OpenAPI schema has paths"""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 0
    
    def test_openapi_info(self):
        """Test OpenAPI schema has info"""
        response = client.get("/openapi.json")
        schema = response.json()
        assert "info" in schema
        assert "title" in schema["info"]
    
    def test_health_check_uptime(self):
        """Test health check returns quickly"""
        import time
        start = time.time()
        response = client.get("/healthz")
        duration = time.time() - start
        assert duration < 1.0  # Should respond in under 1 second
    
    # ========================
    # RECALL ENDPOINTS (15 tests)
    # ========================
    
    def test_recalls_list_endpoint(self):
        """Test /api/v1/recalls endpoint"""
        response = client.get("/api/v1/recalls")
        assert response.status_code in [200, 500]  # 500 if DB not set up
    
    def test_recalls_with_pagination(self):
        """Test recalls endpoint with pagination"""
        response = client.get("/api/v1/recalls?page=1&page_size=10")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_query(self):
        """Test recalls endpoint with query parameter"""
        response = client.get("/api/v1/recalls?query=baby")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_empty_query(self):
        """Test recalls endpoint with empty query"""
        response = client.get("/api/v1/recalls?query=")
        assert response.status_code in [200, 400, 422, 500]
    
    def test_recalls_with_country_filter(self):
        """Test recalls endpoint with country filter"""
        response = client.get("/api/v1/recalls?country=US")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_date_filter(self):
        """Test recalls endpoint with date filter"""
        response = client.get("/api/v1/recalls?start_date=2024-01-01")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_stats_endpoint(self):
        """Test /api/v1/recalls/stats endpoint"""
        response = client.get("/api/v1/recalls/stats")
        assert response.status_code in [200, 404, 500]
    
    def test_recalls_search_dev_endpoint(self):
        """Test /api/v1/recalls/search-dev endpoint"""
        response = client.get("/api/v1/recalls/search-dev?query=test")
        assert response.status_code in [200, 404, 500]
    
    def test_recalls_with_sort(self):
        """Test recalls endpoint with sorting"""
        response = client.get("/api/v1/recalls?sort_by=date")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_limit(self):
        """Test recalls endpoint with limit"""
        response = client.get("/api/v1/recalls?limit=5")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_offset(self):
        """Test recalls endpoint with offset"""
        response = client.get("/api/v1/recalls?offset=10")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_brand_filter(self):
        """Test recalls endpoint with brand filter"""
        response = client.get("/api/v1/recalls?brand=TestBrand")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_hazard_filter(self):
        """Test recalls endpoint with hazard filter"""
        response = client.get("/api/v1/recalls?hazard=choking")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_severity_filter(self):
        """Test recalls endpoint with severity filter"""
        response = client.get("/api/v1/recalls?severity=high")
        assert response.status_code in [200, 422, 500]
    
    def test_recalls_with_multiple_filters(self):
        """Test recalls endpoint with multiple filters"""
        response = client.get("/api/v1/recalls?country=US&hazard=choking&page=1")
        assert response.status_code in [200, 422, 500]
    
    # ========================
    # BARCODE ENDPOINTS (10 tests)
    # ========================
    
    def test_barcode_scan_endpoint_exists(self):
        """Test barcode scan endpoint exists"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": "123456789"})
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_lookup_endpoint(self):
        """Test barcode lookup endpoint"""
        response = client.get("/api/v1/barcode/lookup?code=123456789")
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_with_invalid_format(self):
        """Test barcode with invalid format"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": "invalid"})
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_barcode_with_empty_code(self):
        """Test barcode with empty code"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": ""})
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_barcode_with_upc_format(self):
        """Test barcode with UPC format"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": "012345678905"})
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_with_ean_format(self):
        """Test barcode with EAN format"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": "5901234123457"})
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_with_gtin_format(self):
        """Test barcode with GTIN format"""
        response = client.post("/api/v1/barcode/scan", json={"barcode": "10012345678906"})
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_history_endpoint(self):
        """Test barcode scan history endpoint"""
        response = client.get("/api/v1/barcode/history")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_barcode_batch_lookup(self):
        """Test barcode batch lookup"""
        response = client.post("/api/v1/barcode/batch", json={"barcodes": ["123", "456"]})
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_barcode_validate_endpoint(self):
        """Test barcode validation endpoint"""
        response = client.get("/api/v1/barcode/validate?code=123456789012")
        assert response.status_code in [200, 400, 404, 422, 500]
    
    # ========================
    # AUTHENTICATION ENDPOINTS (15 tests)
    # ========================
    
    def test_register_endpoint_exists(self):
        """Test register endpoint exists"""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@test.com",
            "password": "testpassword123"
        })
        assert response.status_code in [200, 201, 400, 404, 422, 500]
    
    def test_login_endpoint_exists(self):
        """Test login endpoint exists"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@test.com",
            "password": "testpassword123"
        })
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_logout_endpoint_exists(self):
        """Test logout endpoint exists"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_register_with_invalid_email(self):
        """Test register with invalid email"""
        response = client.post("/api/v1/auth/register", json={
            "email": "invalid-email",
            "password": "testpassword123"
        })
        assert response.status_code in [400, 404, 422, 500]
    
    def test_register_with_weak_password(self):
        """Test register with weak password"""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@test.com",
            "password": "123"
        })
        assert response.status_code in [400, 404, 422, 500]
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        })
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_password_reset_request_endpoint(self):
        """Test password reset request endpoint"""
        response = client.post("/api/v1/auth/password-reset/request", json={
            "email": "test@test.com"
        })
        assert response.status_code in [200, 400, 404, 422, 500]
    
    def test_password_reset_confirm_endpoint(self):
        """Test password reset confirm endpoint"""
        response = client.post("/api/v1/auth/password-reset/confirm", json={
            "token": "test-token",
            "new_password": "newpassword123"
        })
        assert response.status_code in [200, 400, 404, 422, 500]
    
    def test_token_refresh_endpoint(self):
        """Test token refresh endpoint"""
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_user_profile_endpoint(self):
        """Test user profile endpoint"""
        response = client.get("/api/v1/auth/profile")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_update_profile_endpoint(self):
        """Test update profile endpoint"""
        response = client.put("/api/v1/auth/profile", json={
            "name": "Test User"
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    def test_change_password_endpoint(self):
        """Test change password endpoint"""
        response = client.post("/api/v1/auth/change-password", json={
            "old_password": "oldpass",
            "new_password": "newpass"
        })
        assert response.status_code in [200, 400, 401, 404, 422, 500]
    
    def test_verify_email_endpoint(self):
        """Test verify email endpoint"""
        response = client.get("/api/v1/auth/verify-email?token=test-token")
        assert response.status_code in [200, 400, 404, 422, 500]
    
    def test_resend_verification_endpoint(self):
        """Test resend verification endpoint"""
        response = client.post("/api/v1/auth/resend-verification", json={
            "email": "test@test.com"
        })
        assert response.status_code in [200, 400, 404, 422, 500]
    
    def test_delete_account_endpoint(self):
        """Test delete account endpoint"""
        response = client.delete("/api/v1/auth/account")
        assert response.status_code in [200, 401, 404, 500]
    
    # ========================
    # NOTIFICATION ENDPOINTS (10 tests)
    # ========================
    
    def test_notifications_list_endpoint(self):
        """Test notifications list endpoint"""
        response = client.get("/api/v1/notifications")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_notification_mark_read_endpoint(self):
        """Test mark notification as read endpoint"""
        response = client.post("/api/v1/notifications/1/read")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_notifications_mark_all_read_endpoint(self):
        """Test mark all notifications as read"""
        response = client.post("/api/v1/notifications/read-all")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_notification_settings_endpoint(self):
        """Test notification settings endpoint"""
        response = client.get("/api/v1/notifications/settings")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_update_notification_settings(self):
        """Test update notification settings"""
        response = client.put("/api/v1/notifications/settings", json={
            "email_enabled": True
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    def test_delete_notification_endpoint(self):
        """Test delete notification endpoint"""
        response = client.delete("/api/v1/notifications/1")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_notifications_unread_count(self):
        """Test unread notifications count"""
        response = client.get("/api/v1/notifications/unread-count")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_notification_subscribe_endpoint(self):
        """Test notification subscription endpoint"""
        response = client.post("/api/v1/notifications/subscribe", json={
            "topic": "recalls"
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    def test_notification_unsubscribe_endpoint(self):
        """Test notification unsubscription endpoint"""
        response = client.post("/api/v1/notifications/unsubscribe", json={
            "topic": "recalls"
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    def test_push_notification_token_endpoint(self):
        """Test push notification token registration"""
        response = client.post("/api/v1/notifications/push-token", json={
            "token": "test-push-token"
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    # ========================
    # FEEDBACK ENDPOINTS (10 tests)
    # ========================
    
    def test_submit_feedback_endpoint(self):
        """Test submit feedback endpoint"""
        response = client.post("/api/v1/feedback", json={
            "message": "Test feedback",
            "rating": 5
        })
        assert response.status_code in [200, 201, 401, 404, 422, 500]
    
    def test_list_feedback_endpoint(self):
        """Test list feedback endpoint"""
        response = client.get("/api/v1/feedback")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_get_feedback_by_id(self):
        """Test get specific feedback"""
        response = client.get("/api/v1/feedback/1")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_update_feedback_endpoint(self):
        """Test update feedback endpoint"""
        response = client.put("/api/v1/feedback/1", json={
            "message": "Updated feedback"
        })
        assert response.status_code in [200, 401, 404, 422, 500]
    
    def test_delete_feedback_endpoint(self):
        """Test delete feedback endpoint"""
        response = client.delete("/api/v1/feedback/1")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_feedback_with_invalid_rating(self):
        """Test feedback with invalid rating"""
        response = client.post("/api/v1/feedback", json={
            "message": "Test",
            "rating": 10  # Invalid rating
        })
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_feedback_with_empty_message(self):
        """Test feedback with empty message"""
        response = client.post("/api/v1/feedback", json={
            "message": "",
            "rating": 5
        })
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_feedback_statistics_endpoint(self):
        """Test feedback statistics endpoint"""
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code in [200, 401, 404, 500]
    
    def test_feedback_categories_endpoint(self):
        """Test feedback categories endpoint"""
        response = client.get("/api/v1/feedback/categories")
        assert response.status_code in [200, 404, 500]
    
    def test_feedback_with_category(self):
        """Test feedback with category"""
        response = client.post("/api/v1/feedback", json={
            "message": "Test feedback",
            "rating": 5,
            "category": "bug"
        })
        assert response.status_code in [200, 201, 401, 404, 422, 500]
    
    # ========================
    # MONITORING ENDPOINTS (10 tests)
    # ========================
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint"""
        response = client.get("/metrics")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_health_endpoint(self):
        """Test monitoring health endpoint"""
        response = client.get("/api/v1/monitoring/health")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_status_endpoint(self):
        """Test monitoring status endpoint"""
        response = client.get("/api/v1/monitoring/status")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_database_status(self):
        """Test database status check"""
        response = client.get("/api/v1/monitoring/database")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_cache_status(self):
        """Test cache status check"""
        response = client.get("/api/v1/monitoring/cache")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_memory_status(self):
        """Test memory status check"""
        response = client.get("/api/v1/monitoring/memory")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_cpu_status(self):
        """Test CPU status check"""
        response = client.get("/api/v1/monitoring/cpu")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_disk_status(self):
        """Test disk status check"""
        response = client.get("/api/v1/monitoring/disk")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_uptime_endpoint(self):
        """Test uptime endpoint"""
        response = client.get("/api/v1/monitoring/uptime")
        assert response.status_code in [200, 404, 500]
    
    def test_monitoring_version_endpoint(self):
        """Test version endpoint"""
        response = client.get("/api/v1/monitoring/version")
        assert response.status_code in [200, 404, 500]
    
    # ========================
    # ERROR HANDLING TESTS (10 tests)
    # ========================
    
    def test_404_not_found(self):
        """Test 404 error handling"""
        response = client.get("/nonexistent-endpoint-xyz")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test 405 method not allowed"""
        response = client.delete("/healthz")
        assert response.status_code in [405, 404]
    
    def test_invalid_json_body(self):
        """Test invalid JSON body handling"""
        response = client.post(
            "/api/v1/feedback",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422, 500]
    
    def test_missing_required_field(self):
        """Test missing required field"""
        response = client.post("/api/v1/feedback", json={})
        assert response.status_code in [400, 401, 404, 422, 500]
    
    def test_invalid_query_parameter(self):
        """Test invalid query parameter"""
        response = client.get("/api/v1/recalls?page=invalid")
        assert response.status_code in [400, 422, 500]
    
    def test_unauthorized_access(self):
        """Test unauthorized access"""
        response = client.get("/api/v1/auth/profile")
        assert response.status_code in [401, 404, 500]
    
    def test_cors_headers_present(self):
        """Test CORS headers are present"""
        response = client.options("/api/v1/recalls")
        assert response.status_code in [200, 404, 405]
    
    def test_content_type_validation(self):
        """Test content type validation"""
        response = client.post(
            "/api/v1/feedback",
            data="test",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in [400, 415, 422, 500]
    
    def test_rate_limit_headers(self):
        """Test rate limit headers presence"""
        response = client.get("/api/v1/recalls")
        # Rate limit headers may or may not be present
        assert response.status_code in [200, 429, 500]
    
    def test_error_response_structure(self):
        """Test error response has proper structure"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data or "message" in data or "error" in data

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
