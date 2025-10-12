"""
HTTP cache utilities for ETag, Last-Modified, and Cache-Control headers
Implements RFC 7232 for conditional requests
"""

import hashlib
import json
import email.utils as email_utils
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse


def http_date(dt: datetime) -> str:
    """
    Format datetime as HTTP date (RFC 7231)

    Args:
        dt: Datetime object (will be converted to UTC if needed)

    Returns:
        HTTP date string like "Mon, 23 Jun 2025 22:49:00 GMT"
    """
    # Ensure UTC timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)

    return email_utils.format_datetime(dt, usegmt=True)


def parse_http_date(date_str: str) -> Optional[datetime]:
    """
    Parse HTTP date string to datetime

    Args:
        date_str: HTTP date string

    Returns:
        Datetime object or None if invalid
    """
    try:
        # parsedate_to_datetime handles various HTTP date formats
        dt = email_utils.parsedate_to_datetime(date_str)
        # Ensure UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def make_etag(content: str, weak: bool = False) -> str:
    """
    Generate ETag from content

    Args:
        content: String content to hash
        weak: Whether to create a weak ETag

    Returns:
        ETag string with quotes (e.g., '"abc123"' or 'W/"abc123"')
    """
    # Generate hash
    hash_value = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]  # Use first 16 chars for brevity

    # Format as ETag
    if weak:
        return f'W/"{hash_value}"'
    else:
        return f'"{hash_value}"'


def make_search_etag(filters_hash: str, as_of: str, result_ids: List[str]) -> str:
    """
    Generate ETag for search results

    Args:
        filters_hash: Hash of search filters
        as_of: Snapshot timestamp
        result_ids: First few result IDs

    Returns:
        ETag string
    """
    # Combine components
    content = f"{filters_hash}:{as_of}:{''.join(result_ids[:5])}"
    return make_etag(content)


def make_detail_etag(item_id: str, last_updated: datetime) -> str:
    """
    Generate ETag for detail endpoint

    Args:
        item_id: Item identifier
        last_updated: Last modification time

    Returns:
        ETag string
    """
    # Use timestamp for uniqueness
    timestamp = last_updated.timestamp() if last_updated else 0
    content = f"{item_id}:{timestamp:.3f}"
    return make_etag(content)


def check_if_none_match(request: Request, etag: str) -> bool:
    """
    Check if ETag matches If-None-Match header

    Args:
        request: FastAPI request
        etag: Current ETag

    Returns:
        True if client has matching ETag (should return 304)
    """
    if_none_match = request.headers.get("If-None-Match")
    if not if_none_match:
        return False

    # Handle multiple ETags (comma-separated)
    client_etags = [tag.strip() for tag in if_none_match.split(",")]

    # Check for wildcard or exact match
    return "*" in client_etags or etag in client_etags


def check_if_modified_since(request: Request, last_modified: datetime) -> bool:
    """
    Check if resource was modified since If-Modified-Since header

    Args:
        request: FastAPI request
        last_modified: Last modification time

    Returns:
        True if NOT modified (should return 304)
    """
    if_modified_since = request.headers.get("If-Modified-Since")
    if not if_modified_since:
        return False

    # Parse client date
    client_date = parse_http_date(if_modified_since)
    if not client_date:
        return False

    # Compare (truncate to seconds for HTTP date precision)
    server_time = last_modified.replace(microsecond=0)
    client_time = client_date.replace(microsecond=0)

    return server_time <= client_time


def add_cache_headers(
    response: Response,
    etag: Optional[str] = None,
    last_modified: Optional[datetime] = None,
    max_age: Optional[int] = None,
    cache_control: Optional[str] = None,
    must_revalidate: bool = False,
    private: bool = False,
    no_cache: bool = False,
    no_store: bool = False,
) -> None:
    """
    Add cache-related headers to response

    Args:
        response: FastAPI response object
        etag: ETag value
        last_modified: Last modification time
        max_age: Max age in seconds
        cache_control: Custom Cache-Control header
        must_revalidate: Add must-revalidate directive
        private: Make cache private
        no_cache: Prevent caching
        no_store: Prevent storage
    """
    # Add ETag
    if etag:
        response.headers["ETag"] = etag

    # Add Last-Modified
    if last_modified:
        response.headers["Last-Modified"] = http_date(last_modified)

    # Build Cache-Control
    if cache_control:
        response.headers["Cache-Control"] = cache_control
    else:
        directives = []

        if no_store:
            directives.append("no-store")
        elif no_cache:
            directives.append("no-cache")
        else:
            # Caching allowed
            directives.append("private" if private else "public")

            if max_age is not None:
                directives.append(f"max-age={max_age}")

            if must_revalidate:
                directives.append("must-revalidate")

            # Add stale-while-revalidate for better UX
            if max_age and max_age > 0:
                stale_time = min(max_age // 10, 30)  # 10% of max_age, capped at 30s
                directives.append(f"stale-while-revalidate={stale_time}")

        if directives:
            response.headers["Cache-Control"] = ", ".join(directives)


def create_not_modified_response(etag: Optional[str] = None, cache_control: Optional[str] = None) -> Response:
    """
    Create a 304 Not Modified response

    Args:
        etag: ETag to include
        cache_control: Cache-Control header

    Returns:
        304 response with appropriate headers
    """
    response = Response(content=None, status_code=304, media_type=None)

    if etag:
        response.headers["ETag"] = etag

    if cache_control:
        response.headers["Cache-Control"] = cache_control

    return response


class CacheableResponse:
    """
    Helper class for creating cacheable responses
    """

    @staticmethod
    def search_response(
        content: Dict[str, Any],
        filters_hash: str,
        as_of: str,
        result_ids: List[str],
        request: Request,
        max_age: int = 60,
    ) -> Response:
        """
        Create cacheable search response with conditional request support
        """
        # Generate ETag
        etag = make_search_etag(filters_hash, as_of, result_ids)

        # Check conditional request
        if check_if_none_match(request, etag):
            return create_not_modified_response(etag=etag, cache_control=f"private, max-age={max_age}")

        # Create full response
        response = JSONResponse(content)
        add_cache_headers(response, etag=etag, max_age=max_age, private=True)

        return response

    @staticmethod
    def detail_response(
        content: Dict[str, Any],
        item_id: str,
        last_updated: datetime,
        request: Request,
        max_age: int = 300,
    ) -> Response:
        """
        Create cacheable detail response with conditional request support
        """
        # Generate ETag
        etag = make_detail_etag(item_id, last_updated)

        # Check conditional requests
        if check_if_none_match(request, etag):
            return create_not_modified_response(etag=etag, cache_control=f"public, max-age={max_age}")

        if check_if_modified_since(request, last_updated):
            return create_not_modified_response(etag=etag, cache_control=f"public, max-age={max_age}")

        # Create full response
        response = JSONResponse(content)
        add_cache_headers(
            response,
            etag=etag,
            last_modified=last_updated,
            max_age=max_age,
            private=False,
        )

        return response
