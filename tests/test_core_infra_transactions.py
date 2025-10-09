"""Tests for core_infra/transactions.py"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from core_infra.transactions import TransactionManager, OptimisticLock, bulk_operation


class TestTransactionManager(unittest.TestCase):
    def setUp(self):
        self.mock_db = Mock(spec=Session)

    def test_transaction_manager_init(self):
        manager = TransactionManager(self.mock_db, max_retries=5)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.max_retries, 5)
        self.assertEqual(manager.db, self.mock_db)

    def test_transaction_manager_default_retries(self):
        manager = TransactionManager(self.mock_db)
        self.assertEqual(manager.max_retries, 3)

    def test_is_retryable_error_deadlock(self):
        manager = TransactionManager(self.mock_db)
        error = SQLAlchemyError("deadlock detected")
        self.assertTrue(manager._is_retryable_error(error))

    def test_is_retryable_error_lock_timeout(self):
        manager = TransactionManager(self.mock_db)
        error = SQLAlchemyError("lock timeout exceeded")
        self.assertTrue(manager._is_retryable_error(error))

    def test_is_retryable_error_connection_lost(self):
        manager = TransactionManager(self.mock_db)
        error = SQLAlchemyError("connection lost")
        self.assertTrue(manager._is_retryable_error(error))

    def test_is_retryable_error_non_retryable(self):
        manager = TransactionManager(self.mock_db)
        error = SQLAlchemyError("constraint violation")
        self.assertFalse(manager._is_retryable_error(error))


class TestOptimisticLock(unittest.TestCase):
    def test_check_version_matching(self):
        entity = Mock()
        entity.version = 5
        # Should not raise
        OptimisticLock.check_version(entity, 5)

    def test_check_version_mismatch(self):
        entity = Mock()
        entity.version = 5
        with self.assertRaises(ValueError) as ctx:
            OptimisticLock.check_version(entity, 3)
        self.assertIn("Version mismatch", str(ctx.exception))

    def test_check_version_no_version_attr(self):
        entity = Mock(spec=[])
        # Should not raise if entity has no version
        OptimisticLock.check_version(entity, 1)

    def test_increment_version_existing(self):
        entity = Mock()
        entity.version = 10
        OptimisticLock.increment_version(entity)
        self.assertEqual(entity.version, 11)

    def test_increment_version_new(self):
        entity = Mock(spec=[])
        OptimisticLock.increment_version(entity)
        self.assertEqual(entity.version, 1)


class TestBulkOperation(unittest.TestCase):
    def test_bulk_operation_success(self):
        mock_db = Mock(spec=Session)
        items = [1, 2, 3, 4, 5]
        operation = Mock()

        with patch("core_infra.transactions.transaction"):
            processed, errors = bulk_operation(mock_db, items, operation, batch_size=2)

        self.assertEqual(processed, 5)
        self.assertEqual(len(errors), 0)

    def test_bulk_operation_empty_list(self):
        mock_db = Mock(spec=Session)
        items = []
        operation = Mock()

        with patch("core_infra.transactions.transaction"):
            processed, errors = bulk_operation(mock_db, items, operation)

        self.assertEqual(processed, 0)
        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
