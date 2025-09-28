import sqlite3, argparse, os, sys

REQUIRED_COLS = {
    # name                  sql type   default
    "scan_id":              ("TEXT",   None),
    "product_name":         ("TEXT",   None),
    "brand":                ("TEXT",   None),
    "manufacturer":         ("TEXT",   None),
    "model_number":         ("TEXT",   None),
    "barcode":              ("TEXT",   None),
    "upc_gtin":             ("TEXT",   None),
    "category":             ("TEXT",   None),
    "scan_type":            ("TEXT",   None),
    "confidence_score":     ("REAL",   1.0),
    "barcode_format":       ("TEXT",   None),
    "verdict":              ("TEXT",   "safe"),
    "risk_level":           ("TEXT",   "low"),
    "recalls_found":        ("INTEGER",0),
    "recall_ids":           ("TEXT",   "[]"),
    "agencies_checked":     ("INTEGER",39),
    "allergen_alerts":      ("TEXT",   "[]"),
    "pregnancy_warnings":   ("TEXT",   "[]"),
    "age_warnings":         ("TEXT",   "[]"),
    "included_in_reports":  ("INTEGER",0),
    "created_at":           ("TEXT",   None)
}

def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY,
            scan_id TEXT
        )
    """)
    conn.commit()

def colnames(conn):
    return {r[1] for r in conn.execute("PRAGMA table_info('scan_history')")}

def add_missing_cols(conn):
    have = colnames(conn)
    missing = [c for c in REQUIRED_COLS.keys() if c not in have]
    for c in missing:
        sqltype, default = REQUIRED_COLS[c]
        conn.execute(f"ALTER TABLE scan_history ADD COLUMN {c} {sqltype}")
    if missing:
        conn.commit()
    return missing

def upsert_row(conn, scan_id, barcode):
    # try to update existing; else insert
    row = conn.execute("SELECT 1 FROM scan_history WHERE scan_id=? LIMIT 1",(scan_id,)).fetchone()
    values = {k: v[1] for k, v in REQUIRED_COLS.items()}
    values["scan_id"] = scan_id
    values["barcode"] = barcode
    placeholders = ",".join([f"{k}=?" for k in values.keys()])
    if row:
        conn.execute(f"UPDATE scan_history SET {placeholders} WHERE scan_id=?",
                     [values[k] for k in values.keys()] + [scan_id])
    else:
        cols = ",".join(values.keys())
        qs = ",".join(["?"]*len(values))
        conn.execute(f"INSERT INTO scan_history ({cols}) VALUES ({qs})",
                     [values[k] for k in values.keys()])
    conn.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="dev.db")
    ap.add_argument("--scan-id", required=True)
    ap.add_argument("--barcode", required=True)
    args = ap.parse_args()

    db = os.path.abspath(args.db)
    conn = sqlite3.connect(db)
    try:
        ensure_table(conn)
        missing = add_missing_cols(conn)
        upsert_row(conn, args.scan_id, args.barcode)
        print(f"✅ scan_history OK (added: {missing}) for scan_id={args.scan_id} in {db}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
