import os
import sqlite3

DB = os.path.abspath("dev.db")
con = sqlite3.connect(DB)
cur = con.cursor()

# Keep it simple for local: no foreign keys; SQLite TEXT for JSON
cur.executescript(
    """
PRAGMA foreign_keys=OFF;

-- already made chat_* tables are fine; these are common extras used by explain-result

CREATE TABLE IF NOT EXISTS barcode_scans (
  trace_id TEXT PRIMARY KEY,
  barcode TEXT,
  product_json TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_request_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id TEXT,
  endpoint TEXT,
  payload_json TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_explanations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id TEXT,
  summary TEXT,
  reasons_json TEXT,
  checks_json TEXT,
  flags_json TEXT,
  disclaimer TEXT,
  created_at TEXT
);
"""
)

con.commit()
con.close()
print("✅ Extra local tables ensured at", DB)
