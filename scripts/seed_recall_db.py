import sys
import os
import logging
from datetime import date

# --- Add project root to Python's path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
# -----------------------------------------

from core_infra.database import SessionLocal, RecallDB, Base, engine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Real Recall Data for the Yoto Mini Player ---
YOTO_MINI_RECALL = {
    "recall_id": "CPSC-YOTO-24-192",
    "product_name": "Yoto Mini Player",
    # matches RecallDB.recall_date
    "recall_date": date(2024, 4, 11),
    # maps to RecallDB.hazard_description
    "hazard_description": (
        "The speaker’s lithium-ion battery can overheat and catch fire, "
        "posing a burn and fire hazard."
    ),
    # required non-nullable field
    "country": "US",
    # maps to RecallDB.source_agency
    "source_agency": "CPSC",
    # optional fields
    "url": (
        "https://www.cpsc.gov/Recalls/2024/"
        "Yoto-Recalls-Yoto-Mini-Speakers-for-Children-Due-to-Burn-and-Fire-Hazards"
    ),
}
# ----------------------------------------------------


def seed_database():
    """Connects to the database and inserts the test recall."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        logger.info("Connecting to the database to seed recall data...")

        # Check if the recall already exists
        existing = (
            db.query(RecallDB).filter(RecallDB.recall_id == YOTO_MINI_RECALL["recall_id"]).first()
        )
        if existing:
            logger.warning(
                f"Recall with ID {YOTO_MINI_RECALL['recall_id']} already exists. Skipping seed."
            )
            return

        # Create and insert the new recall
        db_recall = RecallDB(**YOTO_MINI_RECALL)
        db.add(db_recall)
        db.commit()
        logger.info("✅ Successfully seeded the database with the Yoto Mini Player recall.")

    except Exception as e:
        logger.critical(
            f"❌ FAILED to connect to or seed the database. Is your database running? Error: {e}",
            exc_info=True,
        )
    finally:
        db.close()


def clean_database():
    """Connects to the database and removes the test recall."""
    db = SessionLocal()
    try:
        logger.info("Connecting to the database to clean recall data...")

        # Find and delete the recall
        record = (
            db.query(RecallDB).filter(RecallDB.recall_id == YOTO_MINI_RECALL["recall_id"]).first()
        )
        if record:
            db.delete(record)
            db.commit()
            logger.info("✅ Successfully cleaned the Yoto Mini Player recall from the database.")
        else:
            logger.warning("No test recall record found to clean.")

    except Exception as e:
        logger.critical(
            f"❌ FAILED to connect to or clean the database. Error: {e}",
            exc_info=True,
        )
    finally:
        db.close()


if __name__ == "__main__":
    # Usage: python scripts/seed_recall_db.py [--seed | --clean]
    if len(sys.argv) > 1 and sys.argv[1] == "--seed":
        seed_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "--clean":
        clean_database()
    else:
        print("Usage: python scripts/seed_recall_db.py [--seed | --clean]")
