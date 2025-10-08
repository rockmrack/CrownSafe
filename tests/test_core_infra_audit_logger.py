"""Tests for core_infra/audit_logger.py"""
import unittest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session
from core_infra.audit_logger import AuditLogger, AuditQuery


class TestAuditLogger(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock(spec=Session)
        self.audit_logger = AuditLogger(self.mock_db)
    
    def test_init_with_session(self):
        self.assertEqual(self.audit_logger.db_session, self.mock_db)
        self.assertIsNotNone(self.audit_logger.logger)
    
    def test_init_without_session(self):
        logger = AuditLogger()
        self.assertIsNone(logger.db_session)
    
    def test_calculate_diff_changed(self):
        old = {"name": "Alice", "age": 25}
        new = {"name": "Alice", "age": 26}
        diff = self.audit_logger._calculate_diff(old, new)
        self.assertIsNotNone(diff)
        self.assertIn("age", diff)
        self.assertEqual(diff["age"]["old"], 25)
        self.assertEqual(diff["age"]["new"], 26)
    
    def test_calculate_diff_no_changes(self):
        old = {"name": "Bob", "age": 30}
        new = {"name": "Bob", "age": 30}
        diff = self.audit_logger._calculate_diff(old, new)
        self.assertIsNone(diff)
    
    def test_calculate_diff_added_key(self):
        old = {"name": "Charlie"}
        new = {"name": "Charlie", "age": 35}
        diff = self.audit_logger._calculate_diff(old, new)
        self.assertIn("age", diff)
    
    def test_calculate_diff_removed_key(self):
        old = {"name": "Diana", "age": 40}
        new = {"name": "Diana"}
        diff = self.audit_logger._calculate_diff(old, new)
        self.assertIn("age", diff)
    
    def test_serialize_entity_with_to_dict(self):
        entity = Mock()
        entity.to_dict = Mock(return_value={"id": 1, "name": "Test"})
        result = self.audit_logger._serialize_entity(entity)
        self.assertEqual(result, {"id": 1, "name": "Test"})
    
    def test_serialize_entity_with_dict(self):
        # Create a simple object with __dict__ instead of Mock
        class SimpleEntity:
            def __init__(self):
                self.id = 2
                self.value = "data"
                self._private = "hidden"
        
        entity = SimpleEntity()
        result = self.audit_logger._serialize_entity(entity)
        self.assertIn("id", result)
        self.assertEqual(result["id"], 2)
        self.assertIn("value", result)
        self.assertNotIn("_private", result)
    
    def test_log_create(self):
        entity = Mock()
        entity.__class__.__name__ = "User"
        entity.id = 123
        entity.to_dict = Mock(return_value={"id": 123})
        self.audit_logger.log_create(entity)
        # Should not raise
    
    def test_log_update(self):
        entity = Mock()
        entity.__class__.__name__ = "Product"
        entity.id = 456
        entity.to_dict = Mock(return_value={"id": 456, "name": "New"})
        old_state = {"id": 456, "name": "Old"}
        self.audit_logger.log_update(entity, old_state)
        # Should not raise
    
    def test_log_delete(self):
        entity = Mock()
        entity.__class__.__name__ = "Order"
        entity.id = 789
        entity.to_dict = Mock(return_value={"id": 789})
        self.audit_logger.log_delete(entity)
        # Should not raise


class TestAuditQuery(unittest.TestCase):
    
    def test_init(self):
        mock_db = Mock(spec=Session)
        query = AuditQuery(mock_db)
        self.assertEqual(query.db, mock_db)


if __name__ == '__main__':
    unittest.main()