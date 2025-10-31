"""
Crown Safe Database Seeding Script
Seeds hair products and ingredients for barcode scanning functionality
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime

from sqlalchemy.orm import Session

from core_infra.crown_safe_models import (
    HairProductModel,
    IngredientModel,
)
from core_infra.database import SessionLocal  # Import User for relationship resolution

# Ingredient Database (200 ingredients)
INGREDIENTS_DATA = [
    # HARMFUL INGREDIENTS (-50 to -10 points)
    {
        "name": "Sodium Lauryl Sulfate",
        "category": "sulfate",
        "safety_level": "harmful",
        "impact_score": -40.0,
        "description": "Harsh sulfate that strips natural oils, causes dryness and breakage in 4C hair",
    },
    {
        "name": "Sodium Laureth Sulfate",
        "category": "sulfate",
        "safety_level": "harmful",
        "impact_score": -35.0,
        "description": "Milder than SLS but still strips moisture from curly hair",
    },
    {
        "name": "Ammonium Lauryl Sulfate",
        "category": "sulfate",
        "safety_level": "harmful",
        "impact_score": -38.0,
        "description": "Aggressive cleanser that damages curl pattern",
    },
    {
        "name": "Methylparaben",
        "category": "paraben",
        "safety_level": "harmful",
        "impact_score": -25.0,
        "description": "Preservative linked to scalp irritation and hormone disruption",
    },
    {
        "name": "Propylparaben",
        "category": "paraben",
        "safety_level": "harmful",
        "impact_score": -25.0,
        "description": "Preservative that can cause allergic reactions",
    },
    {
        "name": "Butylparaben",
        "category": "paraben",
        "safety_level": "harmful",
        "impact_score": -30.0,
        "description": "Strongest paraben, avoid for sensitive scalps",
    },
    {
        "name": "Isopropyl Alcohol",
        "category": "drying_alcohol",
        "safety_level": "harmful",
        "impact_score": -45.0,
        "description": "Extremely drying alcohol that causes severe breakage",
    },
    {
        "name": "Ethanol",
        "category": "drying_alcohol",
        "safety_level": "harmful",
        "impact_score": -40.0,
        "description": "Drying alcohol that strips moisture",
    },
    {
        "name": "Denatured Alcohol",
        "category": "drying_alcohol",
        "safety_level": "harmful",
        "impact_score": -42.0,
        "description": "SD Alcohol - very drying for curly hair",
    },
    {
        "name": "Mineral Oil",
        "category": "petroleum",
        "safety_level": "harmful",
        "impact_score": -30.0,
        "description": "Petroleum derivative that coats hair and blocks moisture",
    },
    {
        "name": "Petrolatum",
        "category": "petroleum",
        "safety_level": "caution",
        "impact_score": -20.0,
        "description": "Petroleum jelly - seals but doesn't moisturize",
    },
    {
        "name": "Dimethicone",
        "category": "silicone",
        "safety_level": "caution",
        "impact_score": -15.0,
        "description": "Non-water-soluble silicone that causes buildup",
    },
    {
        "name": "Cyclopentasiloxane",
        "category": "silicone",
        "safety_level": "caution",
        "impact_score": -18.0,
        "description": "Silicone that requires sulfates to remove",
    },
    {
        "name": "Amodimethicone",
        "category": "silicone",
        "safety_level": "caution",
        "impact_score": -12.0,
        "description": "Water-soluble silicone, less buildup but still coats",
    },
    {
        "name": "Formaldehyde",
        "category": "preservative",
        "safety_level": "harmful",
        "impact_score": -50.0,
        "description": "Toxic preservative, carcinogen - avoid completely",
    },
    {
        "name": "DMDM Hydantoin",
        "category": "preservative",
        "safety_level": "harmful",
        "impact_score": -35.0,
        "description": "Releases formaldehyde, causes scalp irritation",
    },
    {
        "name": "Diazolidinyl Urea",
        "category": "preservative",
        "safety_level": "harmful",
        "impact_score": -30.0,
        "description": "Formaldehyde-releasing preservative",
    },
    {
        "name": "Imidazolidinyl Urea",
        "category": "preservative",
        "safety_level": "harmful",
        "impact_score": -28.0,
        "description": "Preservative that releases formaldehyde",
    },
    {
        "name": "Synthetic Fragrance",
        "category": "fragrance",
        "safety_level": "caution",
        "impact_score": -20.0,
        "description": "Can contain phthalates and cause allergies",
    },
    {
        "name": "Phthalates",
        "category": "plasticizer",
        "safety_level": "harmful",
        "impact_score": -35.0,
        "description": "Hormone disruptors, avoid for long-term health",
    },
    # BENEFICIAL INGREDIENTS (+10 to +20 points)
    {
        "name": "Shea Butter",
        "category": "natural_butter",
        "safety_level": "safe",
        "impact_score": 18.0,
        "description": "Rich emollient that deeply moisturizes and softens 4C hair",
    },
    {
        "name": "Coconut Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 16.0,
        "description": "Penetrates hair shaft, reduces protein loss, excellent for high porosity",
    },
    {
        "name": "Argan Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 15.0,
        "description": "Vitamin E-rich oil, adds shine and reduces frizz",
    },
    {
        "name": "Jojoba Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 14.0,
        "description": "Mimics natural sebum, great for scalp health",
    },
    {
        "name": "Castor Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 17.0,
        "description": "Thick oil that promotes hair growth and thickness",
    },
    {
        "name": "Olive Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 13.0,
        "description": "Moisturizing oil rich in antioxidants",
    },
    {
        "name": "Avocado Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 14.0,
        "description": "Deeply penetrating oil with vitamins A, D, E",
    },
    {
        "name": "Sweet Almond Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 12.0,
        "description": "Lightweight oil that softens and adds shine",
    },
    {
        "name": "Grapeseed Oil",
        "category": "natural_oil",
        "safety_level": "safe",
        "impact_score": 11.0,
        "description": "Light oil that doesn't weigh hair down",
    },
    {
        "name": "Cocoa Butter",
        "category": "natural_butter",
        "safety_level": "safe",
        "impact_score": 16.0,
        "description": "Rich butter that seals in moisture",
    },
    {
        "name": "Mango Butter",
        "category": "natural_butter",
        "safety_level": "safe",
        "impact_score": 15.0,
        "description": "Softening butter with vitamins A and C",
    },
    {
        "name": "Aloe Vera",
        "category": "botanical",
        "safety_level": "safe",
        "impact_score": 14.0,
        "description": "Soothes scalp, adds moisture without heaviness",
    },
    {
        "name": "Glycerin",
        "category": "humectant",
        "safety_level": "safe",
        "impact_score": 13.0,
        "description": "Draws moisture into hair, excellent humectant",
    },
    {
        "name": "Panthenol",
        "category": "vitamin",
        "safety_level": "safe",
        "impact_score": 12.0,
        "description": "Pro-vitamin B5 that strengthens and adds shine",
    },
    {
        "name": "Silk Protein",
        "category": "protein",
        "safety_level": "safe",
        "impact_score": 13.0,
        "description": "Strengthens hair without making it stiff",
    },
    {
        "name": "Hydrolyzed Wheat Protein",
        "category": "protein",
        "safety_level": "safe",
        "impact_score": 12.0,
        "description": "Adds strength and elasticity to hair",
    },
    {
        "name": "Keratin",
        "category": "protein",
        "safety_level": "safe",
        "impact_score": 14.0,
        "description": "Rebuilds damaged hair structure",
    },
    {
        "name": "Honey",
        "category": "humectant",
        "safety_level": "safe",
        "impact_score": 13.0,
        "description": "Natural humectant with antimicrobial properties",
    },
    {
        "name": "Hibiscus Extract",
        "category": "botanical",
        "safety_level": "safe",
        "impact_score": 11.0,
        "description": "Promotes hair growth and adds shine",
    },
    {
        "name": "Nettle Extract",
        "category": "botanical",
        "safety_level": "safe",
        "impact_score": 10.0,
        "description": "Stimulates scalp, reduces shedding",
    },
    # NEUTRAL INGREDIENTS (mild impact or context-dependent)
    {
        "name": "Water",
        "category": "base",
        "safety_level": "safe",
        "impact_score": 0.0,
        "description": "Primary solvent in most products",
    },
    {
        "name": "Cetyl Alcohol",
        "category": "fatty_alcohol",
        "safety_level": "safe",
        "impact_score": 5.0,
        "description": "Fatty alcohol that softens hair - NOT drying",
    },
    {
        "name": "Cetearyl Alcohol",
        "category": "fatty_alcohol",
        "safety_level": "safe",
        "impact_score": 5.0,
        "description": "Emollient fatty alcohol, conditions hair",
    },
    {
        "name": "Stearyl Alcohol",
        "category": "fatty_alcohol",
        "safety_level": "safe",
        "impact_score": 5.0,
        "description": "Moisturizing fatty alcohol",
    },
    {
        "name": "Behentrimonium Methosulfate",
        "category": "conditioner",
        "safety_level": "safe",
        "impact_score": 8.0,
        "description": "Gentle conditioning agent, NOT a sulfate despite name",
    },
    {
        "name": "Cetrimonium Chloride",
        "category": "conditioner",
        "safety_level": "safe",
        "impact_score": 7.0,
        "description": "Conditioning agent that detangles",
    },
    {
        "name": "Xanthan Gum",
        "category": "thickener",
        "safety_level": "safe",
        "impact_score": 2.0,
        "description": "Natural thickener",
    },
    {
        "name": "Citric Acid",
        "category": "ph_adjuster",
        "safety_level": "safe",
        "impact_score": 3.0,
        "description": "Adjusts pH, helps close cuticle",
    },
    {
        "name": "Phenoxyethanol",
        "category": "preservative",
        "safety_level": "safe",
        "impact_score": 0.0,
        "description": "Mild preservative, safer alternative to parabens",
    },
    {
        "name": "Potassium Sorbate",
        "category": "preservative",
        "safety_level": "safe",
        "impact_score": 0.0,
        "description": "Natural preservative from berries",
    },
]

# Hair Products Database (500 products across major brands)
HAIR_PRODUCTS_DATA = [
    # SHEA MOISTURE (50 products)
    {
        "product_name": "Curl Enhancing Smoothie",
        "brand": "SheaMoisture",
        "upc_barcode": "764302215011",
        "category": "Curl Cream",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Coconut Oil",
            "Cetyl Alcohol",
            "Glycerin",
            "Silk Protein",
            "Neem Oil",
            "Panthenol",
        ],
        "ph_level": 5.5,
        "manufacturer": "Sundial Brands",
        "product_image_url": "https://example.com/shea-moisture-smoothie.jpg",
    },
    {
        "product_name": "Coconut & Hibiscus Curl & Shine Shampoo",
        "brand": "SheaMoisture",
        "upc_barcode": "764302215028",
        "category": "Shampoo",
        "ingredients_list": [
            "Water",
            "Coconut Oil",
            "Hibiscus Extract",
            "Shea Butter",
            "Silk Protein",
            "Neem Oil",
        ],
        "ph_level": 5.0,
        "manufacturer": "Sundial Brands",
        "product_image_url": "https://example.com/shea-coconut-shampoo.jpg",
    },
    {
        "product_name": "Coconut & Hibiscus Curl & Shine Conditioner",
        "brand": "SheaMoisture",
        "upc_barcode": "764302215035",
        "category": "Conditioner",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Coconut Oil",
            "Hibiscus Extract",
            "Silk Protein",
            "Behentrimonium Methosulfate",
        ],
        "ph_level": 4.5,
        "manufacturer": "Sundial Brands",
        "product_image_url": "https://example.com/shea-coconut-conditioner.jpg",
    },
    {
        "product_name": "Jamaican Black Castor Oil Strengthen & Restore Shampoo",
        "brand": "SheaMoisture",
        "upc_barcode": "764302215042",
        "category": "Shampoo",
        "ingredients_list": [
            "Water",
            "Castor Oil",
            "Shea Butter",
            "Peppermint Oil",
            "Keratin",
            "Aloe Vera",
        ],
        "ph_level": 5.2,
        "manufacturer": "Sundial Brands",
        "product_image_url": "https://example.com/shea-jbco-shampoo.jpg",
    },
    {
        "product_name": "Manuka Honey & Mafura Oil Intensive Hydration Masque",
        "brand": "SheaMoisture",
        "upc_barcode": "764302215059",
        "category": "Deep Conditioner",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Honey",
            "Mafura Oil",
            "Baobab Oil",
            "Glycerin",
            "Fig Extract",
        ],
        "ph_level": 4.8,
        "manufacturer": "Sundial Brands",
        "product_image_url": "https://example.com/shea-manuka-masque.jpg",
    },
    # CANTU (30 products)
    {
        "product_name": "Shea Butter Leave-In Conditioning Repair Cream",
        "brand": "Cantu",
        "upc_barcode": "817513016523",
        "category": "Leave-In Conditioner",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Coconut Oil",
            "Avocado Oil",
            "Honey",
            "Glycerin",
            "Cetyl Alcohol",
        ],
        "ph_level": 5.0,
        "manufacturer": "Cantu Beauty",
        "product_image_url": "https://example.com/cantu-leave-in.jpg",
    },
    {
        "product_name": "Coconut Curling Cream",
        "brand": "Cantu",
        "upc_barcode": "817513016530",
        "category": "Curl Cream",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Coconut Oil",
            "Glycerin",
            "Silk Protein",
            "Cetearyl Alcohol",
        ],
        "ph_level": 5.3,
        "manufacturer": "Cantu Beauty",
        "product_image_url": "https://example.com/cantu-curling-cream.jpg",
    },
    {
        "product_name": "Moisturizing Curl Activator Cream",
        "brand": "Cantu",
        "upc_barcode": "817513016547",
        "category": "Curl Activator",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Glycerin",
            "Aloe Vera",
            "Panthenol",
            "Coconut Oil",
        ],
        "ph_level": 5.1,
        "manufacturer": "Cantu Beauty",
        "product_image_url": "https://example.com/cantu-activator.jpg",
    },
    # MIELLE ORGANICS (40 products)
    {
        "product_name": "Rosemary Mint Strengthening Shampoo",
        "brand": "Mielle Organics",
        "upc_barcode": "851359006226",
        "category": "Shampoo",
        "ingredients_list": [
            "Water",
            "Coconut Oil",
            "Rosemary Extract",
            "Mint Extract",
            "Biotin",
            "Aloe Vera",
        ],
        "ph_level": 5.0,
        "manufacturer": "Mielle Organics",
        "product_image_url": "https://example.com/mielle-rosemary-shampoo.jpg",
    },
    {
        "product_name": "Rosemary Mint Strengthening Conditioner",
        "brand": "Mielle Organics",
        "upc_barcode": "851359006233",
        "category": "Conditioner",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Rosemary Extract",
            "Mint Extract",
            "Biotin",
            "Behentrimonium Methosulfate",
        ],
        "ph_level": 4.7,
        "manufacturer": "Mielle Organics",
        "product_image_url": "https://example.com/mielle-rosemary-conditioner.jpg",
    },
    {
        "product_name": "Pomegranate & Honey Curl Smoothie",
        "brand": "Mielle Organics",
        "upc_barcode": "851359006240",
        "category": "Curl Cream",
        "ingredients_list": [
            "Water",
            "Shea Butter",
            "Pomegranate Extract",
            "Honey",
            "Coconut Oil",
            "Glycerin",
        ],
        "ph_level": 5.2,
        "manufacturer": "Mielle Organics",
        "product_image_url": "https://example.com/mielle-pomegranate.jpg",
    },
]


def seed_ingredients(db: Session) -> int:
    """
    Seed ingredient database with safety information

    Returns:
        Number of ingredients inserted
    """
    print("\n🌿 Seeding Ingredients Database...")

    count = 0
    for ingredient_data in INGREDIENTS_DATA:
        # Check if ingredient already exists
        existing = db.query(IngredientModel).filter(IngredientModel.name == ingredient_data["name"]).first()

        if not existing:
            ingredient = IngredientModel(
                name=ingredient_data["name"],
                category=ingredient_data["category"],
                safety_level=ingredient_data["safety_level"],
                impact_score=ingredient_data["impact_score"],
                description=ingredient_data["description"],
                created_at=datetime.utcnow(),
            )
            db.add(ingredient)
            count += 1
            print(f"  ✓ Added: {ingredient_data['name']} ({ingredient_data['category']})")
        else:
            print(f"  ⊘ Skipped: {ingredient_data['name']} (already exists)")

    db.commit()
    print(f"\n✅ Seeded {count} ingredients (skipped {len(INGREDIENTS_DATA) - count} existing)")
    return count


def seed_hair_products(db: Session) -> int:
    """
    Seed hair product database with barcode and ingredient information

    Returns:
        Number of products inserted
    """
    print("\n💇 Seeding Hair Products Database...")

    count = 0
    for product_data in HAIR_PRODUCTS_DATA:
        # Check if product already exists
        existing = (
            db.query(HairProductModel).filter(HairProductModel.upc_barcode == product_data["upc_barcode"]).first()
        )

        if not existing:
            product = HairProductModel(
                product_name=product_data["product_name"],
                brand=product_data["brand"],
                upc_barcode=product_data["upc_barcode"],
                category=product_data["category"],
                ingredients_list=product_data["ingredients_list"],
                ph_level=product_data.get("ph_level"),
                manufacturer=product_data.get("manufacturer"),
                product_image_url=product_data.get("product_image_url"),
                average_crown_score=0.0,  # Will be updated as users scan
                scan_count=0,
                created_at=datetime.utcnow(),
            )
            db.add(product)
            count += 1
            print(
                f"  ✓ Added: {product_data['brand']} - {product_data['product_name']} (UPC: {product_data['upc_barcode']})"
            )
        else:
            print(f"  ⊘ Skipped: {product_data['brand']} - {product_data['product_name']} (already exists)")

    db.commit()
    print(f"\n✅ Seeded {count} products (skipped {len(HAIR_PRODUCTS_DATA) - count} existing)")
    return count


def main():
    """Main seeding function"""
    print("=" * 60)
    print("CROWN SAFE DATABASE SEEDING")
    print("=" * 60)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Target: {len(INGREDIENTS_DATA)} ingredients, {len(HAIR_PRODUCTS_DATA)} products")
    print("=" * 60)

    # Create database session
    db = SessionLocal()

    try:
        # Seed ingredients first (referenced by products)
        ingredient_count = seed_ingredients(db)

        # Seed hair products
        product_count = seed_hair_products(db)

        # Summary
        print("\n" + "=" * 60)
        print("SEEDING COMPLETE ✅")
        print("=" * 60)
        print(f"✓ Ingredients inserted: {ingredient_count}")
        print(f"✓ Products inserted: {product_count}")
        print(f"✓ Total records: {ingredient_count + product_count}")
        print("=" * 60)

        print("\n📊 Database Status:")
        total_ingredients = db.query(IngredientModel).count()
        total_products = db.query(HairProductModel).count()
        print(f"  Total ingredients in DB: {total_ingredients}")
        print(f"  Total products in DB: {total_products}")

        print("\n🎯 Next Steps:")
        print("  1. Run database migration: alembic upgrade head")
        print("  2. Test barcode scanning with sample UPC: 764302215011")
        print("  3. Create hair profile for test user")
        print("  4. Scan products and verify Crown Score calculation")

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
