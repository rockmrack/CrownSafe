# init_sqlite_scan_history.py
import argparse
import datetime
import os
import sqlite3
from datetime import timezone

DB = os.path.abspath("dev.db")

schema = """
CREATE TABLE IF NOT EXISTS scan_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  scan_id TEXT UNIQUE,
  scan_timestamp TEXT,
  product_name TEXT,
  brand TEXT,
  barcode TEXT,
  model_number TEXT,
  upc_gtin TEXT,
  category TEXT,
  scan_type TEXT,
  confidence_score REAL,
  barcode_format TEXT,
  verdict TEXT,
  risk_level TEXT,
  recalls_found INTEGER,
  recall_ids TEXT,
  agencies_checked INTEGER,
  allergen_alerts TEXT,
  pregnancy_warnings TEXT,
  age_warnings TEXT,
  included_in_reports INTEGER,
  created_at TEXT
);
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-id", required=True)
    ap.add_argument("--barcode", required=True)
    # optional fields if you want to fill them
    ap.add_argument("--verdict", default="no_recalls")
    ap.add_argument("--risk", default="low")
    ap.add_argument("--format", default="EAN_13")
    ap.add_argument("--confidence", type=float, default=0.9)
    args = ap.parse_args()

    con = sqlite3.connect(DB)
    con.executescript(schema)

    # Insert or update the row for this scan
    con.execute(
        """
        INSERT INTO scan_history (
          user_id, scan_id, scan_timestamp, product_name, brand, barcode, model_number,
          upc_gtin, category, scan_type, confidence_score, barcode_format, verdict,
          risk_level, recalls_found, recall_ids, agencies_checked, allergen_alerts,
          pregnancy_warnings, age_warnings, included_in_reports, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scan_id) DO UPDATE SET
          barcode=excluded.barcode,
          confidence_score=excluded.confidence_score,
          barcode_format=excluded.barcode_format,
          verdict=excluded.verdict,
          risk_level=excluded.risk_level,
          recalls_found=excluded.recalls_found,
          created_at=excluded.created_at
    """,
        (
            1,  # user_id
            args.scan_id,
            datetime.datetime.now(datetime.UTC).isoformat() + "Z",  # scan_timestamp
            "Test Product",  # product_name
            "Test Brand",  # brand
            args.barcode,
            None,  # model_number
            args.barcode,  # upc_gtin (reuse barcode for local)
            "general",  # category
            "barcode",  # scan_type
            args.confidence,
            args.format,
            args.verdict,
            args.risk,
            0,  # recalls_found
            None,  # recall_ids
            39,  # agencies_checked (mock)
            None,
            None,
            None,  # allergen/pregnancy/age warnings
            0,  # included_in_reports
            datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        ),
    )
    con.commit()
    con.close()
    print(f"✅ scan_history ready; inserted scan_id={args.scan_id} into {DB}")


if __name__ == "__main__":
    main()
