"""API endpoints for supplemental data and enhanced safety reports"""

import logging
import time

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from api.models.supplemental_models import (
    SupplementalDataRequest,
    SupplementalDataResponse,
)
from api.schemas.common import fail, ok
from core_infra.database import get_db
from core_infra.enhanced_safety_service import enhanced_safety_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supplemental", tags=["Supplemental Data"])


@router.post("/safety-report", response_model=SupplementalDataResponse)
async def get_enhanced_safety_report(
    request: SupplementalDataRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate comprehensive safety report with supplemental data

    Combines recall data with:
    - Food: USDA FoodData Central, Edamam nutritional data
    - Cosmetics: EU CosIng database, ingredient safety
    - Chemicals: OSHA/ATSDR safety data
    """
    start_time = time.time()

    try:
        logger.info(f"Generating enhanced safety report for: {request.product_identifier}")

        # Generate the enhanced safety report
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=request.product_identifier,
            product_name=request.product_name,
            product_type=request.product_type,
            include_food_data=request.include_food_data,
            include_cosmetic_data=request.include_cosmetic_data,
            include_chemical_data=request.include_chemical_data,
        )

        _ = int((time.time() - start_time) * 1000)  # processing_time (reserved for future logging)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error generating enhanced safety report: {e}", exc_info=True)
        return fail(message=f"Failed to generate enhanced safety report: {e!s}", status=500)


@router.get("/food-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_food_data(
    product_identifier: str,
    product_name: str | None = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """Get comprehensive food data from USDA and Edamam

    Returns nutritional information, ingredients, allergens, and safety scores
    """
    start_time = time.time()

    try:
        logger.info(f"Getting food data for: {product_identifier}")

        # Get food data only
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=product_identifier,
            product_name=product_name,
            product_type="food",
            include_food_data=True,
            include_cosmetic_data=False,
            include_chemical_data=False,
        )

        _ = int((time.time() - start_time) * 1000)  # processing_time (reserved for future logging)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting food data: {e}", exc_info=True)
        return fail(message=f"Failed to get food data: {e!s}", status=500)


@router.get("/cosmetic-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_cosmetic_data(
    product_identifier: str,
    product_name: str | None = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """Get cosmetic data from EU CosIng database

    Returns ingredient information, regulatory status, and safety assessments
    """
    start_time = time.time()

    try:
        logger.info(f"Getting cosmetic data for: {product_identifier}")

        # Debug: Check if service is available
        if not enhanced_safety_service:
            logger.error("Enhanced safety service is not available")
            return fail(message="Service not available", status=503)

        # Get cosmetic data only
        logger.info("Calling generate_enhanced_safety_report...")
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=product_identifier,
            product_name=product_name,
            product_type="cosmetic",
            include_food_data=False,
            include_cosmetic_data=True,
            include_chemical_data=False,
        )

        logger.info(f"Generated report: {report}")
        _ = int((time.time() - start_time) * 1000)  # processing_time (reserved for future logging)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting cosmetic data: {e}", exc_info=True)
        return fail(message=f"Failed to get cosmetic data: {e!s}", status=500)


@router.get("/chemical-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_chemical_data(
    product_identifier: str,
    product_name: str | None = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """Get chemical safety data from OSHA and ATSDR

    Returns safety limits, health effects, and exposure guidelines
    """
    start_time = time.time()

    try:
        logger.info(f"Getting chemical data for: {product_identifier}")

        # Get chemical data only
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=product_identifier,
            product_name=product_name,
            product_type="chemical",
            include_food_data=False,
            include_cosmetic_data=False,
            include_chemical_data=True,
        )

        _ = int((time.time() - start_time) * 1000)  # processing_time (reserved for future logging)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting chemical data: {e}", exc_info=True)
        return fail(message=f"Failed to get chemical data: {e!s}", status=500)


@router.get("/data-sources", response_model=dict)
async def get_available_data_sources():
    """Get list of available supplemental data sources and their status"""
    try:
        sources = {
            "food": {
                "usda_fooddata_central": {
                    "enabled": bool(enhanced_safety_service.supplemental_service.usda_client.enabled),
                    "description": "USDA FoodData Central - Nutritional and ingredient data",
                    "api_required": True,
                },
                "edamam": {
                    "enabled": bool(enhanced_safety_service.supplemental_service.edamam_client.enabled),
                    "description": "Edamam Food Database - Nutritional analysis",
                    "api_required": True,
                },
            },
            "cosmetics": {
                "eu_cosing": {
                    "enabled": enhanced_safety_service.supplemental_service.cosing_client.enabled,
                    "description": "EU CosIng Database - Cosmetic ingredients and regulations",
                    "api_required": False,
                },
            },
            "chemicals": {
                "osha": {
                    "enabled": True,  # Mock implementation
                    "description": "OSHA Chemical Safety Data",
                    "api_required": False,
                },
                "atsdr": {
                    "enabled": True,  # Mock implementation
                    "description": "ATSDR Toxic Substances Database",
                    "api_required": False,
                },
            },
        }

        return ok(data=sources)

    except Exception as e:
        logger.error(f"Error getting data sources: {e}", exc_info=True)
        return fail(message=f"Failed to get data sources: {e!s}", status=500)


@router.get("/health", response_model=dict)
async def supplemental_data_health():
    """Health check for supplemental data services"""
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "usda_client": "enabled"
                if enhanced_safety_service.supplemental_service.usda_client.enabled
                else "disabled",
                "edamam_client": "enabled"
                if enhanced_safety_service.supplemental_service.edamam_client.enabled
                else "disabled",
                "cosing_client": "enabled"
                if enhanced_safety_service.supplemental_service.cosing_client.enabled
                else "disabled",
            },
            "timestamp": time.time(),
        }

        return ok(data=health_status)

    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return fail(message=f"Health check failed: {e!s}", status=500)


@router.get("/test-simple", response_model=dict)
async def test_simple():
    """Simple test endpoint that doesn't use any services"""
    try:
        logger.info("Testing simple endpoint...")
        return ok(data={"message": "Simple test successful", "timestamp": time.time()})
    except Exception as e:
        logger.error(f"Error in simple test: {e}", exc_info=True)
        return fail(message=f"Simple test failed: {e!s}", status=500)


@router.get("/test-cosmetic-simple", response_model=dict)
async def test_cosmetic_simple():
    """Simple test to create a CosmeticDataResponse directly"""
    try:
        from api.models.supplemental_models import (
            CosmeticDataResponse,
            CosmeticIngredient,
        )

        # Test creating a simple cosmetic ingredient
        ingredient = CosmeticIngredient(
            name="glycerin",
            functions=["emollient"],
            restrictions=[],
            safety_assessment="safe",
        )

        # Test creating a cosmetic data response
        cosmetic_response = CosmeticDataResponse(
            product_name="Test Product",
            ingredients=[ingredient],
            regulatory_status={"EU": "approved"},
            safety_concerns=[],
            safety_score=0.8,
            source="test",
        )

        return {
            "success": True,
            "ingredient": ingredient.model_dump(),
            "cosmetic_response": cosmetic_response.model_dump(),
        }

    except Exception as e:
        logger.error(f"Simple test error: {e}", exc_info=True)
        return {"error": f"Simple test error: {e!s}"}


@router.get("/test-dataclass", response_model=dict)
async def test_dataclass():
    """Test creating CosmeticData dataclass directly"""
    try:
        from core_infra.supplemental_data_service import CosmeticData

        # Test creating a cosmetic data dataclass
        cosmetic_data = CosmeticData(
            product_name="test_product",
            ingredients=["ingredient1", "ingredient2"],
            regulatory_status={"EU": "approved"},
            safety_concerns=[],
            source="test",
            safety_score=0.8,
        )

        return {"success": True, "cosmetic_data": cosmetic_data.__dict__}

    except Exception as e:
        logger.error(f"Dataclass test error: {e}", exc_info=True)
        return {"error": f"Dataclass test error: {e!s}"}


@router.get("/test-post-endpoint", response_model=dict)
async def test_post_endpoint():
    """Test the POST safety-report endpoint with a GET request for easier testing"""
    try:
        from api.models.supplemental_models import SupplementalDataRequest

        # Simulate the POST request data
        request_data = SupplementalDataRequest(
            product_identifier="glycerin",
            product_name="glycerin",
            product_type="cosmetic",
            include_food_data=False,
            include_cosmetic_data=True,
            include_chemical_data=False,
        )

        # Generate the report
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=request_data.product_identifier,
            product_name=request_data.product_name,
            product_type=request_data.product_type,
            include_food_data=request_data.include_food_data,
            include_cosmetic_data=request_data.include_cosmetic_data,
            include_chemical_data=request_data.include_chemical_data,
        )

        return {
            "success": True,
            "message": "POST endpoint simulation successful",
            "data": report.model_dump() if hasattr(report, "model_dump") else report.__dict__,
        }

    except Exception as e:
        logger.error(f"POST test error: {e}", exc_info=True)
        return {"error": f"POST test error: {e!s}"}


# REMOVED FOR CROWN SAFE: RecallDB test endpoints
# @router.get("/test-recalls-fix", response_model=dict)
# async def test_recalls_fix():
#     """Test that the recalls endpoint fix is working"""
#     # Removed - RecallDB no longer exists in Crown Safe

# @router.get("/test-recall-detail", response_model=dict)
# async def test_recall_detail():
#     """Test the recall detail endpoint functionality"""
#     # Removed - recalls_enhanced table no longer exists in Crown Safe


@router.get("/test-cache-clear", response_model=dict)
async def test_cache_clear():
    """Test the cache clear endpoint functionality"""
    try:
        from api.barcode_bridge import barcode_cache

        # Test cache operations
        cache_size_before = barcode_cache.get_cache_size()

        # Test adding some data to cache
        barcode_cache.set("test123", {"test": "data"})
        cache_size_after_add = barcode_cache.get_cache_size()

        # Test clearing specific barcode
        cleared = barcode_cache.clear_barcode("test123")
        cache_size_after_clear = barcode_cache.get_cache_size()

        return {
            "success": True,
            "message": "Cache clear functionality test successful",
            "cache_size_before": cache_size_before,
            "cache_size_after_add": cache_size_after_add,
            "cache_size_after_clear": cache_size_after_clear,
            "barcode_cleared": cleared,
        }

    except Exception as e:
        logger.error(f"Cache clear test error: {e}", exc_info=True)
        return {"error": f"Cache clear test error: {e!s}"}


@router.get("/test-cosmetic", response_model=dict)
async def test_cosmetic_data():
    """Simple test endpoint for cosmetic data"""
    try:
        logger.info("Testing cosmetic data service...")

        # Test 1: Check if enhanced_safety_service exists
        if not enhanced_safety_service:
            logger.error("enhanced_safety_service is None")
            return fail(message="Enhanced safety service is None", status=500)

        # Test 2: Check if supplemental_service exists
        if not hasattr(enhanced_safety_service, "supplemental_service"):
            logger.error("enhanced_safety_service has no supplemental_service attribute")
            return fail(message="Supplemental service not found", status=500)

        if not enhanced_safety_service.supplemental_service:
            logger.error("supplemental_service is None")
            return fail(message="Supplemental service is None", status=500)

        # Test 3: Check if get_cosmetic_data method exists
        if not hasattr(enhanced_safety_service.supplemental_service, "get_cosmetic_data"):
            logger.error("supplemental_service has no get_cosmetic_data method")
            return fail(message="get_cosmetic_data method not found", status=500)

        # Test 4: Try to call the method
        logger.info("Calling get_cosmetic_data...")
        cosmetic_data = await enhanced_safety_service.supplemental_service.get_cosmetic_data("test")

        # Test 5: Check if we got data back
        if not cosmetic_data:
            logger.error("get_cosmetic_data returned None")
            return fail(message="get_cosmetic_data returned None", status=500)

        return ok(
            data={
                "test_result": "success",
                "cosmetic_data": {
                    "product_name": cosmetic_data.product_name,
                    "ingredients": cosmetic_data.ingredients,
                    "source": cosmetic_data.source,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error in cosmetic test: {e}", exc_info=True)
        return fail(message=f"Cosmetic test failed: {e!s}", status=500)
