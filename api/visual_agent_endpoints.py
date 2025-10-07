from api.pydantic_base import AppModel
"""
Visual Agent API Endpoints - Phase 2
Image upload, analysis, MFV, and HITL review queue
"""

import os
import logging
import hashlib
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Body, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
import boto3

from core_infra.database import get_db as get_db_session
from core_infra.visual_agent_models import (
    ImageJob, ImageExtraction, ReviewQueue, MFVSession,
    JobStatus, ReviewStatus, ConfidenceLevel
)
from core_infra.celery_tasks import process_image, generate_presigned_url
from core_infra.s3_uploads import presign_post, _bucket_region, BUCKET
# Define ApiResponse locally
class ApiResponse(BaseModel):
    """API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None

logger = logging.getLogger(__name__)

# Router
visual_router = APIRouter(prefix="/api/v1/visual", tags=["visual-scanning"])

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")  # ECS region
S3_BUCKET_REGION = os.getenv("S3_BUCKET_REGION", "us-east-1")  # S3 bucket region
S3_BUCKET = os.getenv("S3_UPLOAD_BUCKET") or os.getenv("S3_BUCKET", "babyshield-images")
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN")

# Initialize S3 client with correct bucket region
s3_client = boto3.client('s3', region_name=S3_BUCKET_REGION)


# Request/Response Models
class ImageUploadResponse(BaseModel):
    """Response for image upload"""
    job_id: str
    upload_url: str
    status: str
    message: str


class ImageAnalysisRequest(BaseModel):
    """Request for image analysis with MFV"""
    job_id: Optional[str] = Field(None, description="Job ID from upload")
    image_url: Optional[str] = Field(None, description="Direct image URL for analysis")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image data")
    claimed_product: Optional[str] = Field(None, description="User claimed product name")
    claimed_brand: Optional[str] = Field(None, description="User claimed brand")
    claimed_model: Optional[str] = Field(None, description="User claimed model number")
    skip_mfv: bool = Field(False, description="Skip multi-factor verification")


class ImageAnalysisResponse(BaseModel):
    """Response for image analysis"""
    job_id: str
    status: str
    confidence_level: str
    confidence_score: float
    extraction: Optional[Dict[str, Any]] = None
    recall_check: Optional[Dict[str, Any]] = None
    mfv_required: bool = False
    mfv_message: Optional[str] = None
    needs_review: bool = False
    safety_message: str


class MFVConfirmationRequest(BaseModel):
    """Multi-factor verification confirmation"""
    session_id: str
    confirmed_product: str = Field(..., min_length=1)
    confirmed_brand: Optional[str] = None
    confirmed_model: Optional[str] = None
    user_corrections: Optional[Dict[str, str]] = None


class ReviewQueueFilter(BaseModel):
    """Filter for review queue"""
    status: Optional[ReviewStatus] = None
    priority: Optional[int] = None
    claimed_by: Optional[str] = None
    limit: int = Field(20, le=100)
    offset: int = Field(0, ge=0)


class ReviewAction(BaseModel):
    """Review action for HITL"""
    action: str = Field(..., pattern="^(approve|reject)$", description="Action to take: 'approve' or 'reject'")
    notes: Optional[str] = Field(None, description="Optional review notes")
    corrected_product: Optional[str] = None
    corrected_brand: Optional[str] = None
    corrected_model: Optional[str] = None
    user_message: Optional[str] = None


# Endpoints
@visual_router.post("/upload", response_model=ApiResponse)
async def request_image_upload(
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """
    Request presigned URL for image upload
    
    Returns presigned S3 URL for direct client upload
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Generate S3 key
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        s3_key = f"uploads/{user_id}/{timestamp}_{job_id}.jpg"
        
        # Generate presigned POST URL with region-correct host
        presigned_post = presign_post(s3_key, user_id=user_id, job_id=job_id)
        
        # Create job record
        job = ImageJob(
            id=job_id,
            user_id=user_id,
            s3_bucket=S3_BUCKET,
            s3_key=s3_key,
            status=JobStatus.QUEUED
        )
        db.add(job)
        db.commit()
        
        response = ImageUploadResponse(
            job_id=job_id,
            upload_url=presigned_post['url'],
            status="ready_for_upload",
            message="Upload your image to the provided URL"
        )
        
        # Add form fields to response
        response_dict = response.model_dump()  # Use model_dump() for Pydantic v2
        response_dict['upload_fields'] = presigned_post['fields']
        
        return ApiResponse(success=True, data=response_dict)
        
    except Exception as e:
        logger.error(f"Upload request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@visual_router.post("/analyze", response_model=ApiResponse)
async def analyze_image(
    request: ImageAnalysisRequest,
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """
    Start image analysis with optional MFV
    
    Triggers async processing and returns initial status
    """
    try:
        # Validate input - require at least one image source
        if not any([request.job_id, request.image_url, request.image_base64]):
            raise HTTPException(
                status_code=400, 
                detail="One of job_id, image_url, or image_base64 is required"
            )
        
        # Handle direct image input by creating a job
        if request.image_url or request.image_base64:
            # Create a new job for direct image analysis
            job_id = str(uuid.uuid4())
            job = ImageJob(
                id=job_id,
                user_id=0,  # Anonymous for direct analysis
                image_url=request.image_url,
                image_base64=request.image_base64,
                status=JobStatus.PENDING,
                created_at=datetime.utcnow()
            )
            db.add(job)
            db.commit()
        else:
            # Get existing job
            job = db.query(ImageJob).filter_by(id=request.job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if already processing
        if job.status in [JobStatus.PROCESSING, JobStatus.COMPLETED]:
            extraction = db.query(ImageExtraction).filter_by(job_id=job.id).first()
            
            # Check if MFV is required
            mfv_required = False
            mfv_message = None
            
            if not request.skip_mfv and extraction:
                # Check confidence level
                if job.confidence_level in [ConfidenceLevel.LOW, ConfidenceLevel.MEDIUM]:
                    mfv_required = True
                    mfv_message = "Please confirm the product details"
                    
                    # Create MFV session
                    mfv_session = MFVSession(
                        job_id=job.id,
                        user_id=job.user_id,
                        extracted_product=extraction.product_name,
                        extracted_brand=extraction.brand_name,
                        extracted_model=extraction.model_number,
                        user_claimed_product=request.claimed_product,
                        user_claimed_brand=request.claimed_brand,
                        user_claimed_model=request.claimed_model
                    )
                    db.add(mfv_session)
                    db.commit()
            
            # Build response
            response = ImageAnalysisResponse(
                job_id=job.id,
                status=job.status.value,
                confidence_level=job.confidence_level.value if job.confidence_level else "unknown",
                confidence_score=job.confidence_score or 0.0,
                mfv_required=mfv_required,
                mfv_message=mfv_message,
                needs_review=bool(db.query(ReviewQueue).filter_by(job_id=job.id).first()),
                safety_message=_generate_safety_message(job, extraction)
            )
            
            if extraction:
                response.extraction = {
                    'product_name': extraction.product_name,
                    'brand': extraction.brand_name,
                    'model': extraction.model_number,
                    'upc': extraction.upc_code,
                    'warnings': extraction.warning_labels,
                    'certifications': extraction.certifications
                }
            
            return ApiResponse(success=True, data=response.dict())
        
        # Ensure the uploaded object exists before kicking off processing
        try:
            s3 = boto3.client('s3', region_name=_bucket_region())
            s3.head_object(Bucket=BUCKET, Key=job.s3_key)
            object_exists = True
        except Exception:
            object_exists = False

        if not object_exists:
            queued_payload = ImageAnalysisResponse(
                job_id=job.id,
                status="queued",
                confidence_level="pending",
                confidence_score=0.0,
                mfv_required=False,
                needs_review=False,
                safety_message="Awaiting image upload. Please upload to the provided presigned URL."
            )
            return ApiResponse(success=True, data=queued_payload.dict(), message="Image not uploaded yet; queued")

        # Start processing when the object is available
        process_image.delay(job.id)
        
        response = ImageAnalysisResponse(
            job_id=job.id,
            status="processing",
            confidence_level="pending",
            confidence_score=0.0,
            mfv_required=False,
            needs_review=False,
            safety_message="Processing your image. This may take up to 30 seconds."
        )
        
        return ApiResponse(success=True, data=response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@visual_router.get("/status/{job_id}", response_model=ApiResponse)
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """Get image processing job status"""
    try:
        job = db.query(ImageJob).filter_by(id=job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        extraction = db.query(ImageExtraction).filter_by(job_id=job_id).first()
        review = db.query(ReviewQueue).filter_by(job_id=job_id).first()
        
        data = {
            'job_id': job.id,
            'status': job.status.value,
            'created_at': job.created_at.isoformat(),
            'confidence_level': job.confidence_level.value if job.confidence_level else None,
            'confidence_score': job.confidence_score,
            'error_message': job.error_message
        }
        
        if extraction:
            data['extraction'] = {
                'product_name': extraction.product_name,
                'brand': extraction.brand_name,
                'model': extraction.model_number,
                'upc': extraction.upc_code,
                'barcodes': extraction.barcodes,
                'warnings': extraction.warning_labels
            }
        
        if review:
            data['review'] = {
                'status': review.status.value,
                'reason': review.review_reason,
                'priority': review.priority
            }
        
        return ApiResponse(success=True, data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@visual_router.post("/mfv/confirm", response_model=ApiResponse)
async def confirm_mfv(
    request: MFVConfirmationRequest,
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """
    Confirm multi-factor verification
    
    User confirms or corrects extracted product details
    """
    try:
        # Get MFV session
        mfv = db.query(MFVSession).filter_by(id=request.session_id).first()
        if not mfv:
            raise HTTPException(status_code=404, detail="MFV session not found")
        
        # Update with user confirmation
        mfv.user_confirmed = True
        mfv.user_correction = request.user_corrections
        
        # Calculate match scores
        mfv.product_match = _fuzzy_match(mfv.extracted_product, request.confirmed_product)
        mfv.brand_match = _fuzzy_match(mfv.extracted_brand, request.confirmed_brand)
        mfv.model_match = _fuzzy_match(mfv.extracted_model, request.confirmed_model)
        
        # Overall score
        matches = [mfv.product_match, mfv.brand_match, mfv.model_match]
        mfv.overall_match_score = sum(1 for m in matches if m) / len(matches)
        
        # Determine if verification passed
        mfv.verification_passed = mfv.overall_match_score >= 0.6
        
        if mfv.verification_passed:
            mfv.verification_message = "Product details confirmed"
        else:
            mfv.verification_message = "Product details updated based on your input"
            
            # Update extraction with corrections
            extraction = db.query(ImageExtraction).filter_by(job_id=mfv.job_id).first()
            if extraction:
                extraction.product_name = request.confirmed_product
                extraction.brand_name = request.confirmed_brand
                extraction.model_number = request.confirmed_model
        
        mfv.completed_at = datetime.utcnow()
        db.commit()
        
        # Generate safety message
        job = db.query(ImageJob).filter_by(id=mfv.job_id).first()
        extraction = db.query(ImageExtraction).filter_by(job_id=mfv.job_id).first()
        
        return ApiResponse(success=True, data={
            'verification_passed': mfv.verification_passed,
            'message': mfv.verification_message,
            'safety_message': _generate_safety_message(job, extraction, always_qualified=True)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFV error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# HITL Review Queue Endpoints
@visual_router.get("/review/queue", response_model=ApiResponse)
async def get_review_queue(
    status: Optional[str] = None,
    priority: Optional[int] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """Get HITL review queue"""
    try:
        query = db.query(ReviewQueue)
        
        if status:
            query = query.filter(ReviewQueue.status == ReviewStatus[status.upper()])
        if priority:
            query = query.filter(ReviewQueue.priority == priority)
        
        # Order by priority and creation time
        query = query.order_by(ReviewQueue.priority, ReviewQueue.created_at)
        
        # Pagination
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        
        data = {
            'total': total,
            'items': [
                {
                    'id': item.id,
                    'job_id': item.job_id,
                    'status': item.status.value,
                    'priority': item.priority,
                    'reason': item.review_reason,
                    'claimed_by': item.claimed_by,
                    'created_at': item.created_at.isoformat()
                }
                for item in items
            ]
        }
        
        return ApiResponse(success=True, data=data)
        
    except Exception as e:
        logger.error(f"Review queue error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@visual_router.post("/review/{review_id}/claim", response_model=ApiResponse)
async def claim_review(
    review_id: int,
    request: Request,
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """Claim a review task"""
    try:
        # Handle both raw string and JSON body
        body = await request.body()
        content_type = request.headers.get("content-type", "")
        
        if content_type.startswith("application/json"):
            try:
                body_data = await request.json()
                if isinstance(body_data, dict):
                    # Support both user_id and assignee fields
                    reviewer_email = str(body_data.get("assignee") or body_data.get("user_id", ""))
                else:
                    reviewer_email = str(body_data)
            except:
                reviewer_email = body.decode("utf-8")
        else:
            # Raw string
            reviewer_email = body.decode("utf-8")
        
        review = db.query(ReviewQueue).filter_by(id=review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        if review.status != ReviewStatus.QUEUED:
            raise HTTPException(status_code=400, detail="Review already claimed")
        
        review.status = ReviewStatus.CLAIMED
        review.claimed_by = reviewer_email
        review.claimed_at = datetime.utcnow()
        
        # Add to audit log
        if not review.audit_log:
            review.audit_log = []
        review.audit_log.append({
            'action': 'claimed',
            'by': reviewer_email,
            'at': datetime.utcnow().isoformat()
        })
        
        db.commit()
        
        # Get job details for review
        job = db.query(ImageJob).filter_by(id=review.job_id).first()
        extraction = db.query(ImageExtraction).filter_by(job_id=review.job_id).first()
        
        data = {
            'review_id': review.id,
            'job_id': review.job_id,
            'image_url': generate_presigned_url(job.s3_bucket, job.s3_key) if job else None,
            'extraction': {
                'product_name': extraction.product_name,
                'brand': extraction.brand_name,
                'model': extraction.model_number,
                'ocr_text': extraction.ocr_text,
                'barcodes': extraction.barcodes,
                'labels': extraction.labels
            } if extraction else None
        }
        
        return ApiResponse(success=True, data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Claim error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@visual_router.post("/review/{review_id}/resolve", response_model=ApiResponse)
async def resolve_review(
    review_id: int,
    action: ReviewAction,
    db: Session = Depends(get_db_session)
) -> ApiResponse:
    """Resolve a review task"""
    try:
        review = db.query(ReviewQueue).filter_by(id=review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        if review.status != ReviewStatus.CLAIMED:
            raise HTTPException(status_code=400, detail="Review not claimed")
        
        # Update review based on action
        if action.action == "approve":
            review.status = ReviewStatus.APPROVED
        elif action.action == "reject":
            review.status = ReviewStatus.REJECTED
        
        review.review_notes = action.notes
        review.reviewed_at = datetime.utcnow()
        review.reviewed_by = review.claimed_by
        
        # Apply corrections if provided
        if action.corrected_product or action.corrected_brand or action.corrected_model:
            extraction = db.query(ImageExtraction).filter_by(job_id=review.job_id).first()
            if extraction:
                if action.corrected_product:
                    extraction.product_name = action.corrected_product
                    review.corrected_product_name = action.corrected_product
                if action.corrected_brand:
                    extraction.brand_name = action.corrected_brand
                    review.corrected_brand = action.corrected_brand
                if action.corrected_model:
                    extraction.model_number = action.corrected_model
                    review.corrected_model = action.corrected_model
            
            # Update job confidence after human review
            job = db.query(ImageJob).filter_by(id=review.job_id).first()
            if job:
                job.confidence_score = 0.95  # High confidence after human review
                job.confidence_level = ConfidenceLevel.HIGH
        
        # Set user message if provided
        if action.user_message:
            review.user_message = action.user_message
            review.requires_user_action = True
        
        # Update audit log
        if not review.audit_log:
            review.audit_log = []
        review.audit_log.append({
            'action': action.action,
            'by': review.reviewed_by,
            'at': datetime.utcnow().isoformat(),
            'notes': action.notes
        })
        
        db.commit()
        
        return ApiResponse(success=True, data={
            'review_id': review.id,
            'status': review.status.value,
            'message': f"Review {action.action}d successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resolve error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions
def _generate_safety_message(job: ImageJob, 
                            extraction: Optional[ImageExtraction],
                            always_qualified: bool = False) -> str:
    """
    Generate safety message following legal requirements
    Never says "safe" - only "no recalls found"
    """
    if job.status == JobStatus.FAILED:
        return "Analysis failed. Please try again with a clearer image."
    
    if job.status == JobStatus.PROCESSING:
        return "Analysis in progress. Please wait."
    
    if not extraction:
        return "Unable to extract product information. Please enter details manually."
    
    # Check confidence
    if job.confidence_level == ConfidenceLevel.LOW and not always_qualified:
        return "Image quality too low for accurate analysis. Please take a clearer photo or enter product details manually."
    
    # Build message - NEVER say "safe"
    product_desc = extraction.product_name or "this product"
    
    if extraction.warning_labels:
        warnings = ", ".join(extraction.warning_labels)
        return f"⚠️ Warnings detected: {warnings}. Please verify product model and check official sources."
    
    # Standard message - always qualified, never absolute
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    message = f"No recalls found for {product_desc} as of {date_str}. "
    message += "Please verify the model number and check official sources. "
    message += "Keep packaging and register your product with the manufacturer for future alerts."
    
    return message


def _fuzzy_match(str1: Optional[str], str2: Optional[str]) -> bool:
    """Simple fuzzy string matching"""
    if not str1 or not str2:
        return False
    
    # Normalize
    s1 = str1.lower().strip()
    s2 = str2.lower().strip()
    
    # Exact match
    if s1 == s2:
        return True
    
    # Contains match
    if s1 in s2 or s2 in s1:
        return True
    
    # TODO: Implement proper fuzzy matching with Levenshtein distance
    return False


@visual_router.post("/search", response_model=ApiResponse)
async def visual_search(
    request: ImageAnalysisRequest,
    db: Session = Depends(get_db_session)
):
    """
    Visual search endpoint for product recognition and safety checking
    """
    try:
        # Validate input
        if not request.image_url and not request.image_base64:
            return ApiResponse(
                success=False,
                error="Either image_url or image_base64 must be provided"
            )
        
        # Use real visual search agent
        from agents.visual.visual_search_agent.agent_logic import VisualSearchAgentLogic
        
        visual_agent = VisualSearchAgentLogic("visual_search_001")
        
        # Process image with real agent
        if request.image_url:
            result = await visual_agent.identify_product_from_image(request.image_url)
        else:
            # For base64 images, we need to upload to S3 first or use direct processing
            # For now, return error asking for image_url
            return ApiResponse(
                success=False,
                error="Base64 image processing not yet implemented. Please use image_url."
            )
        
        if result["status"] == "FAILED":
            return ApiResponse(
                success=False,
                error=result.get("error", "Visual analysis failed")
            )
        
        # Extract results
        product_data = result["result"]
        
        # Basic recall check using the identified product
        recall_found = False
        recall_count = 0
        
        if product_data.get("product_name"):
            # Simple recall check - in production this would be more sophisticated
            try:
                from sqlalchemy import text, inspect
                # Check if table exists first
                inspector = inspect(db.bind)
                if inspector.has_table('recalls_enhanced'):
                    recall_query = text("""
                        SELECT COUNT(*) as count 
                        FROM recalls_enhanced 
                        WHERE LOWER(product_name) LIKE LOWER(:product_name)
                        LIMIT 1
                    """)
                    result_count = db.execute(recall_query, {
                        "product_name": f"%{product_data['product_name']}%"
                    }).fetchone()
                    
                    if result_count and result_count[0] > 0:
                        recall_found = True
                        recall_count = result_count[0]
                else:
                    logger.warning("recalls_enhanced table not found, skipping recall check")
            except Exception as recall_err:
                logger.warning(f"Recall check failed: {recall_err}")
        
        # Build response with real data
        return ApiResponse(
            success=True,
            data={
                "status": "completed",
                "confidence_level": "high" if product_data.get("confidence", 0) > 0.8 else "medium" if product_data.get("confidence", 0) > 0.5 else "low",
                "confidence_score": product_data.get("confidence", 0.0),
                "extracted_text": "Product identified via GPT-4 Vision",
                "product_name": product_data.get("product_name", "Unknown"),
                "brand": product_data.get("brand", "Unknown"),
                "model_number": product_data.get("model_number", "Unknown"),
                "safety_status": "no_recalls_found" if not recall_found else "recalls_found",
                "recall_check": {
                    "has_recalls": recall_found,
                    "recall_count": recall_count
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Visual search error: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            error=f"Visual search failed: {str(e)}"
        )
