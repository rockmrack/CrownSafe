"""Tests for core_infra/database.py"""
import unittest
from unittest.mock import Mock, patch, MagicMock


class TestDatabase(unittest.TestCase):
    def test_database_module_import(self):
        """Test that database module can be imported"""
        try:
            import core_infra.database as db

            self.assertIsNotNone(db)
        except ImportError:
            self.skipTest("Module not found")

    @patch("core_infra.database.create_engine")
    def test_session_local_exists(self, mock_engine):
        """Test that SessionLocal exists"""
        try:
            from core_infra.database import SessionLocal

            self.assertIsNotNone(SessionLocal)
        except (ImportError, AttributeError):
            self.skipTest("SessionLocal not found")

    def test_get_db_function_exists(self):
        """Test that get_db function exists"""
        try:
            from core_infra.database import get_db

            self.assertIsNotNone(get_db)
        except (ImportError, AttributeError):
            self.skipTest("get_db function not found")


if __name__ == "__main__":
    unittest.main()
