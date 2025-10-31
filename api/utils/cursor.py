"""Cursor utilities for secure, opaque pagination tokens
Uses HMAC-SHA256 for signing to prevent tampering
"""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, UTC
from typing import Any


def _b64u_encode(data: bytes) -> str:
    """URL-safe base64 encode without padding"""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    """URL-safe base64 decode with padding restoration"""
    # Add padding if needed
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def sign_cursor(payload: dict[str, Any], key: str | None = None) -> str:
    """Create a signed cursor token from a payload

    Args:
        payload: Dictionary containing cursor data
        key: Signing key (uses env var if not provided)

    Returns:
        Signed cursor token as "base64payload.base64signature"

    Raises:
        ValueError: If key is not provided and not in environment

    """
    if key is None:
        key = os.getenv("CURSOR_SIGNING_KEY")
        if not key:
            raise ValueError("CURSOR_SIGNING_KEY not configured")

    # Serialize payload to JSON (compact, deterministic)
    json_bytes = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False,
        sort_keys=True,  # Ensure deterministic output
    ).encode("utf-8")

    # Create HMAC signature
    signature = hmac.new(key.encode("utf-8"), json_bytes, hashlib.sha256).digest()

    # Combine payload and signature
    return _b64u_encode(json_bytes) + "." + _b64u_encode(signature)


def verify_cursor(token: str, key: str | None = None) -> dict[str, Any]:
    """Verify and decode a signed cursor token

    Args:
        token: Signed cursor token
        key: Signing key (uses env var if not provided)

    Returns:
        Decoded payload dictionary

    Raises:
        ValueError: If cursor is invalid, tampered, or expired

    """
    if key is None:
        key = os.getenv("CURSOR_SIGNING_KEY")
        if not key:
            raise ValueError("CURSOR_SIGNING_KEY not configured")

    try:
        # Split token into payload and signature
        parts = token.split(".")
        if len(parts) != 2:
            raise ValueError("Malformed cursor token")

        payload_b64, signature_b64 = parts

        # Decode components
        payload_bytes = _b64u_decode(payload_b64)
        signature = _b64u_decode(signature_b64)

        # Verify signature
        expected_signature = hmac.new(key.encode("utf-8"), payload_bytes, hashlib.sha256).digest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid cursor signature")

        # Decode payload
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check version
        if payload.get("v") != 1:
            raise ValueError(f"Unsupported cursor version: {payload.get('v')}")

        # Check expiry if present
        if "exp" in payload:
            exp_time = datetime.fromisoformat(payload["exp"].replace("Z", "+00:00"))
            if datetime.now(UTC) > exp_time:
                raise ValueError("Cursor has expired")

        return payload

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid cursor payload: {e}") from e
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Invalid cursor: {e}") from e


def create_search_cursor(
    filters_hash: str,
    as_of: datetime,
    limit: int,
    after_tuple: tuple | None = None,
    ttl_hours: int = 24,
) -> str:
    """Create a cursor specifically for search pagination

    Args:
        filters_hash: SHA256 hash of canonical filter JSON
        as_of: Snapshot timestamp
        limit: Page size
        after_tuple: Last item's sort tuple (score, date, id)
        ttl_hours: Hours until cursor expires

    Returns:
        Signed cursor token

    """
    # Ensure as_of is timezone-aware
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=UTC)

    # Calculate expiry
    exp = datetime.now(UTC)
    exp = exp.replace(hour=exp.hour + ttl_hours)

    payload = {
        "v": 1,  # Version
        "f": filters_hash,  # Filter hash
        "as_of": as_of.isoformat().replace("+00:00", "Z"),  # Snapshot time
        "l": limit,  # Limit
        "exp": exp.isoformat().replace("+00:00", "Z"),  # Expiry
    }

    # Add after tuple if provided (for subsequent pages)
    if after_tuple:
        score, date, id_val = after_tuple
        payload["after"] = [
            round(float(score), 6) if score is not None else 0.0,
            str(date) if date else None,
            str(id_val),
        ]

    return sign_cursor(payload)


def hash_filters(filters: dict[str, Any], exclude_cursor: bool = True) -> str:
    """Create a deterministic hash of search filters

    Args:
        filters: Search filter parameters
        exclude_cursor: Whether to exclude nextCursor from hash

    Returns:
        SHA256 hash hex string

    """
    # Create a copy and remove cursor if needed
    canonical = dict(filters)
    if exclude_cursor and "nextCursor" in canonical:
        del canonical["nextCursor"]

    # Remove None values for consistency
    canonical = {k: v for k, v in canonical.items() if v is not None}

    # Serialize to deterministic JSON
    json_str = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False, sort_keys=True)

    # Return SHA256 hash
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def validate_cursor_filters(cursor_data: dict[str, Any], current_filters_hash: str) -> None:
    """Validate that cursor filters match current request filters

    Args:
        cursor_data: Decoded cursor payload
        current_filters_hash: Hash of current request filters

    Raises:
        ValueError: If filters don't match

    """
    cursor_filters_hash = cursor_data.get("f")
    if cursor_filters_hash != current_filters_hash:
        raise ValueError(
            "Cursor filters don't match current search filters. Please start a new search with updated filters.",
        )
