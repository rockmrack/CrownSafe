import os
import re
import sqlite3

identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_safe_identifier(name: str, pattern: re.Pattern = identifier_pattern) -> bool:
    """Return True if the provided identifier can be safely interpolated into SQL."""

    return bool(pattern.fullmatch(name))


# Check all database files
db_files = ["babyshield_recalls.db", "babyshield_dev.db", "babyshield.db"]

print("=" * 70)
print("Searching for Recalled Products Database")
print("=" * 70)
print()

for db_file in db_files:
    if not os.path.exists(db_file):
        print(f"⏭️  {db_file} - Not found")
        continue

    size_mb = os.path.getsize(db_file) / 1024 / 1024
    print(f"\n📁 {db_file} ({size_mb:.2f} MB)")
    print("-" * 70)

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]

        total_recalls = 0

        for table in tables:
            if "recall" in table.lower():
                try:
                    if not _is_safe_identifier(table):
                        print(f"   ⚠️  Skipping table with unsafe name: {table}")
                        continue

                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"   📊 {table}: {count:,} rows")
                    total_recalls += count

                    if count > 0:
                        # Show sample
                        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                        sample = cursor.fetchone()
                        if sample:
                            cursor.execute(f"PRAGMA table_info({table})")
                            cols = [c[1] for c in cursor.fetchall()]
                            print(f"      Columns: {', '.join(cols[:5])}...")
                except Exception as e:
                    print(f"   ⚠️  Error reading {table}: {e}")

        if total_recalls > 0:
            print()
            print(f"   🎯 TOTAL RECALLS IN THIS DB: {total_recalls:,}")

        conn.close()

    except Exception as e:
        print(f"   ❌ Error: {e}")

print()
print("=" * 70)
