"""
Recall Search API Endpoints
Provides searchable, paginated access to recall data
"""

from datetime import date
from typing import List, Optional
import unicodedata
import base64
import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import or_, and_, desc, asc, func, select
from sqlalchemy.orm import Session

from core_infra.database import get_db, RecallDB

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
            "â€œ": '"',  # Left double quotation mark
            "â€": '"',  # Right double quotation mark
            "â€¢": "•",  # Bullet point
            'â€"': "–",  # En dash
            'â€"': "—",  # Em dash
            "â€¦": "…",  # Horizontal ellipsis
            "â€¹": "‹",  # Single left-pointing angle quotation mark
            "â€º": "›",  # Single right-pointing angle quotation mark
            "â€": '"',  # Right double quotation mark
            "â€œ": '"',  # Left double quotation mark
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
        None, ge=0, description="Number of results to skip (offset pagination)"
    ),
    cursor: Optional[str] = Query(
        None, description="Cursor for pagination (cursor-based pagination)"
    ),
    db: Session = Depends(get_db),
):
    """
    Search and list recalls with filtering and pagination

    Supports free text search across product name, brand, description, hazard, and category.
    Also supports filtering by agency, country, category, hazard type, and date range.
    """
    # Base query
    qry = db.query(RecallDB)

    # Free text search filter
    if q:
        like = f"%{q}%"
        qry = qry.filter(
            or_(
                RecallDB.product_name.ilike(like),
                RecallDB.brand.ilike(like),
                RecallDB.description.ilike(like),
                RecallDB.hazard.ilike(like),
                RecallDB.hazard_category.ilike(like),
                RecallDB.manufacturer.ilike(like),
                RecallDB.recall_reason.ilike(like),
                RecallDB.model_number.ilike(like),
            )
        )

    # Specific filters
    if agency:
        qry = qry.filter(RecallDB.source_agency.ilike(f"%{agency}%"))

    if country:
        qry = qry.filter(RecallDB.country.ilike(f"%{country}%"))

    if category:
        # Note: product_category field not available in current schema
        # Filter by product_name or brand instead
        qry = qry.filter(
            or_(
                RecallDB.product_name.ilike(f"%{category}%"),
                RecallDB.brand.ilike(f"%{category}%"),
            )
        )

    if hazard_category:
        qry = qry.filter(RecallDB.hazard_category.ilike(f"%{hazard_category}%"))

    if date_from:
        qry = qry.filter(RecallDB.recall_date >= date_from)

    if date_to:
        qry = qry.filter(RecallDB.recall_date <= date_to)

    # Get total count before pagination
    total = qry.count()

    # Apply sorting
    if sort == "recent":
        qry = qry.order_by(desc(RecallDB.recall_date).nullslast(), desc(RecallDB.id))
    else:
        qry = qry.order_by(asc(RecallDB.recall_date).nullsfirst(), asc(RecallDB.id))

    # Apply pagination (cursor-based or offset-based)
    if cursor:
        # Cursor-based pagination
        cursor_data = decode_cursor(cursor)
        if cursor_data:
            if sort == "recent":
                # For recent sort, get records after the cursor
                qry = qry.filter(
                    or_(
                        RecallDB.recall_date < cursor_data.get("recall_date"),
                        and_(
                            RecallDB.recall_date == cursor_data.get("recall_date"),
                            RecallDB.id < cursor_data.get("id"),
                        ),
                    )
                )
            else:
                # For oldest sort, get records before the cursor
                qry = qry.filter(
                    or_(
                        RecallDB.recall_date > cursor_data.get("recall_date"),
                        and_(
                            RecallDB.recall_date == cursor_data.get("recall_date"),
                            RecallDB.id > cursor_data.get("id"),
                        ),
                    )
                )

        # Get one extra record to check if there are more
        rows = qry.limit(limit + 1).all()
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]  # Remove the extra record
    else:
        # Offset-based pagination
        actual_offset = offset if offset is not None else 0
        rows = qry.offset(actual_offset).limit(limit).all()
        has_more = len(rows) == limit and (actual_offset + limit) < total

    # Convert to response format
    items = []
    for row in rows:
        items.append(
            RecallItem(
                id=row.id,
                recall_id=clean_encoding(row.recall_id),
                agency=clean_encoding(row.source_agency),
                country=clean_encoding(row.country),
                product_name=clean_encoding(row.product_name),
                brand=clean_encoding(row.brand),
                manufacturer=clean_encoding(row.manufacturer),
                model_number=clean_encoding(row.model_number),
                category=None,  # product_category field not available in current schema
                hazard=clean_encoding(row.hazard),
                hazard_category=clean_encoding(row.hazard_category),
                recall_date=row.recall_date,
                recall_reason=clean_encoding(row.recall_reason),
                remedy=clean_encoding(row.remedy),
                recall_class=clean_encoding(row.recall_class),
                reference=row.recall_id,
                url=row.url,
            )
        )

    # Generate next cursor if there are more results
    next_cursor = None
    if has_more and rows:
        last_row = rows[-1]
        next_cursor = encode_cursor(last_row.recall_id or "", last_row.recall_date, last_row.id)

    payload = RecallListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        nextCursor=next_cursor,
        hasMore=has_more,
    )

    return {"success": True, "data": payload.model_dump(), "count": len(payload.items)}


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
    offset: Optional[int] = Query(
        None, ge=0, description="Number of results to skip (offset pagination)"
    ),
    cursor: Optional[str] = Query(
        None, description="Cursor for pagination (cursor-based pagination)"
    ),
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
                r
                for r in filtered_recalls
                if q.lower() in r["product_name"].lower() or q.lower() in r["brand"].lower()
            ]

        if agency:
            filtered_recalls = [r for r in filtered_recalls if agency.upper() in r["agency"]]

        if category:
            filtered_recalls = [
                r for r in filtered_recalls if category.lower() in r["category"].lower()
            ]

        if hazard_category:
            filtered_recalls = [
                r
                for r in filtered_recalls
                if hazard_category.lower() in r["hazard_category"].lower()
            ]

        # Apply sorting
        if sort == "recent":
            filtered_recalls = sorted(
                filtered_recalls, key=lambda x: x["recall_date"], reverse=True
            )
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
            next_cursor = encode_cursor(
                last_recall["recall_id"], last_recall["recall_date"], last_recall["id"]
            )

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
    """
    try:
        # Total recalls
        total_recalls = db.query(RecallDB).count()

        # Recent recalls (last 30 days)
        from datetime import datetime, timedelta, timezone

        thirty_days_ago = datetime.now(timezone.utc).date() - timedelta(days=30)
        recent_recalls = db.query(RecallDB).filter(RecallDB.recall_date >= thirty_days_ago).count()

        # Top agencies
        agency_counts = (
            db.query(RecallDB.source_agency, func.count(RecallDB.id).label("count"))
            .group_by(RecallDB.source_agency)
            .order_by(func.count(RecallDB.id).desc())
            .limit(10)
            .all()
        )

        # Top hazard categories
        hazard_counts = (
            db.query(RecallDB.hazard_category, func.count(RecallDB.id).label("count"))
            .filter(RecallDB.hazard_category.isnot(None))
            .group_by(RecallDB.hazard_category)
            .order_by(func.count(RecallDB.id).desc())
            .limit(10)
            .all()
        )

        return {
            "success": True,
            "data": {
                "total_recalls": total_recalls,
                "recent_recalls_30_days": recent_recalls,
                "top_agencies": [
                    {"agency": agency, "count": count} for agency, count in agency_counts
                ],
                "top_hazard_categories": [
                    {"category": category, "count": count} for category, count in hazard_counts
                ],
            },
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to get recall stats: {str(e)}"}
