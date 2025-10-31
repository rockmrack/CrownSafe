# scripts/seed_for_live_test.py

import logging
import os
import sys
from datetime import date

# CRITICAL: Set environment variables BEFORE importing database module
# This ensures we use the same database as the API server
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///babyshield_test.db")
os.environ["TEST_MODE"] = "true"

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from core_infra.database import (
    DATABASE_URL,
    RecallDB,
    SessionLocal,
    User,
    create_tables,
    drop_tables,
    engine,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def seed_database():
    logger = logging.getLogger(__name__)
    logger.info("--- Seeding Database for Live HTTP Test ---")
    logger.info(f"Using database: {DATABASE_URL}")
    logger.info(f"Engine URL: {engine.url}")

    # Don't drop tables in production! Only recreate if needed
    if os.getenv("RESET_DB", "false").lower() == "true":
        drop_tables()
        create_tables()
        logger.info("Database tables dropped and recreated.")
    else:
        create_tables()  # This will only create if not exists
        logger.info("Ensured database tables exist.")

    with SessionLocal() as db:
        # Check if user already exists
        existing_user = db.query(User).filter_by(id=1).first()
        if existing_user:
            logger.info(f"User with ID 1 already exists: {existing_user.email}")
        else:
            # Create subscribed user
            subscriber = User(
                id=1,
                email="live.test@example.com",
                is_subscribed=True,
                hashed_password="test",
                is_pregnant=False,
            )
            db.add(subscriber)
            logger.info("Added subscribed test user with ID: 1")

        # Check if recall already exists
        existing_recall = db.query(RecallDB).filter_by(recall_id="LIVE-RECALL-001").first()
        if existing_recall:
            logger.info(f"Recall already exists with UPC: {existing_recall.upc}")
            # Update the UPC if needed
            existing_recall.upc = "037000488786"
            db.commit()
            logger.info("Updated existing recall with correct UPC")
        else:
            # Create recall for the test barcode
            test_recall = RecallDB(
                recall_id="LIVE-RECALL-001",
                product_name="Pampers Sensitive Baby Wipes 56ct",
                upc="037000488786",  # <-- The exact barcode your test will send!
                brand="Pampers",
                country="US",
                recall_date=date.today(),
                hazard_description="Sample hazard for demo recall.",
                manufacturer_contact="Procter & Gamble",
                source_agency="LIVE_TEST",
                description="Test recall for live API demo.",
                hazard="Sample Hazard",
                remedy="Do not use this product.",
                url="http://example.com/recall",
            )
            db.add(test_recall)
            logger.info("Added a specific recall record for the test product.")

        db.commit()

    # Verify the data was actually saved
    logger.info("--- Verifying seeded data ---")
    with SessionLocal() as db:
        user_count = db.query(User).count()
        recall_count = db.query(RecallDB).count()
        logger.info(f"Total users in database: {user_count}")
        logger.info(f"Total recalls in database: {recall_count}")

        # Specifically check for our test recall
        test_recall = db.query(RecallDB).filter_by(upc="037000488786").first()
        if test_recall:
            logger.info(
                f"✅ Test recall found: ID={test_recall.recall_id}, UPC={test_recall.upc}, Product={test_recall.product_name}"
            )
        else:
            logger.error("❌ Test recall NOT found in database!")

        # List all recalls with UPC
        all_recalls = db.query(RecallDB).filter(RecallDB.upc.isnot(None)).all()
        logger.info(f"All recalls with UPC: {[(r.recall_id, r.upc) for r in all_recalls]}")

    logger.info("--- Database seeding complete. ---")


if __name__ == "__main__":
    seed_database()
