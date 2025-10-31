"""
A-5 Exact/Valid Scan: Enhanced Barcode Scanning Endpoints
Provides exact validation and comprehensive error handling
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.services.dev_override import dev_entitled
from core_infra.barcode_validator import BarcodeType, ValidationResult
from core_infra.database import get_db_session
from core_infra.enhanced_barcode_service import (
    ExactScanResult,
    enhanced_barcode_service,
)

logger = logging.getLogger(__name__)

# Create router
enhanced_barcode_router = APIRouter(prefix="/api/v1/enhanced-scan", tags=["enhanced-barcode-scanning"])


# Request/Response Models
class EnhancedScanRequest(BaseModel):
    """Request model for enhanced barcode scanning"""

    barcode: str = Field(..., min_length=1, max_length=100, description="Barcode to scan")
    user_id: int = Field(..., ge=1, description="User ID")
    include_recommendations: bool = Field(True, description="Include scan recommendations")
    include_validation_details: bool = Field(True, description="Include detailed validation info")


class EnhancedScanResponse(BaseModel):
    """Response model for enhanced barcode scanning"""

    success: bool
    scan_timestamp: str
    is_valid: bool
    barcode_type: str
    validation_result: str
    normalized_barcode: str
    product_found: bool
    exact_matches_count: int
    confidence_score: float
    error_message: Optional[str] = None
    recommendations: List[str] = []
    validation_details: Optional[Dict[str, Any]] = None
    matches: List[Dict[str, Any]] = []


class ValidationTestRequest(BaseModel):
    """Request model for barcode validation testing"""

    barcode: str = Field(..., description="Barcode to validate")
    expected_type: Optional[str] = Field(None, description="Expected barcode type")


class ValidationTestResponse(BaseModel):
    """Response model for barcode validation testing"""

    success: bool
    is_valid: bool
    barcode_type: str
    validation_result: str
    normalized_barcode: str
    check_digit: Optional[str] = None
    confidence_score: float
    error_message: Optional[str] = None
    recommendations: List[str] = []


@enhanced_barcode_router.post("/exact-scan", response_model=EnhancedScanResponse)
async def exact_barcode_scan(
    request: EnhancedScanRequest, db: Session = Depends(get_db_session)
) -> EnhancedScanResponse:
    """
    A-5 Exact/Valid Scan: Perform exact barcode scanning with comprehensive validation

    This endpoint provides:
    - Exact barcode format validation
    - Check digit verification for numeric barcodes
    - Exact product matching in database
    - Comprehensive error handling
    - Detailed recommendations
    """
    try:
        # Check dev override for premium features
        if not dev_entitled(request.user_id, "enhanced.scan"):
            # Fall back to basic validation for non-premium users
            return await _basic_scan_fallback(request)

        # Perform enhanced exact scan
        scan_result = await enhanced_barcode_service.scan_barcode_exact(request.barcode, request.user_id)

        # Build response
        response_data = {
            "success": True,
            "scan_timestamp": scan_result.scan_timestamp.isoformat(),
            "is_valid": scan_result.is_valid,
            "barcode_type": scan_result.barcode_validation.barcode_type.value,
            "validation_result": scan_result.barcode_validation.validation_result.value
            if scan_result.barcode_validation.validation_result
            else "unknown",
            "normalized_barcode": scan_result.barcode_validation.normalized_barcode,
            "product_found": scan_result.product_found,
            "exact_matches_count": len(scan_result.exact_matches),
            "confidence_score": scan_result.confidence_score,
            "error_message": scan_result.error_message,
            "recommendations": scan_result.recommendations or [],
            "matches": scan_result.exact_matches[:10] if request.include_recommendations else [],  # Limit matches
        }

        # Add validation details if requested
        if request.include_validation_details:
            response_data["validation_details"] = enhanced_barcode_service.validator.get_validation_summary(
                scan_result.barcode_validation
            )

        logger.info(
            f"Enhanced scan completed for user {request.user_id}: "
            f"barcode={scan_result.barcode_validation.normalized_barcode}, "
            f"valid={scan_result.is_valid}, "
            f"matches={len(scan_result.exact_matches)}"
        )

        return EnhancedScanResponse(**response_data)

    except Exception as e:
        logger.error(f"Enhanced scan failed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced scan failed: {str(e)}")


@enhanced_barcode_router.post("/validate", response_model=ValidationTestResponse)
async def validate_barcode_format(
    request: ValidationTestRequest,
) -> ValidationTestResponse:
    """
    A-5 Exact/Valid Scan: Validate barcode format and type

    This endpoint provides:
    - Format validation
    - Type detection
    - Check digit verification
    - Detailed error messages
    """
    try:
        # Perform validation
        validation_result = enhanced_barcode_service.validator.validate_barcode(request.barcode)

        # Build response
        response_data = {
            "success": True,
            "is_valid": validation_result.is_valid,
            "barcode_type": validation_result.barcode_type.value,
            "validation_result": validation_result.validation_result.value
            if validation_result.validation_result
            else "unknown",
            "normalized_barcode": validation_result.normalized_barcode,
            "check_digit": validation_result.check_digit,
            "confidence_score": validation_result.confidence_score,
            "error_message": validation_result.error_message,
            "recommendations": enhanced_barcode_service.validator._get_recommendations(validation_result),
        }

        # Validate against expected type if provided
        if request.expected_type:
            expected_type = BarcodeType(request.expected_type)
            if validation_result.barcode_type != expected_type:
                response_data["error_message"] = (
                    f"Expected {expected_type.value}, got {validation_result.barcode_type.value}"
                )
                response_data["is_valid"] = False

        logger.info(
            f"Barcode validation completed: "
            f"barcode={validation_result.normalized_barcode}, "
            f"type={validation_result.barcode_type.value}, "
            f"valid={validation_result.is_valid}"
        )

        return ValidationTestResponse(**response_data)

    except Exception as e:
        logger.error(f"Barcode validation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@enhanced_barcode_router.get("/test-validation")
async def test_barcode_validation(
    barcode: str = Query(..., description="Barcode to test"),
    expected_type: Optional[str] = Query(None, description="Expected barcode type"),
) -> Dict[str, Any]:
    """
    A-5 Exact/Valid Scan: Test endpoint for barcode validation

    Quick test endpoint for validating barcode formats
    """
    try:
        validation_result = enhanced_barcode_service.validator.validate_barcode(barcode)

        return {
            "success": True,
            "barcode": barcode,
            "normalized": validation_result.normalized_barcode,
            "type": validation_result.barcode_type.value,
            "valid": validation_result.is_valid,
            "confidence": validation_result.confidence_score,
            "check_digit": validation_result.check_digit,
            "error": validation_result.error_message,
            "recommendations": enhanced_barcode_service.validator._get_recommendations(validation_result),
        }

    except Exception as e:
        return {"success": False, "barcode": barcode, "error": str(e)}


async def _basic_scan_fallback(request: EnhancedScanRequest) -> EnhancedScanResponse:
    """Fallback for non-premium users - basic validation only"""
    try:
        # Basic validation only
        validation_result = enhanced_barcode_service.validator.validate_barcode(request.barcode)

        return EnhancedScanResponse(
            success=True,
            scan_timestamp=datetime.utcnow().isoformat(),
            is_valid=validation_result.is_valid,
            barcode_type=validation_result.barcode_type.value,
            validation_result=validation_result.validation_result.value
            if validation_result.validation_result
            else "unknown",
            normalized_barcode=validation_result.normalized_barcode,
            product_found=False,  # No product search for basic users
            exact_matches_count=0,
            confidence_score=validation_result.confidence_score,
            error_message=validation_result.error_message,
            recommendations=["Upgrade to premium for product matching and detailed recommendations"],
            validation_details=enhanced_barcode_service.validator.get_validation_summary(validation_result)
            if request.include_validation_details
            else None,
            matches=[],
        )

    except Exception as e:
        return EnhancedScanResponse(
            success=False,
            scan_timestamp=datetime.utcnow().isoformat(),
            is_valid=False,
            barcode_type="unknown",
            validation_result="error",
            normalized_barcode=request.barcode,
            product_found=False,
            exact_matches_count=0,
            confidence_score=0.0,
            error_message=f"Basic validation failed: {str(e)}",
            recommendations=["Try scanning again or contact support"],
        )


@enhanced_barcode_router.get("/health")
async def enhanced_scan_health() -> Dict[str, Any]:
    """Health check for enhanced barcode scanning service"""
    return {
        "service": "enhanced-barcode-scanning",
        "status": "healthy",
        "version": "1.0.0",
        "features": [
            "exact_validation",
            "check_digit_verification",
            "product_matching",
            "error_handling",
            "recommendations",
        ],
        "supported_types": [btype.value for btype in BarcodeType],
        "timestamp": datetime.utcnow().isoformat(),
    }
