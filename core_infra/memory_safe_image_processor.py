"""Memory-safe image processing for BabyShield
Prevents memory leaks and manages resources properly
"""

import gc
import io
import logging
import os
import tempfile
import weakref
from contextlib import contextmanager
from functools import wraps
from typing import Any

import psutil

logger = logging.getLogger(__name__)


# Track memory usage
def get_memory_usage() -> float:
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def log_memory(func):
    """Decorator to log memory usage"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        before = get_memory_usage()
        result = func(*args, **kwargs)
        after = get_memory_usage()
        diff = after - before

        if diff > 10:  # Log if more than 10MB difference
            logger.warning(f"{func.__name__} used {diff:.2f}MB memory")

        return result

    return wrapper


class MemorySafeImageProcessor:
    """Memory-safe image processing with automatic cleanup"""

    # Maximum image dimensions to prevent memory explosion
    MAX_WIDTH = 4096
    MAX_HEIGHT = 4096
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self) -> None:
        self._temp_files = weakref.WeakSet()
        self._open_resources = []

    def __del__(self) -> None:
        """Cleanup on deletion"""
        self.cleanup()

    def cleanup(self) -> None:
        """Clean up all resources"""
        # Clean temp files
        for temp_file in list(self._temp_files):
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except (OSError, PermissionError):
                pass  # File might be in use or already deleted

        # Clear resources
        for resource in self._open_resources:
            try:
                if hasattr(resource, "close"):
                    resource.close()
            except Exception:
                pass  # Resource might already be closed

        self._open_resources.clear()

        # Force garbage collection
        gc.collect()

    @contextmanager
    def process_image_safely(self, image_path: str):
        """Context manager for safe image processing"""
        import cv2

        image = None
        try:
            # Check file size first
            file_size = os.path.getsize(image_path)
            if file_size > self.MAX_FILE_SIZE:
                raise ValueError(f"Image too large: {file_size} bytes")

            # Read image with OpenCV
            image = cv2.imread(image_path)

            if image is None:
                raise ValueError("Failed to load image")

            # Check dimensions
            height, width = image.shape[:2]
            if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                # Resize if too large
                scale = min(self.MAX_WIDTH / width, self.MAX_HEIGHT / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height))
                logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")

            yield image

        finally:
            # Explicitly delete the image array
            if image is not None:
                del image

            # Force garbage collection
            gc.collect()

    @log_memory
    def process_with_pil(self, image_bytes: bytes) -> dict[str, Any] | None:
        """Process image with PIL, ensuring memory cleanup"""
        from PIL import Image

        img = None
        img_buffer = None

        try:
            # Open image
            img_buffer = io.BytesIO(image_bytes)
            img = Image.open(img_buffer)

            # Check size
            if img.size[0] > self.MAX_WIDTH or img.size[1] > self.MAX_HEIGHT:
                img.thumbnail((self.MAX_WIDTH, self.MAX_HEIGHT), Image.Resampling.LANCZOS)

            # Process image (example)
            result = {"format": img.format, "size": img.size, "mode": img.mode}

            return result

        finally:
            # Clean up PIL image
            if img:
                img.close()
                del img

            if img_buffer:
                img_buffer.close()
                del img_buffer

            gc.collect()

    @log_memory
    def extract_text_ocr(self, image_path: str) -> str | None:
        """Extract text using OCR with memory management"""
        import pytesseract
        from PIL import Image

        img = None
        text = None

        try:
            # Use PIL to open and preprocess
            img = Image.open(image_path)

            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize if too large
            if img.size[0] > 2048 or img.size[1] > 2048:
                img.thumbnail((2048, 2048), Image.Resampling.LANCZOS)

            # Extract text
            text = pytesseract.image_to_string(img)

            return text

        except Exception as e:
            logger.exception(f"OCR error: {e}")
            return None

        finally:
            if img:
                img.close()
                del img
            gc.collect()

    @contextmanager
    def temporary_file(self, suffix: str = ".tmp"):
        """Create a temporary file that's automatically cleaned up"""
        temp_file = None
        try:
            # Create temp file
            fd, temp_file = tempfile.mkstemp(suffix=suffix)
            os.close(fd)

            # Track it
            self._temp_files.add(temp_file)

            yield temp_file

        finally:
            # Clean up
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except (OSError, PermissionError):
                    pass  # File might be in use or already deleted

    def detect_barcodes_safe(self, image_path: str) -> list:
        """Detect barcodes with memory safety"""
        import cv2
        from pyzbar import pyzbar

        barcodes = []

        with self.process_image_safely(image_path) as image:
            try:
                # Convert to grayscale
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

                # Detect barcodes
                detected = pyzbar.decode(gray)

                for barcode in detected:
                    barcodes.append(
                        {
                            "type": barcode.type,
                            "data": barcode.data.decode("utf-8"),
                            "rect": barcode.rect,
                        },
                    )

                # Clean up
                del gray
                del detected

            except Exception as e:
                logger.exception(f"Barcode detection error: {e}")

        gc.collect()
        return barcodes


class ImageMemoryManager:
    """Manage memory for batch image processing"""

    def __init__(self, max_memory_mb: int = 500) -> None:
        self.max_memory_mb = max_memory_mb
        self.processors = []

    def should_cleanup(self) -> bool:
        """Check if cleanup is needed"""
        current_memory = get_memory_usage()
        return current_memory > self.max_memory_mb

    def process_batch(self, image_paths: list, process_func: callable) -> list:
        """Process batch of images with memory management"""
        results = []
        processor = MemorySafeImageProcessor()

        try:
            for i, path in enumerate(image_paths):
                # Check memory before processing
                if self.should_cleanup():
                    logger.info("Memory limit reached, cleaning up...")
                    processor.cleanup()
                    gc.collect()

                # Process image
                try:
                    result = process_func(processor, path)
                    results.append(result)
                except Exception as e:
                    logger.exception(f"Error processing {path}: {e}")
                    results.append(None)

                # Periodic cleanup
                if (i + 1) % 10 == 0:
                    gc.collect()
                    logger.info(f"Processed {i + 1}/{len(image_paths)} images")

        finally:
            processor.cleanup()
            gc.collect()

        return results


# Memory-safe wrapper for existing functions
def make_memory_safe(func):
    """Decorator to make image processing functions memory-safe"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Get memory before
            mem_before = get_memory_usage()

            # Call function
            result = func(*args, **kwargs)

            # Check memory after
            mem_after = get_memory_usage()
            mem_diff = mem_after - mem_before

            # Cleanup if too much memory used
            if mem_diff > 50:  # More than 50MB
                logger.warning(f"{func.__name__} used {mem_diff:.2f}MB, forcing cleanup")
                gc.collect()

            return result

        except Exception as e:
            logger.exception(f"Memory-safe wrapper caught error: {e}")
            gc.collect()
            raise

    return wrapper


# Update existing image processor to use memory-safe version
def patch_image_processor() -> None:
    """Patch existing image processor with memory-safe version"""
    try:
        from core_infra import image_processor

        # Replace with memory-safe version
        original_process = image_processor.process_image

        @make_memory_safe
        def safe_process_image(*args, **kwargs):
            return original_process(*args, **kwargs)

        image_processor.process_image = safe_process_image

        logger.info("✅ Image processor patched with memory-safe version")

    except ImportError:
        logger.warning("Could not patch image processor")


# Resource monitoring
class ResourceMonitor:
    """Monitor resource usage and alert on issues"""

    def __init__(self, alert_memory_mb: int = 1000, alert_cpu_percent: int = 80) -> None:
        self.alert_memory_mb = alert_memory_mb
        self.alert_cpu_percent = alert_cpu_percent

    def check_resources(self) -> dict[str, Any]:
        """Check current resource usage"""
        process = psutil.Process()

        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=1)

        status = {
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "memory_alert": memory_mb > self.alert_memory_mb,
            "cpu_alert": cpu_percent > self.alert_cpu_percent,
        }

        if status["memory_alert"]:
            logger.warning(f"High memory usage: {memory_mb:.2f}MB")
            # Force cleanup
            gc.collect()

        if status["cpu_alert"]:
            logger.warning(f"High CPU usage: {cpu_percent}%")

        return status
