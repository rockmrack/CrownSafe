"""
Recall Search API Endpoints
Provides searchable, paginated access to recall data
"""

import base64
import json
import unicodedata
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import Session

# CROWN SAFE: RecallDB model removed - replaced with HairProductModel
from core_infra.database import get_db

router = APIRouter(prefix="/api/v1/recalls", tags=["recalls"])


def clean_encoding(text: Optional[str]) -> Optional[str]:
    """Clean up encoding issues in text data"""
    if not text:
        return text

    # Normalize Unicode and fix common mojibake issues
    try:
        # Normalize to NFKC form
        normalized = unicodedata.normalize("NFKC", text)

        # Fix common mojibake patterns
        fixes = {
            "â€œ": '"',  # Left double quotation mark
            "â€": '"',  # Right double quotation mark
            "â€™": "'",  # Right single quotation mark
            "â€¢": "•",  # Bullet point
            'â€"': "—",  # Em dash (keeping the longer one)
            "â€¦": "…",  # Horizontal ellipsis
            "â€¹": "‹",  # Single left-pointing angle quotation mark
            "â€º": "›",  # Single right-pointing angle quotation mark
        }

        for mojibake, correct in fixes.items():
            normalized = normalized.replace(mojibake, correct)

        return normalized
    except Exception:
        # If normalization fails, return original text
        return text


def encode_cursor(recall_id: str, recall_date: date, id: int) -> str:
    """Encode cursor for pagination"""
    cursor_data = {
        "recall_id": recall_id,
        "recall_date": recall_date.isoformat() if recall_date else None,
        "id": id,
    }
    cursor_json = json.dumps(cursor_data)
    return base64.b64encode(cursor_json.encode()).decode()


def decode_cursor(cursor: str) -> Optional[dict]:
    """Decode cursor for pagination"""
    try:
        cursor_json = base64.b64decode(cursor.encode()).decode()
        return json.loads(cursor_json)
    except Exception:
        return None


class RecallItem(BaseModel):
    model_config = {"protected_namespaces": ()}  # Allow model_number field

    id: int
    recall_id: Optional[str] = None
    agency: Optional[str] = None
    country: Optional[str] = None
    product_name: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    category: Optional[str] = None
    hazard: Optional[str] = None
    hazard_category: Optional[str] = None
    recall_date: Optional[date] = None
    recall_reason: Optional[str] = None
    remedy: Optional[str] = None
    recall_class: Optional[str] = None
    reference: Optional[str] = None  # recall_id
    url: Optional[str] = None  # source URL if available

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class RecallListResponse(BaseModel):
    items: List[RecallItem]
    total: int
    limit: int
    offset: Optional[int] = None
    nextCursor: Optional[str] = None
    hasMore: bool = False


@router.get("", response_model=dict)
def list_recalls(
    q: Optional[str] = Query(
        None,
        min_length=2,
        description="Free text search over name/brand/description/hazard/category",
    ),
    agency: Optional[str] = Query(None, description="Filter by source agency (e.g., CPSC, FDA)"),
    country: Optional[str] = Query(None, description="Filter by country"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    hazard_category: Optional[str] = Query(None, description="Filter by hazard category"),
    date_from: Optional[date] = Query(None, description="Filter recalls from this date"),
    date_to: Optional[date] = Query(None, description="Filter recalls to this date"),
    sort: str = Query(
        "recent",
        pattern="^(recent|oldest)$",
        description="Sort order: recent (newest first) or oldest",
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of results per page"),
    offset: Optional[int] = Query(
        None,
        ge=0,
        description="Number of results to skip (offset pagination)",
    ),
    page: Optional[int] = Query(
        None,
        ge=1,
        description="Page number (1-indexed) when using classic pagination",
    ),
    page_size: Optional[int] = Query(
        None,
        ge=1,
        le=100,
        description="Page size when using classic pagination",
    ),
    cursor: Optional[str] = Query(
        None,
        description="Cursor for pagination (cursor-based pagination)",
    ),
    db: Session = Depends(get_db),
):
    """
    Search and list recalls with filtering and pagination

    Supports free text search across product name, brand, description, hazard, and category.
    Also supports filtering by agency, country, category, hazard type, and date range.
    """
    # Base query
    # CROWN SAFE: RecallDB model removed - this endpoint returns empty results
    # Baby product recall functionality replaced with hair product safety analysis
    return {
        "recalls": [],
        "total": 0,
        "page": page or 1,
        "page_size": page_size or limit,
        "offset": offset or 0,
        "limit": limit,
        "filters_applied": {
            "query": q,
            "agency": agency,
            "country": country,
            "category": category,
            "hazard_category": hazard_category,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
        },
        "message": "Baby product recalls not available in Crown Safe (hair product platform)",
    }

    # CROWN SAFE: Remaining pagination code also removed
    # Return empty results for baby product recalls

    return {
        "success": True,
        "data": {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset or 0,
            "nextCursor": None,
            "hasMore": False,
        },
        "count": 0,
        "message": "Baby product recalls not available in Crown Safe (hair product platform)",
    }


# DEV OVERRIDE ENDPOINTS - For testing without database dependencies


@router.get("/search-dev", response_model=dict)
def search_recalls_dev(
    q: Optional[str] = Query(None, description="Free text search"),
    agency: Optional[str] = Query(None, description="Filter by source agency"),
    country: Optional[str] = Query(None, description="Filter by country"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    hazard_category: Optional[str] = Query(None, description="Filter by hazard category"),
    date_from: Optional[date] = Query(None, description="Filter recalls from this date"),
    date_to: Optional[date] = Query(None, description="Filter recalls to this date"),
    sort: str = Query("recent", pattern="^(recent|oldest)$", description="Sort order"),
    limit: int = Query(20, ge=1, le=100, description="Number of results per page"),
    offset: Optional[int] = Query(None, ge=0, description="Number of results to skip (offset pagination)"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (cursor-based pagination)"),
):
    """
    DEV OVERRIDE: Search recalls without database dependencies
    """
    try:
        # Mock recall data
        mock_recalls = [
            {
                "id": 1,
                "recall_id": "RECALL-001",
                "agency": "CPSC",
                "country": "USA",
                "product_name": "Baby Pacifier",
                "brand": "SafeBaby",
                "manufacturer": "SafeBaby Inc",
                "model_number": "SB-001",
                "category": "baby_products",
                "hazard": "Choking hazard",
                "hazard_category": "choking",
                "recall_date": "2024-01-15",
                "recall_reason": "Small parts can detach",
                "remedy": "Refund or replacement",
                "recall_class": "Class I",
                "reference": "RECALL-001",
                "url": "https://example.com/recall-001",
            },
            {
                "id": 2,
                "recall_id": "RECALL-002",
                "agency": "FDA",
                "country": "USA",
                "product_name": "Baby Formula",
                "brand": "NutriBaby",
                "manufacturer": "NutriBaby Corp",
                "model_number": "NB-002",
                "category": "food",
                "hazard": "Contamination risk",
                "hazard_category": "contamination",
                "recall_date": "2024-02-20",
                "recall_reason": "Potential bacterial contamination",
                "remedy": "Dispose and contact for refund",
                "recall_class": "Class II",
                "reference": "RECALL-002",
                "url": "https://example.com/recall-002",
            },
            {
                "id": 3,
                "recall_id": "RECALL-003",
                "agency": "CPSC",
                "country": "USA",
                "product_name": "Toy Blocks",
                "brand": "PlaySafe",
                "manufacturer": "PlaySafe Toys",
                "model_number": "PS-003",
                "category": "toys",
                "hazard": "Lead paint",
                "hazard_category": "chemical",
                "recall_date": "2024-03-10",
                "recall_reason": "Lead paint exceeds safety limits",
                "remedy": "Return for refund",
                "recall_class": "Class I",
                "reference": "RECALL-003",
                "url": "https://example.com/recall-003",
            },
        ]

        # Apply filters (mock implementation)
        filtered_recalls = mock_recalls

        if q:
            filtered_recalls = [
                r for r in filtered_recalls if q.lower() in r["product_name"].lower() or q.lower() in r["brand"].lower()
            ]

        if agency:
            filtered_recalls = [r for r in filtered_recalls if agency.upper() in r["agency"]]

        if category:
            filtered_recalls = [r for r in filtered_recalls if category.lower() in r["category"].lower()]

        if hazard_category:
            filtered_recalls = [r for r in filtered_recalls if hazard_category.lower() in r["hazard_category"].lower()]

        # Apply sorting
        if sort == "recent":
            filtered_recalls = sorted(filtered_recalls, key=lambda x: x["recall_date"], reverse=True)
        else:
            filtered_recalls = sorted(filtered_recalls, key=lambda x: x["recall_date"])

        # Apply pagination (cursor-based or offset-based)
        total = len(filtered_recalls)

        if cursor:
            # Cursor-based pagination (mock implementation)
            cursor_data = decode_cursor(cursor)
            if cursor_data:
                # Find the position of the cursor in the sorted list
                cursor_id = cursor_data.get("id")
                cursor_found = False
                start_index = 0

                for i, recall in enumerate(filtered_recalls):
                    if recall["id"] == cursor_id:
                        start_index = i + 1
                        cursor_found = True
                        break

                if not cursor_found:
                    start_index = 0

                paginated_recalls = filtered_recalls[start_index : start_index + limit]
                has_more = len(filtered_recalls) > start_index + limit
            else:
                paginated_recalls = filtered_recalls[:limit]
                has_more = len(filtered_recalls) > limit
        else:
            # Offset-based pagination
            actual_offset = offset if offset is not None else 0
            paginated_recalls = filtered_recalls[actual_offset : actual_offset + limit]
            has_more = len(filtered_recalls) > actual_offset + limit

        # Generate next cursor if there are more results
        next_cursor = None
        if has_more and paginated_recalls:
            last_recall = paginated_recalls[-1]
            next_cursor = encode_cursor(last_recall["recall_id"], last_recall["recall_date"], last_recall["id"])

        return {
            "success": True,
            "data": {
                "items": paginated_recalls,
                "total": total,
                "limit": limit,
                "offset": offset,
                "nextCursor": next_cursor,
                "hasMore": has_more,
            },
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to search recalls: {str(e)}"}


@router.get("/stats-dev", response_model=dict)
def get_recall_stats_dev():
    """
    DEV OVERRIDE: Get recall statistics without database dependencies
    """
    try:
        # Mock statistics
        mock_stats = {
            "total_recalls": 150,
            "by_agency": {"CPSC": 75, "FDA": 45, "NHTSA": 20, "Other": 10},
            "by_category": {
                "baby_products": 60,
                "toys": 40,
                "food": 30,
                "clothing": 20,
            },
            "by_hazard": {
                "choking": 50,
                "chemical": 30,
                "contamination": 25,
                "mechanical": 20,
                "other": 25,
            },
            "recent_trends": {"last_30_days": 15, "last_90_days": 45, "last_year": 150},
        }

        return {"success": True, "data": mock_stats}

    except Exception as e:
        return {"success": False, "error": f"Failed to get recall stats: {str(e)}"}


@router.get("/stats", response_model=dict)
def get_recall_stats(db: Session = Depends(get_db)):
    """
    Get recall statistics and counts
    CROWN SAFE: Returns empty stats - baby product recalls not available
    """
    return {
        "success": True,
        "data": {
            "total_recalls": 0,
            "recent_recalls_30_days": 0,
            "top_agencies": [],
            "top_hazard_categories": [],
        },
        "message": "Baby product recall stats not available in Crown Safe (hair product platform)",
    }
