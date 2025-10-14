# agents/recall_data_agent/agent_logic.py
"""
RecallDataAgent Core Business Logic
Handles both live queries (for safety check workflow) and background ingestion.
Version: 2.0 - Adapted for BabyShield EnhancedRecallDB
"""

import logging
from typing import Dict, Optional, Any, List
import asyncio
from datetime import datetime

# Import Pydantic model
from .models import Recall

# Import BabyShield database components
from core_infra.database import SessionLocal, RecallDB
from sqlalchemy import or_

# Import connectors
from .connectors import ConnectorRegistry


class RecallDataAgentLogic:
    """
    Core logic for RecallDataAgent.

    Responsibilities:
    1. Query recalls database for product matches (called by RouterAgent)
    2. Run background ingestion cycles from 39+ agencies
    3. Upsert recalls into EnhancedRecallDB with deduplication
    """

    def __init__(self, agent_id: str, logger_instance: Optional[logging.Logger] = None):
        """
        Initialize RecallDataAgent logic.

        Args:
            agent_id: Unique identifier for this agent instance
            logger_instance: Optional logger instance (creates one if not provided)
        """
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        self.connector_registry = ConnectorRegistry()
        self.logger.info(
            f"RecallDataAgentLogic initialized as '{agent_id}' with "
            f"{len(self.connector_registry.connectors)} connectors."
        )

    async def process_task(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query database for recalls matching product identifiers.

        This is the main entry point called by RouterAgent during safety check workflow.
        Supports multiple identifier types for comprehensive matching.

        Args:
            inputs: Dictionary containing product identifiers:
                - product_name (str): Product name for fuzzy matching
                - model_number (str): Exact model number
                - upc (str): UPC barcode
                - ean_code (str): EAN barcode
                - gtin (str): GTIN barcode
                - lot_number (str): Lot/batch number
                - brand (str): Brand name

        Returns:
            Dictionary with:
                - status: "COMPLETED" or "FAILED"
                - result: {recalls_found: int, recalls: List[dict]}
                - error: Optional error message
        """
        product_name = inputs.get("product_name")
        model_number = inputs.get("model_number")
        upc = inputs.get("upc")
        ean_code = inputs.get("ean_code")
        gtin = inputs.get("gtin")
        lot_number = inputs.get("lot_number")
        brand = inputs.get("brand")

        self.logger.info(
            f"[{self.agent_id}] Querying recalls database with: "
            f"name='{product_name}', model='{model_number}', upc='{upc}', "
            f"brand='{brand}', lot='{lot_number}'"
        )

        # Validate inputs
        if not any([product_name, model_number, upc, ean_code, gtin, lot_number, brand]):
            return {
                "status": "FAILED",
                "error": "At least one product identifier is required (name, model, UPC, EAN, GTIN, lot, or brand).",
            }

        try:
            # Create database session
            db = SessionLocal()

            try:
                # Build query with multiple identifier types
                query = db.query(RecallDB)
                filters = []

                # Priority 1: Exact identifier matches (highest confidence)
                if model_number:
                    filters.append(RecallDB.model_number.ilike(f"%{model_number}%"))

                if upc:
                    filters.append(RecallDB.upc == upc)

                if ean_code:
                    filters.append(RecallDB.ean_code == ean_code)

                if gtin:
                    filters.append(RecallDB.gtin == gtin)

                if lot_number:
                    filters.append(RecallDB.lot_number.ilike(f"%{lot_number}%"))

                # Priority 2: Brand + name matching (medium confidence)
                if brand and product_name:
                    filters.append(
                        (RecallDB.brand.ilike(f"%{brand}%"))
                        & (RecallDB.product_name.ilike(f"%{product_name}%"))
                    )

                # Priority 3: Product name fuzzy matching (lower confidence)
                if product_name and not filters:
                    filters.append(RecallDB.product_name.ilike(f"%{product_name}%"))

                if brand and not filters:
                    filters.append(RecallDB.brand.ilike(f"%{brand}%"))

                # Execute query with OR logic (any identifier match)
                if filters:
                    recalled_products = query.filter(or_(*filters)).all()
                else:
                    recalled_products = []

                self.logger.info(
                    f"[{self.agent_id}] Found {len(recalled_products)} matching recalls"
                )

                # Convert to dictionaries using Pydantic validation
                found_recalls = []
                for db_recall in recalled_products:
                    try:
                        # Convert SQLAlchemy model to Pydantic model
                        recall_obj = Recall.model_validate(db_recall)
                        found_recalls.append(recall_obj.model_dump())
                    except Exception as e:
                        self.logger.error(f"Error converting recall {db_recall.id}: {e}")
                        continue

                return {
                    "status": "COMPLETED",
                    "result": {
                        "recalls_found": len(found_recalls),
                        "recalls": found_recalls,
                    },
                }

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"[{self.agent_id}] Database query failed: {e}", exc_info=True)
            return {"status": "FAILED", "error": f"Database query failed: {str(e)}"}

    async def run_ingestion_cycle(self) -> Dict[str, Any]:
        """
        Run a full ingestion cycle from all enabled connectors.

        This method:
        1. Fetches recalls from all 39+ agencies concurrently
        2. Deduplicates based on recall_id
        3. Upserts into EnhancedRecallDB (insert or update)
        4. Returns statistics

        Returns:
            Dictionary with:
                - status: "success" or "error"
                - total_fetched: Total recalls fetched from all agencies
                - total_upserted: Number of new/updated records
                - total_skipped: Number of duplicates skipped
                - duration_seconds: Time taken
                - errors: List of any errors encountered
        """
        start_time = datetime.now()
        self.logger.info(f"[{self.agent_id}] Starting new ingestion cycle...")

        try:
            # Fetch from all connectors concurrently
            all_recalls = await self.connector_registry.fetch_all_recalls()

            if not all_recalls:
                self.logger.warning(f"[{self.agent_id}] No new recalls found in this cycle.")
                return {
                    "status": "success",
                    "total_fetched": 0,
                    "total_upserted": 0,
                    "total_skipped": 0,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                }

            self.logger.info(
                f"[{self.agent_id}] Fetched {len(all_recalls)} total recalls from all agencies"
            )

            # Upsert into database
            db = SessionLocal()
            upserted_count = 0
            skipped_count = 0
            errors = []

            try:
                for recall_data in all_recalls:
                    try:
                        # Check if recall already exists
                        existing = (
                            db.query(RecallDB)
                            .filter(RecallDB.recall_id == recall_data.recall_id)
                            .first()
                        )

                        if existing:
                            # Update existing record
                            for key, value in recall_data.model_dump().items():
                                if value is not None:  # Only update non-null values
                                    setattr(existing, key, value)
                            skipped_count += 1
                        else:
                            # Insert new record
                            db_recall = RecallDB(**recall_data.model_dump())
                            db.add(db_recall)
                            upserted_count += 1

                        # Commit in batches of 100 for performance
                        if (upserted_count + skipped_count) % 100 == 0:
                            db.commit()

                    except Exception as e:
                        error_msg = f"Error upserting recall {recall_data.recall_id}: {e}"
                        self.logger.error(error_msg)
                        errors.append(error_msg)
                        db.rollback()

                # Final commit
                db.commit()

            finally:
                db.close()

            duration = (datetime.now() - start_time).total_seconds()

            self.logger.info(
                f"[{self.agent_id}] Ingestion complete. "
                f"Upserted: {upserted_count}, Skipped: {skipped_count}, "
                f"Duration: {duration:.2f}s"
            )

            return {
                "status": "success",
                "total_fetched": len(all_recalls),
                "total_upserted": upserted_count,
                "total_skipped": skipped_count,
                "duration_seconds": duration,
                "errors": errors if errors else None,
            }

        except Exception as e:
            error_msg = f"Ingestion cycle failed: {str(e)}"
            self.logger.error(f"[{self.agent_id}] {error_msg}", exc_info=True)
            return {
                "status": "error",
                "error": error_msg,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get recall database statistics.

        Returns:
            Dictionary with database stats (total recalls, by agency, etc.)
        """
        try:
            db = SessionLocal()

            try:
                total_recalls = db.query(RecallDB).count()

                # Count by agency
                from sqlalchemy import func

                agency_counts = (
                    db.query(RecallDB.source_agency, func.count(RecallDB.id))
                    .group_by(RecallDB.source_agency)
                    .all()
                )

                return {
                    "status": "success",
                    "total_recalls": total_recalls,
                    "by_agency": {agency: count for agency, count in agency_counts},
                }

            finally:
                db.close()

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}


# ================================
# 🧪 TESTING UTILITIES
# ================================


async def test_query(
    product_name: str = None,
    model_number: str = None,
    upc: str = None,
    brand: str = None,
):
    """Test the query functionality"""
    agent = RecallDataAgentLogic(agent_id="test_agent")

    inputs = {}
    if product_name:
        inputs["product_name"] = product_name
    if model_number:
        inputs["model_number"] = model_number
    if upc:
        inputs["upc"] = upc
    if brand:
        inputs["brand"] = brand

    result = await agent.process_task(inputs)
    print(f"Query result: {result}")
    return result


async def test_ingestion():
    """Test the ingestion functionality"""
    agent = RecallDataAgentLogic(agent_id="test_ingestor")
    result = await agent.run_ingestion_cycle()
    print(f"Ingestion result: {result}")
    return result


if __name__ == "__main__":
    # Example usage
    print("RecallDataAgent Logic Module")
    print("Import this module to use RecallDataAgentLogic class")
