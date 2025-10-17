from api.pydantic_base import AppModel

"""
Recall Detail Endpoints for Individual Recall Lookup
"""

from fastapi import APIRouter, HTTPException, Response, Request
from sqlalchemy import text
from typing import Dict, Any, Optional
from core_infra.database import get_db_session
from core_infra.cache_manager import get_cached, set_cached
from urllib.parse import unquote
import re
import logging

router = APIRouter(prefix="/api/v1", tags=["recalls"])
logger = logging.getLogger(__name__)


@router.get("/recall/{recall_id:path}")
async def get_recall_detail(
    recall_id: str, request: Request, response: Response
) -> Dict[str, Any]:
    """
    Get detailed information for a specific recall by ID

    Args:
        recall_id: The unique recall identifier (may include slashes, e.g., RAPEX-A11/00023/23)

    Returns:
        Recall details or 404 if not found
    """
    # URL decode the recall_id to handle encoded slashes
    decoded_recall_id = unquote(recall_id).strip()

    # Validate recall_id format to prevent path traversal attacks
    if not re.fullmatch(r"[A-Za-z0-9/_\-\.]+", decoded_recall_id):
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Invalid recall_id format. Only letters, numbers, slashes, dashes, underscores, and dots are allowed.",
                },
            },
        )

    # Resolve API version from the OpenAPI spec once, then reuse
    v = getattr(request.app.state, "_openapi_version", None)
    if not v:
        try:
            v = request.app.openapi().get("info", {}).get("version", "unknown")
        except Exception:
            v = "unknown"
        request.app.state._openapi_version = v

    response.headers["X-API-Version"] = v

    # Check cache first for performance
    cache_key = f"recall_detail_{decoded_recall_id}"
    cached_result = get_cached("recalls", cache_key)
    if cached_result:
        logger.info(f"Returning cached recall data for {decoded_recall_id}")
        return {"ok": True, "data": cached_result, "cached": True}

    try:
        with get_db_session() as db:
            # Optimized UNION query to check both tables in one go
            query = text(
                """
                SELECT 
                    recall_id as id,
                    product_name as "productName",
                    brand,
                    manufacturer,
                    model_number as "modelNumber",
                    hazard,
                    hazard_category as "hazardCategory",
                    recall_reason as "recallReason",
                    remedy,
                    description,
                    recall_date as "recallDate",
                    source_agency as "sourceAgency",
                    country,
                    regions_affected as "regionsAffected",
                    url,
                    upc,
                    lot_number as "lotNumber",
                    batch_number as "batchNumber",
                    serial_number as "serialNumber",
                    'enhanced' as table_source
                FROM recalls_enhanced
                WHERE recall_id = :recall_id
                
                UNION ALL
                
                SELECT 
                    recall_id as id,
                    product_name as "productName",
                    brand,
                    manufacturer_contact as manufacturer,
                    model_number as "modelNumber",
                    hazard,
                    NULL as "hazardCategory",
                    hazard_description as "recallReason",
                    remedy,
                    description,
                    recall_date as "recallDate",
                    source_agency as "sourceAgency",
                    country,
                    NULL as "regionsAffected",
                    url,
                    upc,
                    NULL as "lotNumber",
                    NULL as "batchNumber",
                    NULL as "serialNumber",
                    'legacy' as table_source
                FROM recalls
                WHERE recall_id = :recall_id
                
                LIMIT 1
            """
            )

            result = db.execute(query, {"recall_id": decoded_recall_id}).fetchone()

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "ok": False,
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Recall not found",
                            "recall_id": decoded_recall_id,
                        },
                    },
                )

            # Convert to dict
            recall_data = (
                dict(result._mapping) if hasattr(result, "_mapping") else dict(result)
            )

            # Format dates
            if recall_data.get("recallDate"):
                recall_data["recallDate"] = str(recall_data["recallDate"])

            # Clean None values
            recall_data = {k: v for k, v in recall_data.items() if v is not None}

            # Cache the result for 1 hour
            set_cached("recalls", cache_key, recall_data, ttl=3600)

            return {"ok": True, "data": recall_data, "cached": False}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recall {decoded_recall_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to fetch recall details: {str(e)}",
                },
            },
        )
