import sqlite3, datetime
db = "babyshield_test.db"

conn = sqlite3.connect(db)
c = conn.cursor()

# 1) recalls_enhanced (columns simplified to TEXT for SQLite)
c.execute("""
CREATE TABLE IF NOT EXISTS recalls_enhanced (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recall_id TEXT,
  product_name TEXT,
  brand TEXT,
  manufacturer TEXT,
  model_number TEXT,
  upc TEXT,
  ean_code TEXT,
  gtin TEXT,
  article_number TEXT,
  lot_number TEXT,
  batch_number TEXT,
  serial_number TEXT,
  part_number TEXT,
  expiry_date TEXT,
  best_before_date TEXT,
  production_date TEXT,
  ndc_number TEXT,
  din_number TEXT,
  vehicle_make TEXT,
  vehicle_model TEXT,
  model_year TEXT,
  vin_range TEXT,
  registry_codes TEXT,
  country TEXT,
  regions_affected TEXT,
  recall_date TEXT,
  source_agency TEXT,
  hazard TEXT,
  hazard_category TEXT,
  recall_reason TEXT,
  remedy TEXT,
  recall_class TEXT,
  description TEXT,
  manufacturer_contact TEXT,
  url TEXT,
  search_keywords TEXT,
  agency_specific_data TEXT
)""")

# 2) report_records (for metadata the API writes)
c.execute("""
CREATE TABLE IF NOT EXISTS report_records (
  report_id TEXT PRIMARY KEY,
  user_id INTEGER,
  report_type TEXT,
  storage_path TEXT,
  created_at TEXT
)""")

# Seed one simple recall if table is empty
row = c.execute("SELECT COUNT(1) FROM recalls_enhanced").fetchone()[0]
if row == 0:
    c.execute("""
      INSERT INTO recalls_enhanced
      (recall_id, product_name, brand, manufacturer, model_number, hazard, hazard_category,
       recall_date, source_agency, url, country, description)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
      "TEST-001", "Sample Baby Crib", "SafeCo", "SafeCo Ltd", "SC-100",
      "Entrapment risk", "Injury",
      datetime.date.today().isoformat(), "CPSC", "https://example.com/recall/test",
      "USA", "Mock row for local report generation"
    ))
    print("Seeded recalls_enhanced with 1 row.")
else:
    print("recalls_enhanced already has data; no seed inserted.")

conn.commit()
conn.close()
print("DB ready.")
