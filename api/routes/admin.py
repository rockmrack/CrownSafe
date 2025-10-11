"""
Admin API routes for ingestion management and monitoring
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text, select, func, and_, or_, Integer
from sqlalchemy.orm import Session

from api.security.admin_auth import require_admin, AdminRateLimit
from api.services.ingestion_runner import IngestionRunner
from api.rate_limiting import RateLimiters
from api.errors import APIError
from core_infra.database import get_db
from core_infra.enhanced_database_schema import EnhancedRecallDB
from db.models.ingestion_run import IngestionRun

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],  # All routes require admin auth
)


def create_response(
    data: Any, request: Request, status_code: int = 200
) -> JSONResponse:
    """Create standard JSON response with trace ID"""
    return JSONResponse(
        content={
            "ok": True,
            "data": data,
            "traceId": getattr(request.state, "trace_id", None),
        },
        status_code=status_code,
    )


@router.post("/ingest", dependencies=[Depends(AdminRateLimit.get_ingest_limiter)])
async def trigger_ingestion(
    request: Request,
    body: Dict[str, Any],
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Trigger a new data ingestion job

    Body:
        agency: Agency code (FDA, CPSC, EU_SAFETY_GATE, etc.)
        mode: Ingestion mode (delta, full, incremental)
        metadata: Optional metadata dictionary
    """
    # Validate inputs
    agency = (body.get("agency") or "").upper()
    mode = (body.get("mode") or "delta").lower()
    metadata = body.get("metadata", {})

    if not agency:
        raise APIError(
            status_code=400, code="MISSING_AGENCY", message="Agency is required"
        )

    if agency not in IngestionRunner.SUPPORTED_AGENCIES:
        raise APIError(
            status_code=400,
            code="UNSUPPORTED_AGENCY",
            message=f"Unsupported agency: {agency}. Supported: {', '.join(sorted(IngestionRunner.SUPPORTED_AGENCIES))}",
        )

    if mode not in ("delta", "full", "incremental"):
        raise APIError(
            status_code=400,
            code="INVALID_MODE",
            message="Mode must be delta, full, or incremental",
        )

    # Start ingestion
    try:
        run_id, status, stdout, stderr = await IngestionRunner.start_ingestion(
            agency=agency,
            mode=mode,
            trace_id=getattr(request.state, "trace_id", None),
            initiated_by=admin,
            metadata=metadata,
        )

        if status == "already_running":
            raise APIError(
                status_code=409,
                code="INGESTION_RUNNING",
                message=f"Ingestion already running for {agency}/{mode}",
            )

        logger.info(
            "Ingestion triggered",
            extra={
                "traceId": getattr(request.state, "trace_id", None),
                "run_id": run_id,
                "agency": agency,
                "mode": mode,
                "admin": admin,
            },
        )

        return create_response(
            {"runId": run_id, "status": status, "agency": agency, "mode": mode}, request
        )

    except ValueError as e:
        raise APIError(status_code=400, code="INVALID_REQUEST", message=str(e))
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}")
        raise APIError(
            status_code=500,
            code="INGESTION_START_FAILED",
            message="Failed to start ingestion job",
        )


@router.get("/runs", dependencies=[Depends(AdminRateLimit.get_query_limiter)])
async def list_ingestion_runs(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    agency: Optional[str] = Query(None, description="Filter by agency"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    List recent ingestion runs with optional filtering
    """
    try:
        # Build query
        query = db.query(IngestionRun)

        # Apply filters
        if agency:
            query = query.filter(IngestionRun.agency == agency.upper())

        if status:
            query = query.filter(IngestionRun.status == status.lower())

        # Order by creation time (most recent first)
        query = query.order_by(IngestionRun.created_at.desc())

        # Get total count
        total = query.count()

        # Apply pagination
        runs = query.offset(offset).limit(limit).all()

        # Convert to dict
        items = [run.to_dict() for run in runs]

        return create_response(
            {
                "items": items,
                "total": total,
                "limit": limit,
                "offset": offset,
                "hasMore": (offset + limit) < total,
            },
            request,
        )

    except Exception as e:
        logger.error(f"Failed to list runs: {e}")
        raise APIError(
            status_code=500,
            code="LIST_RUNS_FAILED",
            message="Failed to retrieve ingestion runs",
        )


@router.get("/runs/{run_id}")
async def get_ingestion_run(
    run_id: str, request: Request, db: Session = Depends(get_db)
):
    """
    Get details of a specific ingestion run
    """
    try:
        # Validate UUID
        try:
            UUID(run_id)
        except ValueError:
            raise APIError(
                status_code=400, code="INVALID_RUN_ID", message="Invalid run ID format"
            )

        # Query run
        run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

        if not run:
            raise APIError(
                status_code=404, code="RUN_NOT_FOUND", message="Ingestion run not found"
            )

        return create_response(run.to_dict(), request)

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to get run {run_id}: {e}")
        raise APIError(
            status_code=500,
            code="GET_RUN_FAILED",
            message="Failed to retrieve ingestion run",
        )


@router.delete("/runs/{run_id}/cancel")
async def cancel_ingestion_run(
    run_id: str,
    request: Request,
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Cancel a running ingestion job
    """
    try:
        # Validate UUID
        try:
            UUID(run_id)
        except ValueError:
            raise APIError(
                status_code=400, code="INVALID_RUN_ID", message="Invalid run ID format"
            )

        # Check if run exists and is running
        run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()

        if not run:
            raise APIError(
                status_code=404, code="RUN_NOT_FOUND", message="Ingestion run not found"
            )

        if run.status != "running":
            raise APIError(
                status_code=400,
                code="NOT_RUNNING",
                message=f"Cannot cancel run with status: {run.status}",
            )

        # Cancel the job
        cancelled = await IngestionRunner.cancel_ingestion(run_id)

        if cancelled:
            logger.info(f"Ingestion {run_id} cancelled by {admin}")
            return create_response({"runId": run_id, "status": "cancelled"}, request)
        else:
            raise APIError(
                status_code=500,
                code="CANCEL_FAILED",
                message="Failed to cancel ingestion",
            )

    except APIError:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel run {run_id}: {e}")
        raise APIError(
            status_code=500, code="CANCEL_FAILED", message="Failed to cancel ingestion"
        )


@router.post("/reindex", dependencies=[Depends(AdminRateLimit.get_reindex_limiter)])
async def reindex_database(
    request: Request, admin: str = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Reindex database and run VACUUM ANALYZE
    """
    try:
        logger.info(f"Database reindex initiated by {admin}")

        # List of indexes to reindex (from Task 2)
        indexes = [
            "ix_recalls_enhanced_product_name_trgm",
            "ix_recalls_enhanced_title_trgm",
            "ix_recalls_enhanced_brand_trgm",
            "ix_recalls_enhanced_description_trgm",
            "ix_recalls_enhanced_agency",
            "ix_recalls_enhanced_riskcategory",
            "ix_recalls_enhanced_severity",
            "ix_recalls_enhanced_recalldate",
        ]

        reindexed = []
        failed = []

        # Reindex each index
        for index_name in indexes:
            try:
                db.execute(text(f"REINDEX INDEX IF EXISTS {index_name}"))
                db.commit()
                reindexed.append(index_name)
            except Exception as e:
                logger.warning(f"Failed to reindex {index_name}: {e}")
                failed.append(index_name)

        # Run VACUUM ANALYZE
        try:
            db.execute(text("VACUUM (ANALYZE) recalls_enhanced"))
            db.commit()
            vacuum_success = True
        except Exception as e:
            logger.warning(f"VACUUM ANALYZE failed: {e}")
            vacuum_success = False

        return create_response(
            {
                "reindexed": reindexed,
                "failed": failed,
                "vacuum": vacuum_success,
                "message": f"Reindexed {len(reindexed)} indexes",
            },
            request,
        )

    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        raise APIError(
            status_code=500, code="REINDEX_FAILED", message="Failed to reindex database"
        )


@router.get("/freshness")
async def data_freshness(request: Request, db: Session = Depends(get_db)):
    """
    Get data freshness statistics
    """
    try:
        # Overall statistics
        total_recalls = db.query(func.count(EnhancedRecallDB.id)).scalar() or 0

        latest_update = db.query(func.max(EnhancedRecallDB.last_updated)).scalar()

        # Per-agency statistics
        agency_stats = (
            db.query(
                EnhancedRecallDB.source_agency.label("agency"),
                func.count(EnhancedRecallDB.id).label("total"),
                func.max(EnhancedRecallDB.last_updated).label("last_updated"),
                func.sum(
                    func.cast(
                        EnhancedRecallDB.last_updated
                        >= datetime.utcnow() - timedelta(hours=24),
                        Integer,
                    )
                ).label("new_24h"),
                func.sum(
                    func.cast(
                        EnhancedRecallDB.last_updated
                        >= datetime.utcnow() - timedelta(days=7),
                        Integer,
                    )
                ).label("new_7d"),
            )
            .group_by(EnhancedRecallDB.source_agency)
            .order_by(EnhancedRecallDB.source_agency)
            .all()
        )

        # Format agency data
        agencies = []
        for stat in agency_stats:
            agencies.append(
                {
                    "agency": stat.agency,
                    "total": stat.total,
                    "lastUpdated": stat.last_updated.isoformat()
                    if stat.last_updated
                    else None,
                    "new24h": stat.new_24h or 0,
                    "new7d": stat.new_7d or 0,
                    "staleness": "fresh"
                    if stat.new_24h > 0
                    else ("recent" if stat.new_7d > 0 else "stale"),
                }
            )

        # Get recent ingestion runs
        recent_runs = (
            db.query(IngestionRun)
            .filter(IngestionRun.finished_at >= datetime.utcnow() - timedelta(hours=24))
            .order_by(IngestionRun.finished_at.desc())
            .limit(5)
            .all()
        )

        recent_ingestions = [
            {
                "agency": run.agency,
                "mode": run.mode,
                "status": run.status,
                "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
                "itemsProcessed": run.total_items_processed,
            }
            for run in recent_runs
        ]

        # Check for running jobs
        running_jobs = IngestionRunner.get_running_jobs()

        return create_response(
            {
                "summary": {
                    "totalRecalls": total_recalls,
                    "lastUpdate": latest_update.isoformat() if latest_update else None,
                    "agencyCount": len(agencies),
                    "runningJobs": sum(1 for v in running_jobs.values() if v),
                },
                "agencies": agencies,
                "recentIngestions": recent_ingestions,
                "runningJobs": [k for k, v in running_jobs.items() if v],
            },
            request,
        )

    except Exception as e:
        logger.error(f"Freshness check failed: {e}")
        raise APIError(
            status_code=500,
            code="FRESHNESS_CHECK_FAILED",
            message="Failed to retrieve freshness data",
        )


@router.get("/stats")
async def admin_statistics(request: Request, db: Session = Depends(get_db)):
    """
    Get comprehensive admin statistics
    """
    try:
        # Database stats
        db_stats = {
            "recalls": db.query(func.count(EnhancedRecallDB.id)).scalar() or 0,
            "ingestion_runs": db.query(func.count(IngestionRun.id)).scalar() or 0,
        }

        # Ingestion stats (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)

        ingestion_stats = (
            db.query(
                func.count(IngestionRun.id).label("total"),
                func.sum(func.cast(IngestionRun.status == "success", Integer)).label(
                    "success"
                ),
                func.sum(func.cast(IngestionRun.status == "failed", Integer)).label(
                    "failed"
                ),
                func.avg(
                    func.extract(
                        "epoch", IngestionRun.finished_at - IngestionRun.started_at
                    )
                ).label("avg_duration"),
            )
            .filter(IngestionRun.created_at >= week_ago)
            .first()
        )

        return create_response(
            {
                "database": db_stats,
                "ingestion": {
                    "total": ingestion_stats.total or 0,
                    "success": ingestion_stats.success or 0,
                    "failed": ingestion_stats.failed or 0,
                    "avgDurationSeconds": round(ingestion_stats.avg_duration or 0, 2),
                },
            },
            request,
        )

    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        raise APIError(
            status_code=500,
            code="STATS_FAILED",
            message="Failed to retrieve statistics",
        )


# Export router
__all__ = ["router"]
