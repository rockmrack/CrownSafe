# agents/recall_data_agent/agent_logic.py
"""RecallDataAgent Core Business Logic
Handles both live queries (for safety check workflow) and background ingestion.
Version: 3.0 - Adapted for Crown Safe (Hair/Cosmetic Products)
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import or_

from core_infra.database import SessionLocal

# Import Crown Safe database components
from core_infra.enhanced_database_schema import EnhancedRecallDB

# Import connectors
from .connectors import ConnectorRegistry

# Import Crown Safe filtering configuration
from .crown_safe_config import is_crown_safe_recall

# Import Pydantic model
from .models import Recall


class RecallDataAgentLogic:
    """Core logic for RecallDataAgent.

    Responsibilities:
    1. Query recalls database for product matches (called by RouterAgent)
    2. Run background ingestion cycles from 39+ agencies
    3. Upsert recalls into EnhancedEnhancedRecallDB with deduplication
    """

    def __init__(self, agent_id: str, logger_instance: logging.Logger | None = None):
        """Initialize RecallDataAgent logic.

        Args:
            agent_id: Unique identifier for this agent instance
            logger_instance: Optional logger instance (creates one if not provided)
        """
        self.agent_id = agent_id
        self.logger = logger_instance or logging.getLogger(__name__)
        self.connector_registry = ConnectorRegistry()
        self.logger.info(
            f"RecallDataAgentLogic initialized as '{agent_id}' with "
            f"{len(self.connector_registry.connectors)} connectors.",
        )

    async def process_task(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Query database for recalls matching product identifiers.

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
            f"brand='{brand}', lot='{lot_number}'",
        )

        # Validate inputs
        if not any([product_name, model_number, upc, ean_code, gtin, lot_number, brand]):
            return {
                "status": "FAILED",
                "error": ("At least one product identifier is required (name, model, UPC, EAN, GTIN, lot, or brand)."),
            }

        try:
            # Create database session
            db = SessionLocal()

            try:
                # Build query with multiple identifier types
                query = db.query(EnhancedRecallDB)
                filters = []

                # Priority 1: Exact identifier matches (highest confidence)
                if model_number:
                    filters.append(EnhancedRecallDB.model_number.ilike(f"%{model_number}%"))

                if upc:
                    filters.append(EnhancedRecallDB.upc == upc)

                if ean_code:
                    filters.append(EnhancedRecallDB.ean_code == ean_code)

                if gtin:
                    filters.append(EnhancedRecallDB.gtin == gtin)

                if lot_number:
                    filters.append(EnhancedRecallDB.lot_number.ilike(f"%{lot_number}%"))

                # Priority 2: Brand + name matching (medium confidence)
                if brand and product_name:
                    filters.append(
                        (EnhancedRecallDB.brand.ilike(f"%{brand}%"))
                        & (EnhancedRecallDB.product_name.ilike(f"%{product_name}%")),
                    )

                # Priority 3: Product name fuzzy matching (lower confidence)
                if product_name and not filters:
                    filters.append(EnhancedRecallDB.product_name.ilike(f"%{product_name}%"))

                if brand and not filters:
                    filters.append(EnhancedRecallDB.brand.ilike(f"%{brand}%"))

                # Execute query with OR logic (any identifier match)
                if filters:
                    recalled_products = query.filter(or_(*filters)).all()
                else:
                    recalled_products = []

                self.logger.info(f"[{self.agent_id}] Found {len(recalled_products)} matching recalls")

                # Convert to dictionaries using Pydantic validation
                found_recalls = []
                for db_recall in recalled_products:
                    try:
                        # Convert SQLAlchemy model to Pydantic model
                        recall_obj = Recall.model_validate(db_recall)
                        recall_dict = recall_obj.model_dump()

                        # Filter for Crown Safe relevance (hair/cosmetic products only)
                        if is_crown_safe_recall(
                            recall_dict.get("title", ""),
                            recall_dict.get("description", ""),
                            recall_dict.get("product_category", ""),
                        ):
                            found_recalls.append(recall_dict)

                    except Exception as e:
                        self.logger.error(f"Error converting recall {db_recall.id}: {e}")
                        continue

                self.logger.info(f"[{self.agent_id}] Filtered to {len(found_recalls)} Crown Safe relevant recalls")

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

    async def run_ingestion_cycle(self) -> dict[str, Any]:
        """Run a full ingestion cycle from all enabled connectors.

        This method:
        1. Fetches recalls from all 39+ agencies concurrently
        2. Deduplicates based on recall_id
        3. Upserts into EnhancedEnhancedRecallDB (insert or update)
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

            self.logger.info(f"[{self.agent_id}] Fetched {len(all_recalls)} total recalls from all agencies")

            # Filter recalls for Crown Safe relevance (hair/cosmetic products only)
            crown_safe_recalls = []
            for recall_data in all_recalls:
                recall_dict = recall_data.model_dump()
                if is_crown_safe_recall(
                    recall_dict.get("title", ""),
                    recall_dict.get("description", ""),
                    recall_dict.get("product_category", ""),
                ):
                    crown_safe_recalls.append(recall_data)

            filtered_count = len(all_recalls) - len(crown_safe_recalls)
            self.logger.info(
                f"[{self.agent_id}] Filtered to {len(crown_safe_recalls)} Crown Safe relevant recalls "
                f"(excluded {filtered_count} non-hair/cosmetic products)",
            )

            if not crown_safe_recalls:
                self.logger.warning(f"[{self.agent_id}] No Crown Safe relevant recalls found after filtering.")
                return {
                    "status": "success",
                    "total_fetched": len(all_recalls),
                    "total_upserted": 0,
                    "total_skipped": 0,
                    "total_filtered": filtered_count,
                    "duration_seconds": (datetime.now() - start_time).total_seconds(),
                }

            # Upsert into database (only Crown Safe relevant recalls)
            db = SessionLocal()
            upserted_count = 0
            skipped_count = 0
            errors = []

            try:
                for recall_data in crown_safe_recalls:
                    try:
                        # Check if recall already exists
                        existing = (
                            db.query(EnhancedRecallDB)
                            .filter(EnhancedRecallDB.recall_id == recall_data.recall_id)
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
                            db_recall = EnhancedRecallDB(**recall_data.model_dump())
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
                f"Filtered: {filtered_count}, Duration: {duration:.2f}s",
            )

            return {
                "status": "success",
                "total_fetched": len(all_recalls),
                "total_crown_safe": len(crown_safe_recalls),
                "total_upserted": upserted_count,
                "total_skipped": skipped_count,
                "total_filtered": filtered_count,
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

    def get_statistics(self) -> dict[str, Any]:
        """Get recall database statistics.

        Returns:
            Dictionary with database stats (total recalls, by agency, etc.)
        """
        try:
            db = SessionLocal()

            try:
                total_recalls = db.query(EnhancedRecallDB).count()

                # Count by agency
                from sqlalchemy import func

                agency_counts = (
                    db.query(EnhancedRecallDB.source_agency, func.count(EnhancedRecallDB.id))
                    .group_by(EnhancedRecallDB.source_agency)
                    .all()
                )

                # List of available connectors (hardcoded for now)
                available_connectors = [
                    "CPSCConnector",
                    "FDAConnector",
                    "NHTSAConnector",
                    "USDA_FSIS_Connector",
                    "HealthCanadaConnector",
                    "CFIAConnector",
                    "TransportCanadaConnector",
                    "EU_RAPEX_Connector",
                    "UK_OPSS_Connector",
                    "UK_FSA_Connector",
                    "UK_TradingStandards_Connector",
                    "UK_DVSA_Connector",
                    "UK_MHRA_Connector",
                    "ACCCConnector",
                    "CommerceCommissionNZConnector",
                    "SG_CPSO_Connector",
                    "JapanMHLWConnector",
                    "ChinaSAMRConnector",
                    "SouthKoreaKCAConnector",
                    "ANMATConnector",
                    "ANVISAConnector",
                    "SENACONConnector",
                    "PROFECOConnector",
                    "UAEMOICCPDConnector",
                ]

                return {
                    "status": "success",
                    "total_recalls": total_recalls,
                    "by_agency": {agency: count for agency, count in agency_counts},
                    "total_connectors": len(available_connectors),
                    "connectors": available_connectors,
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
    product_name: str | None = None,
    model_number: str | None = None,
    upc: str | None = None,
    brand: str | None = None,
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
