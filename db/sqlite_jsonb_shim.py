# sqlite_jsonb_shim.py
"""
Local dev helper: if DATABASE_URL uses sqlite, map SQLAlchemy's JSONB to JSON
so SQLite can create tables. No effect on Postgres/ECS.
"""

import os

DB_URL = os.getenv("DATABASE_URL", "")
if DB_URL.startswith("sqlite"):
    try:
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import JSON

        # monkey-patch: whenever code asks for JSONB, give it JSON instead
        import sqlalchemy.dialects.postgresql as pg_dialect

        pg_dialect.JSONB = JSONB  # keep name for type checks
        JSONB.impl = JSON  # tell SQLA to render SQLite-friendly JSON
        JSONB.cache_ok = True
        print("🔧 SQLite JSONB shim ACTIVE (local dev)")
    except Exception as e:
        print(f"⚠️ SQLite JSONB shim could not load: {e}")
else:
    # On Postgres / ECS, do nothing
    pass
