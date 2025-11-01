#!/usr/bin/env python3
"""Seed a demo hair product for local CrownSafe testing."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core_infra.database import Base, SessionLocal, engine
from core_infra.crown_safe_models import HairProductModel


def seed_demo_product():
    """Insert a demo hair product into the database."""
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")

        # Create session
        session = SessionLocal()

        # Check if product already exists
        existing = session.query(HairProductModel).filter_by(upc_barcode="012345678905").first()
        if existing:
            print(f"⚠️  Product already exists: {existing.product_name}")
            session.close()
            return

        # Create demo product
        prod = HairProductModel(
            product_name="Moisture Repair Leave-In",
            brand="Crown Labs",
            upc_barcode="012345678905",
            category="leave-in conditioner",
            ingredients_list=["water", "shea butter", "cetearyl alcohol", "parfum"],
            ph_level=5.0,
            product_image_url=None,
            manufacturer="Crown Labs R&D",
            average_crown_score=82,
            scan_count=14,
        )

        session.add(prod)
        session.commit()
        print(f"✅ Inserted demo product: {prod.product_name}")
        print(f"   Barcode: {prod.upc_barcode}")
        print(f"   Crown Score: {prod.average_crown_score}")
        session.close()

    except Exception as e:
        print(f"❌ Error seeding product: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed_demo_product()
