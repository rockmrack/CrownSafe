# Testing Guide for Azure Docker Compose

This guide provides step-by-step testing commands for the Azure Celery deployment.

## Prerequisites

1. Create `.env.azure` from `.env.azure.example` with actual credentials
2. Ensure Docker and Docker Compose are installed
3. Ensure `.env.azure` is gitignored (never commit secrets!)

## Test 1: Validate Environment Variable Substitution

Verify docker-compose configuration is valid and all environment variables are correctly substituted:

```bash
docker compose -f docker-compose.azure.yml --env-file .env.azure config
```

**Expected Result:**
- No syntax errors
- Environment variables are replaced with actual values
- Redis URLs use `rediss://` (TLS) on port 6380
- PostgreSQL password is URL-encoded

## Test 2: Start Services

Start both Beat scheduler and Worker:

```bash
docker compose -f docker-compose.azure.yml --env-file .env.azure up -d beat worker
```

**Expected Result:**
- Both containers start successfully
- No immediate errors in startup

## Test 3: Verify Beat Scheduler Logs

Check Beat logs to confirm scheduler is running and tasks are registered:

```bash
docker compose -f docker-compose.azure.yml logs -f beat
```

**Expected Output:**
```
celery beat v5.3.4 (emerald-rush) is starting.
Configuration ->
    . broker -> rediss://default:***@redis-eastus2-dev.redis.cache.windows.net:6380/0
    . scheduler -> celery.beat.PersistentScheduler
[INFO] beat: Starting...
[INFO] Scheduler: Registered task refresh-all-recalls-every-3-days
  Schedule: <crontab: 0 2 */3 * * (m/h/d/dM/MY)>
[INFO] Scheduler: Registered task daily-risk-recalc
  Schedule: <crontab: 0 3 * * * (m/h/d/dM/MY)>
```

**What to Check:**
- Beat started successfully
- Connected to Azure Redis (rediss:// with port 6380)
- Tasks registered: `refresh-all-recalls-every-3-days` and `daily-risk-recalc`
- Schedule shows 3-day crontab: `0 2 */3 * *`

## Test 4: Verify Worker Registered Tasks

Confirm worker has registered all tasks from `risk_ingestion_tasks`:

```bash
docker compose -f docker-compose.azure.yml exec worker \
  celery -A core_infra.risk_ingestion_tasks:celery_app inspect registered | grep risk_ingestion_tasks
```

**Expected Output:**
```
risk_ingestion_tasks.sync_all_agencies
risk_ingestion_tasks.recalculate_high_risk_scores
risk_ingestion_tasks.sync_cpsc_data
risk_ingestion_tasks.sync_eu_safety_gate
risk_ingestion_tasks.recalculate_affected_products
risk_ingestion_tasks.update_company_compliance
risk_ingestion_tasks.send_risk_alerts
risk_ingestion_tasks.enrich_product_from_barcode
```

**What to Check:**
- Worker recognizes all `risk_ingestion_tasks.*` tasks
- No "NotRegistered" errors
- Tasks are from correct Celery app

## Test 5: Manual Task Trigger (End-to-End)

Manually trigger a task to verify the complete pipeline works:

```bash
docker compose -f docker-compose.azure.yml exec worker \
  python -c "from core_infra.risk_ingestion_tasks import recalculate_high_risk_scores as t; print(t.delay().id)"
```

**Expected Output:**
- Returns a task ID (UUID format): `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

Then monitor worker logs:

```bash
docker compose -f docker-compose.azure.yml logs -f worker
```

**Expected in Worker Logs:**
```
[INFO] Task risk_ingestion_tasks.recalculate_high_risk_scores[<task-id>] received
[INFO] Task risk_ingestion_tasks.recalculate_high_risk_scores[<task-id>] succeeded in 0.12s
```

**What to Check:**
- Task is received by worker
- Task executes successfully (no errors)
- Task completes and reports success

## Test 6: Verify Schedule (Optional)

Run the sanity check script to print registered schedule:

```bash
docker compose -f docker-compose.azure.yml exec worker \
  python scripts/print_celery_schedule.py
```

**Expected Output:**
```python
{
  'refresh-all-recalls-every-3-days': 'risk_ingestion_tasks.sync_all_agencies',
  'daily-risk-recalc': 'risk_ingestion_tasks.recalculate_high_risk_scores'
}
```

## Cleanup

Stop and remove containers:

```bash
docker compose -f docker-compose.azure.yml down
```

## Troubleshooting

### Issue: "NotRegistered" Error

**Symptom:** Worker shows `NotRegistered` exception for tasks.

**Solution:**
- Verify worker command uses `core_infra.risk_ingestion_tasks:celery_app`
- Check `CELERY_IMPORTS` environment variable is set
- Ensure both Beat and Worker use the same Celery app

### Issue: Redis Connection Failed

**Symptom:** `ConnectionError: Error connecting to Redis`

**Solution:**
- Verify Redis URL uses `rediss://` (TLS) on port 6380
- Check Azure Redis access key is correct
- Ensure Azure Redis firewall allows your IP

### Issue: PostgreSQL Connection Failed

**Symptom:** `OperationalError: could not connect to server`

**Solution:**
- Verify password is URL-encoded (special characters like `(`, `)`, `?`, `*`)
- Check Azure PostgreSQL firewall allows your IP
- Verify `sslmode=require` is in connection string

### Issue: Beat Not Scheduling Tasks

**Symptom:** Beat logs don't show "Scheduler: Sending due task"

**Solution:**
- Verify Beat is using correct Redis URL (same as worker)
- Check schedule in `core_infra/risk_ingestion_tasks.py`
- Confirm Beat has read access to celerybeat-schedule file

## Success Criteria

All tests pass when:

✅ Configuration validates without errors  
✅ Beat connects to Azure Redis with TLS  
✅ Beat registers 3-day schedule correctly  
✅ Worker registers all `risk_ingestion_tasks.*` tasks  
✅ Manual task trigger executes successfully  
✅ No "NotRegistered" or connection errors  
✅ Logs show UTC timezone configuration  

## Next Steps

After local testing succeeds:

1. Deploy to Azure Container Instances or Azure App Service
2. Monitor first scheduled run (every 3 days at 2 AM UTC)
3. Verify PostgreSQL database populates with recalls
4. Set up alerting for task failures
5. Configure log aggregation for production monitoring
