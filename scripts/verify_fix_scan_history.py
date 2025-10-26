import os
import re
import sqlite3

DB = os.path.abspath("dev.db")
REQUIRED = [
    "scan_id",
    "product_name",
    "brand",
    "manufacturer",
    "model_number",
    "barcode",
    "upc_gtin",
    "category",
    "scan_type",
    "confidence_score",
    "barcode_format",
    "verdict",
    "risk_level",
    "recalls_found",
    "recall_ids",
    "agencies_checked",
    "allergen_alerts",
    "pregnancy_warnings",
    "age_warnings",
    "included_in_reports",
    "created_at",
]

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Ensure table exists minimally
cur.execute("CREATE TABLE IF NOT EXISTS scan_history (id INTEGER PRIMARY KEY, scan_id TEXT)")
conn.commit()

# Current columns
cur.execute("PRAGMA table_info('scan_history')")
have = [r[1] for r in cur.fetchall()]
missing = [c for c in REQUIRED if c not in have]

identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(name: str) -> str:
    """Return a safely-quoted SQLite identifier."""

    if not identifier_pattern.fullmatch(name):
        raise ValueError(f"Unsafe identifier provided: {name}")
    return f'"{name}"'


# Add any missing columns with safe defaults
defaults = {
    "confidence_score": "REAL DEFAULT 1.0",
    "verdict": "TEXT DEFAULT 'safe'",
    "risk_level": "TEXT DEFAULT 'low'",
    "recalls_found": "INTEGER DEFAULT 0",
    "recall_ids": "TEXT DEFAULT '[]'",
    "agencies_checked": "INTEGER DEFAULT 39",
    "allergen_alerts": "TEXT DEFAULT '[]'",
    "pregnancy_warnings": "TEXT DEFAULT '[]'",
    "age_warnings": "TEXT DEFAULT '[]'",
    "included_in_reports": "INTEGER DEFAULT 0",
}
for c in missing:
    sqltype = defaults.get(c, "TEXT")
    quoted_column = _quote_identifier(c)
    cur.execute(f"ALTER TABLE scan_history ADD COLUMN {quoted_column} {sqltype}")

conn.commit()

# Print final state
cur.execute("PRAGMA table_info('scan_history')")
final_cols = [r[1] for r in cur.fetchall()]
print("DB:", DB)
print("Added:", missing)
print("Final columns:", final_cols)

conn.close()
