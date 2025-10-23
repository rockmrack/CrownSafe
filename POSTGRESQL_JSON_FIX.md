# PostgreSQL JSON DISTINCT Fix - Deployed

## Problem Identified by Pavlo

**Error in Production:**
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedFunction) 
could not identify an equality operator for type json
LINE 1: ...ry AS product_golden_records_product_subcategory, product_go...
```

**Root Cause:**
- `recalculate_affected_products` task was doing `DISTINCT` on full `ProductGoldenRecord` rows
- `ProductGoldenRecord` has several `json` type columns (additional_images, qr_code_data, certifications, etc.)
- PostgreSQL's `json` type has no equality operator defined, so `DISTINCT` fails

## Fix Applied (Commit 79adf2e)

**Changed Query Pattern:**
```python
# OLD (BROKEN - DISTINCT on json columns):
recent_products = (
    db.query(ProductGoldenRecord)
    .join(SafetyIncident)
    .filter(SafetyIncident.created_at >= cutoff_date)
    .distinct()  # ❌ Fails on json columns
    .all()
)

# NEW (FIXED - DISTINCT on IDs only):
# Step 1: Get distinct product IDs (scalar column - safe)
product_ids_subquery = (
    db.query(ProductGoldenRecord.id)
    .join(SafetyIncident)
    .filter(SafetyIncident.created_at >= cutoff_date)
    .distinct()  # ✅ Safe - ID is UUID/string
    .subquery()
)

# Step 2: Fetch full rows by joining on IDs
recent_products = (
    db.query(ProductGoldenRecord)
    .join(product_ids_subquery, ProductGoldenRecord.id == product_ids_subquery.c.id)
    .all()
)
```

**Why This Works:**
- PostgreSQL can perform `DISTINCT` on scalar types (UUID, string, integer, etc.)
- We first get distinct IDs (no json columns involved)
- Then fetch full records by joining on those IDs
- Result: Same products, no json equality comparison

## Deployment Instructions for Pavlo

### 1. Pull Latest Code
```bash
cd /path/to/babyshield-backend
git pull origin main
```

**Verify you have commit `79adf2e`:**
```bash
git log -1 --oneline
# Should show: 79adf2e fix: avoid DISTINCT on json columns in recalculate_affected_products
```

### 2. Rebuild Worker Container
```bash
docker compose -f docker-compose.azure.yml --env-file .env.azure build worker
```

**Why rebuild:**
- The fix is in `core_infra/risk_ingestion_tasks.py`
- This file is baked into the worker container image
- Must rebuild to include the fix

### 3. Restart Worker (No Need to Restart Beat)
```bash
docker compose -f docker-compose.azure.yml --env-file .env.azure up -d worker
```

**Beat can keep running:**
- Beat just schedules tasks (drops them on Redis)
- Worker picks tasks from Redis and executes them
- Only worker needs the fixed code

### 4. Test the Fix

**Manual trigger of the failing task:**
```bash
docker compose -f docker-compose.azure.yml exec worker \
  python -c "from core_infra.risk_ingestion_tasks import recalculate_affected_products as t; print(t.delay().id)"
```

**Expected output:**
```
<task-uuid>  # e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Watch logs for success:**
```bash
docker compose -f docker-compose.azure.yml logs -f worker
```

**Expected logs (SUCCESS):**
```
[INFO] Task risk_ingestion_tasks.recalculate_affected_products[<task-id>] received
[INFO] Recalculating risk scores for products updated in last 7 days
[INFO] Updated risk scores for N products
[INFO] Task risk_ingestion_tasks.recalculate_affected_products[<task-id>] succeeded in X.XXs
```

**Should NOT see:**
```
❌ psycopg2.errors.UndefinedFunction: could not identify an equality operator for type json
```

### 5. Verify Task in Redis

**Check task result:**
```bash
# Get task ID from step 4 output
TASK_ID="<paste-task-id-here>"

docker compose -f docker-compose.azure.yml exec worker \
  python -c "from celery.result import AsyncResult; from core_infra.risk_ingestion_tasks import celery_app; r = AsyncResult('$TASK_ID', app=celery_app); print(f'Status: {r.status}'); print(f'Result: {r.result}')"
```

**Expected:**
```
Status: SUCCESS
Result: {'products_updated': <number>}
```

## Additional Context

### Why NotRegistered Errors Happened (Confirmed)

**Previous Issue:**
- Beat was started with wrong Celery app: `core_infra.celery_tasks`
- Scheduled tasks are defined in: `core_infra.risk_ingestion_tasks:celery_app`
- Beat tried to schedule tasks not registered in `celery_tasks` → NotRegistered errors

**Fixed in docker-compose.azure.yml:**
```yaml
services:
  beat:
    command: celery -A core_infra.risk_ingestion_tasks:celery_app beat  # ✅ Correct
  worker:
    command: celery -A core_infra.risk_ingestion_tasks:celery_app worker  # ✅ Correct
```

**Key Point:**
Tasks live in `risk_ingestion_tasks.py`, so both Beat and Worker **must** use `core_infra.risk_ingestion_tasks:celery_app`. Using `core_infra.celery_tasks` will bring back NotRegistered errors.

## All Fixes Now Deployed (Complete List)

1. ✅ **Redis TLS** (commit f5c5c7f) - Changed redis:// to rediss://...6380
2. ✅ **Password URL Encoding** (commit f5c5c7f) - Encoded special characters
3. ✅ **Secrets Externalized** (commit f5c5c7f) - Moved to .env.azure
4. ✅ **Correct Celery App** (commit f5c5c7f) - risk_ingestion_tasks:celery_app for both services
5. ✅ **SSL Certificate Validation** (commit 62930d8) - Added ?ssl_cert_reqs=none to Redis URLs
6. ✅ **PostgreSQL JSON DISTINCT** (commit 79adf2e) - Fixed query to avoid DISTINCT on json columns

## Optional: Long-term Improvement (Not Urgent)

**Convert `json` to `jsonb` in PostgreSQL:**

**Benefits:**
- `jsonb` has equality operator (supports DISTINCT)
- Better performance (binary storage, indexable)
- Enables GIN indexes for JSON queries

**Migration (Alembic):**
```python
# alembic/versions/YYYYMMDD_convert_json_to_jsonb.py

def upgrade():
    op.execute("""
        ALTER TABLE product_golden_records
          ALTER COLUMN additional_images            TYPE jsonb USING additional_images::jsonb,
          ALTER COLUMN qr_code_data                 TYPE jsonb USING qr_code_data::jsonb,
          ALTER COLUMN certifications               TYPE jsonb USING certifications::jsonb,
          ALTER COLUMN safety_standards             TYPE jsonb USING safety_standards::jsonb,
          ALTER COLUMN source_records               TYPE jsonb USING source_records::jsonb,
          ALTER COLUMN manufacturing_date_range     TYPE jsonb USING manufacturing_date_range::jsonb
    """)

def downgrade():
    op.execute("""
        ALTER TABLE product_golden_records
          ALTER COLUMN additional_images            TYPE json USING additional_images::json,
          ALTER COLUMN qr_code_data                 TYPE json USING qr_code_data::json,
          ALTER COLUMN certifications               TYPE json USING certifications::json,
          ALTER COLUMN safety_standards             TYPE json USING safety_standards::json,
          ALTER COLUMN source_records               TYPE json USING source_records::json,
          ALTER COLUMN manufacturing_date_range     TYPE json USING manufacturing_date_range::json
    """)
```

**Not required now** - the code fix handles it. But consider for future optimization.

## Summary

**What was fixed:**
- Query pattern changed to avoid DISTINCT on json columns
- No database migration required
- Code-only fix in `core_infra/risk_ingestion_tasks.py`

**What you need to do:**
1. Pull latest code (commit 79adf2e)
2. Rebuild worker container
3. Restart worker
4. Test with manual trigger
5. Verify success in logs and Redis

**Expected result:**
- `recalculate_affected_products` task completes successfully
- No more "could not identify an equality operator for type json" errors
- All 3 tasks in Beat schedule should now work (sync_all_agencies, recalculate_affected_products, recalculate_high_risk_scores)

---

**Deployed:** October 22, 2025  
**Commit:** 79adf2e  
**Status:** ✅ Ready for production testing
