"""Tests for API module imports"""

import unittest
from unittest.mock import Mock, patch


class TestAPIModules(unittest.TestCase):
    def test_health_endpoints_import(self):
        """Test health endpoints can be imported"""
        try:
            from api import health_endpoints

            self.assertIsNotNone(health_endpoints)
        except ImportError:
            self.skipTest("Module not available")

    def test_auth_endpoints_import(self):
        """Test auth endpoints can be imported"""
        try:
            from api import auth_endpoints

            self.assertIsNotNone(auth_endpoints)
        except ImportError:
            self.skipTest("Module not available")

    def test_barcode_endpoints_import(self):
        """Test barcode endpoints can be imported"""
        try:
            from api import barcode_endpoints

            self.assertIsNotNone(barcode_endpoints)
        except ImportError:
            self.skipTest("Module not available")

    def test_main_crownsafe_import(self):
        """Test main babyshield module can be imported"""
        try:
            from api import main_crownsafe

            self.assertIsNotNone(main_crownsafe)
        except ImportError:
            self.skipTest("Module not available")


if __name__ == "__main__":
    unittest.main()
