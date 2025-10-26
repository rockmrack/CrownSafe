import sqlite3

db_path = r"C:\Users\rossd\AppData\Local\Temp\babyshield_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [t[0] for t in cursor.fetchall()]

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

print("\n=== Migrated Database Verification ===")
print(f"Database: {db_path}\n")

found = []
missing = []
for table in crown_safe_tables:
    if table in all_tables:
        print(f"  ✓ {table}")
        found.append(table)
    else:
        print(f"  ✗ {table}")
        missing.append(table)

print(f"\nResult: {len(found)}/8 Crown Safe tables present")

if len(found) == 8:
    print("\n✓ Migration successful! All Crown Safe tables created.")
else:
    print(f"\n✗ Migration incomplete. Missing: {missing}")

conn.close()
