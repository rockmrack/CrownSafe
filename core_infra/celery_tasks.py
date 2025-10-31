"""Celery async tasks for Visual Agent image processing
Handles async job queue with Azure Blob Storage integration and multi-step processing.
"""

import logging
import os
from datetime import datetime, UTC
from typing import Any

from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded

from core_infra.azure_storage import AzureBlobStorageClient
from core_infra.database import SafetyArticle, get_db_session
from core_infra.image_processor import image_processor
from core_infra.visual_agent_models import (
    ConfidenceLevel,
    ImageExtraction,
    ImageJob,
    JobStatus,
    ReviewQueue,
    ReviewStatus,
)

logger = logging.getLogger(__name__)

# Celery configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
AZURE_REGION = os.getenv("AZURE_REGION", "westeurope")
STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "crownsafe-images")

# Initialize Celery
app = Celery("visual_agent", broker=REDIS_URL, backend=REDIS_URL)

# Celery config
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=30,  # 30 seconds soft limit
    task_time_limit=60,  # 60 seconds hard limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_reject_on_worker_lost=True,
)

# Beat schedule for periodic tasks
from celery.schedules import crontab  # noqa: E402

app.conf.beat_schedule = {
    "purge-legal-retention-daily": {
        "task": "retention.purge_legal_retention",
        "schedule": crontab(minute=15, hour=2),  # 02:15 UTC daily
    },
}

# Initialize Azure Blob Storage client
try:
    storage_client = AzureBlobStorageClient(container_name=STORAGE_CONTAINER)
    logger.info("Azure Blob Storage client initialized for Celery tasks")
except Exception as e:
    storage_client = None
    logger.warning(f"Azure Blob Storage not configured: {e}")


class CallbackTask(Task):
    """Task base class (avoid persistent DB session on task instance)."""

    pass


@app.task(base=CallbackTask, bind=True, name="process_image")
def process_image(self, job_id: str) -> dict[str, Any]:
    """Main image processing task.

    Args:
        job_id: Image job ID

    Returns:
        Processing result

    """
    logger.info(f"Starting image processing for job {job_id}")

    try:
        # Open a fresh session per task execution
        with get_db_session() as db:
            # Get job from database
            job = db.query(ImageJob).filter_by(id=job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Update status
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            db.commit()

        # Download image from Azure Blob Storage
        # Note: job.s3_bucket and job.s3_key should be renamed to blob_container and blob_name in database migration
        image_data = download_from_blob_storage(job.s3_bucket, job.s3_key)

        # Step 1: Virus scan
        virus_clean = virus_scan.run(job_id, image_data)

        if not virus_clean:
            with get_db_session() as db2:
                j = db2.query(ImageJob).filter_by(id=job_id).first()
                if j:
                    j.status = JobStatus.FAILED
                    j.error_message = "Virus detected in image"
                    db2.commit()
            return {"success": False, "error": "Virus detected"}

        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.virus_scanned = True
                db2.commit()

        # Step 2: Normalize image
        normalized_data = normalize_image.run(job_id, image_data)

        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.normalized = True
                db2.commit()

        # Step 3: Extract barcodes
        barcode_result = extract_barcodes.run(job_id, normalized_data)

        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.barcode_extracted = True
                db2.commit()

        # Step 4: OCR
        ocr_result = perform_ocr.run(job_id, normalized_data)

        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.ocr_completed = True
                db2.commit()

        # Step 5: Extract labels
        labels_result = extract_labels.run(job_id, normalized_data)

        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.labels_extracted = True
                db2.commit()

        # Step 6: Combine and save results
        save_extraction.run(
            job_id,
            {"barcodes": barcode_result, "ocr": ocr_result, "labels": labels_result},
        )

        # Step 7: Determine if HITL review needed
        needs_review = check_needs_review.run(job_id)

        if needs_review:
            create_review_task.apply_async(args=[job_id])

        # Update job status
        with get_db_session() as db2:
            j = db2.query(ImageJob).filter_by(id=job_id).first()
            if j:
                j.status = JobStatus.COMPLETED
                j.completed_at = datetime.now(UTC)
                db2.commit()

        logger.info(f"Image processing completed for job {job_id}")

        return {"success": True, "job_id": job_id, "needs_review": needs_review}

    except SoftTimeLimitExceeded:
        logger.exception(f"Task timeout for job {job_id}")
        try:
            with get_db_session() as db2:
                j = db2.query(ImageJob).filter_by(id=job_id).first()
                if j:
                    j.status = JobStatus.TIMEOUT
                    j.error_message = "Processing timeout"
                    db2.commit()
        except Exception:
            pass
        raise

    except Exception as e:
        logger.exception(f"Processing error for job {job_id}: {e}")
        try:
            with get_db_session() as db2:
                j = db2.query(ImageJob).filter_by(id=job_id).first()
                if j:
                    j.status = JobStatus.FAILED
                    j.error_message = str(e)
                    db2.commit()
        except Exception:
            pass
        raise


@app.task(name="virus_scan")
def virus_scan(job_id: str, image_data: bytes) -> bool:
    """Scan image for viruses.

    Note: This is a placeholder. In production, integrate with:
    - ClamAV Lambda layer
    - AWS GuardDuty
    - Or other virus scanning service
    """
    logger.info(f"Virus scanning job {job_id}")

    # Basic checks
    if len(image_data) > 50 * 1024 * 1024:  # 50MB limit
        return False

    # Check file signature (magic bytes)
    signatures = {
        b"\xff\xd8\xff": "JPEG",
        b"\x89\x50\x4e\x47": "PNG",
        b"\x47\x49\x46": "GIF",
        b"\x42\x4d": "BMP",
    }

    file_type = None
    for sig, name in signatures.items():
        if image_data.startswith(sig):
            file_type = name
            break

    if not file_type:
        logger.warning(f"Unknown file type for job {job_id}")
        return False

    # TODO: Integrate with actual virus scanner
    # For now, return True (clean)
    return True


@app.task(name="normalize_image")
def normalize_image(job_id: str, image_data: bytes) -> bytes:
    """Normalize image (resize, strip EXIF, convert format)."""
    logger.info(f"Normalizing image for job {job_id}")

    import io

    from PIL import Image, ImageOps

    # Open image
    img = Image.open(io.BytesIO(image_data))

    # Strip EXIF data
    data = list(img.getdata())
    image_without_exif = Image.new(img.mode, img.size)
    image_without_exif.putdata(data)

    # Resize if too large (max 2048px on longest side)
    max_size = 2048
    if max(image_without_exif.size) > max_size:
        image_without_exif.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

    # Auto-orient based on EXIF
    image_without_exif = ImageOps.exif_transpose(img) or image_without_exif

    # Convert to RGB if needed
    if image_without_exif.mode not in ("RGB", "L"):
        image_without_exif = image_without_exif.convert("RGB")

    # Save as JPEG with optimization
    output = io.BytesIO()
    image_without_exif.save(output, format="JPEG", quality=85, optimize=True)

    # Upload normalized version to Azure Blob Storage
    if storage_client:
        normalized_blob = f"processed/{job_id}_normalized.jpg"
        storage_client.upload_file(
            blob_name=normalized_blob,
            file_data=output.getvalue(),
            content_type="image/jpeg",
        )

    return output.getvalue()


@app.task(name="extract_barcodes")
def extract_barcodes(job_id: str, image_data: bytes) -> dict[str, Any]:
    """Extract barcodes from image."""
    logger.info(f"Extracting barcodes for job {job_id}")

    import asyncio

    from core_infra.barcode_scanner import scanner

    # Run async scanner
    loop = asyncio.new_event_loop()
    scan_results = loop.run_until_complete(scanner.scan_image(image_data))
    loop.close()

    barcodes = []
    for result in scan_results:
        if result.success:
            barcodes.append(
                {
                    "type": result.barcode_type,
                    "data": result.raw_data,
                    "gtin": result.gtin,
                    "lot": result.lot_number,
                    "serial": result.serial_number,
                    "confidence": result.confidence,
                },
            )

    logger.info(f"Found {len(barcodes)} barcodes in job {job_id}")
    return {"barcodes": barcodes}


@app.task(name="perform_ocr")
def perform_ocr(job_id: str, image_data: bytes) -> dict[str, Any]:
    """Perform OCR on image."""
    logger.info(f"Performing OCR for job {job_id}")

    import asyncio
    import io

    from PIL import Image

    # Convert bytes to PIL Image
    img = Image.open(io.BytesIO(image_data))

    # Run OCR
    loop = asyncio.new_event_loop()
    ocr_result = loop.run_until_complete(image_processor._extract_text(img, image_processor._auto_select_providers()))
    loop.close()

    if ocr_result:
        # Redact PII before storing
        from core_infra.image_processor import redact_pii

        clean_text = redact_pii(ocr_result.text)

        return {
            "text": clean_text,
            "confidence": ocr_result.confidence,
            "provider": ocr_result.provider,
        }

    return {"text": "", "confidence": 0.0, "provider": "none"}


@app.task(name="extract_labels")
def extract_labels(job_id: str, image_data: bytes) -> dict[str, Any]:
    """Extract image labels and categories."""
    logger.info(f"Extracting labels for job {job_id}")

    import asyncio

    # Run label extraction
    loop = asyncio.new_event_loop()
    labels_result = loop.run_until_complete(
        image_processor._extract_labels(image_data, image_processor._auto_select_providers()),
    )
    loop.close()

    if labels_result:
        return {
            "labels": labels_result.labels,
            "categories": labels_result.categories,
            "provider": labels_result.provider,
        }

    return {"labels": [], "categories": [], "provider": "none"}


@app.task(base=CallbackTask, bind=True, name="save_extraction")
def save_extraction(self, job_id: str, results: dict[str, Any]) -> None:
    """Save extraction results to database."""
    logger.info(f"Saving extraction for job {job_id}")

    # Parse results
    barcodes = results.get("barcodes", {}).get("barcodes", [])
    ocr = results.get("ocr", {})
    labels = results.get("labels", {})

    # Create extraction record
    extraction = ImageExtraction(
        job_id=job_id,
        ocr_text=ocr.get("text"),
        ocr_confidence=ocr.get("confidence", 0.0),
        ocr_provider=ocr.get("provider"),
        barcodes=barcodes,
        labels=labels.get("labels", []),
    )

    # Extract structured data
    if ocr.get("text"):
        # Use image processor to parse
        from core_infra.image_processor import ExtractionResult

        result = ExtractionResult()
        image_processor._parse_product_info(ocr["text"], result)

        extraction.product_name = result.product_name
        extraction.brand_name = result.brand
        extraction.model_number = result.model_number
        extraction.serial_number = result.serial_number
        extraction.lot_number = result.lot_number
        extraction.upc_code = result.upc
        extraction.warning_labels = result.warnings
        extraction.age_recommendations = result.age_recommendation
        extraction.certifications = result.certifications

    # Extract from barcodes
    if barcodes:
        for barcode in barcodes:
            if barcode.get("gtin") and not extraction.upc_code:
                extraction.upc_code = barcode["gtin"]
            if barcode.get("lot") and not extraction.lot_number:
                extraction.lot_number = barcode["lot"]
            if barcode.get("serial") and not extraction.serial_number:
                extraction.serial_number = barcode["serial"]

    # Persist using a scoped session
    with get_db_session() as db:
        db.add(extraction)

        # Update job confidence
        job = db.query(ImageJob).filter_by(id=job_id).first()
        if job:
            # Calculate confidence
            confidence = ocr.get("confidence", 0.0)
            if barcodes:
                confidence = max(confidence, max(b.get("confidence", 0) for b in barcodes))

            job.confidence_score = confidence

            if confidence >= 0.85:
                job.confidence_level = ConfidenceLevel.HIGH
            elif confidence >= 0.60:
                job.confidence_level = ConfidenceLevel.MEDIUM
            else:
                job.confidence_level = ConfidenceLevel.LOW

        db.commit()
    logger.info(f"Extraction saved for job {job_id}")


@app.task(base=CallbackTask, bind=True, name="check_needs_review")
def check_needs_review(self, job_id: str) -> bool:
    """Check if job needs human review."""
    with get_db_session() as db:
        job = db.query(ImageJob).filter_by(id=job_id).first()
        if not job:
            return False

        extraction = db.query(ImageExtraction).filter_by(job_id=job_id).first()
        if not extraction:
            return True  # No extraction = needs review

        # Check confidence
        if job.confidence_level == ConfidenceLevel.LOW:
            return True

        if job.confidence_level == ConfidenceLevel.MEDIUM:
            return True  # Per requirements: 0.60-0.84 needs HITL

        # Check for missing critical fields
        if not extraction.product_name and not extraction.upc_code:
            return True

        # Check for warnings without clear product ID
        if extraction.warning_labels and not extraction.model_number:
            return True

        return False


@app.task(base=CallbackTask, bind=True, name="create_review_task")
def create_review_task(self, job_id: str) -> None:
    """Create HITL review task."""
    logger.info(f"Creating review task for job {job_id}")
    with get_db_session() as db:
        job = db.query(ImageJob).filter_by(id=job_id).first()
        extraction = db.query(ImageExtraction).filter_by(job_id=job_id).first()

        # Determine review reason
        reasons = []
        if job and job.confidence_level == ConfidenceLevel.LOW:
            reasons.append("Low confidence extraction")
        elif job and job.confidence_level == ConfidenceLevel.MEDIUM:
            reasons.append("Medium confidence - verification required")

        if not extraction or not extraction.product_name:
            reasons.append("Product name not detected")

        if extraction and extraction.warning_labels:
            reasons.append("Safety warnings detected")

        # Create review queue entry
        review = ReviewQueue(
            job_id=job_id,
            status=ReviewStatus.QUEUED,
            priority=3 if (job and job.confidence_level == ConfidenceLevel.LOW) else 5,
            review_reason="; ".join(reasons),
            auto_flagged_issues=[],
        )

        db.add(review)
        db.commit()

    logger.info(f"Review task created for job {job_id}")


# Utility functions
def download_from_blob_storage(container: str, blob_name: str) -> bytes:
    """Download file from Azure Blob Storage."""
    if not storage_client:
        raise RuntimeError("Azure Blob Storage client not initialized")
    return storage_client.download_blob(blob_name, container_name=container)


def generate_sas_url(container: str, blob_name: str, expiry_hours: int = 1) -> str:
    """Generate SAS URL for Azure Blob."""
    if not storage_client:
        raise RuntimeError("Azure Blob Storage client not initialized")
    temp_client = AzureBlobStorageClient(container_name=container)
    return temp_client.generate_sas_url(blob_name=blob_name, expiry_hours=expiry_hours)


# Safety Hub Tasks
@app.task(name="tasks.ingest_safety_articles")
def ingest_safety_articles():
    """A Celery task that runs daily to fetch and store the latest safety articles."""
    import asyncio

    from core_infra.safety_data_connectors import CPSCDataConnector

    logger.info("--- [Celery Task] Starting: Ingest Safety Articles ---")

    # Initialize the CPSC connector
    cpsc_connector = CPSCDataConnector()

    # Fetch articles asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    new_articles = loop.run_until_complete(cpsc_connector.fetch_safety_articles())
    loop.close()

    if not new_articles:
        logger.info("[Celery Task] No new safety articles found.")
        return {"status": "success", "message": "No new articles to ingest", "count": 0}

    upserted_count = 0
    with get_db_session() as db:
        for article_data in new_articles:
            try:
                # Check if article already exists
                existing = (
                    db.query(SafetyArticle).filter(SafetyArticle.article_id == article_data["article_id"]).first()
                )

                if not existing:
                    # Create new article
                    db_article = SafetyArticle(**article_data)
                    db.add(db_article)
                    upserted_count += 1
                    logger.info(f"Added new article: {article_data['title']}")
                else:
                    # Update existing article if needed
                    for key, value in article_data.items():
                        setattr(existing, key, value)
                    logger.debug(f"Updated existing article: {article_data['title']}")

            except Exception as e:
                logger.exception(f"Error processing article {article_data.get('article_id')}: {e}")
                continue

        db.commit()

    logger.info(f"[Celery Task] Ingestion complete. Upserted {upserted_count} new safety articles.")
    return {
        "status": "success",
        "message": f"Ingestion complete. Upserted {upserted_count} new articles.",
        "count": upserted_count,
    }
