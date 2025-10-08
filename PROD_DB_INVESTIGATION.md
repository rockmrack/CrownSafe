# Production Database Investigation Results

**Date:** October 8, 2025  
**Status:** Connection Blocked

---

## Issue Encountered

**Cannot connect to production database from local machine:**
- RDS Instance: `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- Error: Connection timed out
- Reason: Security group restricts access to AWS resources only

---

## Alternative Investigation Methods

### Method 1: Connect via ECS Exec (Recommended)
```bash
# Enable ECS Exec on the service (if not already enabled)
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --enable-execute-command \
  --region eu-north-1

# Get running task ID
TASK_ID=$(aws ecs list-tasks --cluster babyshield-cluster --service-name babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'taskArns[0]' --output text)

# Connect to the container
aws ecs execute-command \
  --cluster babyshield-cluster \
  --task $TASK_ID \
  --container babyshield-backend \
  --command "/bin/bash" \
  --interactive \
  --region eu-north-1

# Once connected, check database:
python3 -c "
from core_infra.database import engine
from sqlalchemy import inspect, text
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
with engine.connect() as conn:
    result = conn.execute(text('SELECT extname FROM pg_extension WHERE extname=\\'pg_trgm\\''))
    print('pg_trgm:', result.fetchone())
"
```

### Method 2: Check CloudWatch Logs
```bash
# Get recent error logs
aws logs tail /ecs/babyshield-backend \
  --follow \
  --since 1h \
  --filter-pattern "ERROR" \
  --region eu-north-1
```

### Method 3: Deploy New Image and Monitor
Since we just built and pushed `production-20251008-1828`, let's deploy it and see if the issue persists.

---

## Recommended Next Steps

### ✅ **Option 2: Deploy New Image** (Proceed Now)

The new image includes:
- All recent code fixes
- Updated search service
- Better error handling
- Database schema validation

**Deploy Command:**
```bash
# Update ECS service with latest image
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --force-new-deployment \
  --region eu-north-1
```

**Monitor Deployment:**
```bash
# Watch deployment progress
aws ecs describe-services \
  --cluster babyshield-cluster \
  --services babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1 \
  --query 'services[0].{rolloutState:deployments[0].rolloutState,runningCount:runningCount}' \
  --output table
```

**Check Logs After Deployment:**
```bash
aws logs tail /ecs/babyshield-backend \
  --follow \
  --since 2m \
  --region eu-north-1
```

---

## Expected Outcomes

### If Issue is Fixed:
- ✅ Smoke tests will pass
- ✅ `/api/v1/search/advanced` with agencies filter returns 200
- ✅ All 8 endpoints working

### If Issue Persists:
- Need to use ECS Exec to investigate database schema
- Check if migrations need to be run
- Verify pg_trgm extension is installed

---

## Action Plan

1. **Deploy new image** (`production-20251008-1828`)
2. **Wait for deployment** to complete (2-5 minutes)
3. **Re-run smoke tests** via GitHub Actions
4. **If tests still fail**, use ECS Exec to investigate database

**Status:** Ready to proceed with deployment

