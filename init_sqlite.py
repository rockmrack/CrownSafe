import sqlite3, os

db = os.path.abspath("dev.db")

schema = """
CREATE TABLE IF NOT EXISTS recalls (
  id INTEGER PRIMARY KEY,
  product_name TEXT,
  brand TEXT,
  recall_date TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY,
  metadata_json TEXT,
  created_at TEXT
);
"""

con = sqlite3.connect(db)
con.executescript(schema)
con.commit(); con.close()
print("SQLite ready at", db)
