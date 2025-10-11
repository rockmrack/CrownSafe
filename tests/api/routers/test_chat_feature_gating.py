import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main_babyshield import app


class TestChatFeatureGating:
    def setup_method(self):
        self.client = TestClient(app)

    @patch("api.routers.chat.fetch_scan_data")
    @patch("api.routers.chat.get_llm_client")
    def test_conversation_blocked_when_chat_disabled_globally(self, mock_llm, mock_fetch):
        """Test that conversation endpoint returns 403 when chat is globally disabled"""
        with patch("core.feature_flags.FEATURE_CHAT_ENABLED", False):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test-scan-123",
                    "user_query": "Is this safe for pregnancy?",
                },
            )

            assert response.status_code == 403
            assert response.json()["detail"] == "chat_disabled"

            # Should not call downstream services
            mock_fetch.assert_not_called()
            mock_llm.assert_not_called()

    @patch("api.routers.chat.fetch_scan_data")
    @patch("api.routers.chat.get_llm_client")
    def test_conversation_blocked_when_user_not_in_rollout(self, mock_llm, mock_fetch):
        """Test that conversation endpoint returns 403 when user is not in rollout percentage"""
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.chat_enabled_for", return_value=False),
        ):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test-scan-123",
                    "user_query": "Is this safe for pregnancy?",
                },
            )

            assert response.status_code == 403
            assert response.json()["detail"] == "chat_disabled"

            # Should not call downstream services
            mock_fetch.assert_not_called()
            mock_llm.assert_not_called()

    @patch("api.routers.chat.fetch_scan_data")
    @patch("api.routers.chat.get_llm_client")
    @patch("api.routers.chat.get_or_create_conversation")
    @patch("api.routers.chat.get_profile")
    @patch("api.routers.chat.log_message")
    @patch("api.routers.chat.run_tool_for_intent")
    def test_conversation_allowed_when_user_in_rollout(
        self, mock_tool, mock_log, mock_profile, mock_conv, mock_llm, mock_fetch
    ):
        """Test that conversation endpoint works when user is in rollout"""
        # Setup mocks
        mock_fetch.return_value = {"product_name": "Test Product", "category": "food"}
        mock_conv.return_value = MagicMock(id="conv-123")
        mock_profile.return_value = {}
        mock_tool.return_value = {"pregnancy": {"risks": [], "notes": ""}}

        mock_llm_client = MagicMock()
        mock_llm_client.chat_json.return_value = {
            "summary": "Test summary",
            "reasons": ["Test reason"],
            "checks": ["Check label"],
            "flags": [],
            "disclaimer": "Not medical advice",
            "jurisdiction": {"code": "US", "label": "FDA"},
            "evidence": [],
        }
        mock_llm.return_value = mock_llm_client

        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.chat_enabled_for", return_value=True),
            patch("api.routers.chat.ChatAgentLogic") as mock_agent_class,
        ):
            mock_agent = MagicMock()
            mock_agent.classify_intent.return_value = "pregnancy_risk"
            mock_agent_class.return_value = mock_agent

            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "scan_id": "test-scan-123",
                    "user_query": "Is this safe for pregnancy?",
                },
            )

            # Should succeed
            assert response.status_code == 200
            data = response.json()
            assert "intent" in data
            assert "message" in data
            assert "trace_id" in data

            # Should call downstream services
            mock_fetch.assert_called_once()

    @patch("api.routers.chat.fetch_scan_data")
    def test_explain_result_not_gated(self, mock_fetch):
        """Test that explain-result endpoint is not gated (for backward compatibility)"""
        mock_fetch.return_value = {"product_name": "Test Product"}

        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", False),
            patch("api.routers.chat.ChatAgentLogic") as mock_agent_class,
        ):
            mock_agent = MagicMock()
            mock_agent.synthesize_result.return_value = {
                "summary": "Test summary",
                "reasons": ["Test reason"],
                "checks": ["Check label"],
                "flags": [],
                "disclaimer": "Not medical advice",
                "jurisdiction": {"code": "US", "label": "FDA"},
                "evidence": [],
            }
            mock_agent_class.return_value = mock_agent

            response = self.client.post(
                "/api/v1/chat/explain-result", json={"scan_id": "test-scan-123"}
            )

            # Should succeed even when chat is disabled
            assert response.status_code == 200
            data = response.json()
            assert "summary" in data

    def test_feature_gating_uses_user_and_device_ids(self):
        """Test that feature gating correctly uses user_id and device_id"""
        with (
            patch("core.feature_flags.FEATURE_CHAT_ENABLED", True),
            patch("core.feature_flags.chat_enabled_for") as mock_enabled,
        ):
            mock_enabled.return_value = False

            response = self.client.post(
                "/api/v1/chat/conversation",
                json={"scan_id": "test-scan-123", "user_query": "Is this safe?"},
            )

            assert response.status_code == 403

            # Should have called chat_enabled_for with user_id_str and device_id
            mock_enabled.assert_called_once()
            args = mock_enabled.call_args[0]
            assert len(args) == 2  # user_id_str, device_id
            # user_id_str should be None or string (depends on auth system)
            # device_id should be None (not implemented in this test)
