"""
Unit tests for input validators
"""

import pytest
from core_infra.validators import (
    validate_barcode,
    validate_email,
    validate_model_number,
    sanitize_html,
    validate_pagination,
    validate_search_query,
)


class TestBarcodeValidation:
    """Test barcode validation"""

    def test_valid_barcodes(self):
        """Test valid barcode formats"""
        valid_barcodes = [
            "123456789012",  # UPC-A
            "12345678",  # UPC-E
            "1234567890123",  # EAN-13
            "12345678901234",  # GTIN
        ]

        for barcode in valid_barcodes:
            assert validate_barcode(barcode) == barcode

    def test_invalid_barcodes(self):
        """Test invalid barcode formats"""
        invalid_barcodes = [
            "",  # Empty
            "12345",  # Too short
            "123456789012345",  # Too long
            "12345ABC",  # Contains letters
            "123-456-789",  # Contains special chars
            "'; DROP TABLE;",  # SQL injection attempt
        ]

        for barcode in invalid_barcodes:
            with pytest.raises(ValueError):
                validate_barcode(barcode)

    def test_barcode_whitespace(self):
        """Test barcode with whitespace"""
        assert validate_barcode("  123456789012  ") == "123456789012"


class TestEmailValidation:
    """Test email validation"""

    def test_valid_emails(self):
        """Test valid email formats"""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "user+tag@example.org",
        ]

        for email in valid_emails:
            assert validate_email(email) == email.lower()

    def test_invalid_emails(self):
        """Test invalid email formats"""
        invalid_emails = [
            "",
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError):
                validate_email(email)


class TestSanitization:
    """Test HTML sanitization"""

    def test_html_sanitization(self):
        """Test XSS prevention"""
        dangerous_inputs = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror='alert(1)'>",
            "javascript:alert('XSS')",
            "<iframe src='evil.com'></iframe>",
        ]

        for input_str in dangerous_inputs:
            sanitized = sanitize_html(input_str)
            assert "<script>" not in sanitized
            assert "javascript:" not in sanitized
            assert "<iframe>" not in sanitized

    def test_safe_text(self):
        """Test that safe text is preserved"""
        safe_text = "This is safe text with numbers 123"
        assert sanitize_html(safe_text) == safe_text


class TestPagination:
    """Test pagination validation"""

    def test_valid_pagination(self):
        """Test valid pagination params"""
        skip, limit = validate_pagination(0, 100)
        assert skip == 0
        assert limit == 100

    def test_negative_skip(self):
        """Test negative skip correction"""
        skip, limit = validate_pagination(-10, 50)
        assert skip == 0
        assert limit == 50

    def test_excessive_limit(self):
        """Test limit capping"""
        skip, limit = validate_pagination(0, 5000)
        assert skip == 0
        assert limit == 1000  # Capped at 1000

    def test_excessive_skip(self):
        """Test deep pagination prevention"""
        with pytest.raises(ValueError):
            validate_pagination(20000, 100)


class TestSearchQuery:
    """Test search query validation"""

    def test_safe_queries(self):
        """Test safe search queries"""
        safe_queries = [
            "baby monitor",
            "crib recall 2024",
            "safety gate",
        ]

        for query in safe_queries:
            result = validate_search_query(query)
            assert isinstance(result, str)

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        dangerous_queries = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "UNION SELECT * FROM users",
        ]

        for query in dangerous_queries:
            with pytest.raises(ValueError):
                validate_search_query(query)

    def test_query_length_limit(self):
        """Test query length limiting"""
        long_query = "a" * 1000
        result = validate_search_query(long_query)
        assert len(result) <= 500


class TestModelNumber:
    """Test model number validation"""

    def test_valid_model_numbers(self):
        """Test valid model numbers"""
        valid_models = [
            "ABC-123",
            "Model_2024",
            "XYZ.456",
            "Product 789",
        ]

        for model in valid_models:
            assert validate_model_number(model) == model

    def test_invalid_model_numbers(self):
        """Test invalid model numbers"""
        invalid_models = [
            "Model'; DROP TABLE;",
            "ABC<script>",
            "a" * 200,  # Too long
        ]

        for model in invalid_models:
            with pytest.raises(ValueError):
                validate_model_number(model)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
