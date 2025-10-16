#!/usr/bin/env python3
import os

import psycopg2

print("Enabling pg_trgm extension...")
conn = psycopg2.connect(
    os.getenv(
        "DATABASE_URL",
        "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres",
    ),
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
