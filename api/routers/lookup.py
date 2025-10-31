"""
Clean barcode lookup endpoints
Provides simple GET endpoints for barcode scanning
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.services.search_service import SearchService
from core_infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lookup", tags=["lookup"])


@router.get("/barcode")
def barcode_lookup(
    code: str = Query(..., min_length=6, max_length=32, description="Barcode to lookup"),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """
    Simple barcode lookup via GET request

    This endpoint provides a clean, cacheable way to lookup products by barcode.
    Uses the same advanced search backend as POST /api/v1/search/advanced.
    """
    try:
        # Create search service and perform search
        search_service = SearchService(db)
        result = search_service.search(query=code, limit=limit)

        if not result.get("ok", False):
            raise HTTPException(status_code=500, detail="Lookup failed")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Barcode lookup failed for {code}: {e}")
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")


@router.get("/barcode/{code}")
def barcode_lookup_path(
    code: str,
    limit: int = Query(5, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db),
):
    """
    Alternative barcode lookup with barcode in path

    Example: GET /api/v1/lookup/barcode/012914632109
    """
    # Validate barcode length
    if len(code) < 6 or len(code) > 32:
        raise HTTPException(status_code=400, detail="Barcode must be 6-32 characters")

    return barcode_lookup(code=code, limit=limit, db=db)
