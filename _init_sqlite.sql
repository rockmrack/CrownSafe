CREATE TABLE IF NOT EXISTS recalls (
  id INTEGER PRIMARY KEY,
  product_name TEXT,
  brand TEXT,
  recall_date TEXT
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id INTEGER PRIMARY KEY,
  metadata_json TEXT,     -- JSONB in PG; use TEXT locally
  created_at TEXT
);
