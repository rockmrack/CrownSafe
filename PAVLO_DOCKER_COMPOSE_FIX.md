# Response to Pavlo - Corrected Docker Compose Commands

## 🐛 Issues Found in Your Docker Compose File

### Issue 1: Beat Service Running Worker Command ❌
```yaml
# WRONG (in your file):
beat:
  command: celery -A core_infra.risk_ingestion_tasks:celery_app worker -l debug
```

**Problem:** The Beat service is running a `worker` command instead of `beat`. Beat is the scheduler (timer), not a task executor.

**Fix:**
```yaml
# CORRECT:
beat:
  command: celery -A core_infra.risk_ingestion_tasks:celery_app beat --loglevel=info
```

### Issue 2: Worker Pointing to Wrong Celery App ❌
```yaml
# WRONG (in your file):
worker:
  command: celery -A core_infra.celery_tasks:app worker -l debug
```

**Problem:** You're using `core_infra.celery_tasks:app` which is for **image processing tasks** (visual agent). The recall sync tasks are in `core_infra.risk_ingestion_tasks:celery_app`.

**Fix:**
```yaml
# CORRECT:
worker:
  command: celery -A core_infra.risk_ingestion_tasks:celery_app worker --loglevel=info --concurrency=4
```

### Issue 3: NotRegistered Error Explained
```json
{"exc_type": "NotRegistered", "exc_message": ["risk_ingestion_tasks.recalculate_high_risk_scores"]}
```

**Root Cause:** When you used `celery -A core_infra.celery_tasks beat`, Beat found the schedule in `risk_ingestion_tasks.py` but tried to queue tasks that don't exist in `celery_tasks.py`. The two Celery apps are separate:

- **`core_infra.celery_tasks:app`** - Image processing tasks (barcode scanning, visual recognition)
- **`core_infra.risk_ingestion_tasks:celery_app`** - Recall sync tasks (CPSC, EU, risk recalc) ← **This is what you need**

---

## ✅ Corrected Commands for Testing

I've created a corrected `docker-compose.azure.yml` file in your repo. Use it with:

### Start Both Services:
```bash
docker-compose -f docker-compose.azure.yml up -d
```

### View Logs:
```bash
# Beat scheduler logs (should show "Scheduler: Registered task refresh-all-recalls-every-3-days")
docker-compose -f docker-compose.azure.yml logs -f beat

# Worker logs (should show "celery@worker ready")
docker-compose -f docker-compose.azure.yml logs -f worker
```

### Stop Services:
```bash
docker-compose -f docker-compose.azure.yml down
```

### Manual Commands (if you prefer running containers separately):

**Beat Scheduler:**
```bash
docker run --rm \
  -e DATABASE_URL="postgresql://pgadmin:LWJE6fTl(At*E)?c@psql-eastus2-dev.postgres.database.azure.com:5432/babyshield-prod-db?sslmode=require" \
  -e CELERY_BROKER_URL="redis://default:ghLOhuWN6asDosIXyt6r5GJJWBD0l3szvAzCaKFZC2c=@redis-eastus2-dev.redis.cache.windows.net:6379/0" \
  -e CELERY_RESULT_BACKEND="redis://default:ghLOhuWN6asDosIXyt6r5GJJWBD0l3szvAzCaKFZC2c=@redis-eastus2-dev.redis.cache.windows.net:6379/0" \
  <your-image> \
  celery -A core_infra.risk_ingestion_tasks:celery_app beat --loglevel=info
```

**Worker:**
```bash
docker run --rm \
  -e DATABASE_URL="postgresql://pgadmin:LWJE6fTl(At*E)?c@psql-eastus2-dev.postgres.database.azure.com:5432/babyshield-prod-db?sslmode=require" \
  -e CELERY_BROKER_URL="redis://default:ghLOhuWN6asDosIXyt6r5GJJWBD0l3szvAzCaKFZC2c=@redis-eastus2-dev.redis.cache.windows.net:6379/0" \
  -e CELERY_RESULT_BACKEND="redis://default:ghLOhuWN6asDosIXyt6r5GJJWBD0l3szvAzCaKFZC2c=@redis-eastus2-dev.redis.cache.windows.net:6379/0" \
  <your-image> \
  celery -A core_infra.risk_ingestion_tasks:celery_app worker --loglevel=info --concurrency=4
```

---

## 📊 What to Expect After Fix

### Beat Scheduler Logs:
```
celery beat v5.3.4 (emerald-rush) is starting.
Configuration ->
    . broker -> redis://default:***@redis-eastus2-dev.redis.cache.windows.net:6379/0
    . scheduler -> celery.beat.PersistentScheduler
[INFO] beat: Starting...
[INFO] Scheduler: Registered task refresh-all-recalls-every-3-days
  Schedule: <crontab: 0 2 */3 * * (m/h/d/dM/MY)>
[INFO] Scheduler: Registered task daily-risk-recalc
  Schedule: <crontab: 0 3 * * * (m/h/d/dM/MY)>
```

### Worker Logs:
```
celery@worker v5.3.4 (emerald-rush)
[config]
    . broker -> redis://default:***@redis-eastus2-dev.redis.cache.windows.net:6379/0
    . app -> risk_assessment:0x...
    . concurrency -> 4 (prefork)
    . task events -> ON

[tasks]
  . risk_ingestion_tasks.recalculate_high_risk_scores
  . risk_ingestion_tasks.sync_all_agencies
  . risk_ingestion_tasks.sync_cpsc_data
  . risk_ingestion_tasks.sync_eu_safety_gate
  . risk_ingestion_tasks.update_company_compliance

[INFO] celery@worker ready.
```

### Redis Data (Check with redis-cli):
```bash
# Connect to Azure Redis
redis-cli -h redis-eastus2-dev.redis.cache.windows.net -p 6379 -a ghLOhuWN6asDosIXyt6r5GJJWBD0l3szvAzCaKFZC2c=

# Check for scheduled tasks (Beat puts entries here)
> KEYS celery-task-meta-*
> KEYS celery-beat-*

# Check for pending jobs
> LLEN celery
```

### PostgreSQL Data:
After the worker runs (every 3 days at 2 AM UTC, or manually triggered):
```sql
-- Check recall count (should increase)
SELECT COUNT(*) FROM recalls_enhanced;

-- Check recent updates
SELECT MAX(last_updated) FROM recalls_enhanced;
```

---

## 🔍 Architecture Summary

```
┌─────────────────┐
│   Celery Beat   │ ← Timer/Scheduler (runs every 3 days)
│ (risk_ingestion)│
└────────┬────────┘
         │ Puts job on Redis at 2 AM UTC every 3 days
         ▼
┌─────────────────┐
│  Azure Redis    │ ← Shared message queue (DB index /0)
│   (eastus2)     │
└────────┬────────┘
         │ Worker picks job from queue
         ▼
┌─────────────────┐
│  Celery Worker  │ ← Task executor
│ (risk_ingestion)│   - Fetches from 39 agencies
└────────┬────────┘   - Normalizes/deduplicates
         │            - Writes to PostgreSQL
         ▼
┌─────────────────┐
│ Azure PostgreSQL│ ← Persistent storage
│ (babyshield-db) │   App reads from here (NOT live APIs)
└─────────────────┘
```

**Key Points:**
- **Beat and Worker MUST use the same Redis URL and DB index** (`/0`)
- **Beat triggers jobs**, Worker executes them
- **App serves from PostgreSQL**, never calls APIs live
- **Sync runs every 3 days** at 2 AM UTC (next: Oct 23, 26, 29...)

---

## 🚀 Quick Test (Manual Trigger)

Don't want to wait 3 days? Manually trigger a sync:

```python
# Inside your container or Python environment:
from core_infra.risk_ingestion_tasks import sync_all_agencies

# Sync last 3 days of recalls from all agencies
result = sync_all_agencies(days_back=3)
print(result)
```

Or via admin API endpoint (if implemented):
```bash
curl -X POST https://your-api.com/api/v1/admin/ingest \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"days_back": 3}'
```

---

## 📝 Summary of Changes

| Component | Old Command | New Command | Why |
|-----------|-------------|-------------|-----|
| Beat | `worker -l debug` | `beat --loglevel=info` | Beat schedules, doesn't execute |
| Worker | `celery_tasks:app` | `risk_ingestion_tasks:celery_app` | Need recall sync tasks, not image tasks |
| Both | Mixed Celery apps | Same app for both | Tasks must be registered in same app |

---

**Files Updated:**
- ✅ `docker-compose.azure.yml` - Corrected Azure production config
- ✅ This explanation document

**Next Steps:**
1. Pull latest code from repo (includes corrected docker-compose.azure.yml)
2. Run `docker-compose -f docker-compose.azure.yml up -d`
3. Check logs to verify Beat registered the 3-day schedule
4. Optionally manually trigger sync to test immediately
5. Wait for automatic sync on Oct 23 at 2 AM UTC

Let me know if you see any errors in the logs!

— Ross
