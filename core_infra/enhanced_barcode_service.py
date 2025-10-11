"""
A-5 Exact/Valid Scan: Enhanced Barcode Scanning Service
Integrates comprehensive validation with exact product matching
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from core_infra.barcode_validator import (
    barcode_validator,
    BarcodeValidationResult,
    BarcodeType,
)
from core_infra.database import get_db_session

try:
    from core_infra.database import RecallDB
except ImportError:
    # Fallback for different database models
    from data_models.recall import RecallDB
from core_infra.barcode_scanner import scanner, ScanResult

logger = logging.getLogger(__name__)


@dataclass
class ExactScanResult:
    """Result of exact barcode scanning with validation"""

    is_valid: bool
    barcode_validation: BarcodeValidationResult
    product_found: bool
    exact_matches: List[Dict[str, Any]]
    confidence_score: float
    scan_timestamp: datetime
    error_message: Optional[str] = None
    recommendations: List[str] = None


class EnhancedBarcodeService:
    """Enhanced barcode scanning service with exact validation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validator = barcode_validator

    async def scan_barcode_exact(self, barcode: str, user_id: int) -> ExactScanResult:
        """
        Perform exact barcode scan with comprehensive validation

        Args:
            barcode: Raw barcode string to scan
            user_id: User ID for logging and tracking

        Returns:
            ExactScanResult with validation and product matching details
        """
        scan_timestamp = datetime.utcnow()

        try:
            # Step 1: Validate barcode format and type
            validation_result = self.validator.validate_barcode(barcode)

            if not validation_result.is_valid:
                return ExactScanResult(
                    is_valid=False,
                    barcode_validation=validation_result,
                    product_found=False,
                    exact_matches=[],
                    confidence_score=validation_result.confidence_score,
                    scan_timestamp=scan_timestamp,
                    error_message=validation_result.error_message,
                    recommendations=self.validator._get_recommendations(
                        validation_result
                    ),
                )

            # Step 2: Search for exact product matches
            exact_matches = await self._find_exact_product_matches(
                validation_result.normalized_barcode, validation_result.barcode_type
            )

            # Step 3: Calculate overall confidence
            confidence = self._calculate_overall_confidence(
                validation_result, exact_matches
            )

            # Step 4: Log scan attempt
            self.logger.info(
                f"Exact scan completed for user {user_id}: "
                f"barcode={validation_result.normalized_barcode}, "
                f"type={validation_result.barcode_type.value}, "
                f"matches={len(exact_matches)}, "
                f"confidence={confidence:.2f}"
            )

            return ExactScanResult(
                is_valid=True,
                barcode_validation=validation_result,
                product_found=len(exact_matches) > 0,
                exact_matches=exact_matches,
                confidence_score=confidence,
                scan_timestamp=scan_timestamp,
                recommendations=self._get_scan_recommendations(
                    validation_result, exact_matches
                ),
            )

        except Exception as e:
            self.logger.error(f"Exact scan failed for user {user_id}: {e}")
            return ExactScanResult(
                is_valid=False,
                barcode_validation=BarcodeValidationResult(
                    is_valid=False,
                    barcode_type=BarcodeType.UNKNOWN,
                    validation_result=None,
                    normalized_barcode=barcode,
                    error_message=f"Scan failed: {str(e)}",
                ),
                product_found=False,
                exact_matches=[],
                confidence_score=0.0,
                scan_timestamp=scan_timestamp,
                error_message=f"Scan failed: {str(e)}",
                recommendations=["Try scanning again or contact support"],
            )

    async def _find_exact_product_matches(
        self, normalized_barcode: str, barcode_type: BarcodeType
    ) -> List[Dict[str, Any]]:
        """Find exact product matches in database"""
        matches = []

        try:
            with get_db_session() as db:
                # Define search conditions based on barcode type
                search_conditions = self._build_search_conditions(
                    normalized_barcode, barcode_type
                )

                # Execute search
                products = db.query(RecallDB).filter(search_conditions).all()

                # Convert to dictionaries
                for product in products:
                    match = {
                        "product_id": product.id,
                        "product_name": product.product_name,
                        "brand_name": product.brand_name,
                        "model_number": product.model_number,
                        "barcode": product.barcode,
                        "upc": product.upc,
                        "ean_code": product.ean_code,
                        "gtin": product.gtin,
                        "recall_status": product.recall_status,
                        "recall_date": product.recall_date.isoformat()
                        if product.recall_date
                        else None,
                        "hazard_description": product.hazard_description,
                        "risk_level": product.risk_level,
                        "match_type": self._determine_match_type(
                            normalized_barcode, product, barcode_type
                        ),
                        "match_confidence": self._calculate_match_confidence(
                            normalized_barcode, product, barcode_type
                        ),
                    }
                    matches.append(match)

                # Sort by match confidence (highest first)
                matches.sort(key=lambda x: x["match_confidence"], reverse=True)

        except Exception as e:
            self.logger.error(f"Database search failed: {e}")

        return matches

    def _build_search_conditions(
        self, normalized_barcode: str, barcode_type: BarcodeType
    ):
        """Build database search conditions based on barcode type"""
        from sqlalchemy import and_, or_

        # Base conditions for different barcode fields
        conditions = []

        # Always search in barcode field
        conditions.append(RecallDB.barcode == normalized_barcode)

        # For numeric barcodes, also search in UPC/EAN/GTIN fields
        if barcode_type in [
            BarcodeType.UPC_A,
            BarcodeType.UPC_E,
            BarcodeType.EAN_13,
            BarcodeType.EAN_8,
        ]:
            conditions.extend(
                [
                    RecallDB.upc == normalized_barcode,
                    RecallDB.ean_code == normalized_barcode,
                    RecallDB.gtin == normalized_barcode,
                ]
            )

        # For GS1-128, search in structured data fields
        if barcode_type == BarcodeType.GS1_128:
            conditions.extend(
                [
                    RecallDB.gtin == normalized_barcode,
                    RecallDB.serial_number == normalized_barcode,
                ]
            )

        # Combine with OR logic
        return or_(*conditions)

    def _determine_match_type(
        self, normalized_barcode: str, product: RecallDB, barcode_type: BarcodeType
    ) -> str:
        """Determine the type of match found"""
        if product.barcode == normalized_barcode:
            return "exact_barcode"
        elif product.upc == normalized_barcode:
            return "exact_upc"
        elif product.ean_code == normalized_barcode:
            return "exact_ean"
        elif product.gtin == normalized_barcode:
            return "exact_gtin"
        elif product.serial_number == normalized_barcode:
            return "exact_serial"
        else:
            return "partial_match"

    def _calculate_match_confidence(
        self, normalized_barcode: str, product: RecallDB, barcode_type: BarcodeType
    ) -> float:
        """Calculate confidence score for a product match"""
        confidence = 0.0

        # Exact matches get highest confidence
        if product.barcode == normalized_barcode:
            confidence = 1.0
        elif (
            product.upc == normalized_barcode or product.ean_code == normalized_barcode
        ):
            confidence = 0.95
        elif product.gtin == normalized_barcode:
            confidence = 0.90
        elif product.serial_number == normalized_barcode:
            confidence = 0.85
        else:
            confidence = 0.50  # Partial match

        # Boost confidence for recent recalls (more relevant)
        if product.recall_date:
            days_old = (datetime.utcnow() - product.recall_date).days
            if days_old < 365:  # Within last year
                confidence += 0.05
            elif days_old < 30:  # Within last month
                confidence += 0.10

        return min(confidence, 1.0)

    def _calculate_overall_confidence(
        self, validation_result: BarcodeValidationResult, matches: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall confidence score"""
        base_confidence = validation_result.confidence_score

        if not matches:
            return base_confidence * 0.5  # Reduce confidence if no matches found

        # Boost confidence based on best match
        best_match_confidence = max(match["match_confidence"] for match in matches)
        return (base_confidence + best_match_confidence) / 2

    def _get_scan_recommendations(
        self, validation_result: BarcodeValidationResult, matches: List[Dict[str, Any]]
    ) -> List[str]:
        """Get recommendations based on scan results"""
        recommendations = []

        if not matches:
            recommendations.append(
                "No products found with this barcode - it may be a new product"
            )
            recommendations.append("Try searching by product name or brand instead")
        else:
            recommendations.append(f"Found {len(matches)} exact product match(es)")

            if matches[0]["recall_status"] == "active":
                recommendations.append(
                    "⚠️ This product has an active recall - check details"
                )
            else:
                recommendations.append("✅ No active recalls found for this product")

        # Add validation-specific recommendations
        if validation_result.barcode_type in [BarcodeType.UPC_A, BarcodeType.EAN_13]:
            recommendations.append("Barcode format is valid and properly formatted")

        return recommendations

    def get_scan_summary(self, result: ExactScanResult) -> Dict[str, Any]:
        """Get comprehensive scan summary"""
        return {
            "scan_timestamp": result.scan_timestamp.isoformat(),
            "is_valid": result.is_valid,
            "barcode_validation": self.validator.get_validation_summary(
                result.barcode_validation
            ),
            "product_found": result.product_found,
            "exact_matches_count": len(result.exact_matches),
            "confidence_score": result.confidence_score,
            "error_message": result.error_message,
            "recommendations": result.recommendations or [],
            "matches": result.exact_matches[:5]
            if result.exact_matches
            else [],  # Limit to top 5
        }


# Global service instance
enhanced_barcode_service = EnhancedBarcodeService()
