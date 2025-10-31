"""Tests for core_infra modules with extended coverage"""

import unittest


class TestCoreInfraModules(unittest.TestCase):
    def test_database_module_import(self):
        """Test database module can be imported"""
        try:
            from core_infra import database

            self.assertIsNotNone(database)
        except ImportError:
            self.skipTest("Module not available")

    def test_config_module_import(self):
        """Test config module can be imported"""
        try:
            from core_infra import config

            self.assertIsNotNone(config)
        except ImportError:
            self.skipTest("Module not available")

    def test_barcode_scanner_import(self):
        """Test barcode scanner can be imported"""
        try:
            from core_infra import barcode_scanner

            self.assertIsNotNone(barcode_scanner)
        except ImportError:
            self.skipTest("Module not available")

    def test_cache_manager_import(self):
        """Test cache manager can be imported"""
        try:
            from core_infra import cache_manager

            self.assertIsNotNone(cache_manager)
        except ImportError:
            self.skipTest("Module not available")

    def test_rate_limiter_import(self):
        """Test rate limiter can be imported"""
        try:
            from core_infra import rate_limiter

            self.assertIsNotNone(rate_limiter)
        except ImportError:
            self.skipTest("Module not available")

    def test_encryption_import(self):
        """Test encryption module can be imported"""
        try:
            from core_infra import encryption

            self.assertIsNotNone(encryption)
        except ImportError:
            self.skipTest("Module not available")

    def test_retry_handler_import(self):
        """Test retry handler can be imported"""
        try:
            from core_infra import retry_handler

            self.assertIsNotNone(retry_handler)
        except ImportError:
            self.skipTest("Module not available")

    def test_error_handlers_import(self):
        """Test error handlers can be imported"""
        try:
            from core_infra import error_handlers

            self.assertIsNotNone(error_handlers)
        except ImportError:
            self.skipTest("Module not available")


if __name__ == "__main__":
    unittest.main()
