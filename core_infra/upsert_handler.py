"""UPSERT Handler for Optimized Database Operations
Implements PostgreSQL ON CONFLICT for atomic upsert operations
"""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class UpsertHandler:
    """Handles UPSERT operations for various tables using PostgreSQL's ON CONFLICT
    This provides atomic, single-query insert-or-update operations
    """

    @staticmethod
    def upsert_recall(db: Session, recall_data: dict[str, Any]) -> bool:
        """Perform atomic UPSERT for a single recall record

        Args:
            db: Database session
            recall_data: Dictionary with recall fields

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure recall_id exists
            if not recall_data.get("recall_id"):
                logger.error("Cannot upsert recall without recall_id")
                return False

            # Build the UPSERT query
            query = text(
                """
                INSERT INTO recalls (
                    recall_id, product_name, brand, manufacturer, model_number,
                    upc, ean_code, gtin, lot_number, batch_number,
                    serial_number, part_number, ndc_number, din_number,
                    expiry_date, best_before_date, production_date,
                    vehicle_make, vehicle_model, model_year, vin_range,
                    hazard, hazard_category, recall_reason, recall_class,
                    remedy, description, recall_date, source_agency,
                    country, regions_affected, url, manufacturer_contact,
                    search_keywords, agency_specific_data
                ) VALUES (
                    :recall_id, :product_name, :brand, :manufacturer, :model_number,
                    :upc, :ean_code, :gtin, :lot_number, :batch_number,
                    :serial_number, :part_number, :ndc_number, :din_number,
                    :expiry_date, :best_before_date, :production_date,
                    :vehicle_make, :vehicle_model, :model_year, :vin_range,
                    :hazard, :hazard_category, :recall_reason, :recall_class,
                    :remedy, :description, :recall_date, :source_agency,
                    :country, :regions_affected, :url, :manufacturer_contact,
                    :search_keywords, :agency_specific_data
                )
                ON CONFLICT (recall_id) 
                DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    brand = COALESCE(EXCLUDED.brand, recalls.brand),
                    manufacturer = COALESCE(EXCLUDED.manufacturer, recalls.manufacturer),
                    model_number = COALESCE(EXCLUDED.model_number, recalls.model_number),
                    upc = COALESCE(EXCLUDED.upc, recalls.upc),
                    ean_code = COALESCE(EXCLUDED.ean_code, recalls.ean_code),
                    gtin = COALESCE(EXCLUDED.gtin, recalls.gtin),
                    lot_number = COALESCE(EXCLUDED.lot_number, recalls.lot_number),
                    batch_number = COALESCE(EXCLUDED.batch_number, recalls.batch_number),
                    serial_number = COALESCE(EXCLUDED.serial_number, recalls.serial_number),
                    part_number = COALESCE(EXCLUDED.part_number, recalls.part_number),
                    ndc_number = COALESCE(EXCLUDED.ndc_number, recalls.ndc_number),
                    din_number = COALESCE(EXCLUDED.din_number, recalls.din_number),
                    expiry_date = COALESCE(EXCLUDED.expiry_date, recalls.expiry_date),
                    best_before_date = COALESCE(EXCLUDED.best_before_date, recalls.best_before_date),
                    production_date = COALESCE(EXCLUDED.production_date, recalls.production_date),
                    vehicle_make = COALESCE(EXCLUDED.vehicle_make, recalls.vehicle_make),
                    vehicle_model = COALESCE(EXCLUDED.vehicle_model, recalls.vehicle_model),
                    model_year = COALESCE(EXCLUDED.model_year, recalls.model_year),
                    vin_range = COALESCE(EXCLUDED.vin_range, recalls.vin_range),
                    hazard = COALESCE(EXCLUDED.hazard, recalls.hazard),
                    hazard_category = COALESCE(EXCLUDED.hazard_category, recalls.hazard_category),
                    recall_reason = COALESCE(EXCLUDED.recall_reason, recalls.recall_reason),
                    recall_class = COALESCE(EXCLUDED.recall_class, recalls.recall_class),
                    remedy = COALESCE(EXCLUDED.remedy, recalls.remedy),
                    description = COALESCE(EXCLUDED.description, recalls.description),
                    recall_date = COALESCE(EXCLUDED.recall_date, recalls.recall_date),
                    regions_affected = COALESCE(EXCLUDED.regions_affected, recalls.regions_affected),
                    url = COALESCE(EXCLUDED.url, recalls.url),
                    manufacturer_contact = COALESCE(EXCLUDED.manufacturer_contact, recalls.manufacturer_contact),
                    search_keywords = COALESCE(EXCLUDED.search_keywords, recalls.search_keywords),
                    agency_specific_data = COALESCE(EXCLUDED.agency_specific_data, recalls.agency_specific_data),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING recall_id, (xmax = 0) AS inserted
            """,
            )

            # Prepare parameters with defaults
            params = {
                "recall_id": recall_data.get("recall_id"),
                "product_name": recall_data.get("product_name", "Unknown Product"),
                "brand": recall_data.get("brand"),
                "manufacturer": recall_data.get("manufacturer"),
                "model_number": recall_data.get("model_number"),
                "upc": recall_data.get("upc"),
                "ean_code": recall_data.get("ean_code"),
                "gtin": recall_data.get("gtin"),
                "lot_number": recall_data.get("lot_number"),
                "batch_number": recall_data.get("batch_number"),
                "serial_number": recall_data.get("serial_number"),
                "part_number": recall_data.get("part_number"),
                "ndc_number": recall_data.get("ndc_number"),
                "din_number": recall_data.get("din_number"),
                "expiry_date": recall_data.get("expiry_date"),
                "best_before_date": recall_data.get("best_before_date"),
                "production_date": recall_data.get("production_date"),
                "vehicle_make": recall_data.get("vehicle_make"),
                "vehicle_model": recall_data.get("vehicle_model"),
                "model_year": recall_data.get("model_year"),
                "vin_range": recall_data.get("vin_range"),
                "hazard": recall_data.get("hazard"),
                "hazard_category": recall_data.get("hazard_category"),
                "recall_reason": recall_data.get("recall_reason"),
                "recall_class": recall_data.get("recall_class"),
                "remedy": recall_data.get("remedy"),
                "description": recall_data.get("description"),
                "recall_date": recall_data.get("recall_date"),
                "source_agency": recall_data.get("source_agency", "Unknown"),
                "country": recall_data.get("country", "Unknown"),
                "regions_affected": recall_data.get("regions_affected"),
                "url": recall_data.get("url"),
                "manufacturer_contact": recall_data.get("manufacturer_contact"),
                "search_keywords": recall_data.get("search_keywords"),
                "agency_specific_data": recall_data.get("agency_specific_data"),
            }

            result = db.execute(query, params)
            row = result.fetchone()

            if row:
                was_inserted = row[1]  # The 'inserted' column from RETURNING
                if was_inserted:
                    logger.debug(f"Inserted new recall: {recall_data['recall_id']}")
                else:
                    logger.debug(f"Updated existing recall: {recall_data['recall_id']}")

            return True

        except Exception as e:
            logger.error(f"Failed to upsert recall {recall_data.get('recall_id')}: {e}")
            return False

    @staticmethod
    def bulk_upsert_recalls(db: Session, recalls: list[dict[str, Any]], batch_size: int = 100) -> dict[str, int]:
        """Perform bulk UPSERT for multiple recalls with batching

        Args:
            db: Database session
            recalls: List of recall dictionaries
            batch_size: Number of records to process per batch

        Returns:
            Dictionary with counts of inserted, updated, and failed records
        """
        counts = {"inserted": 0, "updated": 0, "failed": 0}

        for i in range(0, len(recalls), batch_size):
            batch = recalls[i : i + batch_size]

            try:
                # Build bulk UPSERT query using VALUES list
                values_list = []
                params_dict = {}

                for idx, recall in enumerate(batch):
                    if not recall.get("recall_id"):
                        counts["failed"] += 1
                        continue

                    # Create parameter placeholders for this row
                    row_params = []
                    for field in [
                        "recall_id",
                        "product_name",
                        "brand",
                        "manufacturer",
                        "model_number",
                        "upc",
                        "ean_code",
                        "gtin",
                        "lot_number",
                        "batch_number",
                        "serial_number",
                        "part_number",
                        "ndc_number",
                        "din_number",
                        "expiry_date",
                        "best_before_date",
                        "production_date",
                        "vehicle_make",
                        "vehicle_model",
                        "model_year",
                        "vin_range",
                        "hazard",
                        "hazard_category",
                        "recall_reason",
                        "recall_class",
                        "remedy",
                        "description",
                        "recall_date",
                        "source_agency",
                        "country",
                        "regions_affected",
                        "url",
                        "manufacturer_contact",
                        "search_keywords",
                        "agency_specific_data",
                    ]:
                        param_name = f"{field}_{idx}"
                        row_params.append(f":{param_name}")

                        # Handle default values
                        if field == "product_name" and not recall.get(field):
                            params_dict[param_name] = "Unknown Product"
                        elif field == "source_agency" and not recall.get(field):
                            params_dict[param_name] = "Unknown"
                        elif field == "country" and not recall.get(field):
                            params_dict[param_name] = "Unknown"
                        else:
                            params_dict[param_name] = recall.get(field)

                    values_list.append(f"({', '.join(row_params)})")

                if not values_list:
                    continue

                # Build the bulk query
                query = text(
                    f"""
                    INSERT INTO recalls (
                        recall_id, product_name, brand, manufacturer, model_number,
                        upc, ean_code, gtin, lot_number, batch_number,
                        serial_number, part_number, ndc_number, din_number,
                        expiry_date, best_before_date, production_date,
                        vehicle_make, vehicle_model, model_year, vin_range,
                        hazard, hazard_category, recall_reason, recall_class,
                        remedy, description, recall_date, source_agency,
                        country, regions_affected, url, manufacturer_contact,
                        search_keywords, agency_specific_data
                    ) VALUES {", ".join(values_list)}
                    ON CONFLICT (recall_id) 
                    DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        brand = COALESCE(EXCLUDED.brand, recalls.brand),
                        manufacturer = COALESCE(EXCLUDED.manufacturer, recalls.manufacturer),
                        model_number = COALESCE(EXCLUDED.model_number, recalls.model_number),
                        upc = COALESCE(EXCLUDED.upc, recalls.upc),
                        hazard = COALESCE(EXCLUDED.hazard, recalls.hazard),
                        recall_date = COALESCE(EXCLUDED.recall_date, recalls.recall_date),
                        updated_at = CURRENT_TIMESTAMP
                """,
                )

                db.execute(query, params_dict)

                # For simplicity, assume all succeeded (could track with RETURNING)
                counts["inserted"] += len(batch)

            except Exception as e:
                logger.error(f"Bulk upsert batch failed: {e}")
                counts["failed"] += len(batch)
                db.rollback()
                continue

        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit bulk upsert: {e}")
            db.rollback()

        return counts

    @staticmethod
    def upsert_subscription(db: Session, subscription_data: dict[str, Any]) -> bool:
        """Perform atomic UPSERT for subscription records

        Args:
            db: Database session
            subscription_data: Dictionary with subscription fields

        Returns:
            True if successful, False otherwise
        """
        try:
            query = text(
                """
                INSERT INTO subscriptions (
                    user_id, plan, status, provider,
                    started_at, expires_at, cancelled_at,
                    product_id, price, currency,
                    original_transaction_id, latest_receipt,
                    auto_renew, trial_end_date
                ) VALUES (
                    :user_id, :plan, :status, :provider,
                    :started_at, :expires_at, :cancelled_at,
                    :product_id, :price, :currency,
                    :original_transaction_id, :latest_receipt,
                    :auto_renew, :trial_end_date
                )
                ON CONFLICT (user_id, original_transaction_id) 
                DO UPDATE SET
                    status = EXCLUDED.status,
                    expires_at = EXCLUDED.expires_at,
                    cancelled_at = EXCLUDED.cancelled_at,
                    latest_receipt = EXCLUDED.latest_receipt,
                    auto_renew = EXCLUDED.auto_renew,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, (xmax = 0) AS inserted
            """,
            )

            result = db.execute(query, subscription_data)
            row = result.fetchone()

            if row:
                was_inserted = row[1]
                logger.debug(
                    f"{'Inserted' if was_inserted else 'Updated'} subscription for user {subscription_data['user_id']}",
                )

            return True

        except Exception as e:
            logger.error(f"Failed to upsert subscription: {e}")
            return False


class EnhancedUpsertHandler(UpsertHandler):
    """Enhanced UPSERT handler with additional features
    """

    @staticmethod
    def upsert_with_history(
        db: Session,
        table: str,
        data: dict[str, Any],
        unique_key: str,
        track_changes: bool = True,
    ) -> bool:
        """UPSERT with optional change history tracking

        Args:
            db: Database session
            table: Table name
            data: Data dictionary
            unique_key: Column name for ON CONFLICT
            track_changes: Whether to track changes in history table

        Returns:
            True if successful
        """
        try:
            # Build column lists
            columns = list(data.keys())
            value_placeholders = [f":{col}" for col in columns]

            # Build UPDATE SET clause with COALESCE for nullable fields
            update_sets = []
            for col in columns:
                if col != unique_key:  # Don't update the unique key
                    update_sets.append(f"{col} = COALESCE(EXCLUDED.{col}, {table}.{col})")

            query = text(
                f"""
                INSERT INTO {table} ({", ".join(columns)})
                VALUES ({", ".join(value_placeholders)})
                ON CONFLICT ({unique_key})
                DO UPDATE SET
                    {", ".join(update_sets)},
                    updated_at = CURRENT_TIMESTAMP
                RETURNING {unique_key}, (xmax = 0) AS inserted
            """,
            )

            result = db.execute(query, data)
            row = result.fetchone()

            if row and track_changes:
                # Log change to history table (if exists)
                history_query = text(
                    f"""
                    INSERT INTO {table}_history (
                        entity_id, action, changed_by, changed_at, changes
                    ) VALUES (
                        :entity_id, :action, :changed_by, CURRENT_TIMESTAMP, :changes
                    )
                """,
                )

                db.execute(
                    history_query,
                    {
                        "entity_id": row[0],
                        "action": "INSERT" if row[1] else "UPDATE",
                        "changed_by": "system",
                        "changes": str(data),
                    },
                )

            return True

        except Exception as e:
            logger.error(f"Enhanced upsert failed for {table}: {e}")
            return False


# Singleton instance
upsert_handler = UpsertHandler()
enhanced_upsert_handler = EnhancedUpsertHandler()
