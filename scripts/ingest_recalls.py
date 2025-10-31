#!/usr/bin/env python3
"""
BabyShield Recalls Data Ingestion Script

This script:
1. Runs Alembic migration to create recalls_enhanced table if needed
2. Fetches recall data from agencies and populates the table
3. Supports incremental updates and full refresh

Usage:
    python -m scripts.ingest_recalls --since 2023-01-01
    python -m scripts.ingest_recalls --full-refresh
    python -m scripts.ingest_recalls --agencies FDA,CPSC
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Optional

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import project modules

from alembic.config import Config
from sqlalchemy import text

from agents.recall_data_agent.connectors import (
    CPSCConnector,
    EURAPEXConnector,
    FDAConnector,
    NHTSAConnector,
)
from alembic import command
from core_infra.database import get_db_session

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class RecallDataIngester:
    """Handles fetching and ingesting recall data into the database"""

    def __init__(self):
        self.connectors = {
            "FDA": FDAConnector(),
            "CPSC": CPSCConnector(),
            "NHTSA": NHTSAConnector(),
            "EU_RAPEX": EURAPEXConnector(),
        }

    async def run_migration(self):
        """Run Alembic migration to create/update database schema"""
        try:
            logger.info("🔧 Running database migration...")

            # Run alembic upgrade
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")

            logger.info("✅ Database migration completed successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

    def check_table_exists(self) -> bool:
        """Check if recalls_enhanced table exists"""
        try:
            with get_db_session() as db:
                result = db.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'recalls_enhanced'
                    );
                """
                    )
                )
                return result.scalar()
        except Exception as e:
            logger.error(f"Error checking table existence: {e}")
            return False

    def get_table_count(self) -> int:
        """Get current number of records in recalls_enhanced table"""
        try:
            with get_db_session() as db:
                result = db.execute(text("SELECT COUNT(*) FROM recalls_enhanced"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Could not get table count: {e}")
            return 0

    async def fetch_agency_data(self, agency_name: str, since_date: Optional[date] = None) -> List[dict]:
        """Fetch recall data from a specific agency"""
        try:
            connector = self.connectors.get(agency_name)
            if not connector:
                logger.warning(f"No connector available for agency: {agency_name}")
                return []

            logger.info(f"📡 Fetching data from {agency_name}...")

            # Fetch recalls from the connector
            recalls = await connector.fetch_recent_recalls()

            # Filter by date if specified
            if since_date:
                recalls = [recall for recall in recalls if recall.recall_date and recall.recall_date >= since_date]

            logger.info(f"✅ Fetched {len(recalls)} recalls from {agency_name}")
            return recalls

        except Exception as e:
            logger.error(f"❌ Error fetching data from {agency_name}: {e}")
            return []

    def convert_recall_to_db_record(self, recall_data) -> dict:
        """Convert Recall object to database record dict"""
        try:
            # Build search keywords for full-text search
            search_keywords = " ".join(
                filter(
                    None,
                    [
                        getattr(recall_data, "product_name", ""),
                        getattr(recall_data, "brand", ""),
                        getattr(recall_data, "model_number", ""),
                        getattr(recall_data, "description", ""),
                        getattr(recall_data, "hazard", ""),
                    ],
                )
            )

            # Create database record
            record = {
                "recall_id": recall_data.recall_id,
                "source_agency": recall_data.source_agency,
                "product_name": recall_data.product_name,
                "brand": getattr(recall_data, "brand", None),
                "manufacturer": getattr(recall_data, "manufacturer", None),
                "model_number": getattr(recall_data, "model_number", None),
                "description": getattr(recall_data, "description", None),
                "upc": getattr(recall_data, "upc", None),
                "ean_code": getattr(recall_data, "ean_code", None),
                "gtin": getattr(recall_data, "gtin", None),
                "article_number": getattr(recall_data, "article_number", None),
                "lot_number": getattr(recall_data, "lot_number", None),
                "batch_number": getattr(recall_data, "batch_number", None),
                "serial_number": getattr(recall_data, "serial_number", None),
                "part_number": getattr(recall_data, "part_number", None),
                "expiry_date": getattr(recall_data, "expiry_date", None),
                "best_before_date": getattr(recall_data, "best_before_date", None),
                "production_date": getattr(recall_data, "production_date", None),
                "ndc_number": getattr(recall_data, "ndc_number", None),
                "din_number": getattr(recall_data, "din_number", None),
                "vehicle_make": getattr(recall_data, "vehicle_make", None),
                "vehicle_model": getattr(recall_data, "vehicle_model", None),
                "model_year": getattr(recall_data, "model_year", None),
                "vin_range": getattr(recall_data, "vin_range", None),
                "registry_codes": getattr(recall_data, "registry_codes", None),
                "country": getattr(recall_data, "country", None),
                "regions_affected": getattr(recall_data, "regions_affected", None),
                "recall_date": recall_data.recall_date,
                "hazard": getattr(recall_data, "hazard", None),
                "hazard_category": getattr(recall_data, "hazard_category", None),
                "recall_reason": getattr(recall_data, "recall_reason", None),
                "remedy": getattr(recall_data, "remedy", None),
                "recall_class": getattr(recall_data, "recall_class", None),
                "manufacturer_contact": getattr(recall_data, "manufacturer_contact", None),
                "url": getattr(recall_data, "url", None),
                "search_keywords": search_keywords.strip(),
                "status": "open",  # Default status
                "agency_specific_data": getattr(recall_data, "agency_specific_data", None),
            }

            return record

        except Exception as e:
            logger.error(f"Error converting recall to database record: {e}")
            return None

    def insert_recalls_batch(self, recalls: List[dict], agency_name: str) -> int:
        """Insert batch of recalls using optimized UPSERT"""
        from core_infra.upsert_handler import upsert_handler

        processed_count = 0

        try:
            with get_db_session() as db:
                # Prepare all records
                batch_records = []
                for recall in recalls:
                    db_record = self.convert_recall_to_db_record(recall)
                    if db_record:
                        batch_records.append(db_record)

                # Use bulk UPSERT for better performance
                if batch_records:
                    counts = upsert_handler.bulk_upsert_recalls(db, batch_records)
                    processed_count = counts["inserted"] + counts["updated"]
                    _ = counts["failed"]  # failed_count (reserved for logging)
                    logger.info(
                        f"📊 {agency_name}: {counts['inserted']} inserted, {counts['updated']} updated, {counts['failed']} failed"
                    )

        except Exception as e:
            logger.error(f"Batch insert failed for {agency_name}: {e}")

        return processed_count

    async def ingest_agency_data(self, agency_name: str, since_date: Optional[date] = None) -> int:
        """Ingest data from a specific agency"""
        try:
            # Fetch data from agency
            recalls = await self.fetch_agency_data(agency_name, since_date)

            if not recalls:
                logger.info(f"No data to ingest for {agency_name}")
                return 0

            # Insert into database
            count = self.insert_recalls_batch(recalls, agency_name)
            logger.info(f"✅ Successfully ingested {count} records for {agency_name}")
            return count

        except Exception as e:
            logger.error(f"❌ Failed to ingest data for {agency_name}: {e}")
            return 0

    async def run_full_ingestion(self, agencies: List[str], since_date: Optional[date] = None):
        """Run full data ingestion for specified agencies"""
        logger.info(f"🚀 Starting data ingestion for agencies: {', '.join(agencies)}")

        # Check/create table first
        if not self.check_table_exists():
            logger.info("Table doesn't exist, running migration...")
            if not await self.run_migration():
                logger.error("Migration failed, aborting ingestion")
                return False

        initial_count = self.get_table_count()
        logger.info(f"Initial table count: {initial_count}")

        total_ingested = 0

        # Process each agency
        for agency in agencies:
            if agency in self.connectors:
                count = await self.ingest_agency_data(agency, since_date)
                total_ingested += count
            else:
                logger.warning(f"Unknown agency: {agency}")

        final_count = self.get_table_count()
        logger.info(f"Final table count: {final_count}")
        logger.info(f"🎉 Ingestion complete! Total processed: {total_ingested}")

        return True


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="BabyShield Recalls Data Ingestion")
    parser.add_argument("--since", type=str, help="Fetch recalls since date (YYYY-MM-DD)")
    parser.add_argument("--agencies", type=str, help="Comma-separated list of agencies (default: all)")
    parser.add_argument("--full-refresh", action="store_true", help="Full refresh of all data")
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Only run migration, don't ingest data",
    )

    args = parser.parse_args()

    # Parse since date
    since_date = None
    if args.since:
        try:
            since_date = datetime.strptime(args.since, "%Y-%m-%d").date()
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD")
            return 1
    elif not args.full_refresh:
        # Default to last 12 months for incremental sync
        since_date = (datetime.now() - timedelta(days=365)).date()

    # Parse agencies
    if args.agencies:
        agencies = [a.strip() for a in args.agencies.split(",")]
    else:
        agencies = ["FDA", "CPSC", "NHTSA", "EU_RAPEX"]

    # Create ingester
    ingester = RecallDataIngester()

    # Run migration only if requested
    if args.migrate_only:
        success = await ingester.run_migration()
        return 0 if success else 1

    # Run full ingestion
    try:
        success = await ingester.run_full_ingestion(agencies, since_date)
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("Ingestion interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
