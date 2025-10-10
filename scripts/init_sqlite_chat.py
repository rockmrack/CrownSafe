import sqlite3
import os
import json
import datetime

DB = os.path.abspath("dev.db")
con = sqlite3.connect(DB)
cur = con.cursor()

# bare-bones scan storage (names kept generic so we don't collide)
cur.execute(
    """
CREATE TABLE IF NOT EXISTS barcode_scans (
  trace_id TEXT PRIMARY KEY,
  barcode TEXT,
  product_name TEXT,
  brand TEXT,
  created_at TEXT,
  raw_json TEXT
)
"""
)

# chat explanations storage (all TEXT for SQLite friendliness)
cur.execute(
    """
CREATE TABLE IF NOT EXISTS chat_explanations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id TEXT,
  summary TEXT,
  reasons TEXT,
  checks TEXT,
  flags TEXT,
  disclaimer TEXT,
  created_at TEXT
)
"""
)

con.commit()
con.close()
print("✅ Local chat tables ready at", DB)
