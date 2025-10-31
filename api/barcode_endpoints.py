"""Next-Generation Traceability API Endpoints
Barcode, QR Code, and DataMatrix scanning with precise recall matching.
"""

import base64
import logging
from datetime import date, datetime, UTC
from typing import Any

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.models.scan_results import ScanResultsPage, create_scan_results
from api.v1_endpoints import SafetyIssue
from core_infra.barcode_scanner import ScanResult, scanner

# RecallDB removed - Crown Safe uses HairProductModel
from core_infra.database import get_db as get_db_session
from core_infra.manufacturer_verifier import (
    VerificationInput,
    get_default_verifier,
)
from db.models.serial_verification import SerialVerification


# Define ApiResponse locally
class ApiResponse(BaseModel):
    """API response wrapper."""

    success: bool
    data: Any | None = None
    error: str | None = None
    message: str | None = None


logger = logging.getLogger(__name__)

# Create router
barcode_router = APIRouter(prefix="/api/v1/scan", tags=["barcode-scanning"])

# Additional router for mobile-specific endpoints
mobile_scan_router = APIRouter(prefix="/api/v1/mobile/scan", tags=["mobile-scanning"])

# Router matching documentation path /api/v1/barcode/scan
barcode_scan_router = APIRouter(prefix="/api/v1/barcode", tags=["barcode-scanning"])


# Request/Response Models
class BarcodeScanRequest(BaseModel):
    """Request model for text-based barcode scanning."""

    barcode_data: str = Field(..., description="Raw barcode data string")
    barcode_type: str | None = Field(None, description="Optional barcode type hint")


class ImageScanRequest(BaseModel):
    """Request model for image-based scanning."""

    image_base64: str = Field(..., description="Base64 encoded image data")
    scan_mode: str | None = Field("auto", description="Scan mode: auto, qr, datamatrix, barcode")


class QRGenerateRequest(BaseModel):
    """Request model for QR code generation."""

    gtin: str | None = Field(None, description="Product GTIN/UPC")
    lot_number: str | None = Field(None, description="Lot/Batch number")
    serial_number: str | None = Field(None, description="Serial number")
    expiry_date: str | None = Field(None, description="Expiry date (YYYY-MM-DD)")
    custom_data: dict[str, Any] | None = Field(None, description="Additional custom data")


class RecallCheckResult(BaseModel):
    """Result of recall check against database."""

    recall_found: bool
    recall_count: int = 0
    severity: str | None = None
    recalls: list[SafetyIssue] = []
    match_type: str = Field(
        ...,
        description="Type of match: exact_unit, lot_match, product_match, no_match",
    )
    confidence: float = Field(..., description="Confidence score 0-1")


class ScanResponse(BaseModel):
    """Response model for barcode scanning."""

    ok: bool
    scan_results: list[dict[str, Any]]
    recall_check: RecallCheckResult | None = None
    trace_id: str
    message: str | None = None
    verification: dict[str, Any] | None = None


# Helper Functions
def check_recall_database(scan_result: ScanResult, db: Session) -> RecallCheckResult:
    """Check scanned product against recall database
    REMOVED FOR CROWN SAFE: Recall checking no longer applicable (hair products, not baby recalls).

    Args:
        scan_result: Barcode scan result
        db: Database session

    Returns:
        Recall check result with matching recalls

    """
    # Return empty recall check for backward compatibility
    recall_check = RecallCheckResult(
        recall_found=False,
        recall_count=0,
        match_type="no_match",
        confidence=0.0,
        recalls=[],
    )

    if not scan_result.success:
        return recall_check

    # Original recall checking removed (~150 lines):
    # 1. Exact unit match (serial_number + gtin) -> RecallDB query
    # 2. Lot/Batch match (lot_number + gtin) -> RecallDB query
    # 3. Expiry date match (expiry_date + gtin) -> RecallDB query
    # 4. Product-level match (gtin only) -> RecallDB query
    # All RecallDB queries removed - Crown Safe uses hair products

    return recall_check


def _attempt_unit_verification(scan_result: ScanResult) -> dict[str, Any] | None:
    """Call manufacturer verifier if we have identifiers."""
    if not scan_result or not (scan_result.gtin or scan_result.lot_number or scan_result.serial_number):
        return None
    verifier = get_default_verifier()
    vin = VerificationInput(
        gtin=scan_result.gtin,
        lot_number=scan_result.lot_number,
        serial_number=scan_result.serial_number,
        expiry_date=scan_result.expiry_date,
    )
    try:
        result = verifier.verify(vin)
        return {
            "verified": result.verified,
            "status": result.status,
            "manufacturer": result.manufacturer,
            "source": result.source,
            "message": result.message,
            "checked_at": result.checked_at.isoformat(),
            "payload": result.payload,
        }
    except Exception as e:
        logger.exception(f"Verification error: {e}")
        return {"verified": False, "status": "error", "message": str(e)}


def _persist_verification(
    scan_result: ScanResult,
    verification: dict[str, Any] | None,
    db: Session,
    trace_id: str | None = None,
) -> int | None:
    """Persist verification outcome to serial_verifications table."""
    if not verification:
        return None
    try:
        rec = SerialVerification(
            gtin=scan_result.gtin,
            lot_number=scan_result.lot_number,
            serial_number=scan_result.serial_number,
            expiry_date=scan_result.expiry_date,
            manufacturer=verification.get("manufacturer"),
            status=verification.get("status", "unknown"),
            source=verification.get("source"),
            message=verification.get("message"),
            trace_id=trace_id,
            verification_payload=verification.get("payload"),
            checked_at=datetime.now(UTC),
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id
    except Exception as e:
        logger.exception(f"Failed to persist serial verification: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return None


# REMOVED FOR CROWN SAFE: Helper functions for RecallDB no longer needed
# def _convert_recall_to_safety_issue(recall: RecallDB) -> SafetyIssue:
# def _determine_severity(recall: RecallDB) -> str:
# def _get_highest_severity(recalls: List[RecallDB]) -> str:
# These functions converted RecallDB objects to SafetyIssue models
# Crown Safe uses hair products (HairProductModel), not baby product recalls


# API Endpoints
@barcode_router.post("/barcode", response_model=ApiResponse)
async def scan_barcode_text(request: BarcodeScanRequest, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Scan and parse text barcode data.

    Supports standard barcodes, QR codes, and GS1 formatted data.
    Automatically extracts GTIN, lot numbers, serial numbers, and dates.
    """
    try:
        # Generate trace ID
        trace_id = f"scan_{int(datetime.now(UTC).timestamp())}_{hash(request.barcode_data) % 10000}"

        # Parse barcode
        scan_result = scanner.scan_text(request.barcode_data, request.barcode_type)

        # Check against recall database
        recall_check = check_recall_database(scan_result, db)
        verification = _attempt_unit_verification(scan_result)
        _persist_verification(scan_result, verification, db, trace_id)

        # Build response
        response_data = ScanResponse(
            ok=True,
            scan_results=[scan_result.to_dict()],
            recall_check=recall_check,
            trace_id=trace_id,
            verification=verification,
        )

        # Add warning message if recall found
        if recall_check.recall_found:
            response_data.message = f"⚠️ RECALL ALERT: {recall_check.recall_count} recall(s) found for this product!"

        return ApiResponse(success=True, data=response_data.model_dump(), message=None)

    except Exception as e:
        logger.exception(f"Barcode scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@barcode_router.post("/image", response_model=ApiResponse)
async def scan_image(
    file: UploadFile = File(..., description="Image file to scan"),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    """Scan an image for barcodes, QR codes, and DataMatrix codes.

    Supports multiple barcode detection in a single image.
    Automatically preprocesses images for better detection.
    """
    try:
        # Generate trace ID
        trace_id = f"scan_img_{int(datetime.now(UTC).timestamp())}_{hash(file.filename) % 10000}"

        # Read image data
        image_data = await file.read()

        # Scan image
        scan_results = await scanner.scan_image(image_data)

        # Check each result against database
        recall_checks = []
        any_recalls = False
        verifications: list[dict[str, Any] | None] = []

        for scan_result in scan_results:
            if scan_result.success:
                recall_check = check_recall_database(scan_result, db)
                recall_checks.append(recall_check)
                if recall_check.recall_found:
                    any_recalls = True
                v = _attempt_unit_verification(scan_result)
                verifications.append(v)
                _persist_verification(scan_result, v, db, trace_id)

        # Build response
        response_data = {
            "ok": True,
            "scan_results": [r.to_dict() for r in scan_results],
            "recall_checks": [r.model_dump() for r in recall_checks] if recall_checks else None,
            "trace_id": trace_id,
            "verifications": verifications if verifications else None,
        }

        # Add warning if any recalls found
        if any_recalls:
            total_recalls = sum(r.recall_count for r in recall_checks if r.recall_found)
            response_data["message"] = f"⚠️ RECALL ALERT: {total_recalls} recall(s) found in scanned items!"

        return ApiResponse(success=True, data=response_data, message=None)

    except Exception as e:
        logger.exception(f"Image scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@barcode_router.post("/qr", response_model=ApiResponse)
async def scan_qr_code(request: BarcodeScanRequest, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Specialized QR code scanning with enhanced parsing.

    Supports JSON payloads, URLs, and GS1 Digital Links.
    Extracts structured data for precise recall matching.
    """
    try:
        # Generate trace ID
        timestamp = int(datetime.now(UTC).timestamp())
        hash_val = hash(request.barcode_data) % 10000
        trace_id = f"scan_qr_{timestamp}_{hash_val}"

        # Parse as QR code
        scan_result = scanner.scan_text(request.barcode_data, "QRCODE")

        # Check against recall database
        recall_check = check_recall_database(scan_result, db)
        verification = _attempt_unit_verification(scan_result)
        _persist_verification(scan_result, verification, db, trace_id)

        # Build response
        response_data = ScanResponse(
            ok=True,
            scan_results=[scan_result.to_dict()],
            recall_check=recall_check,
            trace_id=trace_id,
            verification=verification,
        )

        if recall_check.recall_found:
            response_data.message = f"⚠️ RECALL ALERT: {recall_check.recall_count} recall(s) found!"

        return ApiResponse(success=True, data=response_data.model_dump(), message=None)

    except Exception as e:
        logger.exception(f"QR scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@barcode_router.post("/datamatrix", response_model=ApiResponse)
async def scan_datamatrix(request: ImageScanRequest, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Scan DataMatrix 2D barcodes.

    Common in pharmaceuticals and medical devices.
    Supports GS1 DataMatrix with full AI parsing.
    """
    try:
        # Generate trace ID
        trace_id = f"scan_dm_{int(datetime.now(UTC).timestamp())}"

        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)

        # Scan for DataMatrix
        scan_results = await scanner.scan_image(image_data)

        # Filter for DataMatrix results
        dm_results = [r for r in scan_results if r.barcode_type == "DATA_MATRIX"]

        if not dm_results:
            return ApiResponse(
                success=False,
                data={"message": "No DataMatrix codes found in image"},
                message=None,
            )

        # Check against database
        recall_check = check_recall_database(dm_results[0], db)

        # Build response
        response_data = ScanResponse(
            ok=True,
            scan_results=[r.to_dict() for r in dm_results],
            recall_check=recall_check,
            trace_id=trace_id,
        )

        if recall_check.recall_found:
            response_data.message = f"⚠️ RECALL ALERT: {recall_check.recall_count} recall(s) found!"

        return ApiResponse(success=True, data=response_data.model_dump(), message=None)

    except Exception as e:
        logger.exception(f"DataMatrix scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@barcode_router.post("/gs1", response_model=ApiResponse)
async def parse_gs1_data(
    gs1_data: str = Body(..., description="GS1 formatted string with AIs"),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    """Parse GS1-128 or GS1 DataMatrix formatted data.

    Extracts all Application Identifiers (AIs) including:
    - GTIN (01)
    - Batch/Lot (10)
    - Serial Number (21)
    - Expiry Date (17)
    - Production Date (11)
    """
    try:
        # Generate trace ID
        trace_id = f"scan_gs1_{int(datetime.now(UTC).timestamp())}"

        # Parse GS1 data
        scan_result = scanner.scan_text(gs1_data, "GS1_128")

        if not scan_result.success:
            return ApiResponse(success=False, data={"message": "Invalid GS1 format"}, message=None)

        # Check against recall database
        recall_check = check_recall_database(scan_result, db)
        verification = _attempt_unit_verification(scan_result)
        _persist_verification(scan_result, verification, db, trace_id)

        return ApiResponse(
            success=True,
            data={
                "scan_result": scan_result.to_dict(),
                "recall_check": recall_check,
                "verification": verification,
            },
            message="GS1 data parsed successfully",
        )

    except Exception as e:
        logger.exception(f"GS1 parsing error: {e}")
        return ApiResponse(success=False, data={"error": str(e)}, message="Failed to parse GS1 data")


class VerifyRequest(BaseModel):
    """Manual verification request for unit-level identifiers."""

    gtin: str | None = Field(None)
    lot_number: str | None = Field(None)
    serial_number: str | None = Field(None)
    expiry_date: str | None = Field(None, description="YYYY-MM-DD")
    manufacturer: str | None = Field(None, description="Optional hint")


@barcode_router.post("/verify", response_model=ApiResponse)
async def verify_unit(request: VerifyRequest, db: Session = Depends(get_db_session)) -> ApiResponse:
    """Verify a unit (GTIN/lot/serial/expiry) with a pluggable manufacturer connector.
    Always persists a verification record for audit.
    """
    try:
        trace_id = f"verify_{int(datetime.now(UTC).timestamp())}"

        exp = None
        if request.expiry_date:
            try:
                # Accept YYYY-MM-DD
                exp = date.fromisoformat(request.expiry_date)
            except Exception:
                pass

        # Build ScanResult-like stub
        sr = ScanResult(
            success=True,
            barcode_type="GS1_128",
            raw_data=None,
            gtin=(request.gtin or None),
            lot_number=(request.lot_number or None),
            serial_number=(request.serial_number or None),
            expiry_date=exp,
            production_date=None,
            batch_code=None,
            parsed_data={},
            confidence=1.0,
            error_message=None,
        )

        verification = _attempt_unit_verification(sr)
        rec_id = _persist_verification(sr, verification, db, trace_id)

        data = {
            "verification": verification,
            "record_id": rec_id,
            "trace_id": trace_id,
        }
        return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.exception(f"Unit verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@barcode_router.post("/generate-qr")
async def generate_qr_code(request: QRGenerateRequest) -> Response:
    """Generate a QR code with product information.

    Creates a QR code containing structured product data
    that can be scanned for recall checking.
    """
    try:
        # Build data dictionary
        qr_data = {}

        if request.gtin:
            qr_data["gtin"] = request.gtin
        if request.lot_number:
            qr_data["lot"] = request.lot_number
        if request.serial_number:
            qr_data["serial"] = request.serial_number
        if request.expiry_date:
            qr_data["expiry"] = request.expiry_date

        # Add custom data
        if request.custom_data:
            qr_data.update(request.custom_data)

        # Add metadata
        qr_data["generated_by"] = "BabyShield"
        qr_data["timestamp"] = datetime.now(UTC).isoformat()

        # Generate QR code
        qr_image = scanner.generate_qr_code(qr_data)

        filename = f"qr_{request.gtin or 'product'}.png"
        return Response(
            content=qr_image,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.exception(f"QR generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Mobile-Specific Scan Results Endpoints =============


@mobile_scan_router.post("/results", response_model=ScanResultsPage)
async def get_scan_results_page(request: BarcodeScanRequest, db: Session = Depends(get_db_session)) -> ScanResultsPage:
    """Get formatted scan results for mobile display.

    Returns a properly structured results page with:
    - Legally defensible verdict language
    - Transparent barcode detection data
    - Accurate agency reporting (39+)
    - Clear product summary
    - Action buttons for PDF download and details view
    """
    try:
        # Parse barcode
        scan_result = scanner.scan_text(request.barcode_data, request.barcode_type)

        # Check against recall database
        recall_check = check_recall_database(scan_result, db)

        # Prepare scan data
        scan_data = {
            "product_name": scan_result.product_name or "Product Analyzed",
            "brand": scan_result.brand or "Unknown Brand",
            "barcode": scan_result.gtin or request.barcode_data,
            "model_number": scan_result.model_number,
            "upc_gtin": scan_result.gtin,
            "scan_type": "barcode",
        }

        # Prepare barcode detection info
        barcode_info = {
            "barcode": scan_result.gtin or request.barcode_data,
            "format": request.barcode_type or "ean13",
            "confidence": 99.0 if scan_result.success else 50.0,
        }

        # Prepare recall check data
        recall_data = None
        if recall_check:
            recall_data = {
                "recall_found": recall_check.recall_found,
                "recall_count": recall_check.recall_count,
                "recalls": [
                    {
                        "recall_id": r.id,
                        "agency": r.source_agency or "CPSC",
                        "date": r.recall_date.strftime("%Y-%m-%d") if r.recall_date else "",
                        "hazard": r.hazard or "",
                        "remedy": r.remedy or "",
                        "severity": _get_highest_severity([r]),
                        "match_confidence": 0.95,
                    }
                    for r in recall_check.recalls
                ]
                if recall_check.recalls
                else [],
            }

        # Create the results page
        results = create_scan_results(scan_data, recall_data, barcode_info)

        # Track the scan in history (async)
        try:
            from db.models.scan_history import ScanHistory

            scan_history = ScanHistory(
                user_id=request.user_id if hasattr(request, "user_id") else None,
                scan_id=results.scan_id,
                product_name=scan_data.get("product_name"),
                brand=scan_data.get("brand"),
                barcode=scan_data.get("barcode"),
                model_number=scan_data.get("model_number"),
                upc_gtin=scan_data.get("upc_gtin"),
                scan_type=scan_data.get("scan_type"),
                confidence_score=barcode_info.get("confidence"),
                barcode_format=barcode_info.get("format"),
                verdict=results.verdict.value,
                risk_level=recall_data.get("severity", "low") if recall_data else "low",
                recalls_found=len(recall_data.get("recalls", [])) if recall_data else 0,
                recall_ids=([r.get("recall_id") for r in recall_data.get("recalls", [])] if recall_data else None),
                agencies_checked=results.safety_check.agencies_checked,
            )
            db.add(scan_history)
            db.commit()
        except Exception as track_error:
            logger.warning(f"Failed to track scan history: {track_error}")
            # Don't fail the request if tracking fails

        return results

    except Exception as e:
        logger.exception(f"Error creating scan results page: {e}")
        # Return a safe error response
        return create_scan_results(
            {
                "product_name": "Unable to Process",
                "brand": "Error",
                "barcode": request.barcode_data,
                "scan_type": "barcode",
            },
            None,
            {"barcode": request.barcode_data, "format": "unknown", "confidence": 0.0},
        )


@barcode_scan_router.post("/scan", response_model=ApiResponse)
async def barcode_scan_with_file(
    file: UploadFile = File(..., description="Image file to scan for barcodes"),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    """Scan barcode from uploaded image file with security validation.

    This endpoint validates:
    - File type (must be image: jpg, jpeg, png, gif, bmp, webp)
    - File size (max 10MB)

    Args:
        file: Uploaded image file
        db: Database session

    Returns:
        Scan results with recall checking

    Raises:
        400: Invalid file type
        413: File too large
        422: Validation error

    """
    try:
        # Validate file type
        allowed_types = [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/bmp",
            "image/webp",
        ]
        if file.content_type not in allowed_types:
            allowed_str = ", ".join(allowed_types)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: {allowed_str}",
            )

        # Read file content
        content = await file.read()

        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=(f"File too large: {len(content)} bytes. Maximum allowed: {max_size} bytes (10MB)"),
            )

        # Convert to base64 for scanner
        image_base64 = base64.b64encode(content).decode("utf-8")

        # Generate trace ID
        trace_id = f"file_scan_{int(datetime.now(UTC).timestamp())}_{hash(file.filename) % 10000}"

        # Scan image
        scan_results = await scanner.scan_image(image_base64)

        # Check each result against database
        recall_checks = []
        any_recalls = False
        verifications: list[dict[str, Any] | None] = []

        for scan_result in scan_results:
            if scan_result.success:
                recall_check = check_recall_database(scan_result, db)
                recall_checks.append(recall_check)
                if recall_check.recall_found:
                    any_recalls = True
                v = _attempt_unit_verification(scan_result)
                verifications.append(v)
                _persist_verification(scan_result, v, db, trace_id)

        # Build response
        response_data = {
            "ok": True,
            "scan_results": [r.to_dict() for r in scan_results],
            "recall_checks": [r.model_dump() for r in recall_checks] if recall_checks else None,
            "trace_id": trace_id,
            "verifications": verifications if verifications else None,
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size_bytes": len(content),
            },
        }

        # Add warning if any recalls found
        if any_recalls:
            total_recalls = sum(r.recall_count for r in recall_checks if r.recall_found)
            response_data["message"] = f"⚠️ RECALL ALERT: {total_recalls} recall(s) found!"

        return ApiResponse(success=True, data=response_data, message="File scanned successfully")

    except HTTPException:
        # Re-raise HTTP exceptions (400, 413, etc.)
        raise
    except Exception as e:
        logger.exception(f"File scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {e!s}") from e
