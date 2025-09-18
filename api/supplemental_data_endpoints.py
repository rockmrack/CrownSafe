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
    EnhancedSafetyReport
)
from api.schemas.common import ok, fail

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/supplemental",
    tags=["Supplemental Data"]
)

@router.post("/safety-report", response_model=SupplementalDataResponse)
async def get_enhanced_safety_report(
    request: SupplementalDataRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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
            include_chemical_data=request.include_chemical_data
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ok(
            data=report,
            message="Enhanced safety report generated successfully",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating enhanced safety report: {e}", exc_info=True)
        return fail(
            message="Failed to generate enhanced safety report",
            error=str(e),
            status=500
        )

@router.get("/food-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_food_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db)
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
            include_chemical_data=False
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ok(
            data=report,
            message="Food data retrieved successfully",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error getting food data: {e}", exc_info=True)
        return fail(
            message="Failed to get food data",
            error=str(e),
            status=500
        )

@router.get("/cosmetic-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_cosmetic_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db)
):
    """
    Get cosmetic data from EU CosIng database
    
    Returns ingredient information, regulatory status, and safety assessments
    """
    start_time = time.time()
    
    try:
        logger.info(f"Getting cosmetic data for: {product_identifier}")
        
        # Get cosmetic data only
        report = await enhanced_safety_service.generate_enhanced_safety_report(
            product_identifier=product_identifier,
            product_name=product_name,
            product_type="cosmetic",
            include_food_data=False,
            include_cosmetic_data=True,
            include_chemical_data=False
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ok(
            data=report,
            message="Cosmetic data retrieved successfully",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error getting cosmetic data: {e}", exc_info=True)
        return fail(
            message="Failed to get cosmetic data",
            error=str(e),
            status=500
        )

@router.get("/chemical-data/{product_identifier}", response_model=SupplementalDataResponse)
async def get_chemical_data(
    product_identifier: str,
    product_name: Optional[str] = Query(None, description="Product name for better search results"),
    db: Session = Depends(get_db)
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
            include_chemical_data=True
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ok(
            data=report,
            message="Chemical data retrieved successfully",
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error getting chemical data: {e}", exc_info=True)
        return fail(
            message="Failed to get chemical data",
            error=str(e),
            status=500
        )

@router.get("/data-sources", response_model=dict)
async def get_available_data_sources():
    """
    Get list of available supplemental data sources and their status
    """
    try:
        sources = {
            "food": {
                "usda_fooddata_central": {
                    "enabled": bool(enhanced_safety_service.supplemental_service.usda_client.enabled),
                    "description": "USDA FoodData Central - Nutritional and ingredient data",
                    "api_required": True
                },
                "edamam": {
                    "enabled": bool(enhanced_safety_service.supplemental_service.edamam_client.enabled),
                    "description": "Edamam Food Database - Nutritional analysis",
                    "api_required": True
                }
            },
            "cosmetics": {
                "eu_cosing": {
                    "enabled": enhanced_safety_service.supplemental_service.cosing_client.enabled,
                    "description": "EU CosIng Database - Cosmetic ingredients and regulations",
                    "api_required": False
                }
            },
            "chemicals": {
                "osha": {
                    "enabled": True,  # Mock implementation
                    "description": "OSHA Chemical Safety Data",
                    "api_required": False
                },
                "atsdr": {
                    "enabled": True,  # Mock implementation
                    "description": "ATSDR Toxic Substances Database",
                    "api_required": False
                }
            }
        }
        
        return ok(
            data=sources,
            message="Available data sources retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting data sources: {e}", exc_info=True)
        return fail(
            message="Failed to get data sources",
            error=str(e),
            status=500
        )

@router.get("/health", response_model=dict)
async def supplemental_data_health():
    """
    Health check for supplemental data services
    """
    try:
        health_status = {
            "status": "healthy",
            "services": {
                "usda_client": "enabled" if enhanced_safety_service.supplemental_service.usda_client.enabled else "disabled",
                "edamam_client": "enabled" if enhanced_safety_service.supplemental_service.edamam_client.enabled else "disabled",
                "cosing_client": "enabled" if enhanced_safety_service.supplemental_service.cosing_client.enabled else "disabled"
            },
            "timestamp": time.time()
        }
        
        return ok(
            data=health_status,
            message="Supplemental data services health check completed"
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return fail(
            message="Health check failed",
            error=str(e),
            status=500
        )
