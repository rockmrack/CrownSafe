from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import api.routers.chat as chat_router
from fastapi.testclient import TestClient

from api.main_babyshield import app


class TestChatFeatureGating:
    def setup_method(self) -> None:
        self.client = TestClient(app)

    def test_conversation_blocked_when_chat_disabled_globally(self) -> None:
        with (
            patch("api.routers.chat.chat_enabled_for", return_value=False) as mock_flag,
            patch("api.routers.chat.get_llm_client") as mock_llm,
        ):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={"user_id": "test-user-123"},
            )

        assert response.status_code == 403
        body = response.json()
        assert body["error"] is True
        assert body["message"] == "chat_disabled"
        mock_flag.assert_called_once_with("test-user-123", None)
        mock_llm.assert_not_called()

    def test_conversation_blocked_when_user_not_in_rollout(self) -> None:
        with (
            patch("api.routers.chat.chat_enabled_for", return_value=False) as mock_flag,
            patch("api.routers.chat.get_llm_client") as mock_llm,
        ):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "message": "Is this safe for pregnancy?",
                    "conversation_id": None,
                    "user_id": "rolled-out-user",
                },
            )

        assert response.status_code == 403
        body = response.json()
        assert body["error"] is True
        assert body["message"] == "chat_disabled"
        mock_flag.assert_called_once_with("rolled-out-user", None)
        mock_llm.assert_not_called()

    def test_conversation_allowed_when_user_in_rollout(self) -> None:
        mock_llm_client = MagicMock()
        mock_llm_client.chat_json.return_value = {
            "summary": "Test summary",
            "suggested_questions": ["What else should I know?"],
            "emergency": None,
        }

        with (
            patch("api.routers.chat.chat_enabled_for", return_value=True),
            patch("api.routers.chat.get_llm_client", return_value=mock_llm_client),
        ):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "message": "Is this safe for pregnancy?",
                    "conversation_id": None,
                    "user_id": "test-user-123",
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["answer"] == "Test summary"
        assert body["data"]["suggested_questions"]
        assert body["data"]["emergency"] is None
        assert "traceId" in body

    def test_feature_gating_uses_user_and_device_ids(self) -> None:
        mock_llm_client = MagicMock()
        mock_llm_client.chat_json.return_value = {
            "summary": "Test summary",
            "suggested_questions": [],
            "emergency": None,
        }

        with (
            patch("api.routers.chat.chat_enabled_for", return_value=True) as mock_flag,
            patch("api.routers.chat.get_llm_client", return_value=mock_llm_client),
        ):
            response = self.client.post(
                "/api/v1/chat/conversation",
                json={
                    "message": "Need advice",
                    "device_id": "device-456",
                },
            )

        assert response.status_code == 200
        mock_flag.assert_called_once_with(None, "device-456")
        assert response.json()["success"] is True

    def test_explain_result_not_gated(self) -> None:
        mock_session = MagicMock()
        mock_query = mock_session.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = MagicMock(analysis_result={"result": "ok"})

        dummy_response = SimpleNamespace(dict=lambda: {"summary": "Test summary"})
        mock_agent = MagicMock()
        mock_agent.explain_scan_result = AsyncMock(return_value=dummy_response)

        def _override_get_db():
            yield mock_session

        app.dependency_overrides[chat_router.get_db] = _override_get_db

        try:
            with (
                patch("api.routers.chat.get_chat_agent", return_value=mock_agent),
                patch("api.routers.chat.get_llm_client"),
            ):
                response = self.client.post(
                    "/api/v1/chat/explain-result",
                    params={
                        "scan_id": "test-scan-123",
                        "user_query": "What does this mean?",
                    },
                )
        finally:
            app.dependency_overrides.pop(chat_router.get_db, None)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["summary"] == "Test summary"
        mock_agent.explain_scan_result.assert_awaited_once()
