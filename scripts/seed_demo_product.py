#!/usr/bin/env python3
"""Seed a demo hair product for local CrownSafe testing."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database first - this imports base.Base and defines User
from core_infra.database import SessionLocal, User, engine  # noqa: F401

# Now import crown_safe models which will use the same Base
from core_infra.base import Base
from core_infra.crown_safe_models import HairProductModel


def seed_demo_product():
    """Insert a demo hair product into the database."""
    try:
        # Create all tables from the database.py Base (includes User and all models)
        print("Creating all database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified")

        # Create session
        session = SessionLocal()

        # Check if product already exists
        existing = (
            session.query(HairProductModel)
            .filter(HairProductModel.barcode == "012345678905")
            .first()
        )

        if existing:
            print(f"⚠️  Product already exists: {existing.name} (barcode: {existing.barcode})")
            session.close()
            return

        # Create demo product using ORM model
        demo_product = HairProductModel(
            product_id="CROWN_DEMO_001",
            name="Moisture Repair Leave-In",
            brand="Crown Labs",
            barcode="012345678905",
            category="Conditioner",
            product_type="Leave-In Conditioner",
            ingredients=[
                "Water",
                "Shea Butter",
                "Cetearyl Alcohol",
                "Glycerin",
                "Coconut Oil",
                "Aloe Vera",
            ],
            ph_level=5.0,
            avg_crown_score=82,
            is_sulfate_free=True,
            is_silicone_free=True,
            is_paraben_free=True,
            is_curly_girl_approved=True,
        )

        session.add(demo_product)
        session.commit()
        session.refresh(demo_product)

        print("✅ Inserted demo product: Moisture Repair Leave-In")
        print(f"   Product ID: {demo_product.product_id}")
        print(f"   Barcode: {demo_product.barcode}")
        print(f"   Crown Score: {demo_product.avg_crown_score}")
        session.close()

    except Exception as e:
        print(f"❌ Error seeding product: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed_demo_product()
