import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api.main_babyshield import app


class TestChatFlags:
    def setup_method(self):
        self.client = TestClient(app)

    def test_chat_flags_default_values(self):
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", False),
            patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.10),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            data = response.json()
            assert data == {"chat_enabled_global": False, "chat_rollout_pct": 0.10}

    def test_chat_flags_enabled(self):
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.50),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            data = response.json()
            assert data == {"chat_enabled_global": True, "chat_rollout_pct": 0.50}

    def test_chat_flags_full_rollout(self):
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 1.0),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            data = response.json()
            assert data == {"chat_enabled_global": True, "chat_rollout_pct": 1.0}

    def test_chat_flags_zero_rollout(self):
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.FEATURE_CHAT_ROLLOUT_PCT", 0.0),
        ):
            response = self.client.get("/api/v1/chat/flags")

            assert response.status_code == 200
            data = response.json()
            assert data == {"chat_enabled_global": True, "chat_rollout_pct": 0.0}
