"""
Search request validation with strict limits
Enforces bounded inputs for security and performance
"""

from typing import List, Optional, Literal
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, model_validator, constr, conlist
import re

# Type aliases for constrained strings
Str128 = constr(strip_whitespace=True, min_length=1, max_length=128)
Str64 = constr(strip_whitespace=True, min_length=1, max_length=64)
Str32 = constr(strip_whitespace=True, min_length=1, max_length=32)
Str16 = constr(strip_whitespace=True, min_length=1, max_length=16)

# Type alias for keyword lists
KeywordList = conlist(Str32, min_length=1, max_length=8)
AgencyList = conlist(Str32, min_length=1, max_length=10)


class SecureAdvancedSearchRequest(BaseModel):
    """
    Search request with strict validation and size limits
    """

    # Text search fields (capped length)
    query: Optional[Str128] = Field(
        None,
        description="General search query (max 128 chars)",
        examples=["baby formula", "crib recall"],
    )

    product: Optional[Str128] = Field(
        None,
        description="Product name search (max 128 chars)",
        examples=["Graco car seat", "Fisher-Price bouncer"],
    )

    # Keyword search (bounded list)
    keywords: Optional[KeywordList] = Field(
        None,
        description="Keywords for AND search (1-8 items, max 32 chars each)",
        examples=[["infant", "choking", "toy"]],
    )

    # Exact ID lookup (bounded)
    id: Optional[constr(strip_whitespace=True, min_length=3, max_length=64)] = Field(
        None,
        description="Exact recall ID (3-64 chars)",
        examples=["FDA-2025-1234", "CPSC-2025-0001"],
    )

    # Agency filter (bounded list)
    agencies: Optional[AgencyList] = Field(
        None,
        description="Filter by agencies (1-10 items)",
        examples=[["FDA", "CPSC", "NHTSA"]],
    )

    # Enum fields with strict values
    severity: Optional[Literal["low", "medium", "high", "critical"]] = Field(
        None, description="Severity level filter", examples=["high"]
    )

    riskCategory: Optional[
        Literal[
            "drug",
            "device",
            "food",
            "cosmetic",
            "supplement",
            "toy",
            "baby_product",
            "other",
        ]
    ] = Field(None, description="Risk category filter", examples=["toy"])

    # Date range (validated)
    date_from: Optional[date] = Field(
        None, description="Start date for recall date range", examples=["2024-01-01"]
    )

    date_to: Optional[date] = Field(
        None, description="End date for recall date range", examples=["2024-12-31"]
    )

    # Pagination (bounded)
    limit: int = Field(
        default=20, ge=1, le=50, description="Results per page (1-50)", examples=[20]
    )

    # Cursor (length limited)
    nextCursor: Optional[constr(max_length=512)] = Field(
        None,
        description="Pagination cursor (max 512 chars)",
        examples=["eyJ2IjoxLCJmIjoiYWJjZGVmIn0.SIGNATURE"],
    )

    @field_validator("query", "product")
    @classmethod
    def validate_text_fields(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate text search fields
        """
        if v is None:
            return v

        # Strip whitespace
        v = v.strip()

        # Check for empty after stripping
        if not v:
            return None

        # Check for SQL injection patterns
        sql_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute|script|javascript)\b)",
            r"(--|#|/\*|\*/|;)",
            r"('|\")\s*(or|and)\s*('|\")",
            r"(1\s*=\s*1|2\s*=\s*2)",
            r"(\bwaitfor\s+delay\b|\bsleep\s*\()",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid characters in search query")

        # Check for XSS patterns
        xss_patterns = [
            r"<\s*script",
            r"javascript\s*:",
            r"on\w+\s*=",  # onclick, onerror, etc.
            r"<\s*iframe",
            r"<\s*embed",
            r"<\s*object",
        ]

        for pattern in xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid HTML/script content in query")

        return v

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """
        Validate keyword list
        """
        if v is None:
            return v

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for keyword in v:
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower not in seen:
                seen.add(keyword_lower)
                unique.append(keyword.strip())

        if not unique:
            return None

        return unique[:8]  # Enforce max 8 keywords

    @field_validator("agencies")
    @classmethod
    def validate_agencies(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """
        Validate agency codes
        """
        if v is None:
            return v

        # Known valid agencies
        valid_agencies = {
            "FDA",
            "CPSC",
            "NHTSA",
            "USDA",
            "EPA",
            "FSIS",
            "CDC",
            "EU_SAFETY_GATE",
            "UK_OPSS",
            "HEALTH_CANADA",
            "AUSTRALIA_ACCC",
            "JAPAN_CAA",
        }

        validated = []
        for agency in v:
            agency_upper = agency.upper().strip()
            if agency_upper in valid_agencies:
                validated.append(agency_upper)

        return validated[:10] if validated else None

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_dates(cls, v: Optional[date]) -> Optional[date]:
        """
        Validate date ranges
        """
        if v is None:
            return v

        # Don't allow dates too far in past
        min_date = date(1900, 1, 1)
        if v < min_date:
            raise ValueError(f"Date must be after {min_date}")

        # Don't allow future dates beyond next year
        max_date = date.today().replace(year=date.today().year + 1)
        if v > max_date:
            raise ValueError("Date cannot be more than 1 year in future")

        return v

    @model_validator(mode="after")
    def validate_date_range(self):
        """
        Validate date range consistency
        """
        if self.date_from and self.date_to:
            if self.date_to < self.date_from:
                raise ValueError("date_to must be >= date_from")

        return self

    @model_validator(mode="after")
    def validate_search_criteria(self):
        """
        Ensure at least one search criterion is provided
        """
        # Check if ID is provided (exact lookup)
        if self.id:
            return self

        # Check if any text search is provided
        has_text_search = bool(self.query or self.product or self.keywords)

        # Check if any filters are provided
        has_filters = bool(
            self.agencies or self.severity or self.riskCategory or self.date_from or self.date_to
        )

        # If pagination cursor, allow without other criteria
        if self.nextCursor:
            return self

        # Otherwise need at least one criterion
        if not (has_text_search or has_filters):
            raise ValueError(
                "At least one search criterion required: query, product, keywords, or filters"
            )

        return self

    class Config:
        # Pydantic configuration
        str_strip_whitespace = True
        str_min_length = 1
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "product": "baby formula",
                "agencies": ["FDA", "CPSC"],
                "severity": "high",
                "limit": 20,
            }
        }


class RecallDetailRequest(BaseModel):
    """
    Request for recall detail endpoint
    """

    recall_id: constr(
        strip_whitespace=True, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9\-_]+$"
    ) = Field(
        ...,
        description="Recall ID (alphanumeric, dash, underscore only)",
        examples=["FDA-2025-1234", "CPSC_2025_0001"],
    )


# Export models
__all__ = [
    "SecureAdvancedSearchRequest",
    "RecallDetailRequest",
    "Str128",
    "Str64",
    "Str32",
    "Str16",
]
