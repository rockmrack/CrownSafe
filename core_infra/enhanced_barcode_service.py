"""A-5 Exact/Valid Scan: Enhanced Barcode Scanning Service
Integrates comprehensive validation with exact product matching
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# REMOVED FOR CROWN SAFE: RecallDB barcode scanning no longer applicable
# try:
#     from core_infra.database import RecallDB
# except ImportError:
#     # Fallback for different database models
#     from data_models.recall import RecallDB
from core_infra.barcode_validator import (
    BarcodeType,
    BarcodeValidationResult,
    barcode_validator,
)

logger = logging.getLogger(__name__)


@dataclass
class ExactScanResult:
    """Result of exact barcode scanning with validation"""

    is_valid: bool
    barcode_validation: BarcodeValidationResult
    product_found: bool
    exact_matches: list[dict[str, Any]]
    confidence_score: float
    scan_timestamp: datetime
    error_message: str | None = None
    recommendations: list[str] = None


class EnhancedBarcodeService:
    """Enhanced barcode scanning service with exact validation"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.validator = barcode_validator

    async def scan_barcode_exact(self, barcode: str, user_id: int) -> ExactScanResult:
        """Perform exact barcode scan with comprehensive validation

        Args:
            barcode: Raw barcode string to scan
            user_id: User ID for logging and tracking

        Returns:
            ExactScanResult with validation and product matching details

        """
        scan_timestamp = datetime.now(timezone.utc)

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
                    recommendations=self.validator._get_recommendations(validation_result),
                )

            # Step 2: Search for exact product matches
            exact_matches = await self._find_exact_product_matches(
                validation_result.normalized_barcode, validation_result.barcode_type,
            )

            # Step 3: Calculate overall confidence
            confidence = self._calculate_overall_confidence(validation_result, exact_matches)

            # Step 4: Log scan attempt
            self.logger.info(
                f"Exact scan completed for user {user_id}: "
                f"barcode={validation_result.normalized_barcode}, "
                f"type={validation_result.barcode_type.value}, "
                f"matches={len(exact_matches)}, "
                f"confidence={confidence:.2f}",
            )

            return ExactScanResult(
                is_valid=True,
                barcode_validation=validation_result,
                product_found=len(exact_matches) > 0,
                exact_matches=exact_matches,
                confidence_score=confidence,
                scan_timestamp=scan_timestamp,
                recommendations=self._get_scan_recommendations(validation_result, exact_matches),
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
        self, normalized_barcode: str, barcode_type: BarcodeType,
    ) -> list[dict[str, Any]]:
        """Find exact product matches in database"""
        # REMOVED FOR CROWN SAFE: Recall database search no longer applicable
        # Crown Safe uses hair products (HairProductModel), not baby product recalls

        logger.info(f"⏭️  Database search skipped for barcode {normalized_barcode} (deprecated for Crown Safe)")

        # Return empty list for backward compatibility
        return []

        # Original recall database search removed (40+ lines):
        # try:
        #     with get_db_session() as db:
        #         search_conditions = self._build_search_conditions(normalized_barcode, barcode_type)
        #         products = db.query(RecallDB).filter(search_conditions).all()
        #         for product in products:
        #             matches.append({...})  # Product matching logic

    # REMOVED FOR CROWN SAFE: Helper functions for RecallDB search no longer needed
    # def _build_search_conditions(...)
    # def _determine_match_type(...)
    # def _calculate_match_confidence(...)
    # These functions built SQL conditions and analyzed RecallDB product matches
    # Crown Safe uses hair products (HairProductModel), not baby product recalls

    def _calculate_overall_confidence(
        self, validation_result: BarcodeValidationResult, matches: list[dict[str, Any]],
    ) -> float:
        """Calculate overall confidence score"""
        base_confidence = validation_result.confidence_score

        if not matches:
            return base_confidence * 0.5  # Reduce confidence if no matches found

        # Boost confidence based on best match
        best_match_confidence = max(match["match_confidence"] for match in matches)
        return (base_confidence + best_match_confidence) / 2

    def _get_scan_recommendations(
        self, validation_result: BarcodeValidationResult, matches: list[dict[str, Any]],
    ) -> list[str]:
        """Get recommendations based on scan results"""
        recommendations = []

        if not matches:
            recommendations.append("No products found with this barcode - it may be a new product")
            recommendations.append("Try searching by product name or brand instead")
        else:
            recommendations.append(f"Found {len(matches)} exact product match(es)")

            if matches[0]["recall_status"] == "active":
                recommendations.append("⚠️ This product has an active recall - check details")
            else:
                recommendations.append("✅ No active recalls found for this product")

        # Add validation-specific recommendations
        if validation_result.barcode_type in [BarcodeType.UPC_A, BarcodeType.EAN_13]:
            recommendations.append("Barcode format is valid and properly formatted")

        return recommendations

    def get_scan_summary(self, result: ExactScanResult) -> dict[str, Any]:
        """Get comprehensive scan summary"""
        return {
            "scan_timestamp": result.scan_timestamp.isoformat(),
            "is_valid": result.is_valid,
            "barcode_validation": self.validator.get_validation_summary(result.barcode_validation),
            "product_found": result.product_found,
            "exact_matches_count": len(result.exact_matches),
            "confidence_score": result.confidence_score,
            "error_message": result.error_message,
            "recommendations": result.recommendations or [],
            "matches": result.exact_matches[:5] if result.exact_matches else [],  # Limit to top 5
        }


# Global service instance
enhanced_barcode_service = EnhancedBarcodeService()
