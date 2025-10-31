"""
Unit tests for core_infra/barcode_scanner_enhanced.py
Tests enhanced barcode scanner with multiple fallback methods
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from core_infra.barcode_scanner_enhanced import (
    BarcodeResult,
    BarcodeType,
    EnhancedBarcodeScanner,
    enhanced_scanner,
    scan_barcode,
    test_scanner_status,
)


class TestBarcodeType:
    """Test BarcodeType enum"""

    def test_barcode_type_values(self):
        """Test BarcodeType enum values"""
        assert BarcodeType.QRCODE.value == "QRCODE"
        assert BarcodeType.EAN13.value == "EAN13"
        assert BarcodeType.EAN8.value == "EAN8"
        assert BarcodeType.UPCA.value == "UPCA"
        assert BarcodeType.UPCE.value == "UPCE"
        assert BarcodeType.CODE128.value == "CODE128"
        assert BarcodeType.CODE39.value == "CODE39"
        assert BarcodeType.DATAMATRIX.value == "DATAMATRIX"
        assert BarcodeType.UNKNOWN.value == "UNKNOWN"


class TestBarcodeResult:
    """Test BarcodeResult dataclass"""

    def test_barcode_result_init(self):
        """Test BarcodeResult initialization"""
        result = BarcodeResult(
            data="test_data",
            type=BarcodeType.QRCODE,
            rect={"x": 10, "y": 20, "width": 100, "height": 100},
            confidence=0.95,
            method="pyzbar",
        )

        assert result.data == "test_data"
        assert result.type == BarcodeType.QRCODE
        assert result.rect == {"x": 10, "y": 20, "width": 100, "height": 100}
        assert result.confidence == 0.95
        assert result.method == "pyzbar"

    def test_barcode_result_defaults(self):
        """Test BarcodeResult with default values"""
        result = BarcodeResult(data="test_data", type=BarcodeType.QRCODE)

        assert result.data == "test_data"
        assert result.type == BarcodeType.QRCODE
        assert result.rect is None
        assert result.confidence == 1.0
        assert result.method == "unknown"


class TestEnhancedBarcodeScanner:
    """Test EnhancedBarcodeScanner functionality"""

    def test_init(self):
        """Test EnhancedBarcodeScanner initialization"""
        scanner = EnhancedBarcodeScanner()

        assert scanner.logger is not None
        assert scanner.opencv_detector is None

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.cv2")
    def test_init_with_opencv(self, mock_cv2):
        """Test initialization with OpenCV available"""
        mock_cv2.QRCodeDetector.return_value = Mock()
        mock_cv2.barcode = Mock()
        mock_cv2.barcode.BarcodeDetector.return_value = Mock()

        scanner = EnhancedBarcodeScanner()

        assert scanner.qr_detector is not None
        assert scanner.barcode_detector is not None

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", False)
    def test_init_without_opencv(self):
        """Test initialization without OpenCV"""
        scanner = EnhancedBarcodeScanner()

        assert scanner.qr_detector is None
        assert scanner.barcode_detector is None

    @patch("core_infra.barcode_scanner_enhanced.PIL_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.Image")
    def test_bytes_to_cv2_with_pil(self, mock_image):
        """Test _bytes_to_cv2 with PIL available"""
        scanner = EnhancedBarcodeScanner()

        mock_img = Mock()
        mock_img.mode = "RGB"
        mock_img.convert.return_value = mock_img
        mock_image.open.return_value = mock_img

        image_data = b"fake_image_data"
        result = scanner._bytes_to_cv2(image_data)

        mock_image.open.assert_called_once()
        assert result is not None

    @patch("core_infra.barcode_scanner_enhanced.PIL_AVAILABLE", False)
    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.cv2")
    def test_bytes_to_cv2_with_opencv_only(self, mock_cv2):
        """Test _bytes_to_cv2 with OpenCV only"""
        scanner = EnhancedBarcodeScanner()

        mock_cv2.imdecode.return_value = np.array([[1, 2], [3, 4]])

        image_data = b"fake_image_data"
        result = scanner._bytes_to_cv2(image_data)

        mock_cv2.imdecode.assert_called_once()
        assert result is not None

    @patch("core_infra.barcode_scanner_enhanced.PIL_AVAILABLE", False)
    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", False)
    def test_bytes_to_cv2_no_libraries(self):
        """Test _bytes_to_cv2 with no libraries available"""
        scanner = EnhancedBarcodeScanner()

        image_data = b"fake_image_data"
        result = scanner._bytes_to_cv2(image_data)

        assert result is None

    def test_bytes_to_cv2_exception(self):
        """Test _bytes_to_cv2 with exception"""
        scanner = EnhancedBarcodeScanner()

        with patch("core_infra.barcode_scanner_enhanced.PIL_AVAILABLE", True):
            with patch("core_infra.barcode_scanner_enhanced.Image") as mock_image:
                mock_image.open.side_effect = Exception("PIL error")

                image_data = b"fake_image_data"
                result = scanner._bytes_to_cv2(image_data)

                assert result is None

    def test_pyzbar_type_to_enum(self):
        """Test _pyzbar_type_to_enum method"""
        scanner = EnhancedBarcodeScanner()

        assert scanner._pyzbar_type_to_enum("QRCODE") == BarcodeType.QRCODE
        assert scanner._pyzbar_type_to_enum("EAN13") == BarcodeType.EAN13
        assert scanner._pyzbar_type_to_enum("EAN8") == BarcodeType.EAN8
        assert scanner._pyzbar_type_to_enum("UPCA") == BarcodeType.UPCA
        assert scanner._pyzbar_type_to_enum("UPCE") == BarcodeType.UPCE
        assert scanner._pyzbar_type_to_enum("CODE128") == BarcodeType.CODE128
        assert scanner._pyzbar_type_to_enum("CODE39") == BarcodeType.CODE39
        assert scanner._pyzbar_type_to_enum("UNKNOWN_TYPE") == BarcodeType.UNKNOWN

    @patch("core_infra.barcode_scanner_enhanced.PYZBAR_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.pyzbar")
    def test_scan_with_pyzbar_success(self, mock_pyzbar):
        """Test _scan_with_pyzbar with success"""
        scanner = EnhancedBarcodeScanner()

        # Mock decoded object
        mock_obj = Mock()
        mock_obj.type = "QRCODE"
        mock_obj.data = b"test_data"
        mock_obj.rect = Mock()
        mock_obj.rect.left = 10
        mock_obj.rect.top = 20
        mock_obj.rect.width = 100
        mock_obj.rect.height = 100

        mock_pyzbar.decode.return_value = [mock_obj]

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_pyzbar(image)

        assert len(results) == 1
        assert results[0].data == "test_data"
        assert results[0].type == BarcodeType.QRCODE
        assert results[0].method == "pyzbar"
        assert results[0].confidence == 1.0

    @patch("core_infra.barcode_scanner_enhanced.PYZBAR_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.pyzbar")
    def test_scan_with_pyzbar_exception(self, mock_pyzbar):
        """Test _scan_with_pyzbar with exception"""
        scanner = EnhancedBarcodeScanner()

        mock_pyzbar.decode.side_effect = Exception("PyZbar error")

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_pyzbar(image)

        assert len(results) == 0

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    def test_scan_with_opencv_qr_success(self):
        """Test _scan_with_opencv with QR code success"""
        scanner = EnhancedBarcodeScanner()

        # Mock QR detector
        mock_qr_detector = Mock()
        mock_qr_detector.detectAndDecode.return_value = (
            "qr_data",
            np.array([[[10, 20], [110, 20], [110, 120], [10, 120]]]),
            None,
        )
        scanner.qr_detector = mock_qr_detector

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_opencv(image)

        assert len(results) == 1
        assert results[0].data == "qr_data"
        assert results[0].type == BarcodeType.QRCODE
        assert results[0].method == "opencv"
        assert results[0].confidence == 0.9

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    def test_scan_with_opencv_qr_no_data(self):
        """Test _scan_with_opencv with QR detector but no data"""
        scanner = EnhancedBarcodeScanner()

        # Mock QR detector returning no data
        mock_qr_detector = Mock()
        mock_qr_detector.detectAndDecode.return_value = ("", None, None)
        scanner.qr_detector = mock_qr_detector

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_opencv(image)

        assert len(results) == 0

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    def test_scan_with_opencv_barcode_success(self):
        """Test _scan_with_opencv with barcode detector success"""
        scanner = EnhancedBarcodeScanner()

        # Mock barcode detector
        mock_barcode_detector = Mock()
        mock_barcode_detector.detectAndDecode.return_value = (
            True,
            ["barcode_data"],
            ["CODE128"],
            None,
        )
        scanner.barcode_detector = mock_barcode_detector

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_opencv(image)

        assert len(results) == 1
        assert results[0].data == "barcode_data"
        assert results[0].type == BarcodeType.UNKNOWN
        assert results[0].method == "opencv"
        assert results[0].confidence == 0.8

    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    def test_scan_with_opencv_exception(self):
        """Test _scan_with_opencv with exception"""
        scanner = EnhancedBarcodeScanner()

        # Mock QR detector that raises exception
        mock_qr_detector = Mock()
        mock_qr_detector.detectAndDecode.side_effect = Exception("OpenCV error")
        scanner.qr_detector = mock_qr_detector

        image = np.zeros((100, 100), dtype=np.uint8)
        results = scanner._scan_with_opencv(image)

        assert len(results) == 0

    @patch("core_infra.barcode_scanner_enhanced.PYZBAR_AVAILABLE", True)
    def test_scan_image_pyzbar_success(self):
        """Test scan_image with PyZbar success"""
        scanner = EnhancedBarcodeScanner()

        with patch.object(scanner, "_bytes_to_cv2") as mock_bytes_to_cv2:
            with patch.object(scanner, "_scan_with_pyzbar") as mock_scan_pyzbar:
                mock_bytes_to_cv2.return_value = np.zeros((100, 100), dtype=np.uint8)
                mock_scan_pyzbar.return_value = [BarcodeResult("test_data", BarcodeType.QRCODE, method="pyzbar")]

                image_data = b"fake_image_data"
                results = scanner.scan_image(image_data)

                assert len(results) == 1
                assert results[0].data == "test_data"
                assert results[0].method == "pyzbar"

    @patch("core_infra.barcode_scanner_enhanced.PYZBAR_AVAILABLE", False)
    @patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True)
    def test_scan_image_opencv_fallback(self):
        """Test scan_image with OpenCV fallback"""
        scanner = EnhancedBarcodeScanner()

        with patch.object(scanner, "_bytes_to_cv2") as mock_bytes_to_cv2:
            with patch.object(scanner, "_scan_with_opencv") as mock_scan_opencv:
                mock_bytes_to_cv2.return_value = np.zeros((100, 100), dtype=np.uint8)
                mock_scan_opencv.return_value = [BarcodeResult("test_data", BarcodeType.QRCODE, method="opencv")]

                image_data = b"fake_image_data"
                results = scanner.scan_image(image_data)

                assert len(results) == 1
                assert results[0].data == "test_data"
                assert results[0].method == "opencv"

    def test_scan_image_conversion_failure(self):
        """Test scan_image with image conversion failure"""
        scanner = EnhancedBarcodeScanner()

        with patch.object(scanner, "_bytes_to_cv2") as mock_bytes_to_cv2:
            mock_bytes_to_cv2.return_value = None

            image_data = b"fake_image_data"
            results = scanner.scan_image(image_data)

            assert len(results) == 0

    @patch("core_infra.barcode_scanner_enhanced.QRCODE_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.qrcode")
    def test_generate_qrcode_success(self, mock_qrcode):
        """Test generate_qrcode with success"""
        scanner = EnhancedBarcodeScanner()

        # Mock QR code generation
        mock_qr = Mock()
        mock_img = Mock()
        mock_qr.make_image.return_value = mock_img
        mock_qrcode.QRCode.return_value = mock_qr

        # Mock image save
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b"qr_image_data"
        mock_img.save = Mock()

        with patch("core_infra.barcode_scanner_enhanced.BytesIO") as mock_bytesio:
            mock_bytesio.return_value = mock_buffer

            result = scanner.generate_qrcode("test_data")

            assert result == b"qr_image_data"
            mock_qr.add_data.assert_called_once_with("test_data")
            mock_qr.make.assert_called_once_with(fit=True)
            mock_img.save.assert_called_once()

    @patch("core_infra.barcode_scanner_enhanced.QRCODE_AVAILABLE", False)
    def test_generate_qrcode_not_available(self):
        """Test generate_qrcode when QRCode library not available"""
        scanner = EnhancedBarcodeScanner()

        with pytest.raises(ValueError, match="QRCode library not available"):
            scanner.generate_qrcode("test_data")

    @patch("core_infra.barcode_scanner_enhanced.BARCODE_GEN_AVAILABLE", True)
    @patch("core_infra.barcode_scanner_enhanced.python_barcode")
    def test_generate_barcode_success(self, mock_barcode):
        """Test generate_barcode with success"""
        scanner = EnhancedBarcodeScanner()

        # Mock barcode generation
        mock_barcode_class = Mock()
        mock_code = Mock()
        mock_barcode.get_barcode_class.return_value = mock_barcode_class
        mock_barcode_class.return_value = mock_code

        # Mock image save
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b"barcode_image_data"
        mock_code.write = Mock()

        with patch("core_infra.barcode_scanner_enhanced.BytesIO") as mock_bytesio:
            with patch("core_infra.barcode_scanner_enhanced.ImageWriter") as _:  # mock_writer
                mock_bytesio.return_value = mock_buffer

                result = scanner.generate_barcode("123456789", "code128")

                assert result == b"barcode_image_data"
                mock_barcode.get_barcode_class.assert_called_once_with("code128")
                mock_code.write.assert_called_once()

    @patch("core_infra.barcode_scanner_enhanced.BARCODE_GEN_AVAILABLE", False)
    def test_generate_barcode_not_available(self):
        """Test generate_barcode when barcode generation library not available"""
        scanner = EnhancedBarcodeScanner()

        with pytest.raises(ValueError, match="Barcode generation library not available"):
            scanner.generate_barcode("123456789")

    def test_test_functionality(self):
        """Test test_functionality method"""
        scanner = EnhancedBarcodeScanner()

        with patch("core_infra.barcode_scanner_enhanced.PYZBAR_AVAILABLE", True):
            with patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True):
                with patch("core_infra.barcode_scanner_enhanced.QRCODE_AVAILABLE", True):
                    with patch(
                        "core_infra.barcode_scanner_enhanced.BARCODE_GEN_AVAILABLE",
                        True,
                    ):
                        scanner.qr_detector = Mock()
                        scanner.barcode_detector = Mock()

                        status = scanner.test_functionality()

                        assert isinstance(status, dict)
                        assert "pyzbar" in status
                        assert "opencv_qr" in status
                        assert "opencv_barcode" in status
                        assert "qrcode_generation" in status
                        assert "barcode_generation" in status


class TestGlobalFunctions:
    """Test global functions"""

    def test_enhanced_scanner_singleton(self):
        """Test enhanced_scanner singleton instance"""
        assert enhanced_scanner is not None
        assert isinstance(enhanced_scanner, EnhancedBarcodeScanner)

    def test_scan_barcode_function(self):
        """Test scan_barcode function"""
        with patch.object(enhanced_scanner, "scan_image") as mock_scan_image:
            mock_scan_image.return_value = [BarcodeResult("test_data", BarcodeType.QRCODE, method="pyzbar")]

            image_data = b"fake_image_data"
            results = scan_barcode(image_data)

            assert len(results) == 1
            assert results[0].data == "test_data"
            assert results[0].type.value == "QRCODE"
            assert results[0].method == "pyzbar"

    def test_test_scanner_status_function(self):
        """Test test_scanner_status function"""
        with patch.object(enhanced_scanner, "test_functionality") as mock_test_func:
            mock_test_func.return_value = {
                "pyzbar": True,
                "opencv_qr": True,
                "opencv_barcode": False,
                "qrcode_generation": True,
                "barcode_generation": True,
            }

            status = test_scanner_status()

            assert status["status"] == "working"
            assert "PyZbar (Full)" in status["working_methods"]
            assert "OpenCV QR" in status["working_methods"]
            assert "OpenCV Barcode" not in status["working_methods"]
            assert "Barcode scanning operational" in status["message"]

    def test_test_scanner_status_not_working(self):
        """Test test_scanner_status when no methods work"""
        with patch.object(enhanced_scanner, "test_functionality") as mock_test_func:
            mock_test_func.return_value = {
                "pyzbar": False,
                "opencv_qr": False,
                "opencv_barcode": False,
                "qrcode_generation": False,
                "barcode_generation": False,
            }

            status = test_scanner_status()

            assert status["status"] == "not_working"
            assert len(status["working_methods"]) == 0
            assert "No barcode scanning methods available" in status["message"]


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_scan_image_empty_data(self):
        """Test scan_image with empty data"""
        scanner = EnhancedBarcodeScanner()

        results = scanner.scan_image(b"")

        assert len(results) == 0

    def test_scan_image_none_data(self):
        """Test scan_image with None data"""
        scanner = EnhancedBarcodeScanner()

        results = scanner.scan_image(None)

        assert len(results) == 0

    def test_generate_qrcode_empty_data(self):
        """Test generate_qrcode with empty data"""
        scanner = EnhancedBarcodeScanner()

        with patch("core_infra.barcode_scanner_enhanced.QRCODE_AVAILABLE", True):
            with patch("core_infra.barcode_scanner_enhanced.qrcode"):
                with patch("core_infra.barcode_scanner_enhanced.BytesIO"):
                    result = scanner.generate_qrcode("")

                    assert result is not None

    def test_generate_barcode_empty_data(self):
        """Test generate_barcode with empty data"""
        scanner = EnhancedBarcodeScanner()

        with patch("core_infra.barcode_scanner_enhanced.BARCODE_GEN_AVAILABLE", True):
            with patch("core_infra.barcode_scanner_enhanced.python_barcode"):
                with patch("core_infra.barcode_scanner_enhanced.BytesIO"):
                    result = scanner.generate_barcode("")

                    assert result is not None

    def test_scan_with_opencv_color_image(self):
        """Test _scan_with_opencv with color image"""
        scanner = EnhancedBarcodeScanner()

        with patch("core_infra.barcode_scanner_enhanced.OPENCV_AVAILABLE", True):
            with patch("core_infra.barcode_scanner_enhanced.cv2") as mock_cv2:
                mock_cv2.cvtColor.return_value = np.zeros((100, 100), dtype=np.uint8)

                # Color image (3 channels)
                color_image = np.zeros((100, 100, 3), dtype=np.uint8)
                results = scanner._scan_with_opencv(color_image)

                mock_cv2.cvtColor.assert_called_once()
                assert len(results) == 0  # No QR detector mocked


if __name__ == "__main__":
    pytest.main([__file__])
