import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api.main_babyshield import app


class TestChatFlags:
    def setup_method(self):
        self.client = TestClient(app)

    def test_chat_flags_default_values(self):
        with (
            patch("api.routers.chat.FEATURE_CHAT_ENABLED", False),
            patch("api.routers.chat.FEATURE_CHAT_ROLLOUT_PCT", 0.10),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "traceId" in body
            assert body["data"]["chat_enabled_global"] is False
            assert body["data"]["chat_rollout_pct"] == 0.10

    def test_chat_flags_enabled(self):
        with (
            patch("api.routers.chat.FEATURE_CHAT_ENABLED", True),
            patch("api.routers.chat.FEATURE_CHAT_ROLLOUT_PCT", 0.50),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "traceId" in body
            assert body["data"]["chat_enabled_global"] is True
            assert body["data"]["chat_rollout_pct"] == 0.50

    def test_chat_flags_full_rollout(self):
        with (
            patch("api.routers.chat.FEATURE_CHAT_ENABLED", True),
            patch("api.routers.chat.FEATURE_CHAT_ROLLOUT_PCT", 1.0),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "traceId" in body
            assert body["data"]["chat_enabled_global"] is True
            assert body["data"]["chat_rollout_pct"] == 1.0

    def test_chat_flags_zero_rollout(self):
        with (
            patch("api.routers.chat.FEATURE_CHAT_ENABLED", True),
            patch("api.routers.chat.FEATURE_CHAT_ROLLOUT_PCT", 0.0),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert "traceId" in body
            assert body["data"]["chat_enabled_global"] is True
            assert body["data"]["chat_rollout_pct"] == 0.0
