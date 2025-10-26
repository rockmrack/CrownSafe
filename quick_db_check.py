import os
import re
import sqlite3

db_path = "babyshield_dev.db"

if not os.path.exists(db_path):
    print(f"❌ Database file not found: {db_path}")
    print("\nRun Alembic migrations first:")
    print("  $env:DATABASE_URL='sqlite:///./babyshield_dev.db'")
    print("  alembic -c db/alembic.ini upgrade head")
    exit(1)

print("=" * 70)
print(f"Database: {db_path}")
print("=" * 70)
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_safe_identifier(name: str, pattern: re.Pattern = identifier_pattern) -> bool:
    """Return True if the provided identifier can be safely interpolated into SQL."""

    return bool(pattern.fullmatch(name))


print(f"📊 Tables in database: {len(tables)}")
for table in tables:
    print(f"   - {table[0]}")

print()

# Count rows in each table
for table in tables:
    table_name = table[0]
    try:
        if not _is_safe_identifier(table_name):
            print(f"⚠️  Skipping table with unsafe name: {table_name}")
            continue

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"📈 {table_name}: {count:,} rows")

        # Show sample for recall tables
        if "recall" in table_name.lower() and count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            cursor.fetchone()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            print(f"   Sample columns: {', '.join(columns[:5])}...")

    except Exception as e:
        print(f"⚠️  Error reading {table_name}: {e}")

conn.close()

print()
print("=" * 70)
print("💡 To populate recalls, run:")
print("   python agents/recall_data_agent/main.py")
print("=" * 70)
