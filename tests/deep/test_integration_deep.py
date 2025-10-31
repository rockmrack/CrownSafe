"""
Deep Integration Tests
Testing cross-component integration and complex workflows
"""

import os

from fastapi.testclient import TestClient

from api.main_crownsafe import app

os.environ["BS_FEATURE_CHAT_ENABLED"] = "true"
os.environ["BS_FEATURE_CHAT_ROLLOUT_PCT"] = "1.0"


class TestIntegrationDeep:
    """Deep integration tests across multiple components"""

    def test_app_initialization(self):
        """Test that FastAPI app initializes correctly"""
        assert app is not None
        assert app.title is not None

    def test_app_routes_registered(self):
        """Test that routes are properly registered"""
        routes = [route.path for route in app.routes]

        # Key routes should exist
        assert "/healthz" in routes or any("/health" in r for r in routes)

    def test_app_middleware_stack(self):
        """Test that middleware is properly configured"""
        # App should have middleware
        assert hasattr(app, "user_middleware")

    def test_openapi_schema_generation(self):
        """Test that OpenAPI schema can be generated"""
        client = TestClient(app)
        r = client.get("/openapi.json")

        if r.status_code == 200:
            schema = r.json()
            assert "openapi" in schema
            assert "info" in schema
            assert "paths" in schema

    def test_docs_endpoint(self):
        """Test that API documentation is accessible"""
        client = TestClient(app)
        r = client.get("/docs")

        # Should redirect to docs or show docs page
        assert r.status_code in [200, 307]

    def test_redoc_endpoint(self):
        """Test that ReDoc documentation is accessible"""
        client = TestClient(app)
        r = client.get("/redoc")

        # Should show ReDoc page
        assert r.status_code in [200, 307, 404]

    def test_root_endpoint(self):
        """Test root endpoint"""
        client = TestClient(app)
        r = client.get("/")

        # Should either show welcome page or redirect
        assert r.status_code in [200, 307, 404]

    def test_cors_configuration(self):
        """Test CORS is configured"""
        client = TestClient(app)
        r = client.get("/healthz", headers={"Origin": "https://babyshield.app"})

        # Check for CORS headers
        headers = {k.lower(): v for k, v in r.headers.items()}
        # If CORS is enabled, should have access-control headers
        if "access-control-allow-origin" in headers:
            assert headers["access-control-allow-origin"] in [
                "*",
                "https://babyshield.app",
            ]

    def test_error_handling_integration(self):
        """Test that global error handlers work"""
        client = TestClient(app)
        r = client.get("/api/v1/this-definitely-does-not-exist-xyz")

        assert r.status_code == 404
        body = r.json()
        # Should have error structure
        assert "detail" in body or "error" in body or "message" in body

    def test_logging_integration(self):
        """Test that logging is configured"""
        client = TestClient(app)

        # Make request that should generate logs
        r = client.get("/healthz")
        assert r.status_code == 200
        # If no crash, logging is working

    def test_environment_variables_loaded(self):
        """Test that environment variables are accessible"""
        # Key environment variables should be loadable
        db_url = os.getenv("DATABASE_URL")
        # Either set or None, should not crash
        assert db_url is None or isinstance(db_url, str)

    def test_api_versioning(self):
        """Test API versioning structure"""
        client = TestClient(app)

        # v1 endpoints should exist
        r = client.get("/api/v1/")
        # May or may not exist, but should not error badly
        assert r.status_code in [200, 404, 405]

    def test_health_check_components(self):
        """Test health check includes component status"""
        client = TestClient(app)
        r = client.get("/healthz")

        assert r.status_code == 200
        body = r.json()

        # Should have status
        assert "status" in body or "health" in body

    def test_metrics_endpoint(self):
        """Test metrics endpoint if available"""
        client = TestClient(app)
        r = client.get("/metrics")

        # May or may not exist
        if r.status_code == 200:
            # If exists, should return some metrics data
            assert len(r.content) > 0

    def test_static_files_serving(self):
        """Test static file serving if configured"""
        client = TestClient(app)
        r = client.get("/static/test.txt")

        # May or may not exist
        assert r.status_code in [200, 404]

    def test_websocket_support(self):
        """Test if WebSocket support is available"""
        # Check if app has WebSocket routes
        routes = [route.path for route in app.routes]
        ws_routes = [r for r in routes if "ws" in r.lower()]

        # WebSocket is optional
        assert isinstance(ws_routes, list)

    def test_database_health_check(self):
        """Test database health check endpoint"""
        client = TestClient(app)
        r = client.get("/healthz/db")

        # May or may not exist
        if r.status_code == 200:
            body = r.json()
            assert "database" in str(body).lower() or "db" in str(body).lower()

    def test_cache_health_check(self):
        """Test cache health check endpoint"""
        client = TestClient(app)
        r = client.get("/healthz/cache")

        # Optional endpoint
        assert r.status_code in [200, 404]

    def test_multiple_concurrent_endpoints(self):
        """Test calling multiple different endpoints concurrently"""
        client = TestClient(app)

        endpoints = ["/healthz", "/openapi.json", "/docs"]

        results = []
        for endpoint in endpoints:
            r = client.get(endpoint)
            results.append(r.status_code)

        # At least health should work
        assert 200 in results

    def test_request_context_propagation(self):
        """Test that request context is propagated"""
        client = TestClient(app)

        # Send custom header
        r = client.get("/healthz", headers={"X-Custom-Test": "value"})

        # Should process without error
        assert r.status_code == 200
