"""Tests for core_infra/validators.py"""
import unittest
from core_infra.validators import (
    validate_barcode, validate_model_number, validate_email,
    validate_pagination, validate_id, sanitize_html, 
    validate_search_query, sanitize_filename
)


class TestValidators(unittest.TestCase):
    
    def test_validate_barcode_valid(self):
        """Test valid barcode validation"""
        result = validate_barcode("012345678905")
        self.assertEqual(result, "012345678905")
    
    def test_validate_barcode_invalid(self):
        """Test invalid barcode validation"""
        with self.assertRaises(ValueError):
            validate_barcode("")
        with self.assertRaises(ValueError):
            validate_barcode("ABC123")
    
    def test_validate_email(self):
        """Test email validation"""
        valid_email = validate_email("test@example.com")
        self.assertEqual(valid_email, "test@example.com")
        with self.assertRaises(ValueError):
            validate_email("invalid-email")
    
    def test_validate_pagination(self):
        """Test pagination validation"""
        skip, limit = validate_pagination(0, 10)
        self.assertEqual(skip, 0)
        self.assertEqual(limit, 10)
    
    def test_validate_id(self):
        """Test ID validation"""
        valid_id = validate_id("123")
        self.assertEqual(valid_id, 123)
        with self.assertRaises(ValueError):
            validate_id("invalid")
    
    def test_sanitize_html(self):
        """Test HTML sanitization"""
        dangerous = "<script>alert('xss')</script>"
        safe = sanitize_html(dangerous)
        self.assertNotIn("<script>", safe)
    
    def test_validate_search_query(self):
        """Test search query validation"""
        safe_query = validate_search_query("baby toys")
        self.assertEqual(safe_query, "baby toys")
        with self.assertRaises(ValueError):
            validate_search_query("SELECT * FROM users; DROP TABLE")
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        dangerous = "../../../etc/passwd"
        safe = sanitize_filename(dangerous)
        self.assertNotIn("..", safe)


if __name__ == '__main__':
    unittest.main()
