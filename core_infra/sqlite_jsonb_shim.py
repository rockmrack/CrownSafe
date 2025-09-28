import os
ENV = os.getenv("ENVIRONMENT", "").lower()
DB  = os.getenv("DATABASE_URL", "")
ACTIVE = ENV == "local" and DB.startswith("sqlite")
if ACTIVE:
    import logging
    logging.getLogger(__name__).warning("🔧 SQLite JSONB shim ACTIVE (local dev)")
