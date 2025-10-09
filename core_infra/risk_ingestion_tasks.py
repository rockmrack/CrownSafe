"""
Celery tasks for Risk Assessment data ingestion and processing
Orchestrates data collection from multiple sources
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from celery import Celery, group, chain
from celery.schedules import crontab
import asyncio

from sqlalchemy.orm import Session
from core_infra.database import SessionLocal
from core_infra.risk_assessment_models import (
    ProductGoldenRecord,
    ProductRiskProfile,
    SafetyIncident,
    CompanyComplianceProfile,
    DataIngestionJob,
    ProductDataSource,
    DataSource,
)
from core_infra.safety_data_connectors import (
    CPSCDataConnector,
    EUSafetyGateConnector,
    CommercialDatabaseConnector,
    DataUnificationEngine,
    SafetyDataRecord,
)
from core_infra.risk_scoring_engine import RiskScoringEngine
from core_infra.barcode_scanner import BarcodeScanner

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    "risk_assessment",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/1"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/1"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Schedule periodic tasks
celery_app.conf.beat_schedule = {
    "daily-cpsc-sync": {
        "task": "risk_ingestion_tasks.sync_cpsc_data",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
        "args": (),
    },
    "weekly-eu-sync": {
        "task": "risk_ingestion_tasks.sync_eu_safety_gate",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),  # Monday 3 AM
        "args": (),
    },
    "hourly-risk-recalc": {
        "task": "risk_ingestion_tasks.recalculate_high_risk_scores",
        "schedule": crontab(minute=0),  # Every hour
        "args": (),
    },
    "daily-company-compliance": {
        "task": "risk_ingestion_tasks.update_company_compliance",
        "schedule": crontab(hour=4, minute=0),  # 4 AM daily
        "args": (),
    },
}


@celery_app.task(name="risk_ingestion_tasks.sync_cpsc_data")
def sync_cpsc_data(days_back: int = 7, job_id: Optional[str] = None):
    """
    Sync data from CPSC sources
    """
    logger.info(f"Starting CPSC sync for last {days_back} days")

    db = SessionLocal()
    try:
        # Create or update job record
        if not job_id:
            job = DataIngestionJob(
                source_type=DataSource.CPSC_RECALL.value,
                job_type="incremental",
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(job)
            db.commit()
            job_id = job.id
        else:
            job = db.query(DataIngestionJob).filter_by(id=job_id).first()
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        # Initialize connector
        connector = CPSCDataConnector()

        # Fetch recalls
        start_date = datetime.utcnow() - timedelta(days=days_back)

        # Run async code in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        records = loop.run_until_complete(connector.fetch_recalls(start_date=start_date))

        job.records_fetched = len(records)

        # Process each record
        processed = 0
        created = 0
        updated = 0

        unification_engine = DataUnificationEngine()

        for record in records:
            # Find or create product
            product = _find_or_create_product_from_record(record, db)

            if product:
                # Add safety incident
                incident = _create_incident_from_record(record, product.id, db)

                # Update product data source
                _update_product_data_source(product.id, record, db)

                processed += 1
                if incident:
                    created += 1
                else:
                    updated += 1

        # Update job stats
        job.records_processed = processed
        job.records_created = created
        job.records_updated = updated
        job.status = "completed"
        job.completed_at = datetime.utcnow()

        db.commit()

        logger.info(f"CPSC sync completed: {processed} records processed")

        # Trigger risk recalculation for affected products
        recalculate_affected_products.delay(days_back)

        return {
            "job_id": job_id,
            "status": "completed",
            "records_processed": processed,
            "records_created": created,
            "records_updated": updated,
        }

    except Exception as e:
        logger.error(f"CPSC sync failed: {e}")
        if job_id:
            job = db.query(DataIngestionJob).filter_by(id=job_id).first()
            if job:
                job.status = "failed"
                job.errors = [str(e)]
                db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="risk_ingestion_tasks.sync_eu_safety_gate")
def sync_eu_safety_gate(days_back: int = 30):
    """
    Sync data from EU Safety Gate
    """
    logger.info(f"Starting EU Safety Gate sync for last {days_back} days")

    db = SessionLocal()
    try:
        # Create job record
        job = DataIngestionJob(
            source_type=DataSource.EU_SAFETY_GATE.value,
            job_type="incremental",
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()

        # Initialize connector
        connector = EUSafetyGateConnector()

        # Fetch alerts
        start_date = datetime.utcnow() - timedelta(days=days_back)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        records = loop.run_until_complete(connector.fetch_alerts(start_date=start_date))

        job.records_fetched = len(records)

        # Process records
        processed = 0
        for record in records:
            product = _find_or_create_product_from_record(record, db)
            if product:
                _create_incident_from_record(record, product.id, db)
                _update_product_data_source(product.id, record, db)
                processed += 1

        job.records_processed = processed
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"EU Safety Gate sync completed: {processed} records")

        return {"status": "completed", "records_processed": processed}

    except Exception as e:
        logger.error(f"EU sync failed: {e}")
        job.status = "failed"
        job.errors = [str(e)]
        db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="risk_ingestion_tasks.recalculate_affected_products")
def recalculate_affected_products(days_back: int = 7):
    """
    Recalculate risk scores for recently updated products
    """
    logger.info(f"Recalculating risk scores for products updated in last {days_back} days")

    db = SessionLocal()
    risk_engine = RiskScoringEngine()

    try:
        # Find products with recent incidents
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        recent_products = (
            db.query(ProductGoldenRecord)
            .join(SafetyIncident)
            .filter(SafetyIncident.created_at >= cutoff_date)
            .distinct()
            .all()
        )

        updated_count = 0

        for product in recent_products:
            # Get incidents
            incidents = (
                db.query(SafetyIncident).filter(SafetyIncident.product_id == product.id).all()
            )

            # Get company profile
            company_profile = None
            if product.manufacturer:
                company_profile = (
                    db.query(CompanyComplianceProfile)
                    .filter(CompanyComplianceProfile.company_name == product.manufacturer)
                    .first()
                )

            # Calculate risk score
            risk_components = risk_engine.calculate_risk_score(
                product, incidents, company_profile, db
            )

            # Update or create risk profile
            risk_profile = (
                db.query(ProductRiskProfile)
                .filter(ProductRiskProfile.product_id == product.id)
                .first()
            )

            if not risk_profile:
                risk_profile = ProductRiskProfile(product_id=product.id)
                db.add(risk_profile)

            # Update scores
            risk_profile.risk_score = risk_components.total_score
            risk_profile.risk_level = risk_components.risk_level
            risk_profile.severity_score = risk_components.severity_score
            risk_profile.recency_score = risk_components.recency_score
            risk_profile.volume_score = risk_components.volume_score
            risk_profile.violation_score = risk_components.violation_score
            risk_profile.compliance_score = risk_components.compliance_score
            risk_profile.last_calculated = datetime.utcnow()

            # Update trend
            if risk_profile.trend_data:
                historical = risk_profile.trend_data
            else:
                historical = []

            historical.append(
                {
                    "date": datetime.utcnow().isoformat(),
                    "score": risk_components.total_score,
                }
            )

            # Keep last 90 days of history
            cutoff = datetime.utcnow() - timedelta(days=90)
            historical = [h for h in historical if datetime.fromisoformat(h["date"]) > cutoff]

            risk_profile.trend_data = historical
            risk_profile.risk_trend = risk_engine.calculate_trend(
                [(datetime.fromisoformat(h["date"]), h["score"]) for h in historical]
            )

            # Check if needs review
            if risk_components.total_score >= 75 or risk_components.confidence < 0.5:
                risk_profile.requires_review = True
                risk_profile.review_reason = "High risk score or low confidence"

            updated_count += 1

        db.commit()

        logger.info(f"Updated risk scores for {updated_count} products")

        return {"products_updated": updated_count}

    except Exception as e:
        logger.error(f"Risk recalculation failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="risk_ingestion_tasks.recalculate_high_risk_scores")
def recalculate_high_risk_scores():
    """
    Hourly recalculation of high-risk products
    """
    logger.info("Recalculating high-risk product scores")

    db = SessionLocal()
    risk_engine = RiskScoringEngine()

    try:
        # Find high-risk products
        high_risk_profiles = (
            db.query(ProductRiskProfile)
            .filter(ProductRiskProfile.risk_level.in_(["high", "critical"]))
            .all()
        )

        updated = 0
        alerts = []

        for profile in high_risk_profiles:
            product = profile.product

            # Get latest incidents
            incidents = (
                db.query(SafetyIncident).filter(SafetyIncident.product_id == product.id).all()
            )

            # Get company profile
            company_profile = None
            if product.manufacturer:
                company_profile = (
                    db.query(CompanyComplianceProfile)
                    .filter(CompanyComplianceProfile.company_name == product.manufacturer)
                    .first()
                )

            # Recalculate
            risk_components = risk_engine.calculate_risk_score(
                product, incidents, company_profile, db
            )

            # Check for significant changes
            old_score = profile.risk_score
            new_score = risk_components.total_score

            if abs(new_score - old_score) > 10:
                alerts.append(
                    {
                        "product": product.product_name,
                        "old_score": old_score,
                        "new_score": new_score,
                        "change": new_score - old_score,
                    }
                )

            # Update profile
            profile.risk_score = new_score
            profile.risk_level = risk_components.risk_level
            profile.last_calculated = datetime.utcnow()

            updated += 1

        db.commit()

        # Send alerts if significant changes
        if alerts:
            send_risk_alerts.delay(alerts)

        logger.info(f"Updated {updated} high-risk products")

        return {"updated": updated, "alerts": len(alerts)}

    except Exception as e:
        logger.error(f"High-risk recalculation failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="risk_ingestion_tasks.update_company_compliance")
def update_company_compliance():
    """
    Update company compliance profiles daily
    """
    logger.info("Updating company compliance profiles")

    db = SessionLocal()

    try:
        # Get all unique manufacturers
        manufacturers = db.query(ProductGoldenRecord.manufacturer).distinct().all()

        updated = 0

        for (manufacturer,) in manufacturers:
            if not manufacturer:
                continue

            # Get or create company profile
            profile = (
                db.query(CompanyComplianceProfile)
                .filter(CompanyComplianceProfile.company_name == manufacturer)
                .first()
            )

            if not profile:
                profile = CompanyComplianceProfile(company_name=manufacturer)
                db.add(profile)

            # Calculate metrics
            # Count recalls (products with incidents)
            recall_count = (
                db.query(ProductGoldenRecord)
                .filter(ProductGoldenRecord.manufacturer == manufacturer)
                .join(SafetyIncident)
                .distinct()
                .count()
            )

            profile.total_recalls = recall_count

            # Recent recalls (last 12 months)
            cutoff = datetime.utcnow() - timedelta(days=365)
            recent_recalls = (
                db.query(ProductGoldenRecord)
                .filter(ProductGoldenRecord.manufacturer == manufacturer)
                .join(SafetyIncident)
                .filter(SafetyIncident.created_at >= cutoff)
                .distinct()
                .count()
            )

            profile.recent_recalls = recent_recalls

            # Determine if repeat offender
            profile.repeat_offender = recall_count > 3

            # Calculate compliance score (100 = best, 0 = worst)
            base_score = 100
            base_score -= recall_count * 10
            base_score -= recent_recalls * 5
            profile.compliance_score = max(0, base_score)

            # Determine trend
            if recent_recalls > profile.recent_recalls:
                profile.compliance_trend = "declining"
            elif recent_recalls < profile.recent_recalls:
                profile.compliance_trend = "improving"
            else:
                profile.compliance_trend = "stable"

            profile.last_updated = datetime.utcnow()

            updated += 1

        db.commit()

        logger.info(f"Updated {updated} company profiles")

        return {"companies_updated": updated}

    except Exception as e:
        logger.error(f"Company compliance update failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="risk_ingestion_tasks.send_risk_alerts")
def send_risk_alerts(alerts: List[Dict]):
    """
    Send alerts for significant risk changes
    """
    logger.info(f"Sending {len(alerts)} risk alerts")

    # In production, this would send emails/notifications
    # For now, just log them
    for alert in alerts:
        logger.warning(
            f"RISK ALERT: {alert['product']} changed from "
            f"{alert['old_score']:.1f} to {alert['new_score']:.1f} "
            f"(change: {alert['change']:+.1f})"
        )

    return {"alerts_sent": len(alerts)}


@celery_app.task(name="risk_ingestion_tasks.enrich_product_from_barcode")
def enrich_product_from_barcode(product_id: str, barcode: str):
    """
    Enrich product data using barcode (integrates with Phase 1)
    """
    logger.info(f"Enriching product {product_id} with barcode {barcode}")

    db = SessionLocal()

    try:
        product = db.query(ProductGoldenRecord).filter_by(id=product_id).first()

        if not product:
            return {"error": "Product not found"}

        # Use barcode scanner from Phase 1
        scanner = BarcodeScanner()
        scan_result = scanner.scan_text(barcode)

        if scan_result.codes:
            code_data = scan_result.codes[0]

            # Update product with extracted data
            if code_data.get("gtin") and not product.gtin:
                product.gtin = code_data["gtin"]

            if code_data.get("lot_number"):
                lots = product.lot_numbers or []
                if code_data["lot_number"] not in lots:
                    lots.append(code_data["lot_number"])
                    product.lot_numbers = lots

            if code_data.get("expiry_date"):
                product.manufacturing_date_range = {"expiry": code_data["expiry_date"]}

            db.commit()

            return {"status": "enriched", "data": code_data}

        return {"status": "no_data_found"}

    except Exception as e:
        logger.error(f"Barcode enrichment failed: {e}")
        raise
    finally:
        db.close()


# Helper functions
def _find_or_create_product_from_record(
    record: SafetyDataRecord, db: Session
) -> Optional[ProductGoldenRecord]:
    """
    Find or create product from safety data record
    """
    # Try to find by identifiers
    product = None

    if record.gtin:
        product = db.query(ProductGoldenRecord).filter_by(gtin=record.gtin).first()

    if not product and record.upc:
        product = db.query(ProductGoldenRecord).filter_by(upc=record.upc).first()

    if not product and record.product_name:
        # Try fuzzy match
        product = (
            db.query(ProductGoldenRecord)
            .filter(ProductGoldenRecord.product_name.ilike(f"%{record.product_name}%"))
            .first()
        )

    # Create if not found
    if not product:
        product = ProductGoldenRecord(
            product_name=record.product_name,
            brand=record.brand,
            manufacturer=record.manufacturer,
            model_number=record.model_number,
            upc=record.upc,
            gtin=record.gtin,
            confidence_score=0.7,
        )
        db.add(product)
        db.commit()

    return product


def _create_incident_from_record(
    record: SafetyDataRecord, product_id: str, db: Session
) -> Optional[SafetyIncident]:
    """
    Create safety incident from record
    """
    # Check if incident already exists
    existing = (
        db.query(SafetyIncident)
        .filter_by(product_id=product_id, source=record.source, source_id=record.source_id)
        .first()
    )

    if existing:
        return None

    incident = SafetyIncident(
        product_id=product_id,
        incident_date=record.recall_date,
        report_date=record.recall_date,
        source=record.source,
        source_id=record.source_id,
        hazard_type=record.hazard_type,
        severity=record.severity,
        narrative=record.hazard_description,
        created_at=datetime.utcnow(),
    )

    db.add(incident)
    db.commit()

    return incident


def _update_product_data_source(product_id: str, record: SafetyDataRecord, db: Session):
    """
    Update product data source record
    """
    # Check if source exists
    existing = (
        db.query(ProductDataSource)
        .filter_by(product_id=product_id, source_type=record.source, source_id=record.source_id)
        .first()
    )

    if not existing:
        source = ProductDataSource(
            product_id=product_id,
            source_type=record.source,
            source_name=record.source,
            source_id=record.source_id,
            source_url=record.url,
            raw_data=record.raw_data,
            fetched_at=datetime.utcnow(),
        )
        db.add(source)
        db.commit()
