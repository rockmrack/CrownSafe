"""Utilities package for API functionality."""

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
    "CacheableResponse",
    "PIIMasker",
    "PrivacyDataExporter",
    "add_cache_headers",
    "anonymize_ip",
    "calculate_sla_deadline",
    "check_if_modified_since",
    "check_if_none_match",
    "create_not_modified_response",
    "create_search_cursor",
    "detect_jurisdiction",
    "email_hash",
    "format_dsar_response",
    "generate_dsar_token",
    "hash_filters",
    # Cache utilities
    "http_date",
    "make_detail_etag",
    "make_etag",
    "make_search_etag",
    "mask_email",
    "mask_pii",
    # Privacy utilities
    "normalize_email",
    "parse_http_date",
    "privacy_audit_log",
    # Cursor utilities
    "sign_cursor",
    "validate_cursor_filters",
    "validate_email",
    "verify_cursor",
]
