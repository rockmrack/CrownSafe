import sqlite3
import sys

db_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\rossd\AppData\Local\Temp\babyshield_dev.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
all_tables = [t[0] for t in cursor.fetchall()]

print(f"\n=== Database: {db_path} ===\n")
print(f"All tables ({len(all_tables)}):")
for table in all_tables:
    print(f"  - {table}")

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
found = 0
for table in crown_safe_tables:
    if table in all_tables:
        print(f"  ✓ FOUND: {table}")
        found += 1
    else:
        print(f"  ✗ MISSING: {table}")

print(f"\nSummary: {found}/{len(crown_safe_tables)} Crown Safe tables present")

# Check if old tables were removed
removed_tables = ["allergies", "family_members"]
print("\n=== Old Tables Removal Status ===")
for table in removed_tables:
    if table not in all_tables:
        print(f"  ✓ REMOVED: {table}")
    else:
        print(f"  ✗ STILL EXISTS: {table}")

# Check if is_pregnant column was removed from users table
cursor.execute("PRAGMA table_info(users)")
users_columns = [col[1] for col in cursor.fetchall()]
if "is_pregnant" not in users_columns:
    print("  ✓ REMOVED: users.is_pregnant column")
else:
    print("  ✗ STILL EXISTS: users.is_pregnant column")

conn.close()
