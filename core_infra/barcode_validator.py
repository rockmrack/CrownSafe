"""A-5 Exact/Valid Scan: Comprehensive Barcode Validation Service
Provides exact validation, format checking, and error handling for barcode scanning
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BarcodeType(Enum):
    """Supported barcode types"""

    UPC_A = "upc_a"
    UPC_E = "upc_e"
    EAN_13 = "ean_13"
    EAN_8 = "ean_8"
    CODE_128 = "code_128"
    CODE_39 = "code_39"
    QR_CODE = "qr_code"
    DATA_MATRIX = "data_matrix"
    GS1_128 = "gs1_128"
    UNKNOWN = "unknown"


class ValidationResult(Enum):
    """Validation result types"""

    VALID = "valid"
    INVALID_FORMAT = "invalid_format"
    INVALID_CHECK_DIGIT = "invalid_check_digit"
    INVALID_LENGTH = "invalid_length"
    INVALID_CHARACTERS = "invalid_characters"
    UNKNOWN_TYPE = "unknown_type"


@dataclass
class BarcodeValidationResult:
    """Result of barcode validation"""

    is_valid: bool
    barcode_type: BarcodeType
    validation_result: ValidationResult
    normalized_barcode: str
    check_digit: str | None = None
    error_message: str | None = None
    confidence_score: float = 0.0


class BarcodeValidator:
    """Comprehensive barcode validation service"""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

        # Barcode type patterns
        self.patterns = {
            BarcodeType.UPC_A: r"^\d{12}$",
            BarcodeType.UPC_E: r"^\d{6,8}$",
            BarcodeType.EAN_13: r"^\d{13}$",
            BarcodeType.EAN_8: r"^\d{8}$",
            BarcodeType.CODE_128: r"^[\x00-\x7F]+$",  # ASCII printable
            BarcodeType.CODE_39: r"^[0-9A-Z\-\.\s\$\/\+\%]+$",
            BarcodeType.QR_CODE: r"^.{1,2953}$",  # QR codes can be up to 2953 chars
            BarcodeType.DATA_MATRIX: r"^[\x00-\xFF]+$",  # Any byte
            BarcodeType.GS1_128: r"^[\x00-\x7F]+$",  # ASCII with special chars
        }

        # Length requirements
        self.lengths = {
            BarcodeType.UPC_A: 12,
            BarcodeType.UPC_E: (6, 8),  # Can be 6, 7, or 8 digits
            BarcodeType.EAN_13: 13,
            BarcodeType.EAN_8: 8,
            BarcodeType.CODE_128: (1, 80),
            BarcodeType.CODE_39: (1, 43),
            BarcodeType.QR_CODE: (1, 2953),
            BarcodeType.DATA_MATRIX: (1, 2335),
            BarcodeType.GS1_128: (1, 48),
        }

    def validate_barcode(self, barcode: str) -> BarcodeValidationResult:
        """Comprehensive barcode validation

        Args:
            barcode: Raw barcode string to validate

        Returns:
            BarcodeValidationResult with validation details
        """
        if not barcode or not isinstance(barcode, str):
            return BarcodeValidationResult(
                is_valid=False,
                barcode_type=BarcodeType.UNKNOWN,
                validation_result=ValidationResult.INVALID_FORMAT,
                normalized_barcode="",
                error_message="Barcode is empty or not a string",
            )

        # Clean and normalize barcode
        cleaned_barcode = self._clean_barcode(barcode)

        if not cleaned_barcode:
            return BarcodeValidationResult(
                is_valid=False,
                barcode_type=BarcodeType.UNKNOWN,
                validation_result=ValidationResult.INVALID_FORMAT,
                normalized_barcode="",
                error_message="Barcode contains no valid characters",
            )

        # Detect barcode type
        barcode_type = self._detect_barcode_type(cleaned_barcode)

        if barcode_type == BarcodeType.UNKNOWN:
            return BarcodeValidationResult(
                is_valid=False,
                barcode_type=BarcodeType.UNKNOWN,
                validation_result=ValidationResult.UNKNOWN_TYPE,
                normalized_barcode=cleaned_barcode,
                error_message=f"Unknown barcode type for: {cleaned_barcode[:20]}...",
            )

        # Validate format
        format_valid = self._validate_format(cleaned_barcode, barcode_type)
        if not format_valid:
            return BarcodeValidationResult(
                is_valid=False,
                barcode_type=barcode_type,
                validation_result=ValidationResult.INVALID_FORMAT,
                normalized_barcode=cleaned_barcode,
                error_message=f"Invalid format for {barcode_type.value}",
            )

        # Validate length
        length_valid = self._validate_length(cleaned_barcode, barcode_type)
        if not length_valid:
            return BarcodeValidationResult(
                is_valid=False,
                barcode_type=barcode_type,
                validation_result=ValidationResult.INVALID_LENGTH,
                normalized_barcode=cleaned_barcode,
                error_message=f"Invalid length for {barcode_type.value}",
            )

        # Validate check digit for numeric barcodes
        check_digit_valid = True
        check_digit = None
        if barcode_type in [
            BarcodeType.UPC_A,
            BarcodeType.UPC_E,
            BarcodeType.EAN_13,
            BarcodeType.EAN_8,
        ]:
            check_digit_valid, check_digit = self._validate_check_digit(cleaned_barcode, barcode_type)
            if not check_digit_valid:
                return BarcodeValidationResult(
                    is_valid=False,
                    barcode_type=barcode_type,
                    validation_result=ValidationResult.INVALID_CHECK_DIGIT,
                    normalized_barcode=cleaned_barcode,
                    check_digit=check_digit,
                    error_message=f"Invalid check digit for {barcode_type.value}",
                )

        # Calculate confidence score
        confidence = self._calculate_confidence(cleaned_barcode, barcode_type, check_digit_valid)

        return BarcodeValidationResult(
            is_valid=True,
            barcode_type=barcode_type,
            validation_result=ValidationResult.VALID,
            normalized_barcode=cleaned_barcode,
            check_digit=check_digit,
            confidence_score=confidence,
        )

    def _clean_barcode(self, barcode: str) -> str:
        """Clean and normalize barcode string"""
        # Remove whitespace and common separators
        cleaned = re.sub(r"[\s\-\.]", "", barcode.strip())

        # Remove common prefixes/suffixes
        cleaned = re.sub(r"^(UPC|EAN|GTIN|GS1)[\s\-]*", "", cleaned, flags=re.IGNORECASE)

        return cleaned

    def _detect_barcode_type(self, barcode: str) -> BarcodeType:
        """Detect barcode type based on format and length"""
        # Check numeric barcodes FIRST (most common)
        if barcode.isdigit():
            length = len(barcode)
            if length == 12:
                return BarcodeType.UPC_A
            elif length == 13:
                return BarcodeType.EAN_13
            elif length == 8:
                return BarcodeType.EAN_8
            elif 6 <= length <= 8:
                return BarcodeType.UPC_E

        # Check for GS1-128 patterns
        if self._is_gs1_128(barcode):
            return BarcodeType.GS1_128

        # Check for Code 39 patterns
        if self._is_code_39(barcode):
            return BarcodeType.CODE_39

        # Check for Code 128 patterns
        if self._is_code_128(barcode):
            return BarcodeType.CODE_128

        # Check for DataMatrix patterns
        if self._is_data_matrix(barcode):
            return BarcodeType.DATA_MATRIX

        # Check for QR code patterns LAST (often contain URLs, JSON, etc.)
        if self._is_qr_code(barcode):
            return BarcodeType.QR_CODE

        return BarcodeType.UNKNOWN

    def _is_qr_code(self, barcode: str) -> bool:
        """Check if barcode looks like QR code content"""
        # QR codes often contain URLs, JSON, or structured data
        url_pattern = r"^https?://"
        json_pattern = r"^[\{\[].*[\}\]]$"
        base64_pattern = r"^[A-Za-z0-9+/]+=*$"

        return (
            bool(re.match(url_pattern, barcode))
            or bool(re.match(json_pattern, barcode))
            or bool(re.match(base64_pattern, barcode))
            or len(barcode) > 50
        )  # QR codes are typically longer

    def _is_data_matrix(self, barcode: str) -> bool:
        """Check if barcode looks like DataMatrix content"""
        # DataMatrix often contains binary-like data or specific patterns
        return len(barcode) > 20 and not barcode.isalnum() and any(ord(c) > 127 for c in barcode)

    def _is_gs1_128(self, barcode: str) -> bool:
        """Check if barcode follows GS1-128 format"""
        # GS1-128 often contains Application Identifiers in parentheses
        ai_pattern = r"\(\d{2,4}\)"
        return bool(re.search(ai_pattern, barcode))

    def _is_code_39(self, barcode: str) -> bool:
        """Check if barcode follows Code 39 format"""
        code39_chars = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%")
        return all(c in code39_chars for c in barcode.upper())

    def _is_code_128(self, barcode: str) -> bool:
        """Check if barcode follows Code 128 format"""
        # Code 128 supports ASCII printable characters
        return all(32 <= ord(c) <= 126 for c in barcode)

    def _validate_format(self, barcode: str, barcode_type: BarcodeType) -> bool:
        """Validate barcode format against type-specific patterns"""
        if barcode_type not in self.patterns:
            return False

        pattern = self.patterns[barcode_type]
        return bool(re.match(pattern, barcode))

    def _validate_length(self, barcode: str, barcode_type: BarcodeType) -> bool:
        """Validate barcode length"""
        if barcode_type not in self.lengths:
            return False

        length_req = self.lengths[barcode_type]
        actual_length = len(barcode)

        if isinstance(length_req, tuple):
            return length_req[0] <= actual_length <= length_req[1]
        else:
            return actual_length == length_req

    def _validate_check_digit(self, barcode: str, barcode_type: BarcodeType) -> tuple[bool, str | None]:
        """Validate check digit for numeric barcodes"""
        if barcode_type == BarcodeType.UPC_A:
            return self._validate_upc_a_check_digit(barcode)
        elif barcode_type == BarcodeType.EAN_13:
            return self._validate_ean_13_check_digit(barcode)
        elif barcode_type == BarcodeType.EAN_8:
            return self._validate_ean_8_check_digit(barcode)
        elif barcode_type == BarcodeType.UPC_E:
            return self._validate_upc_e_check_digit(barcode)

        return True, None

    def _validate_upc_a_check_digit(self, barcode: str) -> tuple[bool, str | None]:
        """Validate UPC-A check digit"""
        if len(barcode) != 12:
            return False, None

        # Calculate check digit
        odd_sum = sum(int(barcode[i]) for i in range(0, 11, 2))
        even_sum = sum(int(barcode[i]) for i in range(1, 11, 2))
        total = odd_sum * 3 + even_sum
        check_digit = (10 - (total % 10)) % 10

        return int(barcode[11]) == check_digit, str(check_digit)

    def _validate_ean_13_check_digit(self, barcode: str) -> tuple[bool, str | None]:
        """Validate EAN-13 check digit"""
        if len(barcode) != 13:
            return False, None

        # Calculate check digit
        odd_sum = sum(int(barcode[i]) for i in range(0, 12, 2))
        even_sum = sum(int(barcode[i]) for i in range(1, 12, 2))
        total = odd_sum + even_sum * 3
        check_digit = (10 - (total % 10)) % 10

        return int(barcode[12]) == check_digit, str(check_digit)

    def _validate_ean_8_check_digit(self, barcode: str) -> tuple[bool, str | None]:
        """Validate EAN-8 check digit"""
        if len(barcode) != 8:
            return False, None

        # Calculate check digit
        odd_sum = sum(int(barcode[i]) for i in range(0, 7, 2))
        even_sum = sum(int(barcode[i]) for i in range(1, 7, 2))
        total = odd_sum + even_sum * 3
        check_digit = (10 - (total % 10)) % 10

        return int(barcode[7]) == check_digit, str(check_digit)

    def _validate_upc_e_check_digit(self, barcode: str) -> tuple[bool, str | None]:
        """Validate UPC-E check digit"""
        # UPC-E is more complex - for now, just check if it's numeric
        return barcode.isdigit(), None

    def _calculate_confidence(self, barcode: str, barcode_type: BarcodeType, check_digit_valid: bool) -> float:
        """Calculate confidence score for validation"""
        confidence = 0.5  # Base confidence

        # Increase confidence for exact length matches
        if barcode_type in self.lengths:
            length_req = self.lengths[barcode_type]
            if isinstance(length_req, int) and len(barcode) == length_req:
                confidence += 0.2
            elif isinstance(length_req, tuple) and length_req[0] <= len(barcode) <= length_req[1]:
                confidence += 0.1

        # Increase confidence for valid check digits
        if check_digit_valid:
            confidence += 0.2

        # Increase confidence for common barcode types
        if barcode_type in [BarcodeType.UPC_A, BarcodeType.EAN_13]:
            confidence += 0.1

        return min(confidence, 1.0)

    def get_validation_summary(self, result: BarcodeValidationResult) -> dict[str, Any]:
        """Get human-readable validation summary"""
        return {
            "is_valid": result.is_valid,
            "barcode_type": result.barcode_type.value,
            "validation_result": result.validation_result.value,
            "normalized_barcode": result.normalized_barcode,
            "check_digit": result.check_digit,
            "confidence_score": result.confidence_score,
            "error_message": result.error_message,
            "recommendations": self._get_recommendations(result),
        }

    def _get_recommendations(self, result: BarcodeValidationResult) -> list[str]:
        """Get recommendations for invalid barcodes"""
        recommendations = []

        if result.validation_result == ValidationResult.INVALID_FORMAT:
            recommendations.append("Check barcode format and ensure it matches the expected type")

        if result.validation_result == ValidationResult.INVALID_LENGTH:
            recommendations.append("Verify barcode length matches the expected number of characters")

        if result.validation_result == ValidationResult.INVALID_CHECK_DIGIT:
            recommendations.append("Recalculate and verify the check digit")

        if result.validation_result == ValidationResult.INVALID_CHARACTERS:
            recommendations.append("Remove invalid characters and ensure only valid symbols are used")

        if result.validation_result == ValidationResult.UNKNOWN_TYPE:
            recommendations.append("Try scanning again or manually enter the barcode")

        if not recommendations:
            recommendations.append("Barcode appears to be valid")

        return recommendations


# Global validator instance
barcode_validator = BarcodeValidator()
