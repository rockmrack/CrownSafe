"""Tests for core_infra/validators.py"""

import unittest
from core_infra.validators import (
    validate_barcode,
    validate_email,
    validate_pagination,
    validate_id,
    sanitize_html,
    validate_search_query,
    sanitize_filename,
    validate_model_number,
    safe_sql_identifier,
)


class TestValidators(unittest.TestCase):
    def test_validate_barcode_valid_upc_a(self):
        result = validate_barcode("012345678905")
        self.assertEqual(result, "012345678905")

    def test_validate_barcode_valid_ean13(self):
        result = validate_barcode("0123456789012")
        self.assertEqual(result, "0123456789012")

    def test_validate_barcode_empty(self):
        with self.assertRaises(ValueError):
            validate_barcode("")

    def test_validate_barcode_non_numeric(self):
        with self.assertRaises(ValueError):
            validate_barcode("ABC123DEF456")

    def test_validate_barcode_too_short(self):
        with self.assertRaises(ValueError):
            validate_barcode("123")

    def test_validate_email_valid(self):
        result = validate_email("test@example.com")
        self.assertEqual(result, "test@example.com")

    def test_validate_email_valid_subdomain(self):
        result = validate_email("user@mail.example.com")
        self.assertEqual(result, "user@mail.example.com")

    def test_validate_email_invalid_format(self):
        with self.assertRaises(ValueError):
            validate_email("not-an-email")

    def test_validate_email_no_domain(self):
        with self.assertRaises(ValueError):
            validate_email("user@")

    def test_validate_pagination_valid(self):
        skip, limit = validate_pagination(0, 10)
        self.assertEqual(skip, 0)
        self.assertEqual(limit, 10)

    def test_validate_pagination_negative_skip(self):
        skip, limit = validate_pagination(-5, 10)
        self.assertEqual(skip, 0)

    def test_validate_pagination_high_limit(self):
        skip, limit = validate_pagination(0, 5000)
        self.assertEqual(limit, 1000)

    def test_validate_pagination_low_limit(self):
        skip, limit = validate_pagination(0, 0)
        self.assertEqual(limit, 10)

    def test_validate_id_valid(self):
        result = validate_id("123")
        self.assertEqual(result, 123)

    def test_validate_id_valid_int(self):
        result = validate_id(456)
        self.assertEqual(result, 456)

    def test_validate_id_invalid_string(self):
        with self.assertRaises(ValueError):
            validate_id("abc")

    def test_validate_id_negative(self):
        with self.assertRaises(ValueError):
            validate_id("-1")

    def test_sanitize_html_script_tag(self):
        result = sanitize_html("<script>alert('xss')</script>")
        self.assertNotIn("<script>", result)

    def test_sanitize_html_empty(self):
        result = sanitize_html("")
        self.assertEqual(result, "")

    def test_sanitize_html_normal_text(self):
        result = sanitize_html("Hello World")
        self.assertEqual(result, "Hello World")

    def test_validate_search_query_safe(self):
        result = validate_search_query("baby toys")
        self.assertEqual(result, "baby toys")

    def test_validate_search_query_with_drop(self):
        with self.assertRaises(ValueError):
            validate_search_query("SELECT * FROM users; DROP TABLE users")

    def test_validate_search_query_with_union(self):
        with self.assertRaises(ValueError):
            validate_search_query("test' UNION SELECT")

    def test_sanitize_filename_normal(self):
        result = sanitize_filename("document.pdf")
        self.assertEqual(result, "document.pdf")

    def test_sanitize_filename_path_traversal(self):
        result = sanitize_filename("../../../etc/passwd")
        self.assertNotIn("..", result)
        self.assertNotIn("/", result)

    def test_validate_model_number_valid(self):
        result = validate_model_number("MODEL-123-ABC")
        self.assertEqual(result, "MODEL-123-ABC")

    def test_validate_model_number_empty(self):
        result = validate_model_number("")
        self.assertEqual(result, "")

    def test_safe_sql_identifier_valid(self):
        result = safe_sql_identifier("user_table")
        self.assertEqual(result, "user_table")

    def test_safe_sql_identifier_invalid_chars(self):
        with self.assertRaises(ValueError):
            safe_sql_identifier("user-table!")

    def test_safe_sql_identifier_reserved_word(self):
        with self.assertRaises(ValueError):
            safe_sql_identifier("SELECT")


if __name__ == "__main__":
    unittest.main()
