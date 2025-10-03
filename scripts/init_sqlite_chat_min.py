import os, sqlite3
DB = os.path.abspath("dev.db")
con = sqlite3.connect(DB)
cur = con.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS chat_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT,
    request_json TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT,
    result_json TEXT,
    created_at TEXT
);

-- Some builds also write generic conversation logs:
CREATE TABLE IF NOT EXISTS conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT,
    role TEXT,
    content TEXT,
    meta_json TEXT,
    created_at TEXT
);
""")

con.commit()
con.close()
print("✅ Local chat tables ensured at", DB)
