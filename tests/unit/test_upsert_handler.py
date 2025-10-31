"""Unit tests for core_infra/upsert_handler.py.
Tests database UPSERT operations for recalls and subscriptions, including bulk operations and error handling scenarios.
"""

from unittest.mock import Mock

from core_infra.upsert_handler import (
    EnhancedUpsertHandler,
    UpsertHandler,
    enhanced_upsert_handler,
    upsert_handler,
)


class TestUpsertHandler:
    """Test UpsertHandler functionality."""

    def test_upsert_recall_success(self) -> None:
        """Test successful recall upsert."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "RECALL-001" if x == 0 else True)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        recall_data = {
            "recall_id": "RECALL-001",
            "product_name": "Test Product",
            "brand": "Test Brand",
            "hazard": "Test Hazard",
            "source_agency": "CPSC",
        }

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is True
        mock_session.execute.assert_called_once()

    def test_upsert_recall_missing_recall_id(self) -> None:
        """Test upsert_recall with missing recall_id."""
        mock_session = Mock()
        recall_data = {"product_name": "Test Product", "brand": "Test Brand"}

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is False
        mock_session.execute.assert_not_called()

    def test_upsert_recall_database_error(self) -> None:
        """Test upsert_recall with database error."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")

        recall_data = {"recall_id": "RECALL-001", "product_name": "Test Product"}

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is False

    def test_upsert_recall_update_existing(self) -> None:
        """Test upsert_recall updating existing record."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "RECALL-001" if x == 0 else False)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        recall_data = {
            "recall_id": "RECALL-001",
            "product_name": "Updated Product",
            "brand": "Updated Brand",
        }

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is True
        mock_session.execute.assert_called_once()

    def test_bulk_upsert_recalls_success(self) -> None:
        """Test successful bulk upsert of recalls."""
        mock_session = Mock()
        mock_result = Mock()
        mock_session.execute.return_value = mock_result

        recalls = [
            {
                "recall_id": "RECALL-001",
                "product_name": "Product 1",
                "brand": "Brand 1",
            },
            {
                "recall_id": "RECALL-002",
                "product_name": "Product 2",
                "brand": "Brand 2",
            },
        ]

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls, batch_size=10)

        assert result["inserted"] == 2
        assert result["updated"] == 0
        assert result["failed"] == 0
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    def test_bulk_upsert_recalls_with_failures(self) -> None:
        """Test bulk upsert with some failures."""
        mock_session = Mock()

        recalls = [
            {"recall_id": "RECALL-001", "product_name": "Product 1"},
            {
                # Missing recall_id - should fail
                "product_name": "Product 2",
            },
            {"recall_id": "RECALL-003", "product_name": "Product 3"},
        ]

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls, batch_size=10)

        assert result["inserted"] == 2
        assert result["failed"] == 1
        mock_session.execute.assert_called()
        mock_session.commit.assert_called_once()

    def test_bulk_upsert_recalls_database_error(self) -> None:
        """Test bulk upsert with database error."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")

        recalls = [{"recall_id": "RECALL-001", "product_name": "Product 1"}]

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls, batch_size=10)

        assert result["inserted"] == 0
        assert result["failed"] == 1
        mock_session.rollback.assert_called()

    def test_bulk_upsert_recalls_commit_error(self) -> None:
        """Test bulk upsert with commit error."""
        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Commit error")

        recalls = [{"recall_id": "RECALL-001", "product_name": "Product 1"}]

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls, batch_size=10)

        assert result["inserted"] == 1
        assert result["failed"] == 0
        mock_session.rollback.assert_called()

    def test_upsert_subscription_success(self) -> None:
        """Test successful subscription upsert."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: 1 if x == 0 else True)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        subscription_data = {
            "user_id": 123,
            "plan": "premium",
            "status": "active",
            "provider": "stripe",
            "original_transaction_id": "txn_123",
        }

        result = UpsertHandler.upsert_subscription(mock_session, subscription_data)

        assert result is True
        mock_session.execute.assert_called_once()

    def test_upsert_subscription_database_error(self) -> None:
        """Test upsert_subscription with database error."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")

        subscription_data = {"user_id": 123, "plan": "premium"}

        result = UpsertHandler.upsert_subscription(mock_session, subscription_data)

        assert result is False


class TestEnhancedUpsertHandler:
    """Test EnhancedUpsertHandler functionality."""

    def test_upsert_with_history_success(self) -> None:
        """Test successful upsert with history tracking."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "entity_123" if x == 0 else True)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = {"id": "entity_123", "name": "Test Entity", "value": "Test Value"}

        result = EnhancedUpsertHandler.upsert_with_history(mock_session, "test_table", data, "id", track_changes=True)

        assert result is True
        # Should call execute twice: once for upsert, once for history
        assert mock_session.execute.call_count == 2

    def test_upsert_with_history_no_tracking(self) -> None:
        """Test upsert without history tracking."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "entity_123" if x == 0 else True)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = {"id": "entity_123", "name": "Test Entity"}

        result = EnhancedUpsertHandler.upsert_with_history(mock_session, "test_table", data, "id", track_changes=False)

        assert result is True
        # Should call execute only once for upsert
        assert mock_session.execute.call_count == 1

    def test_upsert_with_history_database_error(self) -> None:
        """Test upsert_with_history with database error."""
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")

        data = {"id": "entity_123", "name": "Test Entity"}

        result = EnhancedUpsertHandler.upsert_with_history(mock_session, "test_table", data, "id")

        assert result is False

    def test_upsert_with_history_update_existing(self) -> None:
        """Test upsert_with_history updating existing record."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "entity_123" if x == 0 else False)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        data = {"id": "entity_123", "name": "Updated Entity"}

        result = EnhancedUpsertHandler.upsert_with_history(mock_session, "test_table", data, "id", track_changes=True)

        assert result is True
        assert mock_session.execute.call_count == 2

        # Check that history record was created with UPDATE action
        history_call = mock_session.execute.call_args_list[1]
        history_params = history_call[0][1]
        assert history_params["action"] == "UPDATE"


class TestSingletonInstances:
    """Test singleton instances."""

    def test_upsert_handler_singleton(self) -> None:
        """Test upsert_handler singleton instance."""
        assert upsert_handler is not None
        assert isinstance(upsert_handler, UpsertHandler)

    def test_enhanced_upsert_handler_singleton(self) -> None:
        """Test enhanced_upsert_handler singleton instance."""
        assert enhanced_upsert_handler is not None
        assert isinstance(enhanced_upsert_handler, EnhancedUpsertHandler)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_upsert_recall_empty_data(self) -> None:
        """Test upsert_recall with empty data."""
        mock_session = Mock()
        recall_data = {}

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is False
        mock_session.execute.assert_not_called()

    def test_upsert_recall_none_data(self) -> None:
        """Test upsert_recall with None data."""
        mock_session = Mock()
        recall_data = None

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is False
        mock_session.execute.assert_not_called()

    def test_bulk_upsert_empty_list(self) -> None:
        """Test bulk_upsert_recalls with empty list."""
        mock_session = Mock()
        recalls = []

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls)

        assert result["inserted"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        mock_session.execute.assert_not_called()

    def test_bulk_upsert_none_list(self) -> None:
        """Test bulk_upsert_recalls with None list."""
        mock_session = Mock()
        recalls = None

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls)

        assert result["inserted"] == 0
        assert result["updated"] == 0
        assert result["failed"] == 0
        mock_session.execute.assert_not_called()

    def test_upsert_subscription_empty_data(self) -> None:
        """Test upsert_subscription with empty data."""
        mock_session = Mock()
        subscription_data = {}

        result = UpsertHandler.upsert_subscription(mock_session, subscription_data)

        assert result is True  # Should still attempt to execute
        mock_session.execute.assert_called_once()

    def test_enhanced_upsert_empty_data(self) -> None:
        """Test enhanced upsert with empty data."""
        mock_session = Mock()
        data = {}

        result = EnhancedUpsertHandler.upsert_with_history(mock_session, "test_table", data, "id")

        assert result is True
        mock_session.execute.assert_called_once()


class TestParameterHandling:
    """Test parameter handling and defaults."""

    def test_upsert_recall_default_values(self) -> None:
        """Test upsert_recall with default values."""
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda x: "RECALL-001" if x == 0 else True)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result

        recall_data = {
            "recall_id": "RECALL-001",
            # Missing other fields - should use defaults
        }

        result = UpsertHandler.upsert_recall(mock_session, recall_data)

        assert result is True

        # Check that default values were used
        execute_call = mock_session.execute.call_args[0]
        params = execute_call[1]
        assert params["product_name"] == "Unknown Product"
        assert params["source_agency"] == "Unknown"
        assert params["country"] == "Unknown"

    def test_bulk_upsert_batch_size(self) -> None:
        """Test bulk_upsert_recalls with different batch sizes."""
        mock_session = Mock()
        mock_result = Mock()
        mock_session.execute.return_value = mock_result

        recalls = [{"recall_id": f"RECALL-{i:03d}", "product_name": f"Product {i}"} for i in range(5)]

        result = UpsertHandler.bulk_upsert_recalls(mock_session, recalls, batch_size=2)

        assert result["inserted"] == 5
        # Should execute multiple times due to batch size
        assert mock_session.execute.call_count >= 2
