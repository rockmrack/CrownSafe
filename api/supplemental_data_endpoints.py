"""
API endpoints for supplemental data and enhanced safety reports
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from core_infra.database import get_db
from core_infra.enhanced_safety_service import enhanced_safety_service
from api.models.supplemental_models import (
    SupplementalDataRequest,
    SupplementalDataResponse,
    EnhancedSafetyReport,
)
from api.schemas.common import ok, fail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/supplemental", tags=["Supplemental Data"])


@router.post("/safety-report", response_model=SupplementalDataResponse)
async def get_enhanced_safety_report(
    request: SupplementalDataRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Generate comprehensive safety report with supplemental data

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

        processing_time = int((time.time() - start_time) * 1000)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error generating enhanced safety report: {e}", exc_info=True)
        return fail(message=f"Failed to generate enhanced safety report: {str(e)}", status=500)


@router.get("/food-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_food_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """
    Get comprehensive food data from USDA and Edamam

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

        processing_time = int((time.time() - start_time) * 1000)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting food data: {e}", exc_info=True)
        return fail(message=f"Failed to get food data: {str(e)}", status=500)


@router.get("/cosmetic-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_cosmetic_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """
    Get cosmetic data from EU CosIng database

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
        processing_time = int((time.time() - start_time) * 1000)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting cosmetic data: {e}", exc_info=True)
        return fail(message=f"Failed to get cosmetic data: {str(e)}", status=500)


@router.get("/chemical-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_chemical_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db),
):
    """
    Get chemical safety data from OSHA and ATSDR

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

        processing_time = int((time.time() - start_time) * 1000)

        return ok(data=report)

    except Exception as e:
        logger.error(f"Error getting chemical data: {e}", exc_info=True)
        return fail(message=f"Failed to get chemical data: {str(e)}", status=500)


@router.get("/data-sources", response_model=dict)
async def get_available_data_sources():
    """
    Get list of available supplemental data sources and their status
    """
    try:
        sources = {
            "food": {
                "usda_fooddata_central": {
                    "enabled": bool(
                        enhanced_safety_service.supplemental_service.usda_client.enabled
                    ),
                    "description": "USDA FoodData Central - Nutritional and ingredient data",
                    "api_required": True,
                },
                "edamam": {
                    "enabled": bool(
                        enhanced_safety_service.supplemental_service.edamam_client.enabled
                    ),
                    "description": "Edamam Food Database - Nutritional analysis",
                    "api_required": True,
                },
            },
            "cosmetics": {
                "eu_cosing": {
                    "enabled": enhanced_safety_service.supplemental_service.cosing_client.enabled,
                    "description": "EU CosIng Database - Cosmetic ingredients and regulations",
                    "api_required": False,
                }
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
        return fail(message=f"Failed to get data sources: {str(e)}", status=500)


@router.get("/health", response_model=dict)
async def supplemental_data_health():
    """
    Health check for supplemental data services
    """
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
        return fail(message=f"Health check failed: {str(e)}", status=500)


@router.get("/test-simple", response_model=dict)
async def test_simple():
    """
    Simple test endpoint that doesn't use any services
    """
    try:
        logger.info("Testing simple endpoint...")
        return ok(data={"message": "Simple test successful", "timestamp": time.time()})
    except Exception as e:
        logger.error(f"Error in simple test: {e}", exc_info=True)
        return fail(message=f"Simple test failed: {str(e)}", status=500)


@router.get("/test-cosmetic-simple", response_model=dict)
async def test_cosmetic_simple():
    """
    Simple test to create a CosmeticDataResponse directly
    """
    try:
        from api.models.supplemental_models import CosmeticDataResponse, CosmeticIngredient

        # Test creating a simple cosmetic ingredient
        ingredient = CosmeticIngredient(
            name="glycerin", functions=["emollient"], restrictions=[], safety_assessment="safe"
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
        return {"error": f"Simple test error: {str(e)}"}


@router.get("/test-dataclass", response_model=dict)
async def test_dataclass():
    """
    Test creating CosmeticData dataclass directly
    """
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
        return {"error": f"Dataclass test error: {str(e)}"}


@router.get("/test-post-endpoint", response_model=dict)
async def test_post_endpoint():
    """
    Test the POST safety-report endpoint with a GET request for easier testing
    """
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
        return {"error": f"POST test error: {str(e)}"}


@router.get("/test-recalls-fix", response_model=dict)
async def test_recalls_fix():
    """
    Test that the recalls endpoint fix is working
    """
    try:
        from core_infra.database import get_db_session

        with get_db_session() as db:
            from core_infra.database import RecallDB

            # Test a simple query to make sure the model works
            count = db.query(RecallDB).count()

            # Test that we can access the fields without errors
            sample_recall = db.query(RecallDB).first()
            if sample_recall:
                # Test accessing fields that exist
                test_fields = {
                    "id": sample_recall.id,
                    "recall_id": sample_recall.recall_id,
                    "product_name": sample_recall.product_name,
                    "brand": sample_recall.brand,
                    "manufacturer": getattr(sample_recall, "manufacturer", None),
                    "model_number": sample_recall.model_number,
                    "hazard": sample_recall.hazard,
                    "hazard_category": getattr(sample_recall, "hazard_category", None),
                    "recall_date": sample_recall.recall_date,
                    "recall_reason": getattr(sample_recall, "recall_reason", None),
                    "remedy": sample_recall.remedy,
                    "recall_class": getattr(sample_recall, "recall_class", None),
                    "url": sample_recall.url,
                }

                return {
                    "success": True,
                    "message": "Recalls endpoint fix successful",
                    "total_recalls": count,
                    "sample_fields": test_fields,
                }
            else:
                return {
                    "success": True,
                    "message": "Recalls endpoint fix successful - no data in database",
                    "total_recalls": count,
                }

    except Exception as e:
        logger.error(f"Recalls test error: {e}", exc_info=True)
        return {"error": f"Recalls test error: {str(e)}"}


@router.get("/test-recall-detail", response_model=dict)
async def test_recall_detail():
    """
    Test the recall detail endpoint functionality
    """
    try:
        from core_infra.database import get_db_session
        from sqlalchemy import text

        with get_db_session() as db:
            # Test the SQL query directly
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
                LIMIT 1
            """
            )

            result = db.execute(query).fetchone()

            if result:
                recall_data = dict(result._mapping) if hasattr(result, "_mapping") else dict(result)
                return {
                    "success": True,
                    "message": "Recall detail query successful",
                    "sample_data": recall_data,
                }
            else:
                return {
                    "success": True,
                    "message": "Recall detail query successful - no data in enhanced table",
                }

    except Exception as e:
        logger.error(f"Recall detail test error: {e}", exc_info=True)
        return {"error": f"Recall detail test error: {str(e)}"}


@router.get("/test-cache-clear", response_model=dict)
async def test_cache_clear():
    """
    Test the cache clear endpoint functionality
    """
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
        return {"error": f"Cache clear test error: {str(e)}"}


@router.get("/test-cosmetic", response_model=dict)
async def test_cosmetic_data():
    """
    Simple test endpoint for cosmetic data
    """
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
            }
        )

    except Exception as e:
        logger.error(f"Error in cosmetic test: {e}", exc_info=True)
        return fail(message=f"Cosmetic test failed: {str(e)}", status=500)
