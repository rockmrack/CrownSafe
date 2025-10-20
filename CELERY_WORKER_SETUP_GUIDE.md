# 🔧 CELERY WORKER SETUP & DATA INGESTION GUIDE

**Date:** October 20, 2025  
**Issue:** Celery worker running in Azure but no data in PostgreSQL or Redis  
**Status:** ✅ **ROOT CAUSE IDENTIFIED + SOLUTION PROVIDED**  
**Architecture:** 3-day recall refresh cycle (updated)

---

## 🎯 HOW BABYSHIELD WORKS (SIMPLE)

### **Searches (Mobile App)**
- ✅ **App NEVER calls agency APIs live**
- ✅ **App reads from PostgreSQL recalls database** → Fast & reliable
- ✅ **131,743+ recalls** available instantly (no API delays)

### **Updates (Background Process)**
- ✅ **Database refreshed every 3 days** by pulling new recalls from 39 agencies
- ✅ **Automatic** - runs in background via Celery Beat scheduler
- ✅ **Normalizes & deduplicates** data before storing

### **Celery's Role**

| Component         | Purpose         | What It Does                                                                  |
| ----------------- | --------------- | ----------------------------------------------------------------------------- |
| **Celery Beat**   | Timer/Scheduler | Drops a job onto Redis every 3 days at scheduled time                         |
| **Celery Worker** | Doer/Executor   | Picks job from Redis, fetches recalls, normalizes/dedupes, writes to Postgres |
| **Redis (Azure)** | Shared Queue    | Message broker between Beat and Worker (MUST use same Azure Redis URL)        |
| **PostgreSQL**    | Data Storage    | Stores normalized recall data for fast app searches                           |

---

## 🔄 DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                    EVERY 3 DAYS (2 AM UTC)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Celery Beat     │
                    │  (Scheduler)     │
                    └────────┬─────────┘
                             │ Drops job on queue
                             ▼
                    ┌──────────────────┐
                    │  Redis (Azure)   │
                    │  Message Broker  │
                    └────────┬─────────┘
                             │ Worker picks job
                             ▼
                    ┌──────────────────┐
                    │  Celery Worker   │
                    │  (Executor)      │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
  ┌──────────┐         ┌──────────┐        ┌──────────┐
  │  CPSC    │         │ EU Gate  │        │ FDA/etc  │
  │  API     │         │  API     │        │  APIs    │
  └────┬─────┘         └────┬─────┘        └────┬─────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │ Fetch recalls (last 3 days)
                            ▼
                   ┌─────────────────┐
                   │  Normalize &    │
                   │  Deduplicate    │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  PostgreSQL     │
                   │  (131,743+      │
                   │   recalls)      │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Update Redis   │
                   │  Cache          │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Mobile App     │
                   │  (Instant       │
                   │   Search)       │
                   └─────────────────┘
```

---

## 🎯 ANSWER TO YOUR QUESTION

Hi Ross,

**Root Cause:** The Celery worker is running, but **no tasks are being triggered**. The Celery worker is like a listener waiting for jobs, but there's **no scheduler (Celery Beat)** running to automatically trigger the periodic data ingestion tasks, and **no manual API calls** have been made to start ingestion.

**Think of it like this:**
- ✅ **Celery Worker** = Workers waiting at a factory (RUNNING in Azure)
- ❌ **Celery Beat** = The manager who assigns work schedules (NOT RUNNING)
- ❌ **Manual Triggers** = Manual work orders via API (NOT CALLED)

**Result:** Workers are idle because no one is telling them what to do.

---

## 📊 CURRENT SYSTEM ARCHITECTURE

### 1. **Celery Workers (Background Task Processors)**

**Purpose:** Execute background tasks like:
- Data ingestion from 39 regulatory agencies (CPSC, FDA, NHTSA, etc.)
- Risk score recalculation
- Company compliance profile updates
- Safety article fetching
- Image processing for visual search

**Current Status:** ✅ Running in Azure, but **IDLE** (no tasks assigned)

### 2. **Celery Beat (Periodic Task Scheduler)**

**Purpose:** Automatically trigger tasks on schedule:
- **Every 3 days at 2 AM UTC:** Sync ALL 39 agencies (`sync_all_agencies`)
- **Daily at 3 AM UTC:** Recalculate risk scores (`recalculate_high_risk_scores`)

**Current Status:** ❌ **NOT RUNNING** (no automatic task scheduling)

### 3. **Redis (Message Broker & Result Backend)**

**Purpose:** 
- Queue for pending Celery tasks
- Storage for task results
- Caching layer for API responses

**Configuration:**
```bash
REDIS_URL=redis://localhost:6379/0        # Default Redis connection
CELERY_BROKER_URL=redis://localhost:6379/1  # Celery task queue
CELERY_RESULT_BACKEND=redis://localhost:6379/2  # Celery results
```

**Current Status:** ✅ Running in Azure, but **EMPTY** (no tasks queued)

### 4. **PostgreSQL (Database)**

**Purpose:** Store ingested recall data, user data, scan history

**Current Status:** ✅ Running, but **NO RECALL DATA** (no ingestion triggered)

---

## 🚀 SOLUTION: 3 WAYS TO TRIGGER DATA INGESTION

### **Option 1: Start Celery Beat (Recommended for Production)**

**What It Does:** Automatically runs scheduled tasks (daily/hourly recall ingestion)

**How to Start:**

```bash
# In Azure Container or VM where Celery worker is running:

# Start Celery Beat scheduler (separate process from worker)
celery -A core_infra.risk_ingestion_tasks beat --loglevel=info

# Or combine worker + beat in one command:
celery -A core_infra.risk_ingestion_tasks worker --beat --loglevel=info
```

**Expected Outcome:**
- ✅ All recalls database refreshed every 3 days at 2 AM UTC
- ✅ Risk scores recalculated daily at 3 AM UTC (after any ingestion)
- ✅ Data automatically normalized and deduplicated
- ✅ Redis cache updated after each ingestion

**Logs You'll See:**
```
[2025-10-20 02:00:00] INFO: Starting CPSC sync for last 7 days
[2025-10-20 02:01:30] INFO: CPSC sync completed: 1,234 records processed
[2025-10-20 02:01:31] INFO: Recalculating risk scores for 456 products
```

---

### **Option 2: Manual API Trigger (Immediate Testing)**

**What It Does:** Manually trigger a one-time ingestion job via admin API

**Admin API Endpoints:**

#### **Trigger Ingestion:**
```bash
POST https://babyshield.cureviax.ai/api/v1/admin/ingest
Authorization: Bearer <ADMIN_JWT_TOKEN>
Content-Type: application/json

{
  "agency": "CPSC",
  "mode": "delta",
  "metadata": {
    "days_back": 30
  }
}
```

**Supported Agencies:**
- `CPSC` - US Consumer Product Safety Commission
- `FDA` - US Food & Drug Administration  
- `NHTSA` - US National Highway Traffic Safety Administration
- `EU_SAFETY_GATE` - European Union Safety Gate
- `TRANSPORT_CANADA` - Transport Canada
- `HEALTH_CANADA` - Health Canada
- *(See `IngestionRunner.SUPPORTED_AGENCIES` for full list)*

**Ingestion Modes:**
- `delta` - Fetch only recent updates (last 7-30 days)
- `full` - Full historical data fetch (WARNING: slow, large dataset)
- `incremental` - Smart incremental updates based on last run

**Response:**
```json
{
  "ok": true,
  "data": {
    "runId": "550e8400-e29b-41d4-a716-446655440000",
    "status": "started",
    "agency": "CPSC",
    "mode": "delta"
  }
}
```

#### **Check Ingestion Status:**
```bash
GET https://babyshield.cureviax.ai/api/v1/admin/runs/{runId}
Authorization: Bearer <ADMIN_JWT_TOKEN>
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "agency": "CPSC",
    "mode": "delta",
    "status": "running",  // or "success", "failed"
    "started_at": "2025-10-20T10:30:00Z",
    "finished_at": null,
    "total_items_processed": 1234,
    "errors": []
  }
}
```

#### **List Recent Ingestion Runs:**
```bash
GET https://babyshield.cureviax.ai/api/v1/admin/runs?limit=10&agency=CPSC
Authorization: Bearer <ADMIN_JWT_TOKEN>
```

#### **Check Data Freshness:**
```bash
GET https://babyshield.cureviax.ai/api/v1/admin/freshness
Authorization: Bearer <ADMIN_JWT_TOKEN>
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "summary": {
      "totalRecalls": 131743,
      "lastUpdate": "2025-10-20T08:45:30Z",
      "agencyCount": 39,
      "runningJobs": 1
    },
    "agencies": [
      {
        "agency": "CPSC",
        "total": 45678,
        "lastUpdated": "2025-10-20T02:01:30Z",
        "new24h": 23,
        "new7d": 145,
        "staleness": "fresh"
      }
    ]
  }
}
```

---

### **Option 3: Direct Python Script (For Development/Testing)**

**What It Does:** Run ingestion directly without API or Celery

**Method A: Using Celery Task Directly**

```python
# run_cpsc_ingestion.py
from core_infra.risk_ingestion_tasks import sync_cpsc_data

# Trigger immediate CPSC sync (last 30 days)
result = sync_cpsc_data(days_back=30)

print(f"Ingestion complete: {result}")
# Output: {'job_id': '...', 'status': 'completed', 'records_processed': 1234}
```

**Method B: Using Recall Connectors Directly**

```python
# direct_cpsc_fetch.py
import asyncio
from core_infra.safety_data_connectors import CPSCDataConnector
from datetime import datetime, timedelta

async def fetch_cpsc_data():
    connector = CPSCDataConnector()
    
    # Fetch last 30 days
    start_date = datetime.utcnow() - timedelta(days=30)
    records = await connector.fetch_recalls(start_date=start_date)
    
    print(f"Fetched {len(records)} recalls from CPSC")
    
    for record in records[:5]:  # Show first 5
        print(f"  - {record.product_name} ({record.recall_date})")
    
    return records

# Run it
records = asyncio.run(fetch_cpsc_data())
```

**Run Script:**
```bash
cd /path/to/babyshield-backend
python direct_cpsc_fetch.py
```

---

## 🔍 DIAGNOSTIC COMMANDS

### **Check if Celery Worker is Running:**

```bash
# In Azure VM/Container:
ps aux | grep celery

# Expected output:
# celery worker --app=core_infra.risk_ingestion_tasks --loglevel=info
```

### **Check if Celery Beat is Running:**

```bash
ps aux | grep "celery.*beat"

# If EMPTY: Celery Beat is NOT running (no auto-scheduling)
```

### **Check Redis Queue Status:**

```bash
# Connect to Redis
redis-cli

# Check pending tasks in Celery queue
LLEN celery

# Check result backend
KEYS celery-task-meta-*

# If both return 0 or empty: No tasks queued or completed
```

### **Check PostgreSQL Recall Count:**

```bash
# Connect to PostgreSQL
psql -h <HOST> -U <USER> -d <DATABASE>

# Count recalls
SELECT COUNT(*) FROM recalls_enhanced;

# If 0: No data ingested yet
# If > 130,000: Data already populated (good!)
```

### **Check Celery Worker Logs:**

```bash
# Azure Container Logs:
docker logs <container_id> | grep -i "celery\|task\|ingestion"

# Look for:
# - "Starting CPSC sync" = Task triggered
# - "CPSC sync completed" = Task finished
# - "No tasks" or "Idle" = Worker waiting for tasks
```

---

## ⚙️ PRODUCTION DEPLOYMENT GUIDE

### **Docker Compose Configuration:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: babyshield
      POSTGRES_USER: babyshield_user
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  celery_worker:
    build: .
    command: celery -A core_infra.risk_ingestion_tasks worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    depends_on:
      - redis
      - postgres
    volumes:
      - .:/app

  celery_beat:
    build: .
    command: celery -A core_infra.risk_ingestion_tasks beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - redis
      - postgres
    volumes:
      - .:/app

  api:
    build: .
    command: uvicorn api.main_babyshield:app --host 0.0.0.0 --port 8001
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8001:8001"
    depends_on:
      - redis
      - postgres

volumes:
  redis_data:
  postgres_data:
```

**Start Everything:**
```bash
docker-compose up -d
```

**Check Logs:**
```bash
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

---

## 🎯 RECOMMENDED IMMEDIATE ACTIONS

### **Step 1: Verify Current Status**

```bash
# Check if Celery Beat is running
ps aux | grep "celery.*beat"
# If empty → Need to start Celery Beat

# Check Redis queue
redis-cli LLEN celery
# If 0 → No pending tasks

# Check PostgreSQL data
psql -c "SELECT COUNT(*) FROM recalls_enhanced;"
# If 0 → No data yet
```

### **Step 2: Start Celery Beat (Recommended)**

```bash
# Start Celery Beat to enable auto-scheduling
celery -A core_infra.risk_ingestion_tasks beat --loglevel=info &

# Verify it started
ps aux | grep "celery.*beat"
```

**Expected Output:**
```
[2025-10-20 10:30:00] INFO: Beat: Starting...
[2025-10-20 10:30:01] INFO: Scheduler: Registered task daily-cpsc-sync (schedule: 2 AM UTC daily)
[2025-10-20 10:30:01] INFO: Scheduler: Registered task weekly-eu-sync (schedule: Monday 3 AM UTC)
[2025-10-20 10:30:01] INFO: Scheduler: Registered task hourly-risk-recalc (schedule: Every hour)
```

### **Step 3: Trigger Immediate Test Ingestion (Don't Wait for Schedule)**

**Option A: Via Admin API**

```bash
# Get admin JWT token first
curl -X POST https://babyshield.cureviax.ai/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@babyshield.dev",
    "password": "<ADMIN_PASSWORD>"
  }'

# Use the token to trigger ingestion
curl -X POST https://babyshield.cureviax.ai/api/v1/admin/ingest \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "agency": "CPSC",
    "mode": "delta",
    "metadata": {"days_back": 7}
  }'
```

**Option B: Direct Python Script**

```bash
cd /app  # Or wherever babyshield-backend is deployed

python3 << EOF
from core_infra.risk_ingestion_tasks import sync_cpsc_data
result = sync_cpsc_data(days_back=7)
print(f"Result: {result}")
EOF
```

### **Step 4: Monitor Progress**

```bash
# Watch Celery worker logs
tail -f /var/log/celery/worker.log

# Or if using Docker:
docker logs -f celery_worker

# Check PostgreSQL every 30 seconds:
watch -n 30 'psql -c "SELECT COUNT(*) FROM recalls_enhanced;"'
```

**Expected Progress:**
```
[10:30:00] INFO: Starting CPSC sync for last 7 days
[10:30:15] INFO: Fetching recalls from CPSC API...
[10:31:00] INFO: Fetched 234 records
[10:31:30] INFO: Processing record 1/234: Baby Crib Recall
[10:32:00] INFO: Processing record 50/234: Stroller Recall
[10:33:30] INFO: CPSC sync completed: 234 records processed
[10:33:31] INFO: Triggering risk recalculation for 234 products
[10:34:00] INFO: Risk recalculation complete
```

### **Step 5: Verify Data in Database**

```bash
# Connect to PostgreSQL
psql -h <HOST> -U <USER> -d <DATABASE>

# Check recall count
SELECT COUNT(*) FROM recalls_enhanced;
-- Should show > 0 if ingestion worked

# Show recent recalls
SELECT product_name, source_agency, recall_date 
FROM recalls_enhanced 
ORDER BY last_updated DESC 
LIMIT 10;

# Check by agency
SELECT source_agency, COUNT(*) 
FROM recalls_enhanced 
GROUP BY source_agency;
```

**Expected Output:**
```
 source_agency | count 
---------------+-------
 CPSC          | 45678
 FDA           | 23456
 NHTSA         | 12345
 EU_SAFETY_GATE| 34567
 (39 rows)
```

---

## 🐛 TROUBLESHOOTING

### **Problem 1: Celery Worker Shows "No tasks received"**

**Cause:** Celery Beat not running, or no manual triggers

**Solution:**
```bash
# Start Celery Beat
celery -A core_infra.risk_ingestion_tasks beat --loglevel=info &

# OR manually trigger via API (see Option 2 above)
```

---

### **Problem 2: Redis Connection Refused**

**Symptom:** `ConnectionError: Error 111 connecting to localhost:6379`

**Cause:** Redis not running or wrong REDIS_URL

**Solution:**
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server &

# Update environment variable
export REDIS_URL="redis://<AZURE_REDIS_HOST>:6379/0"
export CELERY_BROKER_URL="redis://<AZURE_REDIS_HOST>:6379/1"
```

---

### **Problem 3: PostgreSQL Connection Error**

**Symptom:** `OperationalError: could not connect to server`

**Solution:**
```bash
# Check PostgreSQL is running
pg_isready -h <HOST> -p 5432

# Update DATABASE_URL
export DATABASE_URL="postgresql://user:password@<AZURE_PG_HOST>:5432/babyshield"
```

---

### **Problem 4: Tasks Fail with "No module named 'core_infra'"**

**Cause:** Python path not configured

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH=/app:$PYTHONPATH

# Or run from project root
cd /app
celery -A core_infra.risk_ingestion_tasks worker --loglevel=info
```

---

## 📈 MONITORING & ALERTS

### **Key Metrics to Monitor:**

1. **Celery Worker Status**
   ```bash
   celery -A core_infra.risk_ingestion_tasks inspect active
   # Should show active tasks when ingestion running
   ```

2. **Redis Queue Length**
   ```bash
   redis-cli LLEN celery
   # Should be 0 when idle, > 0 when tasks queued
   ```

3. **Database Freshness**
   ```bash
   curl https://babyshield.cureviax.ai/api/v1/admin/freshness
   # Check "new24h" and "staleness" fields
   ```

4. **Failed Tasks**
   ```bash
   celery -A core_infra.risk_ingestion_tasks inspect failed
   # Should be empty []
   ```

### **Set Up Alerts:**

```python
# Add to monitoring system (e.g., Prometheus, Datadog)
# Alert if:
# - No data ingested in 24 hours
# - Celery worker down for > 5 minutes
# - Task failure rate > 5%
# - Redis queue length > 100 (tasks backing up)
```

---

## ✅ SUCCESS CRITERIA

**You'll know the system is working when:**

1. ✅ **Celery Beat is running** and scheduling tasks
2. ✅ **Celery Worker logs show** "Starting CPSC sync..." messages
3. ✅ **Redis shows task activity** (LLEN celery > 0 during ingestion)
4. ✅ **PostgreSQL recalls_enhanced table** has > 130,000 rows
5. ✅ **Admin API `/freshness` endpoint** shows recent data (new24h > 0)
6. ✅ **Mobile app search** returns recall results

---

## 🎓 SUMMARY

**Your Current Situation:**
- ✅ Celery Worker: RUNNING (idle, waiting for tasks)
- ❌ Celery Beat: NOT RUNNING (no auto-scheduling)
- ✅ Redis: RUNNING (empty, no tasks queued)
- ✅ PostgreSQL: RUNNING (empty, no data ingested)

**Root Cause:**
- No one is telling the workers what to do (no Beat scheduler, no manual triggers)

**Solution:**
1. **Start Celery Beat** for automatic daily/hourly ingestion
2. **OR** manually trigger via Admin API for immediate testing
3. Monitor logs to confirm data ingestion is working

**Next Step:**
Choose Option 1 (Celery Beat) for production, or Option 2 (Manual API) for immediate testing.

---

**Questions?** Contact: dev@babyshield.dev  
**Documentation:** See `core_infra/risk_ingestion_tasks.py` for task definitions
