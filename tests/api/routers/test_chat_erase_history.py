from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from api.main_crownsafe import app

client = TestClient(app)


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
def test_erase_history_without_auth():
    """Test erase history endpoint without authentication"""
    response = client.post("/api/v1/chat/erase-history")
    assert response.status_code == 401
    assert "auth_required" in response.json()["detail"]


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
@patch("api.routers.chat.get_db")
@patch("api.routers.chat.mark_erase_requested")
@patch("api.routers.chat.purge_conversations_for_user")
def test_erase_history_sync_mode(mock_purge, mock_mark_erase, mock_get_db):
    """Test erase history endpoint in synchronous mode"""
    # Mock database session
    mock_db = Mock()
    mock_get_db.return_value = mock_db

    # Mock user authentication (replace with your actual auth mock)
    with patch("api.routers.chat.current_user") as mock_user:
        mock_user.id = "test-user-123"

        # Mock the purge function to return deleted count
        mock_purge.return_value = 3

        response = client.post("/api/v1/chat/erase-history")

        assert response.status_code == 200
        data = response.json()

        assert data["ok"]
        assert data["mode"] == "sync"
        assert data["deleted"] == 3
        assert "trace_id" in data
        assert response.headers.get("X-Trace-Id") is not None

        # Verify the functions were called
        mock_mark_erase.assert_called_once()
        mock_purge.assert_called_once()


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
@patch("api.routers.chat.get_db")
@patch("api.routers.chat.mark_erase_requested")
@patch("workers.tasks.chat_cleanup.purge_user_history_task")
def test_erase_history_with_celery_task(mock_task, mock_mark_erase, mock_get_db):
    """Test erase history endpoint with Celery task (async mode)"""
    # Mock database session
    mock_db = Mock()
    mock_get_db.return_value = mock_db

    # Mock user authentication
    with patch("api.routers.chat.current_user") as mock_user:
        mock_user.id = "test-user-123"

        # Mock the task to have a delay method (simulating Celery)
        mock_task.delay = Mock()
        mock_task.return_value = 2  # Direct call returns count

        response = client.post("/api/v1/chat/erase-history")

        assert response.status_code == 200
        data = response.json()

        assert data["ok"]
        assert data["mode"] == "sync"  # Falls back to sync when direct call works
        assert data["deleted"] == 2

        # Verify the functions were called
        mock_mark_erase.assert_called_once()
        mock_task.assert_called_once_with("test-user-123")


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
@patch("api.routers.chat.get_db")
@patch("api.routers.chat.mark_erase_requested")
@patch("api.routers.chat.purge_conversations_for_user")
def test_erase_history_fallback_to_sync(mock_purge, mock_mark_erase, mock_get_db):
    """Test erase history endpoint falls back to sync when Celery fails"""
    # Mock database session
    mock_db = Mock()
    mock_get_db.return_value = mock_db

    # Mock user authentication
    with patch("api.routers.chat.current_user") as mock_user:
        mock_user.id = "test-user-123"

        # Mock the purge function to return deleted count
        mock_purge.return_value = 1

        # Mock import failure for Celery task
        with patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'workers.tasks.chat_cleanup'"),
        ):
            response = client.post("/api/v1/chat/erase-history")

            assert response.status_code == 200
            data = response.json()

            assert data["ok"]
            assert data["mode"] == "sync"
            assert data["deleted"] == 1

            # Verify fallback to direct purge was used
            mock_purge.assert_called_once()


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
@patch("api.routers.chat.get_db")
@patch("api.routers.chat.mark_erase_requested")
def test_erase_history_no_conversations(mock_mark_erase, mock_get_db):
    """Test erase history when user has no conversations"""
    # Mock database session
    mock_db = Mock()
    mock_get_db.return_value = mock_db

    # Mock user authentication
    with patch("api.routers.chat.current_user") as mock_user:
        mock_user.id = "test-user-123"

        # Mock purge returning 0 (no conversations)
        with patch("api.routers.chat.purge_conversations_for_user", return_value=0):
            response = client.post("/api/v1/chat/erase-history")

            assert response.status_code == 200
            data = response.json()

            assert data["ok"]
            assert data["deleted"] == 0

            # Should still mark erase as requested
            mock_mark_erase.assert_called_once()


@pytest.mark.skip(
    reason="Erase history endpoint not yet implemented in api.routers.chat. This test suite is for a planned feature.",
)
def test_erase_history_trace_id_header():
    """Test that erase history endpoint returns trace ID in header"""
    with (
        patch("api.routers.chat.get_db"),
        patch("api.routers.chat.mark_erase_requested"),
        patch("api.routers.chat.purge_conversations_for_user", return_value=1),
        patch("api.routers.chat.current_user") as mock_user,
    ):
        mock_user.id = "test-user-123"

        response = client.post("/api/v1/chat/erase-history")

        assert response.status_code == 200
        assert "X-Trace-Id" in response.headers

        # Trace ID should match the one in response body
        data = response.json()
        assert response.headers["X-Trace-Id"] == data["trace_id"]
