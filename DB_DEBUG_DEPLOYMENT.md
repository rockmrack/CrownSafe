# Database Debug Deployment - October 12, 2025 17:13

## Issue Summary
Production API still returns "column users.is_active does not exist" error even after:
- ✅ Adding is_active column to babyshield_db database
- ✅ Building new Docker image with updated code
- ✅ Deploying to ECS (confirmed correct image sha256:a737ea774794...)
- ❌ Error persists - suggests app connects to different database

## Debug Endpoint Added
Added `/debug/db-info` endpoint to `api/main_babyshield.py` (commit 3103073)

### Endpoint Details
- **URL**: `https://babyshield.cureviax.ai/debug/db-info`
- **Method**: GET
- **Authentication**: None (public system endpoint)
- **Purpose**: Reveal actual database connection details

### What It Returns
```json
{
  "status": "ok",
  "current_database": "<actual database name>",
  "current_schema": "<actual schema name>",
  "postgres_version": "<PostgreSQL version>",
  "users_table_columns_count": <number>,
  "is_active_column_exists": true/false,
  "users_columns": [
    {
      "name": "column_name",
      "type": "data_type",
      "nullable": "YES/NO",
      "default": "default_value"
    }
  ]
}
```

## Docker Image Built
```
Image: babyshield-backend:db-debug-20251012-1713
ECR Tag: 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:db-debug-20251012-1713
Also tagged: latest
Build Time: ~5.7s (used cache)
Platform: linux/amd64
Commit: 3103073
```

## Deployment Steps

### 1. Push to ECR
```powershell
# Authenticate
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Push with timestamp tag
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:db-debug-20251012-1713

# Push as latest
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
```

### 2. Deploy to ECS
Option A: Force new deployment (recommended)
```bash
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --force-new-deployment \
  --region eu-north-1
```

Option B: Stop existing tasks (faster)
```bash
# List tasks
aws ecs list-tasks --cluster babyshield-cluster --region eu-north-1

# Stop task (replace TASK_ID)
aws ecs stop-task --cluster babyshield-cluster --task <TASK_ID> --region eu-north-1
```

### 3. Call Debug Endpoint
```powershell
# After deployment completes (wait ~2 minutes)
Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/debug/db-info" | Select-Object -ExpandProperty Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

Or with curl:
```bash
curl https://babyshield.cureviax.ai/debug/db-info | jq .
```

## Expected Results

### Scenario 1: Database Name Mismatch
If `current_database` shows something other than `babyshield_db`:
```json
{
  "current_database": "babyshield_prod",  // Different from where we added column!
  "is_active_column_exists": false
}
```
**Solution**: Connect to correct database and add column there

### Scenario 2: Schema Mismatch
If `current_schema` is not `public`:
```json
{
  "current_schema": "myschema",  // Not public schema
  "is_active_column_exists": false
}
```
**Solution**: Add column to correct schema

### Scenario 3: Column Already Exists
If column exists but query still fails:
```json
{
  "is_active_column_exists": true,
  "users_columns": [
    {"name": "is_active", "type": "boolean", "nullable": "NO", "default": "true"}
  ]
}
```
**Solution**: Different issue - check connection pooling, ORM mapping, or query logic

## Next Steps After Diagnosis

### If database name is different:
1. Connect to actual database shown in response
2. Run: `ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;`
3. Verify column added
4. Retest download report endpoint

### If schema is different:
1. Add column to correct schema
2. Or update application to use correct schema in search_path

### If column exists but still fails:
1. Check SQLAlchemy model mapping
2. Clear connection pool (restart app)
3. Check for table inheritance issues
4. Verify no other database connection in code

## Rollback Plan
If debug endpoint causes issues, revert to previous image:
```bash
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --task-definition <PREVIOUS_TASK_DEF> \
  --region eu-north-1
```

Previous working image: sha256:a737ea774794a1326760c993c416031036bfea1131505060200f308df162e36f

## Timeline
- **16:48** - First deployment with is_active fix (still failing)
- **17:07** - User confirmed correct image running
- **17:10** - Decided to add debug endpoint
- **17:13** - Built db-debug-20251012-1713 image with diagnostic endpoint
- **Next** - Push to ECR and deploy to ECS

## Files Modified
- `api/main_babyshield.py` - Added `/debug/db-info` endpoint (lines 2067-2101)

## Commits
- `3103073` - "debug: Add database diagnostic endpoint to identify db connection"
- Previous: `56b5464` - "fix: Add is_active column to users table and download report tests"

## Contact
After calling the debug endpoint, share the output to determine correct fix approach.
