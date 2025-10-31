import datetime
import os
import sqlite3

db = os.path.abspath("dev.db")
scan_id = r"barcode_2c69d21d"
barcode = "079400751508"
conn = sqlite3.connect(db)
c = conn.cursor()
# upsert
row = c.execute("SELECT 1 FROM scan_history WHERE scan_id=? LIMIT 1", (scan_id,)).fetchone()
values = dict(
    scan_id=scan_id,
    product_name=None,
    brand=None,
    manufacturer=None,
    model_number=None,
    barcode=barcode,
    upc_gtin=None,
    category=None,
    scan_type="barcode",
    confidence_score=1.0,
    barcode_format="EAN13",
    verdict="safe",
    risk_level="low",
    recalls_found=0,
    recall_ids="[]",
    agencies_checked=39,
    allergen_alerts="[]",
    pregnancy_warnings="[]",
    age_warnings="[]",
    included_in_reports=0,
    created_at=datetime.datetime.utcnow().isoformat() + "Z",
)
if row:
    sets = ",".join([f"{k}=?" for k in values.keys()])
    c.execute(f"UPDATE scan_history SET {sets} WHERE scan_id=?", [*values.values(), scan_id])
else:
    cols = ",".join(values.keys())
    qs = ",".join(["?"] * len(values))
    c.execute(f"INSERT INTO scan_history ({cols}) VALUES ({qs})", list(values.values()))
conn.commit()
conn.close()
print("seeded scan_history for", scan_id)
