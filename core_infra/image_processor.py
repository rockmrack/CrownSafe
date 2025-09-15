"""
Image Processing Module for Visual Agent - Phase 2
Handles OCR, barcode detection, label extraction with multiple providers
"""

import os
import io
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import re

# Image processing
from PIL import Image
import cv2
import numpy as np

# Cloud providers
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False
    logging.warning("Google Cloud Vision not available")

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logging.warning("AWS SDK not available")

# Local OCR - Feature flags for optional backends
ENABLE_TESSERACT = os.getenv("ENABLE_TESSERACT", "false").lower() == "true"
ENABLE_EASYOCR = os.getenv("ENABLE_EASYOCR", "false").lower() == "true"

TESSERACT_AVAILABLE = False
if ENABLE_TESSERACT:
    try:
        import pytesseract
        TESSERACT_AVAILABLE = True
        logging.info("Tesseract enabled and available")
    except ImportError:
        logging.warning("Tesseract requested but not available")
else:
    logging.info("Tesseract disabled by config")

EASYOCR_AVAILABLE = False
if ENABLE_EASYOCR:
    try:
        import easyocr
        EASYOCR_AVAILABLE = True
        logging.info("EasyOCR enabled and available")
    except ImportError:
        logging.warning("EasyOCR requested but not available")
else:
    logging.info("EasyOCR disabled by config")

# Import barcode scanner from Phase 1
from core_infra.barcode_scanner import scanner as barcode_scanner

logger = logging.getLogger(__name__)


class Provider(Enum):
    """Available vision API providers"""
    GOOGLE_VISION = "google_vision"
    AWS_REKOGNITION = "aws_rekognition"
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    LOCAL = "local"


@dataclass
class OCRResult:
    """OCR extraction result"""
    text: str
    confidence: float
    provider: str
    blocks: List[Dict[str, Any]] = None  # Text blocks with positions
    processing_time_ms: int = 0


@dataclass
class LabelResult:
    """Image labeling/classification result"""
    labels: List[Dict[str, float]]  # [{"name": "baby bottle", "confidence": 0.92}]
    categories: List[str]
    provider: str
    processing_time_ms: int = 0


@dataclass
class ExtractionResult:
    """Complete extraction result from image"""
    # Core extractions
    ocr: Optional[OCRResult] = None
    barcodes: List[Dict[str, Any]] = None
    labels: Optional[LabelResult] = None
    
    # Parsed product info
    product_name: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    lot_number: Optional[str] = None
    upc: Optional[str] = None
    
    # Safety info
    warnings: List[str] = None
    age_recommendation: Optional[str] = None
    certifications: List[str] = None
    
    # Metadata
    confidence_score: float = 0.0
    confidence_level: str = "low"  # high/medium/low
    flags: List[str] = None  # Issues detected
    
    def to_dict(self):
        return asdict(self)


class ImageAnalysisService:
    """
    Unified image analysis service with multi-provider support
    Implements abstraction layer for easy provider switching
    """
    
    def __init__(self, 
                 google_credentials_path: str = None,
                 aws_region: str = "us-east-1",
                 enable_caching: bool = True):
        """
        Initialize image analysis service
        
        Args:
            google_credentials_path: Path to Google Cloud credentials JSON
            aws_region: AWS region for Rekognition
            enable_caching: Enable result caching
        """
        self.enable_caching = enable_caching
        
        # Initialize Google Vision
        self.vision_client = None
        if GOOGLE_VISION_AVAILABLE and google_credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials_path
            self.vision_client = vision.ImageAnnotatorClient()
            logger.info("Google Vision API initialized")
        
        # Initialize AWS Rekognition
        self.rekognition_client = None
        if AWS_AVAILABLE:
            try:
                self.rekognition_client = boto3.client('rekognition', region_name=aws_region)
                logger.info("AWS Rekognition initialized")
            except Exception as e:
                logger.warning(f"AWS Rekognition init failed: {e}")
        
        # Initialize EasyOCR
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                self.easyocr_reader = easyocr.Reader(['en'])
                logger.info("EasyOCR initialized")
            except Exception as e:
                logger.warning(f"EasyOCR init failed: {e}")
        
        # Compile patterns for extraction
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for extraction"""
        self.patterns = {
            'model': [
                r'Model[:\s#]*([A-Z0-9\-]+)',
                r'Model No[:\s.]*([A-Z0-9\-]+)',
                r'Item[:\s#]*([A-Z0-9\-]+)',
                r'SKU[:\s]*([A-Z0-9\-]+)',
            ],
            'serial': [
                r'S/N[:\s]*([A-Z0-9\-]+)',
                r'Serial[:\s#]*([A-Z0-9\-]+)',
                r'Serial No[:\s.]*([A-Z0-9\-]+)',
            ],
            'lot': [
                r'LOT[:\s#]*([A-Z0-9\-]+)',
                r'Batch[:\s#]*([A-Z0-9\-]+)',
                r'Lot No[:\s.]*([A-Z0-9\-]+)',
            ],
            'upc': [
                r'\b(\d{12})\b',  # Standard UPC
                r'\b(\d{13})\b',  # EAN-13
                r'UPC[:\s]*(\d+)',
            ],
            'age': [
                r'(\d+)\+\s*years',
                r'Ages?\s+(\d+)\+',
                r'(\d+)\s*months?\+',
                r'Not suitable for children under (\d+)',
            ],
            'warnings': [
                r'WARNING[:\s]*([^.!]+[.!])',
                r'CAUTION[:\s]*([^.!]+[.!])',
                r'CHOKING HAZARD[:\s]*([^.!]+[.!])',
                r'Keep away from ([^.!]+[.!])',
            ],
            'certifications': [
                r'\b(CE|CPSC|ASTM|EN\d+|ISO\d+|UL)\b',
                r'Certified\s+([\w\s]+)',
                r'Complies with\s+([\w\s]+)',
            ]
        }
    
    async def analyze_image(self, 
                           image_data: bytes,
                           providers: List[Provider] = None,
                           extract_all: bool = True) -> ExtractionResult:
        """
        Analyze image with specified providers
        
        Args:
            image_data: Image bytes
            providers: List of providers to use (None = auto-select)
            extract_all: Extract all possible information
            
        Returns:
            Complete extraction result
        """
        # Calculate file hash for caching
        file_hash = hashlib.sha256(image_data).hexdigest()
        
        # Check cache if enabled
        if self.enable_caching:
            cached = self._check_cache(file_hash)
            if cached:
                logger.info(f"Cache hit for image {file_hash[:8]}")
                return cached
        
        # Auto-select providers if not specified
        if providers is None:
            providers = self._auto_select_providers()
        
        result = ExtractionResult()
        
        # Preprocess image
        pil_image = Image.open(io.BytesIO(image_data))
        
        # 1. Extract barcodes (Phase 1 integration)
        if extract_all or 'barcode' in extract_all:
            result.barcodes = await self._extract_barcodes(image_data)
        
        # 2. OCR text extraction
        if extract_all or 'ocr' in extract_all:
            result.ocr = await self._extract_text(pil_image, providers)
        
        # 3. Label extraction
        if extract_all or 'labels' in extract_all:
            result.labels = await self._extract_labels(image_data, providers)
        
        # 4. Parse structured data from OCR
        if result.ocr and result.ocr.text:
            self._parse_product_info(result.ocr.text, result)
        
        # 5. Calculate overall confidence
        self._calculate_confidence(result)
        
        # 6. Detect issues/flags
        self._detect_issues(result, pil_image)
        
        # Cache result if enabled
        if self.enable_caching:
            self._cache_result(file_hash, result)
        
        return result
    
    def _auto_select_providers(self) -> List[Provider]:
        """Auto-select best available providers"""
        providers = []
        
        # Prefer cloud providers for accuracy
        if self.vision_client:
            providers.append(Provider.GOOGLE_VISION)
        elif self.rekognition_client:
            providers.append(Provider.AWS_REKOGNITION)
        
        # Add local fallback
        if TESSERACT_AVAILABLE:
            providers.append(Provider.TESSERACT)
        elif EASYOCR_AVAILABLE:
            providers.append(Provider.EASYOCR)
        
        if not providers:
            providers.append(Provider.LOCAL)
        
        return providers
    
    async def _extract_barcodes(self, image_data: bytes) -> List[Dict[str, Any]]:
        """Extract barcodes using Phase 1 scanner"""
        try:
            scan_results = await barcode_scanner.scan_image(image_data)
            barcodes = []
            
            for result in scan_results:
                if result.success:
                    barcodes.append({
                        'type': result.barcode_type,
                        'data': result.raw_data,
                        'gtin': result.gtin,
                        'lot': result.lot_number,
                        'serial': result.serial_number,
                        'confidence': result.confidence
                    })
            
            return barcodes
        except Exception as e:
            logger.error(f"Barcode extraction error: {e}")
            return []
    
    async def _extract_text(self, image: Image.Image, providers: List[Provider]) -> Optional[OCRResult]:
        """Extract text using specified providers"""
        for provider in providers:
            try:
                if provider == Provider.GOOGLE_VISION and self.vision_client:
                    return await self._ocr_google_vision(image)
                elif provider == Provider.AWS_REKOGNITION and self.rekognition_client:
                    return await self._ocr_aws_rekognition(image)
                elif provider == Provider.TESSERACT and TESSERACT_AVAILABLE:
                    return await self._ocr_tesseract(image)
                elif provider == Provider.EASYOCR and self.easyocr_reader:
                    return await self._ocr_easyocr(image)
            except Exception as e:
                logger.warning(f"OCR failed with {provider.value}: {e}")
                continue
        
        return None
    
    async def _ocr_google_vision(self, image: Image.Image) -> OCRResult:
        """OCR using Google Cloud Vision"""
        start_time = datetime.now()
        
        # Convert PIL to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # Create Vision image
        vision_image = vision.Image(content=img_bytes)
        
        # Perform OCR
        response = self.vision_client.text_detection(image=vision_image)
        texts = response.text_annotations
        
        if texts:
            # First item contains all text
            full_text = texts[0].description
            
            # Calculate average confidence
            confidence = 0.9  # Google Vision doesn't provide confidence per default
            
            # Extract text blocks
            blocks = []
            for text in texts[1:]:  # Skip first (full text)
                blocks.append({
                    'text': text.description,
                    'vertices': [(v.x, v.y) for v in text.bounding_poly.vertices]
                })
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return OCRResult(
                text=full_text,
                confidence=confidence,
                provider="google_vision",
                blocks=blocks,
                processing_time_ms=processing_time
            )
        
        return OCRResult(text="", confidence=0.0, provider="google_vision")
    
    async def _ocr_tesseract(self, image: Image.Image) -> OCRResult:
        """OCR using Tesseract"""
        start_time = datetime.now()
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Get detailed data
        data = pytesseract.image_to_data(img_array, output_type=pytesseract.Output.DICT)
        
        # Extract text with confidence
        text_parts = []
        total_conf = 0
        valid_items = 0
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0:  # Valid detection
                text_parts.append(data['text'][i])
                total_conf += int(data['conf'][i])
                valid_items += 1
        
        full_text = ' '.join(text_parts)
        avg_confidence = (total_conf / valid_items / 100) if valid_items > 0 else 0
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return OCRResult(
            text=full_text,
            confidence=avg_confidence,
            provider="tesseract",
            processing_time_ms=processing_time
        )
    
    async def _extract_labels(self, image_data: bytes, providers: List[Provider]) -> Optional[LabelResult]:
        """Extract image labels/tags"""
        for provider in providers:
            try:
                if provider == Provider.GOOGLE_VISION and self.vision_client:
                    return await self._labels_google_vision(image_data)
                elif provider == Provider.AWS_REKOGNITION and self.rekognition_client:
                    return await self._labels_aws_rekognition(image_data)
            except Exception as e:
                logger.warning(f"Label extraction failed with {provider.value}: {e}")
                continue
        
        return None
    
    async def _labels_google_vision(self, image_data: bytes) -> LabelResult:
        """Extract labels using Google Vision"""
        start_time = datetime.now()
        
        vision_image = vision.Image(content=image_data)
        response = self.vision_client.label_detection(image=vision_image)
        labels = response.label_annotations
        
        label_list = []
        categories = set()
        
        for label in labels:
            label_list.append({
                'name': label.description,
                'confidence': label.score
            })
            
            # Categorize
            if any(word in label.description.lower() for word in ['baby', 'infant', 'child']):
                categories.add('baby_product')
            if any(word in label.description.lower() for word in ['toy', 'game', 'play']):
                categories.add('toy')
        
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return LabelResult(
            labels=label_list,
            categories=list(categories),
            provider="google_vision",
            processing_time_ms=processing_time
        )
    
    def _parse_product_info(self, text: str, result: ExtractionResult):
        """Parse product information from OCR text"""
        if not text:
            return
        
        # Extract using patterns
        for field, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1) if match.groups() else match.group(0)
                    
                    if field == 'model':
                        result.model_number = value
                    elif field == 'serial':
                        result.serial_number = value
                    elif field == 'lot':
                        result.lot_number = value
                    elif field == 'upc' and not result.upc:
                        result.upc = value
                    elif field == 'age':
                        result.age_recommendation = value
                    elif field == 'warnings':
                        if not result.warnings:
                            result.warnings = []
                        result.warnings.append(value)
                    elif field == 'certifications':
                        if not result.certifications:
                            result.certifications = []
                        result.certifications.append(value)
                    
                    break  # Use first match for each field
        
        # Extract brand (common patterns)
        brand_match = re.search(r'(?:by|from|©|®|™)\s*([A-Z][A-Za-z\s&]+)', text)
        if brand_match:
            result.brand = brand_match.group(1).strip()
        
        # Extract product name (usually largest text or first line)
        lines = text.split('\n')
        if lines and not result.product_name:
            # Assume first substantial line is product name
            for line in lines:
                if len(line) > 10 and not any(word in line.lower() for word in ['warning', 'caution', 'model']):
                    result.product_name = line.strip()
                    break
    
    def _calculate_confidence(self, result: ExtractionResult):
        """Calculate overall confidence score and level"""
        scores = []
        
        # OCR confidence
        if result.ocr:
            scores.append(result.ocr.confidence)
        
        # Barcode confidence (high weight)
        if result.barcodes:
            barcode_conf = max(b['confidence'] for b in result.barcodes)
            scores.append(barcode_conf * 1.2)  # Weight barcodes higher
        
        # Extraction completeness
        fields_extracted = sum([
            bool(result.product_name),
            bool(result.brand),
            bool(result.model_number),
            bool(result.upc or result.barcodes)
        ])
        completeness = fields_extracted / 4
        scores.append(completeness)
        
        # Average confidence
        if scores:
            result.confidence_score = sum(scores) / len(scores)
        else:
            result.confidence_score = 0.0
        
        # Determine level
        if result.confidence_score >= 0.85:
            result.confidence_level = "high"
        elif result.confidence_score >= 0.60:
            result.confidence_level = "medium"
        else:
            result.confidence_level = "low"
    
    def _detect_issues(self, result: ExtractionResult, image: Image.Image):
        """Detect potential issues with the image/extraction"""
        if not result.flags:
            result.flags = []
        
        # Check image quality
        if image.size[0] < 500 or image.size[1] < 500:
            result.flags.append("low_resolution")
        
        # Check blur (using variance of Laplacian)
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()
        if variance < 100:
            result.flags.append("blur_detected")
        
        # Check OCR quality
        if result.ocr:
            if result.ocr.confidence < 0.5:
                result.flags.append("poor_ocr_quality")
            if len(result.ocr.text) < 20:
                result.flags.append("minimal_text")
        
        # Check missing critical fields
        if not result.product_name:
            result.flags.append("no_product_name")
        if not result.brand and not result.model_number:
            result.flags.append("no_identifiers")
        
        # Check for multiple products
        if result.barcodes and len(result.barcodes) > 2:
            result.flags.append("multiple_products_detected")
    
    def _check_cache(self, file_hash: str) -> Optional[ExtractionResult]:
        """Check cache for existing analysis"""
        # TODO: Implement cache lookup from database
        return None
    
    def _cache_result(self, file_hash: str, result: ExtractionResult):
        """Cache analysis result"""
        # TODO: Implement cache storage to database
        pass


# PII Redaction utility
def redact_pii(text: str) -> str:
    """Redact potential PII from text"""
    if not text:
        return text
    
    # Phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    # Credit card
    text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[CARD]', text)
    
    return text


# Singleton instance
image_processor = ImageAnalysisService()
