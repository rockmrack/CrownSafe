"""Tests for core_infra/transactions.py"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from core_infra.transactions import (
    transaction, TransactionManager, OptimisticLock, 
    bulk_operation, transactional
)


class TestTransaction(unittest.TestCase):
    def setUp(self):
        self.mock_db = Mock(spec=Session)
    
    def test_transaction_context_manager(self):
        """Test basic transaction context manager"""
        with patch.object(self.mock_db, 'commit'):
            with transaction(self.mock_db) as session:
                self.assertIsNotNone(session)
            self.mock_db.commit.assert_called_once()
    
    def test_transaction_manager_initialization(self):
        """Test TransactionManager initialization"""
        manager = TransactionManager(self.mock_db, max_retries=3)
        self.assertIsNotNone(manager)
        self.assertEqual(manager.max_retries, 3)
    
    def test_optimistic_lock_check_version(self):
        """Test OptimisticLock version checking"""
        entity = Mock()
        entity.version = 1
        OptimisticLock.check_version(entity, 1)
        with self.assertRaises(ValueError):
            OptimisticLock.check_version(entity, 2)
    
    def test_optimistic_lock_increment_version(self):
        """Test OptimisticLock version increment"""
        entity = Mock()
        entity.version = 1
        OptimisticLock.increment_version(entity)
        self.assertEqual(entity.version, 2)


if __name__ == '__main__':
    unittest.main()
