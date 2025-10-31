"""Privacy utility functions for GDPR/CCPA compliance
Handles email normalization, hashing, validation, and PII masking
"""

import hashlib
import json
import logging
import re
import secrets
from datetime import datetime, timezone
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$",
)

# PII patterns for masking
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}


def normalize_email(email: str) -> str:
    """Normalize email address for consistent processing

    Args:
        email: Email address to normalize

    Returns:
        Normalized email (lowercase, trimmed)

    """
    if not email:
        return ""
    return email.strip().lower()


def validate_email(email: str) -> bool:
    """Validate email address format

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise

    """
    if not email or len(email) > 320:  # RFC 5321 max length
        return False

    normalized = normalize_email(email)
    return bool(EMAIL_REGEX.match(normalized))


def email_hash(email: str) -> str:
    """Generate SHA-256 hash of normalized email

    Args:
        email: Email address to hash

    Returns:
        Hex digest of SHA-256 hash

    """
    normalized = normalize_email(email)
    return hashlib.sha256(normalized.encode()).hexdigest()


def mask_email(email: str) -> str:
    """Mask email address for privacy (e.g., j***@example.com)

    Args:
        email: Email address to mask

    Returns:
        Masked email address

    """
    if not email or "@" not in email:
        return "***"

    parts = email.split("@")
    username = parts[0]
    domain = parts[1]

    if len(username) <= 2:
        masked_username = "*" * len(username)
    else:
        masked_username = username[0] + "*" * (len(username) - 2) + username[-1]

    return f"{masked_username}@{domain}"


def mask_pii(text: str, mask: str = "***") -> str:
    """Mask PII in text content

    Args:
        text: Text to mask
        mask: Replacement string for PII

    Returns:
        Text with masked PII

    """
    if not text:
        return text

    masked = text
    for pattern_name, pattern in PII_PATTERNS.items():
        if pattern_name == "email":
            # Special handling for emails to preserve partial domain
            masked = pattern.sub(lambda m: mask_email(m.group()), masked)
        else:
            masked = pattern.sub(mask, masked)

    return masked


def anonymize_ip(ip_address: str) -> str:
    """Anonymize IP address by removing last octet (IPv4) or last 64 bits (IPv6)

    Args:
        ip_address: IP address to anonymize

    Returns:
        Anonymized IP address

    """
    if not ip_address:
        return ""

    # IPv4
    if "." in ip_address:
        parts = ip_address.split(".")
        if len(parts) == 4:
            parts[3] = "0"
            return ".".join(parts)

    # IPv6
    elif ":" in ip_address:
        parts = ip_address.split(":")
        if len(parts) >= 4:
            # Zero out last 4 segments (64 bits)
            for i in range(max(0, len(parts) - 4), len(parts)):
                parts[i] = "0"
            return ":".join(parts)

    return ip_address


def detect_jurisdiction(ip_address: str | None = None, country_code: str | None = None) -> str:
    """Detect privacy jurisdiction based on location indicators

    Args:
        ip_address: Client IP address
        country_code: ISO country code

    Returns:
        Jurisdiction code (gdpr, ccpa, pipeda, etc.)

    """
    # This is a simplified version. In production, you'd use a GeoIP service

    if country_code:
        country_code = country_code.upper()

        # European Union countries (GDPR)
        eu_countries = {
            "AT",
            "BE",
            "BG",
            "HR",
            "CY",
            "CZ",
            "DK",
            "EE",
            "FI",
            "FR",
            "DE",
            "GR",
            "HU",
            "IE",
            "IT",
            "LV",
            "LT",
            "LU",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SK",
            "SI",
            "ES",
            "SE",
        }

        if country_code in eu_countries:
            return "gdpr"
        elif country_code == "GB":
            return "uk_gdpr"
        elif country_code == "US":
            # Could be more specific with state detection for CCPA
            return "ccpa"
        elif country_code == "CA":
            return "pipeda"
        elif country_code == "BR":
            return "lgpd"
        elif country_code == "JP":
            return "appi"

    return "other"


def generate_dsar_token() -> str:
    """Generate secure token for DSAR verification

    Returns:
        URL-safe token

    """
    return secrets.token_urlsafe(48)


def calculate_sla_deadline(jurisdiction: str, submitted_at: datetime | None = None) -> datetime:
    """Calculate SLA deadline based on jurisdiction

    Args:
        jurisdiction: Privacy jurisdiction code
        submitted_at: Request submission time

    Returns:
        Deadline datetime

    """
    from datetime import timedelta

    if submitted_at is None:
        submitted_at = datetime.now(timezone.utc)

    # SLA by jurisdiction (in days)
    sla_days = {
        "gdpr": 30,
        "uk_gdpr": 30,
        "ccpa": 45,
        "pipeda": 30,
        "lgpd": 15,
        "appi": 30,
        "other": 30,
    }

    days = sla_days.get(jurisdiction, 30)
    return submitted_at + timedelta(days=days)


def format_dsar_response(request_type: str, status: str = "queued", jurisdiction: str = "other") -> dict[str, Any]:
    """Format standard DSAR response

    Args:
        request_type: Type of request (export, delete, etc.)
        status: Current status
        jurisdiction: Privacy jurisdiction

    Returns:
        Formatted response dictionary

    """
    sla_days = {
        "export": {"gdpr": 30, "ccpa": 45, "other": 30},
        "delete": {"gdpr": 30, "ccpa": 45, "other": 30},
        "rectify": {"gdpr": 30, "ccpa": 45, "other": 30},
    }

    days = sla_days.get(request_type, {}).get(jurisdiction, 30)

    messages = {
        "export": f"Export request received. We will email you within {days} days.",
        "delete": f"Deletion request received. We will confirm via email within {days} days.",
        "rectify": f"Rectification request received. We will update and confirm within {days} days.",
        "access": f"Access request received. We will provide information within {days} days.",
        "restrict": f"Processing restriction request received. We will confirm within {days} days.",
        "object": f"Objection request received. We will respond within {days} days.",
    }

    return {
        "message": messages.get(request_type, f"Request received. We will respond within {days} days."),
        "sla_days": days,
        "status": status,
        "request_type": request_type,
        "jurisdiction": jurisdiction,
    }


def privacy_audit_log(func):
    """Decorator to audit privacy-related operations

    Usage:
        @privacy_audit_log
        def process_dsar_request(...):
            ...
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now(timezone.utc)
        operation = func.__name__

        try:
            # Log operation start
            logger.info(
                f"Privacy operation started: {operation}",
                extra={"operation": operation, "timestamp": start_time.isoformat()},
            )

            # Execute function
            result = await func(*args, **kwargs)

            # Log success
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Privacy operation completed: {operation}",
                extra={
                    "operation": operation,
                    "duration_seconds": duration,
                    "status": "success",
                },
            )

            return result

        except Exception as e:
            # Log failure
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(
                f"Privacy operation failed: {operation}",
                extra={
                    "operation": operation,
                    "duration_seconds": duration,
                    "status": "error",
                    "error": str(e),
                },
            )
            raise

    return wrapper


class PrivacyDataExporter:
    """Helper class for exporting user data in various formats
    """

    @staticmethod
    def to_json(data: dict[str, Any], pretty: bool = True) -> str:
        """Export data as JSON

        Args:
            data: Data to export
            pretty: Whether to format JSON with indentation

        Returns:
            JSON string

        """
        if pretty:
            return json.dumps(data, indent=2, default=str, ensure_ascii=False)
        return json.dumps(data, default=str, ensure_ascii=False)

    @staticmethod
    def to_csv(data: list[dict[str, Any]]) -> str:
        """Export data as CSV

        Args:
            data: List of dictionaries to export

        Returns:
            CSV string

        """
        import csv
        import io

        if not data:
            return ""

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()

    @staticmethod
    def create_export_package(user_data: dict[str, Any]) -> dict[str, Any]:
        """Create comprehensive data export package

        Args:
            user_data: User data to export

        Returns:
            Export package with metadata

        """
        return {
            "export_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "format_version": "1.0",
                "data_categories": list(user_data.keys()),
                "record_count": sum(len(v) if isinstance(v, list) else 1 for v in user_data.values()),
            },
            "user_data": user_data,
            "data_sources": {
                "primary_database": "PostgreSQL",
                "file_storage": "AWS S3",
                "cache": "Redis",
            },
            "retention_policy": {
                "support_emails": "1 year",
                "crash_logs": "90 days",
                "api_logs": "30 days",
                "dsar_records": "3 years",
            },
        }


class PIIMasker:
    """Advanced PII masking for logs and responses
    """

    def __init__(self, custom_patterns: dict[str, re.Pattern] | None = None) -> None:
        """Initialize PII masker

        Args:
            custom_patterns: Additional patterns to mask

        """
        self.patterns = PII_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def mask_dict(self, data: dict[str, Any], sensitive_keys: list[str] | None = None) -> dict[str, Any]:
        """Mask PII in dictionary

        Args:
            data: Dictionary to mask
            sensitive_keys: Additional keys to mask entirely

        Returns:
            Dictionary with masked PII

        """
        if not data:
            return data

        sensitive_keys = sensitive_keys or ["password", "token", "api_key", "secret"]
        masked = {}

        for key, value in data.items():
            if any(sk in key.lower() for sk in sensitive_keys):
                masked[key] = "***REDACTED***"
            elif isinstance(value, str):
                masked[key] = mask_pii(value)
            elif isinstance(value, dict):
                masked[key] = self.mask_dict(value, sensitive_keys)
            elif isinstance(value, list):
                masked[key] = [mask_pii(item) if isinstance(item, str) else item for item in value]
            else:
                masked[key] = value

        return masked


# Export all utilities
__all__ = [
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
    "EMAIL_REGEX",
    "PII_PATTERNS",
]
