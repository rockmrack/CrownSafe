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

        # Create hair_products table with correct schema matching HairProductModel
        session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS hair_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE NOT NULL,
                barcode TEXT,
                name TEXT NOT NULL,
                brand TEXT NOT NULL,
                category TEXT NOT NULL,
                product_type TEXT NOT NULL,
                description TEXT,
                size TEXT,
                ingredients TEXT NOT NULL,
                ph_level REAL,
                is_curly_girl_approved INTEGER DEFAULT 0,
                is_sulfate_free INTEGER DEFAULT 0,
                is_silicone_free INTEGER DEFAULT 0,
                is_protein_free INTEGER DEFAULT 0,
                is_paraben_free INTEGER DEFAULT 0,
                price REAL,
                currency TEXT DEFAULT 'USD',
                available_at TEXT,
                affiliate_links TEXT,
                avg_crown_score INTEGER,
                image_url TEXT,
                thumbnail_url TEXT,
                review_count INTEGER DEFAULT 0,
                avg_rating REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """
            )
        )
        session.commit()
        print("✅ Database tables created/verified")

        # Check if product already exists
        existing = session.execute(
            text("SELECT * FROM hair_products WHERE barcode = :barcode"),
            {"barcode": "012345678905"},
        ).first()
        if existing:
            print("⚠️  Product already exists with barcode 012345678905")
            session.close()
            return

        # Insert demo product using raw SQL with correct column names
        session.execute(
            text(
                """
            INSERT INTO hair_products (
                product_id, name, brand, barcode, category, 
                product_type, ingredients, ph_level, 
                avg_crown_score, is_sulfate_free, is_silicone_free,
                is_paraben_free, is_curly_girl_approved
            ) VALUES (
                :product_id, :name, :brand, :barcode, :category,
                :product_type, :ingredients, :ph,
                :score, :sulfate_free, :silicone_free,
                :paraben_free, :cg_approved
            )
        """
            ),
            {
                "product_id": "CROWN_DEMO_001",
                "name": "Moisture Repair Leave-In",
                "brand": "Crown Labs",
                "barcode": "012345678905",
                "category": "Conditioner",
                "product_type": "Leave-In Conditioner",
                "ingredients": ('["Water", "Shea Butter", "Cetearyl Alcohol", "Glycerin", "Coconut Oil", "Aloe Vera"]'),
                "ph": 5.0,
                "score": 82,
                "sulfate_free": 1,
                "silicone_free": 1,
                "paraben_free": 1,
                "cg_approved": 1,
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
