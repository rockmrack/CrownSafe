import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from uuid import uuid4
from api.main_crownsafe import app


class TestExplainFeedbackEndpoint:
    """Test the explain feedback analytics endpoint"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_explain_feedback_valid_payload(self):
        """Test POST /analytics/explain-feedback with valid payload"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            # Mock database session
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # Mock CRUD function
            mock_create.return_value = 12345

            # Valid payload
            payload = {
                "scan_id": "test_scan_123",
                "helpful": True,
                "trace_id": "trace_abc_456",
                "reason": "clear_explanation",
                "comment": "Very helpful explanation",
                "platform": "ios",
                "app_version": "1.2.0",
                "locale": "en-US",
                "jurisdiction_code": "US",
            }

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["id"] == 12345

            # Verify CRUD function was called correctly
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["scan_id"] == "test_scan_123"
            assert call_kwargs["helpful"] is True
            assert call_kwargs["trace_id"] == "trace_abc_456"
            assert call_kwargs["reason"] == "clear_explanation"
            assert call_kwargs["comment"] == "Very helpful explanation"
            assert call_kwargs["platform"] == "ios"
            assert call_kwargs["app_version"] == "1.2.0"
            assert call_kwargs["locale"] == "en-US"
            assert call_kwargs["jurisdiction_code"] == "US"

    def test_explain_feedback_minimal_payload(self):
        """Test with only required fields"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 67890

            # Minimal payload
            payload = {"scan_id": "minimal_scan_456", "helpful": False}

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            assert data["id"] == 67890

            # Verify optional fields are None
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["scan_id"] == "minimal_scan_456"
            assert call_kwargs["helpful"] is False
            assert call_kwargs["trace_id"] is None
            assert call_kwargs["reason"] is None
            assert call_kwargs["comment"] is None

    def test_explain_feedback_missing_scan_id(self):
        """Test validation error for missing scan_id"""
        payload = {
            "helpful": True
            # Missing scan_id
        }

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)

        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("scan_id" in str(err) for err in error_detail)

    def test_explain_feedback_missing_helpful(self):
        """Test validation error for missing helpful field"""
        payload = {
            "scan_id": "test_scan_789"
            # Missing helpful
        }

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)

        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("helpful" in str(err) for err in error_detail)

    def test_explain_feedback_invalid_field_lengths(self):
        """Test validation for field length limits"""
        # Test scan_id too long
        payload = {"scan_id": "x" * 65, "helpful": True}  # Max is 64

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

        # Test reason too long
        payload = {
            "scan_id": "valid_scan",
            "helpful": True,
            "reason": "x" * 257,
        }  # Max is 256

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

        # Test comment too long
        payload = {
            "scan_id": "valid_scan",
            "helpful": True,
            "comment": "x" * 501,
        }  # Max is 500

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

    def test_explain_feedback_with_headers(self):
        """Test that request headers are used for platform info"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 11111

            payload = {"scan_id": "header_test_scan", "helpful": True}

            # Send with headers
            response = self.client.post(
                "/api/v1/analytics/explain-feedback",
                json=payload,
                headers={
                    "X-Platform": "android",
                    "X-App-Version": "2.1.0",
                    "X-Locale": "es-ES",
                },
            )

            assert response.status_code == 200

            # Verify headers were used
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["platform"] == "android"
            assert call_kwargs["app_version"] == "2.1.0"
            assert call_kwargs["locale"] == "es-ES"

    def test_explain_feedback_payload_overrides_headers(self):
        """Test that payload values override headers"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 22222

            payload = {
                "scan_id": "override_test_scan",
                "helpful": False,
                "platform": "web",  # Should override header
                "app_version": "3.0.0",  # Should override header
            }

            response = self.client.post(
                "/api/v1/analytics/explain-feedback",
                json=payload,
                headers={
                    "X-Platform": "ios",  # Should be overridden
                    "X-App-Version": "1.0.0",  # Should be overridden
                    "X-Locale": "fr-FR",  # Should be used (not overridden)
                },
            )

            assert response.status_code == 200

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["platform"] == "web"  # From payload
            assert call_kwargs["app_version"] == "3.0.0"  # From payload
            assert call_kwargs["locale"] == "fr-FR"  # From header

    def test_explain_feedback_with_authenticated_user(self):
        """Test that user_id is resolved when authenticated"""
        test_user_id = uuid4()

        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
            patch("core.auth.current_user") as mock_user,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 33333

            # Mock authenticated user
            mock_user.id = test_user_id

            payload = {"scan_id": "auth_test_scan", "helpful": True}

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 200

            # Verify user_id was passed
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["user_id"] == test_user_id

    def test_explain_feedback_unauthenticated_user(self):
        """Test that unauthenticated users can still provide feedback"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 44444

            # No auth mocking - should handle gracefully
            payload = {"scan_id": "unauth_test_scan", "helpful": False}

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 200

            # Verify user_id is None
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["user_id"] is None

    def test_explain_feedback_database_error(self):
        """Test handling of database errors"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            # Mock database error
            mock_create.side_effect = Exception("Database connection failed")

            payload = {"scan_id": "error_test_scan", "helpful": True}

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 500
            assert response.json()["detail"] == "failed_to_record_feedback"

    def test_explain_feedback_metrics_integration(self):
        """Test that metrics are recorded when available"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
            patch("core.metrics.inc_explain_feedback") as mock_metrics,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 55555

            payload = {
                "scan_id": "metrics_test_scan",
                "helpful": True,
                "reason": "very_clear",
            }

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 200

            # Verify metrics were recorded
            mock_metrics.assert_called_once_with(True, "very_clear")

    def test_explain_feedback_metrics_not_available(self):
        """Test graceful handling when metrics module is not available"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 66666

            # Mock ImportError for metrics
            with patch(
                "api.routers.analytics.inc_explain_feedback",
                side_effect=ImportError("No metrics"),
            ):
                payload = {"scan_id": "no_metrics_scan", "helpful": False}

                response = self.client.post(
                    "/api/v1/analytics/explain-feedback", json=payload
                )

                # Should still succeed
                assert response.status_code == 200
                assert response.json()["id"] == 66666


class TestExplainFeedbackValidation:
    """Test detailed validation scenarios"""

    def setup_method(self):
        self.client = TestClient(app)

    def test_helpful_boolean_validation(self):
        """Test that helpful field requires boolean"""
        # String instead of boolean
        payload = {"scan_id": "bool_test", "helpful": "true"}  # Should be boolean

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

        # Number instead of boolean
        payload = {"scan_id": "bool_test", "helpful": 1}  # Should be boolean

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

    def test_scan_id_empty_string(self):
        """Test that scan_id cannot be empty string"""
        payload = {
            "scan_id": "",
            "helpful": True,
        }  # Empty string should fail min_length=1

        response = self.client.post("/api/v1/analytics/explain-feedback", json=payload)
        assert response.status_code == 422

    def test_optional_fields_null_values(self):
        """Test that optional fields accept null values"""
        with (
            patch("api.routers.analytics.get_db") as mock_get_db,
            patch("api.routers.analytics.create_explain_feedback") as mock_create,
        ):
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_create.return_value = 77777

            payload = {
                "scan_id": "null_test_scan",
                "helpful": True,
                "trace_id": None,
                "reason": None,
                "comment": None,
                "platform": None,
                "app_version": None,
                "locale": None,
                "jurisdiction_code": None,
            }

            response = self.client.post(
                "/api/v1/analytics/explain-feedback", json=payload
            )

            assert response.status_code == 200

            # Verify None values were passed through
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["trace_id"] is None
            assert call_kwargs["reason"] is None
            assert call_kwargs["comment"] is None
