"""Utilities package for API functionality"""

from .cursor import (
    create_search_cursor,
    hash_filters,
    sign_cursor,
    validate_cursor_filters,
    verify_cursor,
)
from .http_cache import (
    CacheableResponse,
    add_cache_headers,
    check_if_modified_since,
    check_if_none_match,
    create_not_modified_response,
    http_date,
    make_detail_etag,
    make_etag,
    make_search_etag,
    parse_http_date,
)
from .privacy import (
    PIIMasker,
    PrivacyDataExporter,
    anonymize_ip,
    calculate_sla_deadline,
    detect_jurisdiction,
    email_hash,
    format_dsar_response,
    generate_dsar_token,
    mask_email,
    mask_pii,
    normalize_email,
    privacy_audit_log,
    validate_email,
)

__all__ = [
    # Cursor utilities
    "sign_cursor",
    "verify_cursor",
    "create_search_cursor",
    "hash_filters",
    "validate_cursor_filters",
    # Cache utilities
    "http_date",
    "parse_http_date",
    "make_etag",
    "make_search_etag",
    "make_detail_etag",
    "check_if_none_match",
    "check_if_modified_since",
    "add_cache_headers",
    "create_not_modified_response",
    "CacheableResponse",
    # Privacy utilities
    "normalize_email",
    "validate_email",
    "email_hash",
    "mask_email",
    "mask_pii",
    "anonymize_ip",
    "detect_jurisdiction",
    "generate_dsar_token",
    "calculate_sla_deadline",
    "format_dsar_response",
    "privacy_audit_log",
    "PrivacyDataExporter",
    "PIIMasker",
]
