from api.pydantic_base import AppModel

"""
Task 12: Enhanced Barcode Scan → Result Bridge
Implements intelligent UPC/EAN matching with fallback search and caching
"""

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone
import logging
import json
import hashlib
import re
from collections import OrderedDict

try:
    from core_infra.database import get_db as get_db_session, RecallDB
except ImportError:
    # Fallback for testing without full infrastructure
    from typing import Any

    def get_db_session():
        return None

    class RecallDB:
        pass


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/barcode", tags=["Barcode Bridge"])


# ========================= PAYLOAD NORMALIZATION =========================


def _normalize_scan_payload(barcode: str, payload: dict, trace_id: str, cached: bool) -> dict:
    """
    Ensure the response payload has all required fields for BarcodeScanResponse.
    Never read barcode from upstream objects – always use the request barcode.
    """
    data = dict(payload or {})

    # hard guarantees / defaults
    data["barcode"] = barcode  # <-- never from EnhancedRecallDB
    data.setdefault("ok", bool(data.get("ok", True)))
    data.setdefault("recalls", [])
    data.setdefault("total_recalls", len(data.get("recalls", [])))
    data["cached"] = bool(cached)
    data.setdefault("match_status", "ok" if data["ok"] else "error")
    data.setdefault("message", "")
    data["trace_id"] = trace_id

    # new required field (fixes Pydantic v2 error)
    if not data.get("scan_timestamp"):
        data["scan_timestamp"] = datetime.now(timezone.utc).isoformat()

    return data


# ========================= MODELS =========================


class BarcodeScanRequest(BaseModel):
    """Enhanced barcode scan request"""

    barcode: str = Field(..., description="UPC/EAN barcode value")
    barcode_type: Optional[str] = Field("UPC", description="Barcode type: UPC, EAN, CODE128, etc")
    user_id: Optional[str] = Field(None, description="User ID for caching")
    device_id: Optional[str] = Field(None, description="Device ID for caching")
    include_similar: bool = Field(True, description="Include similar products if no exact match")


class BarcodeProduct(AppModel):
    """Product information from barcode"""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    barcode: str
    product_name: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    model_number: Optional[str] = None


class RecallMatch(BaseModel):
    """Recall match information"""

    recall_id: str
    product_name: str
    brand: Optional[str]
    hazard: Optional[str]
    remedy: Optional[str]
    recall_date: Optional[str]
    agency: str
    match_confidence: float = Field(..., ge=0, le=1, description="0-1 confidence score")
    match_type: str = Field(..., description="exact, similar, brand_only, category")


class BarcodeScanResponse(BaseModel):
    """Enhanced barcode scan response"""

    ok: bool = True
    barcode: str
    product: Optional[BarcodeProduct] = None
    match_status: str = Field(..., description="exact_match, similar_found, no_recalls, no_match")
    message: Optional[str] = None
    recalls: List[RecallMatch] = []
    total_recalls: int = 0
    cached: bool = False
    scan_timestamp: datetime
    trace_id: Optional[str] = None


# ========================= CACHE IMPLEMENTATION =========================


class BarcodeCache:
    """Simple in-memory LRU cache for last 50 barcode scans"""

    def __init__(self, max_size: int = 50):
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.max_size = max_size

    def get_key(self, barcode: str, user_id: Optional[str] = None) -> str:
        """Generate cache key"""
        if user_id:
            return f"{user_id}:{barcode}"
        return f"anon:{barcode}"

    def get(self, barcode: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached scan result"""
        key = self.get_key(barcode, user_id)

        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)

            # Check if cache is still valid (24 hours)
            cached_data = self.cache[key]
            if datetime.now() - cached_data["timestamp"] < timedelta(hours=24):
                logger.info(f"Cache hit for barcode: {barcode[:4]}****")
                return cached_data
            else:
                # Expired, remove it
                del self.cache[key]

        return None

    def set(self, barcode: str, data: Dict[str, Any], user_id: Optional[str] = None):
        """Cache scan result"""
        key = self.get_key(barcode, user_id)

        # Add timestamp
        data["timestamp"] = datetime.now()
        data["cached"] = True

        # Add to cache
        self.cache[key] = data

        # Enforce max size (remove oldest)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

        logger.info(
            f"Cached scan result for barcode: {barcode[:4]}**** (cache size: {len(self.cache)})"
        )

    def clear_user_cache(self, user_id: str):
        """Clear all cache entries for a specific user"""
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self.cache[key]

    def clear_barcode(self, barcode: str) -> bool:
        """Clear cache entry for a specific barcode"""
        keys_to_remove = [k for k in self.cache.keys() if k.endswith(f":{barcode}")]
        for key in keys_to_remove:
            del self.cache[key]
        return len(keys_to_remove) > 0

    def clear_all_cache(self):
        """Clear all cache entries"""
        self.cache.clear()

    def get_cache_size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


# Global cache instance
barcode_cache = BarcodeCache(max_size=50)


# ========================= BARCODE UTILITIES =========================


def validate_upc(upc: str) -> bool:
    """Validate UPC-A (12 digits) or UPC-E (8 digits) with check digit"""
    upc = upc.strip()

    # Remove any non-digits
    upc = re.sub(r"\D", "", upc)

    if len(upc) not in [8, 12]:
        return False

    try:
        # Calculate check digit
        if len(upc) == 12:
            # UPC-A check digit calculation
            odd_sum = sum(int(upc[i]) for i in range(0, 11, 2))
            even_sum = sum(int(upc[i]) for i in range(1, 10, 2))
            check = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10
            return check == int(upc[11])
        else:
            # UPC-E validation (simplified)
            return True
    except:
        return False


def validate_ean(ean: str) -> bool:
    """Validate EAN-13 or EAN-8 with check digit"""
    ean = ean.strip()

    # Remove any non-digits
    ean = re.sub(r"\D", "", ean)

    if len(ean) not in [8, 13]:
        return False

    try:
        # Calculate check digit
        odd_sum = sum(int(ean[i]) for i in range(0, len(ean) - 1, 2))
        even_sum = sum(int(ean[i]) for i in range(1, len(ean) - 1, 2))

        if len(ean) == 13:
            check = (10 - ((odd_sum + even_sum * 3) % 10)) % 10
        else:  # EAN-8
            check = (10 - ((odd_sum * 3 + even_sum) % 10)) % 10

        return check == int(ean[-1])
    except:
        return False


def normalize_barcode(barcode: str) -> Tuple[str, str]:
    """
    Normalize barcode and detect type
    Returns: (normalized_barcode, barcode_type)
    """
    # Remove spaces and special characters
    barcode = re.sub(r"[^0-9A-Za-z]", "", barcode)

    # Check if numeric
    if barcode.isdigit():
        if len(barcode) == 12 and validate_upc(barcode):
            return barcode, "UPC-A"
        elif len(barcode) == 8 and validate_upc(barcode):
            return barcode, "UPC-E"
        elif len(barcode) == 13 and validate_ean(barcode):
            return barcode, "EAN-13"
        elif len(barcode) == 8 and validate_ean(barcode):
            return barcode, "EAN-8"

    # Default to original
    return barcode, "UNKNOWN"


def extract_brand_from_barcode(barcode: str) -> Optional[str]:
    """
    Extract potential brand from barcode prefix
    Common manufacturer prefixes (simplified)
    """
    if not barcode.isdigit() or len(barcode) < 6:
        return None

    # Common manufacturer prefixes (first 6 digits)
    # This is a simplified example - in production, use a comprehensive database
    manufacturer_prefixes = {
        "012345": "Example Brand",
        "037000": "Procter & Gamble",
        "038000": "Kellogg's",
        "041196": "Walmart",
        "043000": "General Mills",
        "070470": "Gerber",
        # Add more as needed
    }

    prefix = barcode[:6]
    return manufacturer_prefixes.get(prefix)


# ========================= DATABASE SEARCH =========================


def search_exact_barcode(barcode: str, db: Session) -> List[RecallDB]:
    """Search for exact barcode match in recalls"""

    # Try different barcode fields (fixed for actual schema)
    recalls = (
        db.query(RecallDB)
        .filter(
            or_(
                RecallDB.upc == barcode,
                RecallDB.ean_code == barcode,
                RecallDB.gtin == barcode,
                RecallDB.article_number == barcode,
            )
        )
        .limit(10)
        .all()
    )

    return recalls


def search_similar_products(
    barcode: str, brand: Optional[str], category: Optional[str], db: Session
) -> List[RecallDB]:
    """
    Search for similar products when exact match not found
    Uses brand, category, and partial barcode matching
    """

    conditions = []

    # If we have a brand, search for it
    if brand:
        conditions.append(
            or_(
                func.lower(RecallDB.brand).like(f"%{brand.lower()}%"),
                func.lower(RecallDB.manufacturer).like(f"%{brand.lower()}%"),
            )
        )

    # Search for partial barcode match (first 6 digits for manufacturer)
    if len(barcode) >= 6 and barcode.isdigit():
        prefix = barcode[:6]
        conditions.append(
            or_(
                RecallDB.upc.like(f"{prefix}%"),
                RecallDB.ean_code.like(f"{prefix}%"),
                RecallDB.gtin.like(f"{prefix}%"),
            )
        )

    # Category search if available
    if category:
        # Note: product_category field not available in current schema
        # Search by product_name and brand instead
        conditions.append(
            or_(
                func.lower(RecallDB.product_name).like(f"%{category.lower()}%"),
                func.lower(RecallDB.brand).like(f"%{category.lower()}%"),
            )
        )

    if not conditions:
        return []

    # Combine conditions with OR
    recalls = (
        db.query(RecallDB)
        .filter(or_(*conditions))
        .order_by(RecallDB.recall_date.desc())
        .limit(20)
        .all()
    )

    return recalls


def calculate_match_confidence(barcode: str, recall: RecallDB) -> float:
    """
    Calculate confidence score for a recall match
    Returns: 0.0 to 1.0 confidence score
    """

    confidence = 0.0

    # Exact UPC match
    if recall.upc == barcode:
        return 1.0

    # Partial UPC match (same manufacturer)
    if recall.upc and barcode.isdigit() and len(barcode) >= 6:
        if recall.upc[:6] == barcode[:6]:
            confidence = max(confidence, 0.6)

    # Model number contains barcode (similar to product codes)
    if recall.model_number and barcode in recall.model_number:
        confidence = max(confidence, 0.7)

    # Brand match from barcode prefix
    brand = extract_brand_from_barcode(barcode)
    if brand and recall.brand:
        if brand.lower() in recall.brand.lower():
            confidence = max(confidence, 0.5)

    return confidence


# ========================= API ENDPOINTS =========================


@router.post("/scan", response_model=BarcodeScanResponse)
async def scan_barcode(
    request: BarcodeScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Enhanced barcode scanning with intelligent matching and fallback

    Flow:
    1. Check cache for recent scan
    2. Validate and normalize barcode
    3. Search for exact match
    4. If no exact match and include_similar=true, search for similar products
    5. Cache the result
    6. Return with appropriate message
    """

    try:
        # Validate request has required barcode field
        if not request.barcode or not request.barcode.strip():
            logger.warning("Barcode scan request missing or empty barcode")
            err = {
                "ok": False,
                "match_status": "error",
                "message": "Barcode is required",
            }
            payload = _normalize_scan_payload("", err, "error", cached=False)
            return BarcodeScanResponse.model_validate(payload)

        # Use provided user_id or from request
        user_id = user_id or request.user_id
        device_id = device_id or request.device_id

        # Generate trace ID
        trace_id = (
            f"barcode_{hashlib.md5(f'{request.barcode}{datetime.now()}'.encode()).hexdigest()[:8]}"
        )
    except Exception as e:
        logger.error(f"Error initializing barcode scan: {str(e)}")
        # Return error response instead of raising 500
        barcode_value = getattr(request, "barcode", "") if hasattr(request, "barcode") else ""
        err = {
            "ok": False,
            "match_status": "error",
            "message": "Failed to process barcode",
        }
        payload = _normalize_scan_payload(barcode_value, err, "error", cached=False)
        return BarcodeScanResponse.model_validate(payload)

    try:
        # Check cache first
        cached_result = barcode_cache.get(request.barcode, user_id)
        if cached_result:
            # Return cached result with normalized payload
            payload = _normalize_scan_payload(request.barcode, cached_result, trace_id, cached=True)
            return BarcodeScanResponse.model_validate(payload)

        # Normalize and validate barcode
        normalized_barcode, barcode_type = normalize_barcode(request.barcode)
    except Exception as e:
        logger.error(f"Barcode scan error at start: {str(e)}")
        normalized_barcode = request.barcode
        barcode_type = "UNKNOWN"

    # Wrap entire logic in try-catch to prevent 500 errors
    try:
        # Extract potential brand
        brand = extract_brand_from_barcode(normalized_barcode)

        # Build product info
        product = BarcodeProduct(
            barcode=normalized_barcode,
            brand=brand,
            category=None,  # Would come from product database in production
        )

        # Search for exact matches
        try:
            exact_recalls = search_exact_barcode(normalized_barcode, db) if db else []
        except Exception as e:
            logger.error(f"Database error searching barcode: {str(e)}")
            exact_recalls = []
    except Exception as e:
        logger.error(f"Critical error in barcode processing: {str(e)}")
        # Return safe error response
        err = {
            "ok": False,
            "match_status": "error",
            "message": f"Error processing barcode: {str(e)[:100]}",
        }
        payload = _normalize_scan_payload(normalized_barcode, err, trace_id, cached=False)
        return BarcodeScanResponse.model_validate(payload)

    # Final safety wrapper for all response generation
    try:
        if exact_recalls:
            # Found exact matches
            recalls = []
            for recall in exact_recalls[:5]:  # Limit to top 5
                try:
                    recalls.append(
                        RecallMatch(
                            recall_id=str(recall.recall_id) if recall.recall_id else "",
                            product_name=recall.product_name or "Unknown Product",
                            brand=recall.brand if hasattr(recall, "brand") else None,
                            hazard=recall.hazard if hasattr(recall, "hazard") else None,
                            remedy=recall.remedy if hasattr(recall, "remedy") else None,
                            recall_date=str(recall.recall_date)
                            if hasattr(recall, "recall_date") and recall.recall_date
                            else None,
                            agency=recall.source_agency
                            if hasattr(recall, "source_agency")
                            else "Unknown",
                            match_confidence=1.0,
                            match_type="exact",
                        )
                    )
                except Exception as recall_error:
                    logger.error(f"Error processing recall: {str(recall_error)}")
                    continue

            # Build fresh result with normalized payload
            raw_payload = {
                "ok": True,
                "product": product,
                "match_status": "exact_match",
                "message": f"Found {len(recalls)} recall(s) for this product",
                "recalls": recalls,
                "total_recalls": len(recalls),
            }
            payload = _normalize_scan_payload(
                normalized_barcode, raw_payload, trace_id, cached=False
            )
            response = BarcodeScanResponse.model_validate(payload)

        elif request.include_similar:
            # No exact match, try similar products
            try:
                similar_recalls = (
                    search_similar_products(normalized_barcode, brand, product.category, db)
                    if db
                    else []
                )
            except Exception as e:
                logger.error(f"Database error searching similar products: {str(e)}")
                similar_recalls = []

            if similar_recalls:
                # Calculate confidence and sort
                recall_matches = []
                for recall in similar_recalls:
                    confidence = calculate_match_confidence(normalized_barcode, recall)
                    if confidence > 0.3:  # Minimum confidence threshold
                        recall_matches.append((confidence, recall))

                # Sort by confidence
                recall_matches.sort(key=lambda x: x[0], reverse=True)

                # Build response
                recalls = []
                for confidence, recall in recall_matches[:5]:  # Top 5
                    match_type = "similar"
                    if confidence >= 0.6:
                        match_type = "brand_only" if brand else "similar"

                    recalls.append(
                        RecallMatch(
                            recall_id=str(recall.recall_id) if recall.recall_id else "",
                            product_name=recall.product_name or "Unknown Product",
                            brand=recall.brand if hasattr(recall, "brand") else None,
                            hazard=recall.hazard if hasattr(recall, "hazard") else None,
                            remedy=recall.remedy if hasattr(recall, "remedy") else None,
                            recall_date=str(recall.recall_date)
                            if hasattr(recall, "recall_date") and recall.recall_date
                            else None,
                            agency=recall.source_agency
                            if hasattr(recall, "source_agency")
                            else "Unknown",
                            match_confidence=confidence,
                            match_type=match_type,
                        )
                    )

                # Build fresh result with normalized payload
                raw_payload = {
                    "ok": True,
                    "product": product,
                    "match_status": "similar_found",
                    "message": "No direct match—showing similar recalls",
                    "recalls": recalls,
                    "total_recalls": len(recalls),
                }
                payload = _normalize_scan_payload(
                    normalized_barcode, raw_payload, trace_id, cached=False
                )
                response = BarcodeScanResponse.model_validate(payload)
            else:
                # No recalls found at all
                raw_payload = {
                    "ok": True,
                    "product": product,
                    "match_status": "no_recalls",
                    "message": "No recalls found for this product",
                    "recalls": [],
                    "total_recalls": 0,
                }
                payload = _normalize_scan_payload(
                    normalized_barcode, raw_payload, trace_id, cached=False
                )
                response = BarcodeScanResponse.model_validate(payload)
        else:
            # No exact match and similar search disabled
            raw_payload = {
                "ok": True,
                "product": product,
                "match_status": "no_match",
                "message": "No exact match found",
                "recalls": [],
                "total_recalls": 0,
            }
            payload = _normalize_scan_payload(
                normalized_barcode, raw_payload, trace_id, cached=False
            )
            response = BarcodeScanResponse.model_validate(payload)

    except Exception as response_error:
        logger.error(f"Error generating response: {str(response_error)}")
        # Return safe fallback response with normalized payload
        err = {
            "ok": False,
            "match_status": "error",
            "message": "Unable to process barcode scan",
        }
        payload = _normalize_scan_payload(normalized_barcode, err, trace_id, cached=False)
        response = BarcodeScanResponse.model_validate(payload)

    # Cache the result (exclude trace_id for caching, but keep scan_timestamp)
    try:
        cache_data = response.dict(exclude={"trace_id", "cached"})
        background_tasks.add_task(barcode_cache.set, normalized_barcode, cache_data, user_id)
    except Exception as cache_error:
        logger.error(f"Error caching result: {str(cache_error)}")

    # Log scan
    try:
        logger.info(
            f"Barcode scan completed",
            extra={
                "barcode": normalized_barcode[:4] + "****"
                if len(normalized_barcode) > 4
                else normalized_barcode,
                "match_status": response.match_status,
                "recalls_found": response.total_recalls,
                "user_id": user_id,
                "device_id": device_id,
                "trace_id": trace_id,
            },
        )
    except Exception as log_error:
        logger.error(f"Error logging barcode scan: {str(log_error)}")

    return response


@router.get("/cache/status")
async def get_cache_status(user_id: Optional[str] = Header(None, alias="X-User-ID")):
    """Get cache status and optionally user's cached items"""

    cache_info = {
        "ok": True,
        "total_cached": len(barcode_cache.cache),
        "max_size": barcode_cache.max_size,
        "cache_ttl_hours": 24,
    }

    if user_id:
        # Count user's cached items
        user_items = sum(1 for k in barcode_cache.cache.keys() if k.startswith(f"{user_id}:"))
        cache_info["user_cached_items"] = user_items

    return cache_info


@router.delete("/cache/clear", operation_id="clear_cache_delete")
@router.post("/cache/clear", operation_id="clear_cache_post")
async def clear_cache(
    barcode: Optional[str] = Query(None, description="Specific barcode to clear (optional)"),
    user_id: Optional[str] = Header(
        None, alias="X-User-ID", description="User ID for user-specific cache"
    ),
):
    """Clear cache - all or specific barcode"""

    if barcode:
        # Clear specific barcode
        if hasattr(barcode_cache, "clear_barcode"):
            cleared = barcode_cache.clear_barcode(barcode)
        else:
            # Fallback: manually clear barcode entries
            keys_to_remove = [k for k in barcode_cache.cache.keys() if k.endswith(f":{barcode}")]
            for key in keys_to_remove:
                del barcode_cache.cache[key]
            cleared = len(keys_to_remove) > 0
        return {
            "ok": True,
            "cleared": 1 if cleared else 0,
            "total_cached_after": getattr(
                barcode_cache, "get_cache_size", lambda: len(barcode_cache.cache)
            )(),
        }
    elif user_id:
        # Clear user-specific cache
        if hasattr(barcode_cache, "clear_user_cache"):
            barcode_cache.clear_user_cache(user_id)
        else:
            # Fallback: manually clear user entries
            keys_to_remove = [k for k in barcode_cache.cache.keys() if k.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del barcode_cache.cache[key]
        return {
            "ok": True,
            "cleared": 1,
            "total_cached_after": getattr(
                barcode_cache, "get_cache_size", lambda: len(barcode_cache.cache)
            )(),
        }
    else:
        # Clear all cache
        total_before = getattr(barcode_cache, "get_cache_size", lambda: len(barcode_cache.cache))()
        if hasattr(barcode_cache, "clear_all_cache"):
            barcode_cache.clear_all_cache()
        else:
            # Fallback: manually clear all cache
            barcode_cache.cache.clear()
        return {"ok": True, "cleared": total_before, "total_cached_after": 0}


# ========================= TEST BARCODES =========================


@router.get("/test/barcodes")
async def get_test_barcodes():
    """
    Get 5 test barcodes with expected behaviors for acceptance testing
    """
    return {
        "ok": True,
        "test_barcodes": [
            {
                "barcode": "070470003795",
                "description": "Gerber baby food - should find exact recall match",
                "expected_behavior": "exact_match",
                "product": "Gerber Graduates Puffs",
            },
            {
                "barcode": "037000123456",
                "description": "P&G product - should find similar brand recalls",
                "expected_behavior": "similar_found",
                "message": "No direct match - showing similar recalls",
            },
            {
                "barcode": "999999999999",
                "description": "Invalid/unknown barcode - should show no recalls",
                "expected_behavior": "no_recalls",
                "message": "No recalls found for this product",
            },
            {
                "barcode": "12345678",
                "description": "Valid UPC-E - should validate and search",
                "expected_behavior": "no_match or similar_found",
                "message": "Depends on database content",
            },
            {
                "barcode": "5901234123457",
                "description": "Valid EAN-13 - should validate and search",
                "expected_behavior": "no_match or similar_found",
                "message": "International product barcode",
            },
        ],
        "notes": {
            "caching": "Second scan of same barcode returns cached result",
            "fallback": "When no exact match, automatically searches similar products",
            "validation": "Invalid barcodes are normalized and searched anyway",
        },
    }
