"""
Input validation and sanitization for BabyShield
Prevents SQL injection, XSS, and invalid data
"""

import re
from typing import Optional, Any
from pydantic import BaseModel, field_validator, EmailStr
import html
import bleach

# Barcode patterns
BARCODE_PATTERNS = {
    "UPC-A": r"^[0-9]{12}$",
    "UPC-E": r"^[0-9]{8}$",
    "EAN-13": r"^[0-9]{13}$",
    "EAN-8": r"^[0-9]{8}$",
    "GTIN": r"^[0-9]{14}$",
}

def validate_barcode(barcode: str) -> str:
    """
    Validate barcode format
    Prevents SQL injection by ensuring only numbers
    """
    if not barcode:
        raise ValueError("Barcode cannot be empty")
    
    # Remove any whitespace
    barcode = barcode.strip()
    
    # Check length
    if len(barcode) < 8 or len(barcode) > 14:
        raise ValueError(f"Invalid barcode length: {len(barcode)}")
    
    # Ensure only digits
    if not barcode.isdigit():
        raise ValueError("Barcode must contain only numbers")
    
    # Check against known patterns
    valid = False
    for pattern_name, pattern in BARCODE_PATTERNS.items():
        if re.match(pattern, barcode):
            valid = True
            break
    
    if not valid and len(barcode) not in [8, 12, 13, 14]:
        raise ValueError(f"Invalid barcode format: {barcode}")
    
    return barcode

def validate_model_number(model: str) -> str:
    """
    Validate model number
    Allows alphanumeric with some special chars
    """
    if not model:
        return ""
    
    # Remove dangerous characters
    model = model.strip()
    
    # Allow only safe characters
    if not re.match(r"^[A-Za-z0-9\-_\.\s]+$", model):
        raise ValueError("Model number contains invalid characters")
    
    # Limit length
    if len(model) > 100:
        raise ValueError("Model number too long")
    
    return model

def sanitize_html(text: str) -> str:
    """
    Sanitize HTML to prevent XSS attacks.
    Removes dangerous tags, attributes, and JavaScript URIs.
    """
    import re
    
    if not text:
        return ""
    
    # Remove javascript: URIs (case insensitive) - CRITICAL for XSS prevention
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    
    # Remove data: URIs
    text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
    
    # Remove vbscript: URIs
    text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Use bleach for additional sanitization if available
    try:
        import bleach
        # Allow only safe tags and attributes
        text = bleach.clean(
            text,
            tags=['p', 'br', 'strong', 'em', 'u', 'a'],
            attributes={'a': ['href', 'title']},
            strip=True
        )
    except ImportError:
        # If bleach not available, we already escaped HTML above
        pass
    
    return text
def validate_email(email: str) -> str:
    """
    Validate email format
    """
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email.lower()):
        raise ValueError("Invalid email format")
    
    # Limit length
    if len(email) > 255:
        raise ValueError("Email too long")
    
    return email.lower()

def validate_pagination(skip: int, limit: int) -> tuple[int, int]:
    """
    Validate pagination parameters
    """
    # Ensure non-negative
    if skip < 0:
        skip = 0
    
    # Limit maximum skip to prevent deep pagination
    if skip > 10000:
        raise ValueError("Pagination too deep")
    
    # Ensure reasonable limit
    if limit < 1:
        limit = 10
    if limit > 1000:
        limit = 1000
    
    return skip, limit

def validate_id(id_value: Any) -> int:
    """
    Validate database ID
    """
    try:
        id_int = int(id_value)
        if id_int < 1:
            raise ValueError("Invalid ID")
        return id_int
    except (TypeError, ValueError):
        raise ValueError(f"Invalid ID format: {id_value}")

def validate_search_query(query: str) -> str:
    """
    Validate and sanitize search queries to prevent SQL injection.
    Raises ValueError if dangerous patterns detected.
    """
    if not query:
        return ""
    
    query_upper = query.upper()
    
    # SQL injection patterns that should raise ValueError
    dangerous_patterns = [
        'DROP TABLE',
        'DROP DATABASE',
        'DELETE FROM',
        'INSERT INTO',
        'UPDATE ',
        'CREATE TABLE',
        'ALTER TABLE',
        'TRUNCATE',
        'EXEC',
        'EXECUTE',
        'UNION SELECT',
        'UNION ALL',
        '--',  # SQL comment
        '/*',  # SQL comment
        '*/',  # SQL comment
        'SCRIPT>',  # XSS
        'JAVASCRIPT:',  # XSS
        '<IFRAME',  # XSS
        'ONERROR=',  # XSS
    ]
    
    # Check for dangerous patterns
    for pattern in dangerous_patterns:
        if pattern in query_upper:
            raise ValueError(f"Dangerous pattern detected in search query: {pattern}")
    
    # Check for SQL injection indicators
    if ';' in query and ('DROP' in query_upper or 'DELETE' in query_upper or 'INSERT' in query_upper):
        raise ValueError("SQL injection attempt detected")
    
    # Limit query length
    if len(query) > 500:
        raise ValueError("Search query too long (max 500 characters)")
    
    return query.strip()
def validate_file_upload(filename: str, content_type: str, size: int) -> bool:
    """
    Validate file upload
    """
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}
    ALLOWED_CONTENT_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'application/pdf'
    }
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    # Check file extension
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type not allowed: {ext}")
    
    # Check content type
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"Content type not allowed: {content_type}")
    
    # Check file size
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {size} bytes")
    
    return True

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal
    """
    import os
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:240] + ext
    
    return filename

# Pydantic models with validation
class ValidatedSafetyCheckRequest(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_number field
    
    barcode: str
    model_number: Optional[str] = None
    
    @field_validator('barcode')
    @classmethod
    def validate_barcode_field(cls, v):
        return validate_barcode(v)
    
    @field_validator('model_number')
    @classmethod
    def validate_model_field(cls, v):
        if v:
            return validate_model_number(v)
        return v

class ValidatedPaginationParams(BaseModel):
    skip: int = 0
    limit: int = 100
    
    @field_validator('skip', 'limit')
    @classmethod
    def validate_pagination_fields(cls, v, info):
        if info.field_name == 'skip' and v < 0:
            v = 0
        if info.field_name == 'limit':
            if v < 1:
                v = 10
            if v > 1000:
                v = 1000
        return v

class ValidatedSearchRequest(BaseModel):
    query: str
    category: Optional[str] = None
    
    @field_validator('query')
    @classmethod
    def validate_search_field(cls, v):
        return validate_search_query(v)
    
    @field_validator('category')
    @classmethod
    def validate_category_field(cls, v):
        if v:
            # Whitelist of allowed categories
            ALLOWED_CATEGORIES = [
                'toys', 'furniture', 'electronics', 'clothing',
                'food', 'cosmetics', 'automotive', 'other'
            ]
            if v.lower() not in ALLOWED_CATEGORIES:
                raise ValueError(f"Invalid category: {v}")
        return v

# SQL injection prevention helper
def safe_sql_identifier(identifier: str) -> str:
    """
    Validate SQL identifier (table/column name)
    """
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    
    # Check against reserved words
    RESERVED_WORDS = {
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
        'CREATE', 'ALTER', 'TABLE', 'FROM', 'WHERE'
    }
    
    if identifier.upper() in RESERVED_WORDS:
        raise ValueError(f"Reserved word used as identifier: {identifier}")
    
    return identifier

# XSS prevention for JSON responses
def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize dictionary values
    """
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = sanitize_html(value)
        elif isinstance(value, dict):
            cleaned[key] = sanitize_dict(value)
        elif isinstance(value, list):
            cleaned[key] = [
                sanitize_html(item) if isinstance(item, str) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned
