"""
Comprehensive Input Validation Middleware
Prevents SQL injection, XSS, and other injection attacks
"""

import re
import logging
from typing import Any, Dict, Optional, List
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, validator, Field
from enum import Enum

logger = logging.getLogger(__name__)


class BarcodeFormat(str, Enum):
    """Supported barcode formats"""

    UPC = "upc"
    EAN = "ean"
    CODE128 = "code128"
    QR = "qr"
    DATAMATRIX = "datamatrix"
    GS1 = "gs1"


class InputValidator:
    """Centralized input validation for BabyShield API"""

    # Regex patterns for validation
    PATTERNS = {
        "barcode": r"^[0-9]{8,14}$",  # UPC/EAN barcodes
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "user_id": r"^[0-9]+$",
        "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "alphanumeric": r"^[a-zA-Z0-9]+$",
        "safe_text": r"^[a-zA-Z0-9\s\-_.()]+$",  # No special chars that could be SQL/XSS
        "model_number": r"^[a-zA-Z0-9\-_./#]+$",
        "phone": r"^\+?[0-9]{10,15}$",
        "date": r"^\d{4}-\d{2}-\d{2}$",  # ISO 8601
    }

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r"(<script|<iframe|<object|<embed)",  # XSS
        r"(union\s+select|drop\s+table|insert\s+into|delete\s+from)",  # SQL injection
        r"(javascript:|data:text\/html|vbscript:)",  # Protocol injection
        r"(\.\.\/|\.\.\\)",  # Path traversal
        r"(\$\{|\{\{)",  # Template injection
    ]

    # Length limits
    MAX_LENGTHS = {
        "barcode": 50,
        "email": 255,
        "product_name": 500,
        "description": 5000,
        "comment": 2000,
        "search_query": 200,
        "model_number": 100,
    }

    @classmethod
    def validate_barcode(cls, barcode: str) -> str:
        """
        Validate barcode format

        Args:
            barcode: Barcode string to validate

        Returns:
            Cleaned barcode string

        Raises:
            ValueError: If barcode is invalid
        """
        if not barcode:
            raise ValueError("Barcode cannot be empty")

        # Remove whitespace
        barcode = barcode.strip()

        # Check length
        if len(barcode) > cls.MAX_LENGTHS["barcode"]:
            raise ValueError(
                f"Barcode too long (max {cls.MAX_LENGTHS['barcode']} characters)"
            )

        # Check for dangerous patterns
        if cls._contains_dangerous_pattern(barcode):
            raise ValueError("Barcode contains invalid characters")

        # Allow alphanumeric + some special chars for GS1 codes
        if not re.match(r"^[0-9A-Za-z\-_.\(\)\[\]]+$", barcode):
            raise ValueError("Barcode contains invalid characters")

        return barcode

    @classmethod
    def validate_email(cls, email: str) -> str:
        """Validate email address"""
        if not email:
            raise ValueError("Email cannot be empty")

        email = email.strip().lower()

        if len(email) > cls.MAX_LENGTHS["email"]:
            raise ValueError(
                f"Email too long (max {cls.MAX_LENGTHS['email']} characters)"
            )

        if not re.match(cls.PATTERNS["email"], email):
            raise ValueError("Invalid email format")

        return email

    @classmethod
    def validate_user_id(cls, user_id: Any) -> int:
        """Validate user ID"""
        try:
            user_id = int(user_id)
            if user_id <= 0:
                raise ValueError("User ID must be positive")
            return user_id
        except (ValueError, TypeError):
            raise ValueError("Invalid user ID format")

    @classmethod
    def validate_product_name(cls, name: str) -> str:
        """Validate product name"""
        if not name:
            raise ValueError("Product name cannot be empty")

        name = name.strip()

        if len(name) > cls.MAX_LENGTHS["product_name"]:
            raise ValueError(
                f"Product name too long (max {cls.MAX_LENGTHS['product_name']} characters)"
            )

        if cls._contains_dangerous_pattern(name):
            raise ValueError("Product name contains invalid content")

        # Remove any HTML tags
        name = re.sub(r"<[^>]+>", "", name)

        return name

    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate search query"""
        if not query:
            raise ValueError("Search query cannot be empty")

        query = query.strip()

        if len(query) > cls.MAX_LENGTHS["search_query"]:
            raise ValueError(
                f"Search query too long (max {cls.MAX_LENGTHS['search_query']} characters)"
            )

        if cls._contains_dangerous_pattern(query):
            raise ValueError("Search query contains invalid content")

        return query

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """
        Remove HTML tags and dangerous content from text

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove script content
        text = re.sub(
            r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL
        )

        # Remove inline event handlers
        text = re.sub(r'on\w+\s*=\s*["\'].*?["\']', "", text, flags=re.IGNORECASE)

        return text

    @classmethod
    def _contains_dangerous_pattern(cls, text: str) -> bool:
        """Check if text contains dangerous patterns"""
        text_lower = text.lower()
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected: {pattern}")
                return True
        return False

    @classmethod
    def validate_pagination(cls, limit: int, offset: int) -> tuple[int, int]:
        """
        Validate and normalize pagination parameters

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (validated_limit, validated_offset)
        """
        # Limit range: 1-100
        limit = max(1, min(limit, 100))

        # Offset must be non-negative
        offset = max(0, offset)

        # Prevent extremely large offsets (potential DoS)
        if offset > 10000:
            raise ValueError("Offset too large (max 10000)")

        return limit, offset

    @classmethod
    def validate_date_range(
        cls, date_from: Optional[str], date_to: Optional[str]
    ) -> tuple[Optional[str], Optional[str]]:
        """Validate date range"""
        if date_from and not re.match(cls.PATTERNS["date"], date_from):
            raise ValueError("Invalid date_from format (use YYYY-MM-DD)")

        if date_to and not re.match(cls.PATTERNS["date"], date_to):
            raise ValueError("Invalid date_to format (use YYYY-MM-DD)")

        if date_from and date_to and date_from > date_to:
            raise ValueError("date_from must be before date_to")

        return date_from, date_to


class SecureRequestValidator:
    """Middleware for validating all incoming requests"""

    MAX_BODY_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_URL_LENGTH = 2000

    @classmethod
    async def validate_request(cls, request: Request):
        """
        Validate incoming request

        Raises:
            HTTPException: If request is invalid or dangerous
        """
        # Check URL length
        if len(str(request.url)) > cls.MAX_URL_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="Request URL too long",
            )

        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > cls.MAX_BODY_SIZE:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Request body too large (max {cls.MAX_BODY_SIZE} bytes)",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header",
                )

        # Check for suspicious headers
        suspicious_headers = ["x-forwarded-host", "x-original-url", "x-rewrite-url"]
        for header in suspicious_headers:
            if header in request.headers:
                logger.warning(f"Suspicious header detected: {header}")


# Pydantic validators for common fields
def validate_barcode_field(v: str) -> str:
    """Pydantic validator for barcode fields"""
    return InputValidator.validate_barcode(v)


def validate_email_field(v: str) -> str:
    """Pydantic validator for email fields"""
    return InputValidator.validate_email(v)


def validate_user_id_field(v: Any) -> int:
    """Pydantic validator for user_id fields"""
    return InputValidator.validate_user_id(v)


def validate_product_name_field(v: str) -> str:
    """Pydantic validator for product name fields"""
    return InputValidator.validate_product_name(v)


# Example Pydantic models with validation
class SafeBarcodeScanRequest(BaseModel):
    """Validated barcode scan request"""

    barcode: str = Field(..., description="Barcode to scan")
    user_id: int = Field(..., gt=0, description="User ID")
    barcode_type: Optional[BarcodeFormat] = Field(None, description="Barcode format")

    @validator("barcode")
    def validate_barcode(cls, v):
        return InputValidator.validate_barcode(v)

    @validator("user_id")
    def validate_user_id(cls, v):
        return InputValidator.validate_user_id(v)


class SafeSearchRequest(BaseModel):
    """Validated search request"""

    query: str = Field(..., min_length=1, max_length=200, description="Search query")
    limit: int = Field(20, ge=1, le=100, description="Results per page")
    offset: int = Field(0, ge=0, le=10000, description="Results to skip")

    @validator("query")
    def validate_query(cls, v):
        return InputValidator.validate_search_query(v)
