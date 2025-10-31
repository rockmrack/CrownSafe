from api.pydantic_base import AppModel

#!/usr/bin/env python3
"""
BabyShield API v1 Endpoints
Implements versioned API endpoints with backward compatibility
"""

import logging
import os

# Import database and recall logic
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import ProgrammingError

from core_infra.database import get_db_session  # RecallDB removed - Crown Safe uses HairProductModel

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

# Search backend configuration
SEARCH_BACKEND_MODE = os.getenv("SEARCH_BACKEND_MODE", "db")  # "db" | "upstream"
ALLOW_UPSTREAM_FALLBACK = os.getenv("ALLOW_UPSTREAM_FALLBACK", "true").lower() == "true"

# ==================== RESPONSE MODELS ====================


class Agency(BaseModel):
    """Agency information model"""

    code: str = Field(..., description="Agency code (e.g., 'FDA')")
    name: str = Field(..., description="Full agency name")
    country: str = Field(..., description="Country or region")
    website: Optional[str] = Field(None, description="Official website URL")


class SafetyIssue(BaseModel):
    """Safety issue/recall model with all required fields"""

    id: str = Field(..., description="Unique identifier")
    agencyCode: str = Field(..., description="Agency code")
    title: str = Field(..., description="Recall title")
    description: Optional[str] = Field(None, description="Detailed description")
    productName: Optional[str] = Field(None, description="Product name")
    brand: Optional[str] = Field(None, description="Brand name")
    model: Optional[str] = Field(None, description="Model number")
    upc: Optional[str] = Field(None, description="UPC/barcode")
    hazard: Optional[str] = Field(None, description="Hazard description")
    riskCategory: Optional[str] = Field(None, description="Risk category")
    severity: Optional[str] = Field(None, description="Severity level", pattern="^(low|medium|high)$")
    status: Optional[str] = Field(None, description="Recall status", pattern="^(open|closed)$")
    imageUrl: Optional[str] = Field(None, description="Product image URL")
    affectedCountries: Optional[List[str]] = Field(None, description="Affected countries")
    recallDate: Optional[str] = Field(None, description="Recall date (YYYY-MM-DD)")
    lastUpdated: Optional[str] = Field(None, description="Last update timestamp (ISO-8601)")
    sourceUrl: str = Field(..., description="Source URL for recall details")


class SearchResults(BaseModel):
    """Search results with pagination"""

    items: List[SafetyIssue]
    nextCursor: Optional[str] = None
    total: Optional[int] = None


class SuccessResponse(BaseModel):
    """Success response envelope"""

    ok: bool = True
    data: Any
    traceId: str


class ErrorDetail(BaseModel):
    """Error detail model"""

    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response envelope"""

    ok: bool = False
    error: ErrorDetail
    traceId: str


# ==================== FIXED AGENCY DATA ====================

AGENCIES = [
    # North America (9 agencies)
    # United States (4 agencies)
    Agency(
        code="FDA",
        name="U.S. Food and Drug Administration",
        country="United States",
        website="https://www.fda.gov",
    ),
    Agency(
        code="CPSC",
        name="U.S. Consumer Product Safety Commission",
        country="United States",
        website="https://www.cpsc.gov",
    ),
    Agency(
        code="NHTSA",
        name="National Highway Traffic Safety Administration",
        country="United States",
        website="https://www.nhtsa.gov",
    ),
    Agency(
        code="USDA_FSIS",
        name="Food Safety and Inspection Service",
        country="United States",
        website="https://www.fsis.usda.gov",
    ),
    # Canada (3 agencies)
    Agency(
        code="HEALTH_CANADA",
        name="Health Canada",
        country="Canada",
        website="https://www.canada.ca/en/health-canada",
    ),
    Agency(
        code="CFIA",
        name="Canadian Food Inspection Agency",
        country="Canada",
        website="https://www.inspection.gc.ca",
    ),
    Agency(
        code="TRANSPORT_CANADA",
        name="Transport Canada",
        country="Canada",
        website="https://www.tc.gc.ca",
    ),
    # Mexico (2 agencies)
    Agency(
        code="PROFECO",
        name="Federal Consumer Protection Agency",
        country="Mexico",
        website="https://www.profeco.gob.mx",
    ),
    Agency(
        code="COFEPRIS",
        name="Federal Commission for Protection against Sanitary Risk",
        country="Mexico",
        website="https://www.gob.mx/cofepris",
    ),
    # Europe (22 agencies)
    # European Union (1 agency)
    Agency(
        code="EU_SAFETY_GATE",
        name="EU Safety Gate (RAPEX)",
        country="European Union",
        website="https://ec.europa.eu/safety-gate",
    ),
    # United Kingdom (2 agencies)
    Agency(
        code="UK_OPSS",
        name="UK Office for Product Safety and Standards",
        country="United Kingdom",
        website="https://www.gov.uk/government/organisations/office-for-product-safety-and-standards",
    ),
    Agency(
        code="UK_FSA",
        name="Food Standards Agency",
        country="United Kingdom",
        website="https://www.food.gov.uk",
    ),
    Agency(
        code="UK_TRADING_STANDARDS",
        name="Trading Standards (Local Authorities)",
        country="United Kingdom",
        website="https://www.tradingstandards.uk/consumers/product-recalls",
    ),
    Agency(
        code="UK_DVSA",
        name="Driver and Vehicle Standards Agency",
        country="United Kingdom",
        website="https://www.gov.uk/vehicle-recalls-and-faults",
    ),
    Agency(
        code="UK_MHRA",
        name="Medicines and Healthcare products Regulatory Agency",
        country="United Kingdom",
        website="https://www.gov.uk/drug-device-alerts",
    ),
    # France (1 agency)
    Agency(
        code="RAPPEL_CONSO",
        name="RappelConso",
        country="France",
        website="https://rappel.conso.gouv.fr",
    ),
    # Germany (1 agency)
    Agency(
        code="LEBENSMITTELWARNUNG",
        name="Lebensmittelwarnung",
        country="Germany",
        website="https://www.lebensmittelwarnung.de",
    ),
    # Netherlands (1 agency)
    Agency(
        code="NVWA",
        name="Food and Product Safety Authority",
        country="Netherlands",
        website="https://www.nvwa.nl",
    ),
    # Spain (1 agency)
    Agency(
        code="AESAN",
        name="Food Safety and Nutrition Agency",
        country="Spain",
        website="https://www.aesan.gob.es",
    ),
    # Italy (1 agency)
    Agency(
        code="MINISTRY_HEALTH_ITALY",
        name="Ministry of Health",
        country="Italy",
        website="https://www.salute.gov.it",
    ),
    # Switzerland (3 agencies)
    Agency(
        code="FCAB",
        name="Federal Consumer Affairs Bureau",
        country="Switzerland",
        website="https://www.konsum.admin.ch",
    ),
    Agency(
        code="FSVO",
        name="Federal Food Safety and Veterinary Office",
        country="Switzerland",
        website="https://www.blv.admin.ch",
    ),
    Agency(
        code="SWISSMEDIC",
        name="Swissmedic",
        country="Switzerland",
        website="https://www.swissmedic.ch",
    ),
    # Sweden (2 agencies)
    Agency(
        code="CONSUMER_AGENCY_SWEDEN",
        name="Consumer Agency",
        country="Sweden",
        website="https://www.konsumentverket.se",
    ),
    Agency(
        code="FOOD_AGENCY_SWEDEN",
        name="Food Agency",
        country="Sweden",
        website="https://www.livsmedelsverket.se",
    ),
    # Norway (2 agencies)
    Agency(
        code="DSB",
        name="Directorate for Civil Protection",
        country="Norway",
        website="https://www.dsb.no",
    ),
    Agency(
        code="MATTILSYNET",
        name="Food Safety Authority",
        country="Norway",
        website="https://www.mattilsynet.no",
    ),
    # Denmark (2 agencies)
    Agency(
        code="SAFETY_TECH_AUTHORITY_DENMARK",
        name="Safety Technology Authority",
        country="Denmark",
        website="https://www.sik.dk",
    ),
    Agency(
        code="FOOD_ADMIN_DENMARK",
        name="Food Administration",
        country="Denmark",
        website="https://www.foedevarestyrelsen.dk",
    ),
    # Finland (2 agencies)
    Agency(
        code="TUKES",
        name="Safety and Chemicals Agency",
        country="Finland",
        website="https://www.tukes.fi",
    ),
    Agency(
        code="FOOD_AUTHORITY_FINLAND",
        name="Food Authority",
        country="Finland",
        website="https://www.ruokavirasto.fi",
    ),
    # Asia-Pacific (7 agencies)
    # Singapore (1 agency)
    Agency(
        code="CPSO",
        name="Consumer Product Safety Office",
        country="Singapore",
        website="https://www.cpsa.gov.sg",
    ),
    # Australia (3 agencies)
    Agency(
        code="ACCC",
        name="Competition and Consumer Commission",
        country="Australia",
        website="https://www.accc.gov.au",
    ),
    Agency(
        code="TGA",
        name="Therapeutic Goods Administration",
        country="Australia",
        website="https://www.tga.gov.au",
    ),
    Agency(
        code="FSANZ",
        name="Food Standards (shared with NZ)",
        country="Australia",
        website="https://www.foodstandards.gov.au",
    ),
    # New Zealand (3 agencies)
    Agency(
        code="TRADING_STANDARDS_NZ",
        name="Trading Standards",
        country="New Zealand",
        website="https://www.consumerprotection.govt.nz",
    ),
    Agency(
        code="MPI",
        name="Ministry for Primary Industries",
        country="New Zealand",
        website="https://www.mpi.govt.nz",
    ),
    Agency(
        code="MEDSAFE",
        name="Medsafe",
        country="New Zealand",
        website="https://www.medsafe.govt.nz",
    ),
    # South America (4 agencies)
    # Brazil (3 agencies)
    Agency(
        code="ANVISA",
        name="National Health Surveillance Agency",
        country="Brazil",
        website="https://www.gov.br/anvisa",
    ),
    Agency(
        code="SENACON",
        name="National Consumer Secretary",
        country="Brazil",
        website="https://www.gov.br/mj/pt-br/assuntos/senacon",
    ),
    Agency(
        code="INMETRO",
        name="National Institute of Metrology",
        country="Brazil",
        website="https://www.gov.br/inmetro",
    ),
    # Argentina (1 agency)
    Agency(
        code="ANMAT",
        name="National Administration of Drugs, Foods and Medical Technology",
        country="Argentina",
        website="https://www.anmat.gov.ar",
    ),
]

# Map internal agency names to API codes
AGENCY_CODE_MAP = {
    # North America
    "FDA": "FDA",
    "CPSC": "CPSC",
    "NHTSA": "NHTSA",
    "USDA FSIS": "USDA_FSIS",
    "Health Canada": "HEALTH_CANADA",
    "CFIA": "CFIA",
    "Transport Canada": "TRANSPORT_CANADA",
    "PROFECO": "PROFECO",
    "COFEPRIS": "COFEPRIS",
    # Europe
    "EU RAPEX": "EU_SAFETY_GATE",
    "UK OPSS": "UK_OPSS",
    "UK FSA": "UK_FSA",
    "UK Trading Standards": "UK_TRADING_STANDARDS",
    "UK DVSA": "UK_DVSA",
    "UK MHRA": "UK_MHRA",
    "RappelConso": "RAPPEL_CONSO",
    "Lebensmittelwarnung": "LEBENSMITTELWARNUNG",
    "NVWA": "NVWA",
    "AESAN": "AESAN",
    "Ministry of Health Italy": "MINISTRY_HEALTH_ITALY",
    "FCAB": "FCAB",
    "FSVO": "FSVO",
    "Swissmedic": "SWISSMEDIC",
    "Consumer Agency Sweden": "CONSUMER_AGENCY_SWEDEN",
    "Food Agency Sweden": "FOOD_AGENCY_SWEDEN",
    "DSB": "DSB",
    "Mattilsynet": "MATTILSYNET",
    "Safety Technology Authority Denmark": "SAFETY_TECH_AUTHORITY_DENMARK",
    "Food Administration Denmark": "FOOD_ADMIN_DENMARK",
    "Tukes": "TUKES",
    "Food Authority Finland": "FOOD_AUTHORITY_FINLAND",
    # Asia-Pacific
    "CPSO": "CPSO",
    "ACCC": "ACCC",
    "TGA": "TGA",
    "FSANZ": "FSANZ",
    "Trading Standards NZ": "TRADING_STANDARDS_NZ",
    "MPI": "MPI",
    "Medsafe": "MEDSAFE",
    # South America
    "ANVISA": "ANVISA",
    "SENACON": "SENACON",
    "INMETRO": "INMETRO",
    "ANMAT": "ANMAT",
}

# Reverse map for queries
API_CODE_TO_INTERNAL = {v: k for k, v in AGENCY_CODE_MAP.items()}

# ==================== ROUTER SETUP ====================

router = APIRouter()

# ==================== INDEX ROUTE ====================


@router.get("/", include_in_schema=False)
def api_v1_index():
    """API v1 index endpoint to prevent 404 logs"""
    return {
        "ok": True,
        "version": "1.2.0",
        "message": "BabyShield API v1",
        "endpoints": {
            "search": "/api/v1/search",
            "recalls": "/api/v1/recalls",
            "safety_check": "/api/v1/safety-check",
            "health": "/healthz",
        },
    }


# ==================== HELPER FUNCTIONS ====================


def generate_trace_id() -> str:
    """Generate a unique trace ID for the request"""
    return f"trace_{uuid.uuid4().hex[:16]}_{int(datetime.now().timestamp())}"


def convert_recall_to_safety_issue(recall: Any, agency_code: str) -> SafetyIssue:
    """Convert recall object to SafetyIssue model - DEPRECATED FOR CROWN SAFE"""
    # REMOVED FOR CROWN SAFE: This function converted RecallDB objects to SafetyIssue
    # Crown Safe focuses on hair product testing (HairProductModel), not baby recalls
    # Return minimal valid object with deprecation notice
    return SafetyIssue(
        id="deprecated",
        agencyCode=agency_code,
        title="Recall lookup deprecated for Crown Safe",
        description="Crown Safe focuses on hair product testing",
        productName="N/A",
        brand=None,
        model=None,
        upc=None,
        hazard=None,
        riskCategory=None,
        severity="low",
        status="closed",
        imageUrl=None,
        affectedCountries=[],
        recallDate=None,
        lastUpdated=datetime.now().isoformat(),
        sourceUrl="https://crownsafe.cureviax.ai",
    )


def check_table_exists(db_session) -> bool:
    """Check if recalls_enhanced table exists"""
    try:
        from sqlalchemy import inspect

        inspector = inspect(db_session.bind)
        return inspector.has_table("recalls_enhanced")
    except Exception as e:
        logger.warning(f"Could not check table existence: {e}")
        return False


def get_empty_search_result() -> dict:
    """Return empty search result structure"""
    return {"items": [], "nextCursor": None, "total": 0}


async def search_agency_upstream(agency_code: str, product: str, limit: int = 20) -> dict:
    """Search using upstream agency connectors (bypass database)"""
    logger.info(f"🔄 Using upstream search for {agency_code} (product: {product})")

    # Import connectors dynamically to avoid circular imports
    try:
        from agents.recall_data_agent.connectors import CPSCConnector, FDAConnector

        connector = None
        if agency_code == "CPSC":
            connector = CPSCConnector()
        elif agency_code == "FDA":
            connector = FDAConnector()

        if connector:
            # Fetch recent recalls from upstream
            recalls = await connector.fetch_recent_recalls()

            # Filter by product search term
            filtered_recalls = []
            for recall in recalls[:limit]:  # Limit results
                if (
                    (product.lower() in recall.product_name.lower() if recall.product_name else False)
                    or (product.lower() in recall.description.lower() if recall.description else False)
                    or (product.lower() in (recall.brand or "").lower())
                ):
                    filtered_recalls.append(recall)

            # Convert to SafetyIssue format
            items = []
            for recall in filtered_recalls[:limit]:
                try:
                    # Create a mock database object for conversion
                    mock_recall = type(
                        "MockRecall",
                        (),
                        {
                            "recall_id": recall.recall_id,
                            "product_name": recall.product_name,
                            "brand": getattr(recall, "brand", None),
                            "description": getattr(recall, "description", None),
                            "model_number": getattr(recall, "model_number", None),
                            "hazard": getattr(recall, "hazard", None),
                            "hazard_category": getattr(recall, "hazard_category", None),
                            "recall_date": recall.recall_date,
                            "url": getattr(recall, "url", None),
                            "manufacturer": getattr(recall, "manufacturer", None),
                            "manufacturer_contact": getattr(recall, "manufacturer_contact", None),
                            "country": getattr(recall, "country", None),
                            "regions_affected": getattr(recall, "regions_affected", None),
                            "upc": getattr(recall, "upc", None),
                        },
                    )()

                    safety_issue = convert_recall_to_safety_issue(mock_recall, agency_code)
                    items.append(safety_issue)
                except Exception as e:
                    logger.warning(f"Failed to convert upstream recall {recall.recall_id}: {e}")
                    continue

            return {
                "items": [item.dict() for item in items],
                "nextCursor": None,  # Upstream doesn't support cursor pagination
                "total": len(items),
            }
        else:
            logger.warning(f"No upstream connector available for {agency_code}")
            return get_empty_search_result()

    except Exception as e:
        logger.error(f"Upstream search failed for {agency_code}: {e}", exc_info=True)
        return get_empty_search_result()


async def search_agency_recalls(agency_code: str, product: str, limit: int = 20, cursor: Optional[str] = None) -> dict:
    """
    Search recalls for a specific agency with graceful table missing handling

    Returns empty results if table doesn't exist, preventing 500 errors
    """

    # 🚨 HOTFIX: Check if we should use upstream mode to bypass DB
    if SEARCH_BACKEND_MODE == "upstream":
        logger.info(f"🔄 HOTFIX MODE: Using upstream search for {agency_code} to bypass database issues")
        return await search_agency_upstream(agency_code, product, limit)

    # Map API code to internal agency name
    internal_agency = API_CODE_TO_INTERNAL.get(agency_code)
    if not internal_agency:
        raise ValueError(f"Invalid agency code: {agency_code}")

    try:
        with get_db_session() as db:
            # Check if table exists first
            if not check_table_exists(db):
                logger.warning(f"Table 'recalls_enhanced' does not exist for {agency_code}")
                if ALLOW_UPSTREAM_FALLBACK:
                    logger.info(f"🔄 Falling back to upstream search for {agency_code}")
                    return await search_agency_upstream(agency_code, product, limit)
                return get_empty_search_result()

            # Check if table is empty
            try:
                row_count = db.execute(text("SELECT COUNT(*) FROM recalls_enhanced")).scalar()
                if row_count == 0:
                    logger.info(f"Table 'recalls_enhanced' is empty for {agency_code}")
                    if ALLOW_UPSTREAM_FALLBACK:
                        logger.info(f"🔄 Falling back to upstream search for {agency_code}")
                        return await search_agency_upstream(agency_code, product, limit)
                    return get_empty_search_result()
            except Exception as e:
                logger.warning(f"Could not check table row count: {e}")
                if ALLOW_UPSTREAM_FALLBACK:
                    logger.info(f"🔄 Falling back to upstream search for {agency_code}")
                    return await search_agency_upstream(agency_code, product, limit)
                return get_empty_search_result()

            # REMOVED FOR CROWN SAFE: RecallDB search logic gutted
            # Crown Safe focuses on hair product testing (HairProductModel), not baby recalls
            # This previously queried RecallDB by:
            # - product_name, brand, description, model_number (ILIKE search)
            # - cursor pagination by recall_id
            # - convert_recall_to_safety_issue for each result

            return get_empty_search_result()

    except ProgrammingError as e:
        # Handle specific case where table doesn't exist or has schema issues
        error_message = str(e.orig) if hasattr(e, "orig") else str(e)
        if "does not exist" in error_message.lower() or "relation" in error_message.lower():
            logger.warning(f"Database table issue for {agency_code}: {error_message}")
            if ALLOW_UPSTREAM_FALLBACK:
                logger.info(f"🔄 Falling back to upstream search for {agency_code}")
                return await search_agency_upstream(agency_code, product, limit)
            return get_empty_search_result()
        else:
            logger.error(f"Database programming error for {agency_code}: {e}", exc_info=True)
            raise
    except Exception as e:
        logger.error(f"Search failed for agency {agency_code}: {e}", exc_info=True)
        if ALLOW_UPSTREAM_FALLBACK:
            logger.warning(f"🔄 Falling back to upstream search for {agency_code} due to error: {e}")
            return await search_agency_upstream(agency_code, product, limit)
        raise


# ==================== VERSIONED ENDPOINTS ====================


@router.get("/api/v1/agencies", response_model=SuccessResponse, tags=["agencies"])
async def list_agencies_v1(request: Request):
    """List all supported agencies (versioned)"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] GET /api/v1/agencies")

    return SuccessResponse(ok=True, data=AGENCIES, traceId=trace_id)


@router.get("/api/v1/fda", tags=["search"])
async def search_fda_v1(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search FDA recalls (versioned)"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] GET /api/v1/fda?product={product}&limit={limit}&cursor={cursor}")

    try:
        results = await search_agency_recalls("FDA", product, limit, cursor)
        return JSONResponse(content={"ok": True, "data": results, "traceId": trace_id})
    except ValueError as e:
        logger.error(f"[{trace_id}] FDA validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {"code": "BAD_REQUEST", "message": str(e)},
                "traceId": trace_id,
            },
        )
    except Exception as e:
        logger.error(f"[{trace_id}] FDA search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to search FDA recalls: {str(e)}",
                },
                "traceId": trace_id,
            },
        )


@router.get("/api/v1/cpsc", tags=["search"])
async def search_cpsc_v1(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search CPSC recalls (versioned)"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] GET /api/v1/cpsc?product={product}&limit={limit}&cursor={cursor}")

    try:
        results = await search_agency_recalls("CPSC", product, limit, cursor)
        return JSONResponse(content={"ok": True, "data": results, "traceId": trace_id})
    except ValueError as e:
        logger.error(f"[{trace_id}] CPSC validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {"code": "BAD_REQUEST", "message": str(e)},
                "traceId": trace_id,
            },
        )
    except Exception as e:
        logger.error(f"[{trace_id}] CPSC search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to search CPSC recalls: {str(e)}",
                },
                "traceId": trace_id,
            },
        )


@router.get("/api/v1/eu_safety_gate", tags=["search"])
async def search_eu_safety_gate_v1(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search EU Safety Gate (RAPEX) recalls (versioned)"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] GET /api/v1/eu_safety_gate?product={product}&limit={limit}&cursor={cursor}")

    try:
        results = await search_agency_recalls("EU_SAFETY_GATE", product, limit, cursor)
        return JSONResponse(content={"ok": True, "data": results, "traceId": trace_id})
    except ValueError as e:
        logger.error(f"[{trace_id}] EU Safety Gate validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {"code": "BAD_REQUEST", "message": str(e)},
                "traceId": trace_id,
            },
        )
    except Exception as e:
        logger.error(f"[{trace_id}] EU Safety Gate search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to search EU Safety Gate recalls: {str(e)}",
                },
                "traceId": trace_id,
            },
        )


@router.get("/api/v1/uk_opss", tags=["search"])
async def search_uk_opss_v1(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search UK OPSS recalls (versioned)"""
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] GET /api/v1/uk_opss?product={product}&limit={limit}&cursor={cursor}")

    try:
        results = await search_agency_recalls("UK_OPSS", product, limit, cursor)
        return JSONResponse(content={"ok": True, "data": results, "traceId": trace_id})
    except ValueError as e:
        logger.error(f"[{trace_id}] UK OPSS validation error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": {"code": "BAD_REQUEST", "message": str(e)},
                "traceId": trace_id,
            },
        )
    except Exception as e:
        logger.error(f"[{trace_id}] UK OPSS search error: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to search UK OPSS recalls: {str(e)}",
                },
                "traceId": trace_id,
            },
        )


# ==================== UNVERSIONED ALIASES (Backward Compatibility) ====================


@router.get("/agencies", response_model=SuccessResponse, tags=["agencies"])
async def list_agencies_alias(request: Request):
    """List all supported agencies (unversioned alias for backward compatibility)"""
    return await list_agencies_v1(request)


@router.get("/fda", tags=["search"], include_in_schema=False)
async def search_fda_alias(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search FDA recalls (unversioned alias - backward compatibility)"""
    return await search_fda_v1(request, product, limit, cursor)


@router.get("/cpsc", tags=["search"])
async def search_cpsc_alias(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search CPSC recalls (unversioned alias for backward compatibility)"""
    return await search_cpsc_v1(request, product, limit, cursor)


@router.get("/eu_safety_gate", tags=["search"])
async def search_eu_safety_gate_alias(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search EU Safety Gate recalls (unversioned alias for backward compatibility)"""
    return await search_eu_safety_gate_v1(request, product, limit, cursor)


@router.get("/uk_opss", tags=["search"])
async def search_uk_opss_alias(
    request: Request,
    product: str = Query(..., description="Product search term"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """Search UK OPSS recalls (unversioned alias for backward compatibility)"""
    return await search_uk_opss_v1(request, product, limit, cursor)
