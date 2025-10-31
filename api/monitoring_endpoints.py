"""Product Monitoring Management Endpoints."""

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.monitoring_scheduler import (
    MonitoredProduct,
    MonitoringRun,
    ProductMonitoringScheduler,
)
from api.pydantic_base import AppModel
from api.schemas.common import ApiResponse, fail, ok
from core_infra.auth import get_current_active_user
from core_infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])


class AddProductRequest(AppModel):
    """Request to add product to monitoring."""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    product_name: str
    brand_name: str | None = None
    model_number: str | None = None
    upc_code: str | None = None
    check_frequency_hours: int = 24


class MonitoredProductResponse(AppModel):
    """Monitored product details."""

    model_config = {"protected_namespaces": ()}  # Allow model_number field

    id: int
    product_name: str
    brand_name: str | None
    model_number: str | None
    upc_code: str | None
    is_active: bool
    check_frequency_hours: int
    last_checked: datetime | None
    next_check: datetime
    recall_status: str
    recalls_found: int
    created_at: datetime


@router.post("/products/add", response_model=ApiResponse)
async def add_product_to_monitoring(
    request: AddProductRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Add a product to 24/7 monitoring."""
    try:
        # Add to monitoring
        product = await ProductMonitoringScheduler.add_product_to_monitoring(
            user_id=current_user.id,
            product_name=request.product_name,
            brand_name=request.brand_name,
            model_number=request.model_number,
            upc_code=request.upc_code,
            check_frequency_hours=request.check_frequency_hours,
        )

        # Schedule immediate check in background
        background_tasks.add_task(ProductMonitoringScheduler.check_product_for_recalls, product, db)

        response = MonitoredProductResponse(
            id=product.id,
            product_name=product.product_name,
            brand_name=product.brand_name,
            model_number=product.model_number,
            upc_code=product.upc_code,
            is_active=product.is_active,
            check_frequency_hours=product.check_frequency_hours,
            last_checked=product.last_checked,
            next_check=product.next_check,
            recall_status=product.recall_status,
            recalls_found=product.recalls_found,
            created_at=product.created_at,
        )

        return ok({"message": "Product added to monitoring", "product": response.model_dump()})

    except Exception as e:
        logger.error(f"Error adding product to monitoring: {e}", exc_info=True)
        return fail(f"Failed to add product: {e!s}", status=500)


@router.get("/products", response_model=ApiResponse)
async def get_monitored_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active_only: bool = True,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get list of monitored products."""
    try:
        query = db.query(MonitoredProduct).filter(MonitoredProduct.user_id == current_user.id)

        if active_only:
            query = query.filter(MonitoredProduct.is_active)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        products = query.order_by(desc(MonitoredProduct.created_at)).offset(offset).limit(page_size).all()

        # Build response
        items = []
        for product in products:
            item = MonitoredProductResponse(
                id=product.id,
                product_name=product.product_name,
                brand_name=product.brand_name,
                model_number=product.model_number,
                upc_code=product.upc_code,
                is_active=product.is_active,
                check_frequency_hours=product.check_frequency_hours,
                last_checked=product.last_checked,
                next_check=product.next_check,
                recall_status=product.recall_status,
                recalls_found=product.recalls_found,
                created_at=product.created_at,
            )
            items.append(item.model_dump())

        # Count products with recalls
        recalled_count = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == current_user.id,
                MonitoredProduct.is_active,
                MonitoredProduct.recall_status == "recalled",
            )
            .count()
        )

        return ok(
            {
                "products": items,
                "total": total,
                "recalled_count": recalled_count,
                "page": page,
                "page_size": page_size,
                "has_more": (offset + page_size) < total,
            },
        )

    except Exception as e:
        logger.error(f"Error fetching monitored products: {e}", exc_info=True)
        return fail(f"Failed to fetch products: {e!s}", status=500)


@router.delete("/products/{product_id}", response_model=ApiResponse)
async def remove_product_from_monitoring(
    product_id: int,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Remove a product from monitoring."""
    try:
        product = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.id == product_id,
                MonitoredProduct.user_id == current_user.id,
            )
            .first()
        )

        if not product:
            return fail("Product not found", code="NOT_FOUND", status=404)

        # Soft delete
        product.is_active = False
        product.updated_at = datetime.now(UTC)
        db.commit()

        return ok({"message": "Product removed from monitoring"})

    except Exception as e:
        logger.error(f"Error removing product: {e}", exc_info=True)
        return fail(f"Failed to remove product: {e!s}", status=500)


@router.put("/products/{product_id}/frequency", response_model=ApiResponse)
async def update_check_frequency(
    product_id: int,
    frequency_hours: int = Query(..., ge=1, le=168),  # 1 hour to 1 week
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update monitoring frequency for a product."""
    try:
        product = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.id == product_id,
                MonitoredProduct.user_id == current_user.id,
            )
            .first()
        )

        if not product:
            return fail("Product not found", code="NOT_FOUND", status=404)

        product.check_frequency_hours = frequency_hours
        product.next_check = datetime.now(UTC) + timedelta(hours=frequency_hours)
        product.updated_at = datetime.now(UTC)
        db.commit()

        return ok(
            {
                "message": "Check frequency updated",
                "next_check": product.next_check.isoformat() + "Z",
            },
        )

    except Exception as e:
        logger.error(f"Error updating frequency: {e}", exc_info=True)
        return fail(f"Failed to update frequency: {e!s}", status=500)


@router.post("/products/{product_id}/check-now", response_model=ApiResponse)
async def check_product_now(
    product_id: int,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Trigger immediate check for a product."""
    try:
        product = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.id == product_id,
                MonitoredProduct.user_id == current_user.id,
            )
            .first()
        )

        if not product:
            return fail("Product not found", code="NOT_FOUND", status=404)

        # Run check in background
        result = await ProductMonitoringScheduler.check_product_for_recalls(product, db)

        # Update product
        product.last_checked = datetime.now(UTC)
        product.next_check = datetime.now(UTC) + timedelta(hours=product.check_frequency_hours)

        if result.get("recalls_found", 0) > 0:
            product.recall_status = "recalled"
            product.recalls_found = result["recalls_found"]

            # Send notification if new recalls
            if product.recalls_found < result["recalls_found"]:
                background_tasks.add_task(
                    ProductMonitoringScheduler.send_recall_notification,
                    current_user.id,
                    product,
                    result["recalls"],
                    db,
                )
        else:
            product.recall_status = "safe"

        db.commit()

        return ok(
            {
                "message": "Product checked",
                "recalls_found": result.get("recalls_found", 0),
                "recalls": result.get("recalls", []),
            },
        )

    except Exception as e:
        logger.error(f"Error checking product: {e}", exc_info=True)
        return fail(f"Failed to check product: {e!s}", status=500)


@router.post("/auto-add-scans", response_model=ApiResponse)
async def auto_add_from_scans(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Automatically add products from recent scans to monitoring."""
    try:
        from core_infra.visual_agent_models import ImageExtraction, ImageJob, JobStatus

        # Get user's recent completed scans
        recent_scans = (
            db.query(ImageJob)
            .join(ImageExtraction)
            .filter(
                ImageJob.user_id == current_user.id,
                ImageJob.status == JobStatus.COMPLETED,
                ImageJob.created_at >= datetime.now(UTC) - timedelta(days=30),
            )
            .all()
        )

        added_count = 0
        skipped_count = 0

        for job in recent_scans:
            extraction = db.query(ImageExtraction).filter_by(job_id=job.id).first()
            if extraction and extraction.product_name:
                # Check if already monitoring
                existing = (
                    db.query(MonitoredProduct)
                    .filter(
                        MonitoredProduct.user_id == current_user.id,
                        MonitoredProduct.source_job_id == job.id,
                    )
                    .first()
                )

                if not existing:
                    _ = await ProductMonitoringScheduler.add_product_to_monitoring(
                        user_id=current_user.id,
                        product_name=extraction.product_name,
                        brand_name=extraction.brand_name,
                        model_number=extraction.model_number,
                        upc_code=extraction.upc_code,
                        source_job_id=job.id,
                    )
                    added_count += 1
                else:
                    skipped_count += 1

        return ok(
            {
                "message": f"Added {added_count} products to monitoring",
                "added": added_count,
                "skipped": skipped_count,
                "total_scans": len(recent_scans),
            },
        )

    except Exception as e:
        logger.error(f"Error auto-adding products: {e}", exc_info=True)
        return fail(f"Failed to auto-add products: {e!s}", status=500)


@router.get("/status", response_model=ApiResponse)
async def get_monitoring_status(current_user=Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Get overall monitoring status and statistics."""
    try:
        # Get user's monitoring stats
        total_products = (
            db.query(MonitoredProduct)
            .filter(MonitoredProduct.user_id == current_user.id, MonitoredProduct.is_active)
            .count()
        )

        recalled_products = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == current_user.id,
                MonitoredProduct.is_active,
                MonitoredProduct.recall_status == "recalled",
            )
            .count()
        )

        # Get products needing check soon
        due_soon = (
            db.query(MonitoredProduct)
            .filter(
                MonitoredProduct.user_id == current_user.id,
                MonitoredProduct.is_active,
                MonitoredProduct.next_check <= datetime.now(UTC) + timedelta(hours=1),
            )
            .count()
        )

        # Get last monitoring run
        last_run = (
            db.query(MonitoringRun)
            .filter(MonitoringRun.status == "completed")
            .order_by(desc(MonitoringRun.completed_at))
            .first()
        )

        status = {
            "monitoring_active": True,
            "total_products": total_products,
            "recalled_products": recalled_products,
            "safe_products": total_products - recalled_products,
            "products_due_check": due_soon,
            "last_system_check": last_run.completed_at.isoformat() + "Z" if last_run else None,
            "next_system_check": (datetime.now(UTC) + timedelta(hours=1)).isoformat() + "Z",
        }

        return ok(status)

    except Exception as e:
        logger.error(f"Error fetching monitoring status: {e}", exc_info=True)
        return fail(f"Failed to fetch status: {e!s}", status=500)
