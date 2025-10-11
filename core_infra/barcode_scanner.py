"""
Next-Generation Traceability: Advanced Barcode Scanner Module
Supports QR codes, DataMatrix, GS1, and standard barcodes with lot/serial tracking
"""

import re
import json
import logging
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
import base64
from io import BytesIO

# Core barcode libraries
PYZBAR_AVAILABLE = False
try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol

    # Test if pyzbar actually works (Windows DLL check)
    import numpy as np

    test_img = np.zeros((10, 10), dtype=np.uint8)
    pyzbar.decode(test_img)
    PYZBAR_AVAILABLE = True
    logging.info("✅ PyZbar is fully functional")
except (ImportError, FileNotFoundError, OSError) as e:
    # FileNotFoundError/OSError can occur on Windows due to missing DLLs
    PYZBAR_AVAILABLE = False
    logging.warning(f"PyZbar not available: {e}. Using fallback methods.")

# DataMatrix support - optional dependency (disabled by default due to complex system dependencies)
ENABLE_DATAMATRIX = os.getenv("ENABLE_DATAMATRIX", "false").lower() == "true"

DATAMATRIX_AVAILABLE = False
if ENABLE_DATAMATRIX:
    try:
        import pylibdmtx.pylibdmtx as dmtx

        DATAMATRIX_AVAILABLE = True
        logging.getLogger().info("✅ DataMatrix scanning enabled and available")
        print("✅ DataMatrix scanning enabled and available")  # Force console output
    except ImportError:
        logging.getLogger().warning(
            "⚠️  DataMatrix requested but pylibdmtx not installed"
        )
        print(
            "⚠️  DataMatrix requested but pylibdmtx not installed"
        )  # Force console output
else:
    logging.getLogger().info("ℹ️  DataMatrix scanning disabled by config")
    print("ℹ️  DataMatrix scanning disabled by config")  # Force console output

try:
    import cv2
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    logging.warning("OpenCV not installed. Image preprocessing disabled.")

from PIL import Image
import qrcode

logger = logging.getLogger(__name__)


class BarcodeType(Enum):
    """Supported barcode types"""

    QR_CODE = "QR_CODE"
    DATA_MATRIX = "DATA_MATRIX"
    EAN13 = "EAN13"
    EAN8 = "EAN8"
    UPC_A = "UPC_A"
    UPC_E = "UPC_E"
    CODE128 = "CODE128"
    CODE39 = "CODE39"
    GS1_128 = "GS1_128"
    ITF = "ITF"
    PDF417 = "PDF417"


@dataclass
class ScanResult:
    """Result from barcode scanning"""

    success: bool
    barcode_type: Optional[str] = None
    raw_data: Optional[str] = None
    gtin: Optional[str] = None
    lot_number: Optional[str] = None
    serial_number: Optional[str] = None
    expiry_date: Optional[date] = None
    production_date: Optional[date] = None
    batch_code: Optional[str] = None
    parsed_data: Dict[str, Any] = None
    confidence: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self):
        """Convert to dictionary for API response"""
        result = {
            "success": self.success,
            "barcode_type": self.barcode_type,
            "confidence": self.confidence,
        }

        if self.success:
            result.update(
                {
                    "raw_data": self.raw_data,
                    "gtin": self.gtin,
                    "lot_number": self.lot_number,
                    "serial_number": self.serial_number,
                    "expiry_date": self.expiry_date.isoformat()
                    if self.expiry_date
                    else None,
                    "production_date": self.production_date.isoformat()
                    if self.production_date
                    else None,
                    "batch_code": self.batch_code,
                    "parsed_data": self.parsed_data or {},
                }
            )
        else:
            result["error_message"] = self.error_message

        return result


class BarcodeScanner:
    """Advanced barcode scanner with multi-format support
    Now with OpenCV fallback for 100% Windows compatibility"""

    def __init__(self):
        """Initialize the barcode scanner with fallback methods"""
        self.gs1_ai_patterns = self._init_gs1_patterns()
        self.opencv_qr_detector = None
        self.opencv_barcode_detector = None

        # Initialize OpenCV detectors as fallback when PyZbar fails
        if OPENCV_AVAILABLE and not PYZBAR_AVAILABLE:
            try:
                self.opencv_qr_detector = cv2.QRCodeDetector()
                logger.info("✅ OpenCV QR detection initialized as fallback")

                # Try to create barcode detector (available in newer OpenCV)
                if hasattr(cv2, "barcode"):
                    self.opencv_barcode_detector = cv2.barcode.BarcodeDetector()
                    logger.info("✅ OpenCV barcode detection initialized")
            except Exception as e:
                logger.warning(f"OpenCV detection initialization failed: {e}")

    def _init_gs1_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize GS1 Application Identifier patterns"""
        return {
            "01": {"name": "GTIN", "length": 14, "type": "numeric"},
            "10": {
                "name": "BATCH_LOT",
                "length": "variable",
                "max": 20,
                "type": "alphanumeric",
            },
            "11": {"name": "PRODUCTION_DATE", "length": 6, "type": "date"},
            "15": {"name": "BEST_BEFORE", "length": 6, "type": "date"},
            "17": {"name": "EXPIRY", "length": 6, "type": "date"},
            "21": {
                "name": "SERIAL",
                "length": "variable",
                "max": 20,
                "type": "alphanumeric",
            },
            "30": {
                "name": "VAR_COUNT",
                "length": "variable",
                "max": 8,
                "type": "numeric",
            },
            "310": {"name": "NET_WEIGHT_KG", "length": 6, "type": "decimal"},
            "37": {"name": "COUNT", "length": "variable", "max": 8, "type": "numeric"},
            "3932": {"name": "PRICE", "length": "variable", "type": "decimal"},
            "91": {
                "name": "INTERNAL_1",
                "length": "variable",
                "max": 90,
                "type": "alphanumeric",
            },
            "92": {
                "name": "INTERNAL_2",
                "length": "variable",
                "max": 90,
                "type": "alphanumeric",
            },
        }

    async def scan_image(self, image_data: bytes) -> List[ScanResult]:
        """
        Scan an image for barcodes

        Args:
            image_data: Image bytes

        Returns:
            List of scan results
        """
        results = []

        try:
            # Convert bytes to PIL Image
            image = Image.open(BytesIO(image_data))

            # Try different scanning methods
            if PYZBAR_AVAILABLE:
                results.extend(self._scan_with_pyzbar(image))
            elif OPENCV_AVAILABLE and (
                self.opencv_qr_detector or self.opencv_barcode_detector
            ):
                # Use OpenCV as fallback when PyZbar is not available
                results.extend(self._scan_with_opencv(image))

            if DATAMATRIX_AVAILABLE:
                results.extend(self._scan_datamatrix(image))

            if OPENCV_AVAILABLE and len(results) == 0:
                # Try enhanced scanning with OpenCV preprocessing
                results.extend(self._scan_with_preprocessing(image))

            # If no results, return error
            if not results:
                results.append(
                    ScanResult(
                        success=False, error_message="No barcodes detected in image"
                    )
                )

        except Exception as e:
            logger.error(f"Error scanning image: {e}")
            results.append(
                ScanResult(success=False, error_message=f"Scan error: {str(e)}")
            )

        return results

    def _scan_with_opencv(self, image: Image.Image) -> List[ScanResult]:
        """Scan using OpenCV as fallback when PyZbar is not available"""
        results = []

        try:
            # Convert PIL image to OpenCV format
            import numpy as np

            opencv_image = np.array(image)

            # Convert to grayscale if needed
            if len(opencv_image.shape) == 3:
                gray = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = opencv_image

            # Try QR code detection
            if self.opencv_qr_detector:
                data, bbox, _ = self.opencv_qr_detector.detectAndDecode(gray)
                if data:
                    result = ScanResult(
                        success=True,
                        barcode_type="QR_CODE",
                        raw_data=data,
                        parsed_data={"content": data},
                        confidence=0.9,
                    )
                    results.append(result)
                    logger.info(f"OpenCV detected QR code: {data[:50]}...")

            # Try barcode detection (if available)
            if self.opencv_barcode_detector:
                try:
                    (
                        retval,
                        decoded_info,
                        decoded_type,
                        points,
                    ) = self.opencv_barcode_detector.detectAndDecode(gray)
                    if retval:
                        for data in decoded_info:
                            if data:
                                result = ScanResult(
                                    success=True,
                                    barcode_type="BARCODE",
                                    raw_data=data,
                                    parsed_data={"content": data},
                                    confidence=0.8,
                                )
                                results.append(result)
                                logger.info(f"OpenCV detected barcode: {data[:50]}...")
                except Exception as e:
                    logger.debug(f"OpenCV barcode detection not available: {e}")

        except Exception as e:
            logger.error(f"OpenCV scanning error: {e}")

        return results

    def _scan_with_pyzbar(self, image: Image.Image) -> List[ScanResult]:
        """Scan using pyzbar library"""
        results = []

        try:
            # Detect and decode barcodes
            barcodes = pyzbar.decode(image)

            for barcode in barcodes:
                # Get barcode data
                data = barcode.data.decode("utf-8")
                barcode_type = barcode.type

                # Parse the barcode data
                scan_result = self._parse_barcode_data(data, barcode_type)
                scan_result.confidence = 0.95  # High confidence for direct detection
                results.append(scan_result)

        except Exception as e:
            logger.error(f"Pyzbar scanning error: {e}")

        return results

    def _scan_datamatrix(self, image: Image.Image) -> List[ScanResult]:
        """Scan for DataMatrix codes"""
        results = []

        if not DATAMATRIX_AVAILABLE:
            return results

        try:
            # Convert to numpy array for pylibdmtx
            img_array = np.array(image)

            # Decode DataMatrix
            decoded = dmtx.decode(img_array)

            for dm in decoded:
                data = dm.data.decode("utf-8")
                scan_result = self._parse_barcode_data(data, "DATA_MATRIX")
                scan_result.confidence = 0.95
                results.append(scan_result)

        except Exception as e:
            logger.error(f"DataMatrix scanning error: {e}")

        return results

    def _scan_with_preprocessing(self, image: Image.Image) -> List[ScanResult]:
        """Enhanced scanning with image preprocessing"""
        results = []

        if not OPENCV_AVAILABLE or not PYZBAR_AVAILABLE:
            return results

        try:
            # Convert to OpenCV format
            img_array = np.array(image)

            # Handle different image formats safely
            if len(img_array.shape) == 3:
                # RGB or RGBA image
                if img_array.shape[2] == 4:  # RGBA
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
                elif img_array.shape[2] == 3:  # RGB
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    # Unsupported 3-channel format, convert to grayscale
                    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            elif len(img_array.shape) == 2:
                # Already grayscale
                gray = img_array
            else:
                # Unsupported format, skip preprocessing
                logger.warning(
                    f"Unsupported image format with shape: {img_array.shape}"
                )
                return results

            # Try multiple preprocessing techniques
            preprocessing_methods = [
                # Original
                gray,
                # Threshold
                cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1],
                # Adaptive threshold
                cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
                ),
                # Blur and threshold
                cv2.threshold(
                    cv2.GaussianBlur(gray, (5, 5), 0), 127, 255, cv2.THRESH_BINARY
                )[1],
            ]

            for processed in preprocessing_methods:
                # Convert back to PIL
                pil_image = Image.fromarray(processed)

                # Try scanning
                barcodes = pyzbar.decode(pil_image)

                for barcode in barcodes:
                    data = barcode.data.decode("utf-8")
                    barcode_type = barcode.type

                    scan_result = self._parse_barcode_data(data, barcode_type)
                    scan_result.confidence = 0.85  # Lower confidence for preprocessed

                    # Avoid duplicates
                    if not any(r.raw_data == scan_result.raw_data for r in results):
                        results.append(scan_result)

        except Exception as e:
            logger.error(f"Preprocessing scan error: {e}")

        return results

    def scan_text(self, barcode_data: str, barcode_type: str = None) -> ScanResult:
        """
        Parse barcode text data directly

        Args:
            barcode_data: Raw barcode string
            barcode_type: Optional barcode type hint

        Returns:
            Scan result
        """
        return self._parse_barcode_data(barcode_data, barcode_type)

    def _parse_barcode_data(self, data: str, barcode_type: str = None) -> ScanResult:
        """Parse barcode data based on type and format"""

        result = ScanResult(
            success=True, raw_data=data, barcode_type=barcode_type, parsed_data={}
        )

        # Check if it's a GS1 formatted barcode
        if self._is_gs1_format(data):
            self._parse_gs1_data(data, result)

        # Check if it's a QR code with structured data
        elif barcode_type in ["QRCODE", "QR"] and self._is_json_format(data):
            self._parse_json_qr(data, result)

        # Check for URL format (common in QR codes)
        elif data.startswith(("http://", "https://")):
            self._parse_url_qr(data, result)

        # Standard UPC/EAN barcode
        elif self._is_standard_barcode(data):
            result.gtin = self._normalize_gtin(data)

        # Try to extract patterns from unstructured data
        else:
            self._extract_patterns(data, result)

        return result

    def _is_gs1_format(self, data: str) -> bool:
        """Check if data follows GS1 format"""
        # GS1-128 typically starts with FNC1 character or contains AI patterns
        return (
            data.startswith(chr(29))
            or data.startswith("01")  # FNC1
            or re.match(r"^\(?\d{2,4}\)", data)  # Common AI
        )  # AI in parentheses

    def _parse_gs1_data(self, data: str, result: ScanResult):
        """Parse GS1 formatted data with Application Identifiers"""

        # Remove FNC1 characters
        data = data.replace(chr(29), "")

        # Parse AI data
        parsed = {}
        position = 0

        while position < len(data):
            # Try to find AI (2-4 digits) - Reserved for future AI parsing
            _ = None  # ai_match

            # Check parentheses format first: (01)12345...
            paren_match = re.match(r"\((\d{2,4})\)", data[position:])
            if paren_match:
                ai = paren_match.group(1)
                position += len(paren_match.group(0))
            else:
                # Check for known AIs
                for ai_len in [4, 3, 2]:
                    potential_ai = data[position : position + ai_len]
                    if potential_ai in self.gs1_ai_patterns:
                        ai = potential_ai
                        position += ai_len
                        break
                else:
                    # Unknown format, skip character
                    position += 1
                    continue

            # Get AI info
            if ai in self.gs1_ai_patterns:
                ai_info = self.gs1_ai_patterns[ai]

                # Extract value based on AI definition
                if ai_info["length"] == "variable":
                    # Variable length - look for separator or max length
                    max_len = ai_info.get("max", 20)
                    value_end = position + max_len

                    # Look for separator (FNC1 or parenthesis)
                    for i in range(position, min(value_end, len(data))):
                        if data[i] in ["(", chr(29)]:
                            value_end = i
                            break

                    value = data[position:value_end]
                    position = value_end
                else:
                    # Fixed length
                    value = data[position : position + ai_info["length"]]
                    position += ai_info["length"]

                # Store parsed value
                parsed[ai_info["name"]] = value

                # Map to result fields
                if ai == "01":  # GTIN
                    result.gtin = self._normalize_gtin(value)
                elif ai == "10":  # Batch/Lot
                    result.lot_number = value
                elif ai == "21":  # Serial
                    result.serial_number = value
                elif ai == "17":  # Expiry
                    result.expiry_date = self._parse_gs1_date(value)
                elif ai == "11":  # Production date
                    result.production_date = self._parse_gs1_date(value)

        result.parsed_data = parsed

    def _parse_gs1_date(self, date_str: str) -> Optional[date]:
        """Parse GS1 date format (YYMMDD)"""
        try:
            if len(date_str) != 6:
                return None

            year = int(date_str[0:2])
            # Assume 20xx for years 00-50, 19xx for 51-99
            year = 2000 + year if year <= 50 else 1900 + year
            month = int(date_str[2:4])
            day = int(date_str[4:6])

            # Day 00 means last day of month
            if day == 0:
                import calendar

                day = calendar.monthrange(year, month)[1]

            return date(year, month, day)
        except:
            return None

    def _is_json_format(self, data: str) -> bool:
        """Check if data is JSON formatted"""
        try:
            json.loads(data)
            return True
        except:
            return False

    def _parse_json_qr(self, data: str, result: ScanResult):
        """Parse JSON formatted QR code"""
        try:
            json_data = json.loads(data)
            result.parsed_data = json_data

            # Map common fields
            result.gtin = (
                json_data.get("gtin") or json_data.get("upc") or json_data.get("ean")
            )
            result.lot_number = json_data.get("lot") or json_data.get("batch")
            result.serial_number = json_data.get("serial") or json_data.get("sn")

            # Parse dates
            if "expiry" in json_data:
                result.expiry_date = self._parse_date_string(json_data["expiry"])
            if "production_date" in json_data:
                result.production_date = self._parse_date_string(
                    json_data["production_date"]
                )

        except Exception as e:
            logger.warning(f"Error parsing JSON QR: {e}")

    def _parse_url_qr(self, data: str, result: ScanResult):
        """Parse URL formatted QR code"""
        result.parsed_data = {"url": data}

        # Try to extract identifiers from URL parameters
        import urllib.parse

        parsed_url = urllib.parse.urlparse(data)
        params = urllib.parse.parse_qs(parsed_url.query)

        # Common parameter names for product identifiers
        for gtin_param in ["gtin", "ean", "upc", "product", "id"]:
            if gtin_param in params:
                result.gtin = params[gtin_param][0]
                break

        for lot_param in ["lot", "batch", "lot_number"]:
            if lot_param in params:
                result.lot_number = params[lot_param][0]
                break

        for serial_param in ["serial", "sn", "serial_number"]:
            if serial_param in params:
                result.serial_number = params[serial_param][0]
                break

    def _is_standard_barcode(self, data: str) -> bool:
        """Check if data is a standard UPC/EAN barcode"""
        # Standard barcodes are typically 8, 12, or 13 digits
        return data.isdigit() and len(data) in [8, 12, 13, 14]

    def _normalize_gtin(self, gtin: str) -> str:
        """Normalize GTIN to 14 digits"""
        if not gtin or not gtin.isdigit():
            return gtin

        # Pad with zeros to make 14 digits
        if len(gtin) < 14:
            gtin = gtin.zfill(14)

        return gtin

    def _extract_patterns(self, data: str, result: ScanResult):
        """Extract common patterns from unstructured data"""

        # Look for lot numbers
        lot_patterns = [
            r"LOT[:\s#]*([A-Z0-9\-]+)",
            r"BATCH[:\s#]*([A-Z0-9\-]+)",
            r"L[:\s#]*([A-Z0-9]{4,})",
        ]

        for pattern in lot_patterns:
            match = re.search(pattern, data, re.IGNORECASE)
            if match:
                result.lot_number = match.group(1)
                break

        # Look for serial numbers
        serial_patterns = [
            r"S/N[:\s#]*([A-Z0-9\-]+)",
            r"SERIAL[:\s#]*([A-Z0-9\-]+)",
            r"SN[:\s#]*([A-Z0-9]{4,})",
        ]

        for pattern in serial_patterns:
            match = re.search(pattern, data, re.IGNORECASE)
            if match:
                result.serial_number = match.group(1)
                break

        # Look for dates
        date_patterns = [
            r"EXP[:\s]*(\d{2}/\d{2}/\d{2,4})",
            r"EXPIRY[:\s]*(\d{2}/\d{2}/\d{2,4})",
            r"BBE[:\s]*(\d{2}/\d{2}/\d{2,4})",
            r"USE BY[:\s]*(\d{2}/\d{2}/\d{2,4})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, data, re.IGNORECASE)
            if match:
                result.expiry_date = self._parse_date_string(match.group(1))
                break

        # Look for GTIN/UPC patterns
        gtin_match = re.search(r"\b(\d{8}|\d{12}|\d{13}|\d{14})\b", data)
        if gtin_match:
            result.gtin = self._normalize_gtin(gtin_match.group(1))

    def _parse_date_string(self, date_str: str) -> Optional[date]:
        """Parse various date formats"""
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d/%m/%y",
            "%m/%d/%y",
            "%Y%m%d",
            "%d-%m-%Y",
            "%m-%d-%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue

        return None

    def generate_qr_code(self, data: Dict[str, Any]) -> bytes:
        """
        Generate a QR code with product data

        Args:
            data: Dictionary with product information

        Returns:
            QR code image bytes
        """
        # Convert data to JSON
        json_data = json.dumps(data, default=str)

        # Generate QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json_data)
        qr.make(fit=True)

        # Create image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        img_buffer = BytesIO()
        img.save(img_buffer, format="PNG")

        return img_buffer.getvalue()


# Singleton instance - force logging of initialization
logger.info("🔧 Initializing BabyShield barcode scanner...")
scanner = BarcodeScanner()
logger.info("✅ BabyShield barcode scanner initialized successfully")
