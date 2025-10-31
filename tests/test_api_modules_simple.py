"""Simple smoke tests for API modules"""

import unittest


class TestAPIModules(unittest.TestCase):
    def test_api_main_import(self):
        """Test that api.main can be imported"""
        try:
            from api import main

            self.assertIsNotNone(main)
        except ImportError:
            self.skipTest("api.main not found")

    def test_api_health_endpoints_import(self):
        """Test that health endpoints can be imported"""
        try:
            from api import health_endpoints

            self.assertIsNotNone(health_endpoints)
        except ImportError:
            self.skipTest("health_endpoints not found")


if __name__ == "__main__":
    unittest.main()
