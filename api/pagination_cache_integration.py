"""Integration module for pagination and caching features (Task 5)
Shows how to wire cursor pagination and HTTP caching into existing endpoints
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.services.search_service_v2 import SearchServiceV2
from api.utils import (
    add_cache_headers,
    check_if_none_match,
    create_not_modified_response,
    hash_filters,
    make_search_etag,
    verify_cursor,
)
from api.utils.redis_cache import get_cache
from core_infra.database import get_db

# from core_infra.enhanced_database_schema import EnhancedRecallDB  # REMOVED FOR CROWN SAFE

logger = logging.getLogger(__name__)


def setup_pagination_cache(app: FastAPI) -> None:
    """Configure pagination and caching for the FastAPI app

    Args:
        app: FastAPI application instance

    """

    # Add startup/shutdown for cache
    @app.on_event("startup")
    async def init_cache() -> None:
        _ = await get_cache()  # cache (initializes connection)
        logger.info("Redis search cache initialized")

    @app.on_event("shutdown")
    async def close_cache() -> None:
        from api.utils.redis_cache import close_cache as close_redis_cache

        await close_redis_cache()
        logger.info("Redis search cache closed")

    logger.info("Pagination and cache setup complete")


def create_search_endpoint_v2(app: FastAPI) -> None:
    """Create enhanced search endpoint with cursor pagination and caching
    """

    @app.post("/api/v2/search/advanced")
    async def search_advanced_v2(request: Request, payload: dict[str, Any], db: Session = Depends(get_db)):
        """Enhanced search with cursor pagination and HTTP caching

        Features:
        - Opaque, signed cursor tokens
        - Snapshot isolation via as_of timestamp
        - Keyset pagination (no OFFSET)
        - HTTP caching with ETag and 304 support
        - Redis micro-cache for 60s
        """
        try:
            # Extract trace ID if available
            trace_id = getattr(request.state, "trace_id", None)

            # Check cache first
            cache = await get_cache()

            # Generate filter hash for caching
            filters_hash = hash_filters(payload, exclude_cursor=True)

            # Parse cursor if present
            cursor_token = payload.get("nextCursor")
            as_of_str = None
            after_tuple = None

            if cursor_token:
                try:
                    cursor_data = verify_cursor(cursor_token)
                    as_of_str = cursor_data.get("as_of")
                    after_tuple = cursor_data.get("after")
                except ValueError as e:
                    # Invalid cursor
                    error_code = "INVALID_CURSOR"
                    if "filter" in str(e) and "mismatch" in str(e):
                        error_code = "INVALID_CURSOR_FILTER_MISMATCH"

                    return JSONResponse(
                        content={
                            "ok": False,
                            "error": {"code": error_code, "message": str(e)},
                            "traceId": trace_id,
                        },
                        status_code=400,
                    )
            else:
                # New search - set snapshot time
                as_of = datetime.now(timezone.utc)
                as_of_str = as_of.isoformat().replace("+00:00", "Z")

            # Check Redis cache
            cached_result = await cache.get(filters_hash, as_of_str, after_tuple)

            if cached_result:
                # Generate ETag for cached result
                result_ids = [item["id"] for item in cached_result.get("data", {}).get("items", [])][:5]
                etag = make_search_etag(filters_hash, as_of_str, result_ids)

                # Check If-None-Match
                if check_if_none_match(request, etag):
                    return create_not_modified_response(etag=etag, cache_control="private, max-age=60")

                # Return cached result with headers
                response = JSONResponse(cached_result)
                add_cache_headers(response, etag=etag, max_age=60, private=True)
                return response

            # Not cached - execute search
            service = SearchServiceV2(db)
            result = service.search_with_cursor(
                query=payload.get("query"),
                product=payload.get("product"),
                id=payload.get("id"),
                keywords=payload.get("keywords"),
                agencies=payload.get("agencies"),
                severity=payload.get("severity"),
                risk_category=payload.get("riskCategory"),
                date_from=payload.get("date_from"),
                date_to=payload.get("date_to"),
                limit=min(payload.get("limit", 20), 100),
                next_cursor=cursor_token,
            )

            # Add trace ID to response
            result["traceId"] = trace_id

            # Cache the result
            await cache.set(filters_hash, as_of_str, after_tuple, result, ttl=60)  # 60 seconds

            # Generate ETag
            result_ids = [item["id"] for item in result.get("data", {}).get("items", [])][:5]
            etag = make_search_etag(filters_hash, as_of_str, result_ids)

            # Check If-None-Match
            if check_if_none_match(request, etag):
                return create_not_modified_response(etag=etag, cache_control="private, max-age=60")

            # Return with cache headers
            response = JSONResponse(result)
            add_cache_headers(response, etag=etag, max_age=60, private=True)

            return response

        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return JSONResponse(
                content={
                    "ok": False,
                    "error": {"code": "SEARCH_ERROR", "message": str(e)},
                    "traceId": getattr(request.state, "trace_id", None),
                },
                status_code=500,
            )


def enhance_recall_detail_endpoint(app: FastAPI) -> None:
    """Enhance recall detail endpoint with HTTP caching
    """
    # Get the existing endpoint and wrap it
    # Or define a new one:

    @app.get("/api/v2/recall/{recall_id}")
    async def get_recall_detail_v2(recall_id: str, request: Request, db: Session = Depends(get_db)) -> None:
        """Get recall detail with HTTP caching support

        Features:
        - ETag based on ID + last_updated
        - Last-Modified header
        - 304 Not Modified support
        - 5 minute cache with stale-while-revalidate
        """
        try:
            # REMOVED FOR CROWN SAFE: EnhancedRecallDB query gutted
            # Crown Safe focuses on hair product testing (HairProductModel), not baby recalls
            raise HTTPException(status_code=404, detail="Recall lookup deprecated for Crown Safe")

        except HTTPException:
            raise

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Recall detail error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error")


# Integration code for existing main.py
INTEGRATION_EXAMPLE = """
# Add to your main_crownsafe.py:

from api.pagination_cache_integration import (
    setup_pagination_cache,
    create_search_endpoint_v2,
    enhance_recall_detail_endpoint
)

# Setup pagination and cache
setup_pagination_cache(app)

# Add v2 endpoints with enhanced features
create_search_endpoint_v2(app)
enhance_recall_detail_endpoint(app)

# Or enhance existing endpoints:

from api.utils import (
    hash_filters,
    create_search_cursor,
    CacheableResponse,
    check_if_none_match
)

# In your existing search endpoint, add:

# 1. Generate filter hash
filters_hash = hash_filters(request_dict)

# 2. Handle cursor
if request.nextCursor:
    cursor_data = verify_cursor(request.nextCursor)
    # Validate filters match
    validate_cursor_filters(cursor_data, filters_hash)

# 3. Create next cursor if has more results
if has_more:
    next_cursor = create_search_cursor(
        filters_hash=filters_hash,
        as_of=as_of,
        limit=limit,
        after_tuple=(last_score, last_date, last_id)
    )

# 4. Add caching headers
return CacheableResponse.search_response(
    content=result,
    filters_hash=filters_hash,
    as_of=as_of_str,
    result_ids=[item["id"] for item in items[:5]],
    request=request
)
"""


class PaginationConfig:
    """Configuration for pagination settings"""

    # Cursor settings
    CURSOR_TTL_HOURS = int(os.getenv("CURSOR_TTL_HOURS", "24"))
    CURSOR_SIGNING_KEY = os.getenv("CURSOR_SIGNING_KEY", "change-this-in-production")

    # Cache settings
    SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "60"))
    DETAIL_CACHE_TTL = int(os.getenv("DETAIL_CACHE_TTL", "300"))

    # Pagination settings
    DEFAULT_LIMIT = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    MAX_LIMIT = int(os.getenv("MAX_PAGE_SIZE", "100"))

    @classmethod
    def validate(cls) -> None:
        """Validate configuration"""
        if cls.CURSOR_SIGNING_KEY == "change-this-in-production":
            logger.warning("Using default cursor signing key - change in production!")

        if len(cls.CURSOR_SIGNING_KEY) < 32:
            logger.warning("Cursor signing key should be at least 32 bytes")

        logger.info(f"Pagination config: TTL={cls.CURSOR_TTL_HOURS}h, Cache={cls.SEARCH_CACHE_TTL}s")


# Validate config on import
PaginationConfig.validate()
