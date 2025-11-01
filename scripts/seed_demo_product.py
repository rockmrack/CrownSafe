#!/usr/bin/env python3
"""Seed a demo hair product for local CrownSafe testing."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from core_infra.database import SessionLocal


def seed_demo_product():
    """Insert a demo hair product into the database."""
    try:
        # Create session
        session = SessionLocal()

        # Create hair_products table manually to avoid relationship issues
        session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS hair_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                brand TEXT NOT NULL,
                upc_barcode TEXT,
                category TEXT,
                ingredients_list TEXT,
                ph_level REAL,
                product_image_url TEXT,
                manufacturer TEXT,
                average_crown_score INTEGER,
                scan_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )
        session.commit()
        print("✅ Database tables created/verified")

        # Check if product already exists
        existing = session.execute(
            text("SELECT * FROM hair_products WHERE upc_barcode = :barcode"),
            {"barcode": "012345678905"},
        ).first()
        if existing:
            print("⚠️  Product already exists with barcode 012345678905")
            session.close()
            return

        # Insert demo product using raw SQL to avoid ORM relationship issues
        session.execute(
            text(
                """
            INSERT INTO hair_products (
                product_name, brand, upc_barcode, category, 
                ingredients_list, ph_level, manufacturer, 
                average_crown_score, scan_count
            ) VALUES (
                :name, :brand, :barcode, :category,
                :ingredients, :ph, :manufacturer,
                :score, :scans
            )
        """
            ),
            {
                "name": "Moisture Repair Leave-In",
                "brand": "Crown Labs",
                "barcode": "012345678905",
                "category": "leave-in conditioner",
                "ingredients": '["water", "shea butter", "cetearyl alcohol", "parfum"]',
                "ph": 5.0,
                "manufacturer": "Crown Labs R&D",
                "score": 82,
                "scans": 14,
            },
        )
        session.commit()
        print("✅ Inserted demo product: Moisture Repair Leave-In")
        print("   Barcode: 012345678905")
        print("   Crown Score: 82")
        session.close()

    except Exception as e:
        print(f"❌ Error seeding product: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    seed_demo_product()
