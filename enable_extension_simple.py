#!/usr/bin/env python3
import os

import psycopg2

print("Enabling pg_trgm extension...")
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. Please set it to your PostgreSQL connection string."
    )
conn = psycopg2.connect(
    database_url,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
print("✅ Extension enabled")
cur.execute("SELECT similarity('baby', 'baby');")
result = cur.fetchone()
if result:
    print(f"Test similarity: {result[0]}")
cur.close()
conn.close()
print("Done!")
