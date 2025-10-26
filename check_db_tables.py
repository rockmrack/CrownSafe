"""Check database tables"""

import sqlite3

conn = sqlite3.connect("db/babyshield_dev.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

print("\n=== Existing Tables ===")
for table in tables:
    print(f"  - {table[0]}")

print(f"\nTotal: {len(tables)} tables")

# Check for Crown Safe tables
crown_safe_tables = [
    "hair_profiles",
    "hair_products",
    "ingredients",
    "product_scans",
    "product_reviews",
    "brand_certifications",
    "salon_accounts",
    "market_insights",
]

print("\n=== Crown Safe Tables Status ===")
existing_table_names = [t[0] for t in tables]
for cs_table in crown_safe_tables:
    status = "✓ EXISTS" if cs_table in existing_table_names else "✗ MISSING"
    print(f"  {status}: {cs_table}")

conn.close()
