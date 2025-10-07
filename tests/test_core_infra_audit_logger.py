"""Tests for core_infra/audit_logger.py"""
import unittest
from unittest.mock import Mock, MagicMock
from sqlalchemy.orm import Session
from core_infra.audit_logger import AuditLogger, AuditQuery, audit_action


class TestAuditLogger(unittest.TestCase):
    
    def setUp(self):
        self.mock_db = Mock(spec=Session)
        self.audit_logger = AuditLogger(self.mock_db)
    
    def test_audit_logger_initialization(self):
        """Test AuditLogger initialization"""
        self.assertIsNotNone(self.audit_logger)
        self.assertEqual(self.audit_logger.db_session, self.mock_db)
    
    def test_log_create(self):
        """Test logging entity creation"""
        mock_entity = Mock()
        mock_entity.__class__.__name__ = "TestEntity"
        mock_entity.id = 123
        self.audit_logger.log_create(mock_entity)
        self.assertIsNotNone(self.audit_logger.logger)
    
    def test_calculate_diff(self):
        """Test diff calculation"""
        old = {"name": "John", "age": 30}
        new = {"name": "John", "age": 31}
        diff = self.audit_logger._calculate_diff(old, new)
        self.assertIsNotNone(diff)
        self.assertIn("age", diff)
    
    def test_serialize_entity(self):
        """Test entity serialization"""
        mock_entity = Mock()
        mock_entity.to_dict = Mock(return_value={"id": 1, "name": "test"})
        result = self.audit_logger._serialize_entity(mock_entity)
        self.assertEqual(result, {"id": 1, "name": "test"})
    
    def test_audit_query_initialization(self):
        """Test AuditQuery initialization"""
        query = AuditQuery(self.mock_db)
        self.assertIsNotNone(query)
        self.assertEqual(query.db, self.mock_db)
    
    def test_audit_action_decorator(self):
        """Test audit_action decorator"""
        @audit_action("TEST", "TestEntity")
        def test_function():
            return "success"
        result = test_function()
        self.assertEqual(result, "success")


if __name__ == '__main__':
    unittest.main()
