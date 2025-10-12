# Production Deployment - is_active Column Fix
## October 12, 2025

---

## Summary

**Issue:** Production API failing with "column users.is_active does not exist" error  
**Fix:** Added `is_active` column to users table and built new Docker image  
**Status:** ✅ Code pushed to GitHub | ⚠️ Awaiting ECR push and ECS deployment

---

## What Was Done

### 1. Database Schema Fix ✅
- Added `is_active BOOLEAN NOT NULL DEFAULT true` column to production `users` table
- Verified column exists in database schema
- Created Alembic migration: `db/alembic/versions/20251012_add_is_active.py`

### 2. Code Changes Pushed to GitHub ✅
- **Commit:** `56b5464`
- **Branch:** `main` (and merged to `development`)
- **Files Changed:**
  - `db/alembic/versions/20251012_add_is_active.py` - Migration
  - `add_is_active_column.py` - Direct DB update script
  - `test_download_report.py` - Local testing
  - `test_download_report_production.py` - Production testing
  - `IS_ACTIVE_COLUMN_FIX_COMPLETE.md` - Documentation

### 3. Docker Image Built ✅
- **Image:** `babyshield-backend:is-active-fix-20251012-1648`
- **Tagged as:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:is-active-fix-20251012-1648`
- **Also tagged as:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest`
- **Platform:** `linux/amd64`
- **Dockerfile:** `Dockerfile.final` (production optimized)

---

## Next Steps - Manual Deployment Required

### Step 1: Push Docker Image to ECR

```powershell
# Authenticate with ECR (if not already done)
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Push the timestamped image
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:is-active-fix-20251012-1648

# Push the latest tag
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
```

### Step 2: Deploy to ECS

```powershell
# Force new deployment with latest image
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --force-new-deployment `
  --region eu-north-1
```

**OR use the deployment script:**

```powershell
.\deploy_production_hotfix.ps1
```

### Step 3: Verify Deployment

```powershell
# Test the production API
python test_download_report_production.py

# Should now return 200 or 401 (not 500)
```

```bash
# Check API health
curl https://babyshield.cureviax.ai/healthz

# Test report generation endpoint
curl -X POST https://babyshield.cureviax.ai/api/v1/baby/reports/generate \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_type": "product_safety", "product_id": 123}'
```

### Step 4: Monitor Logs

```bash
# Check ECS task logs
aws logs tail /ecs/babyshield-backend --follow --region eu-north-1

# Look for successful startup
# Should NOT see "column users.is_active does not exist" errors
```

---

## Production Configuration

### ECR Repository
- **Registry:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com`
- **Repository:** `babyshield-backend`
- **Region:** `eu-north-1`

### ECS Cluster
- **Cluster:** `babyshield-cluster`
- **Service:** `babyshield-backend-task-service-0l41s2a9`
- **Region:** `eu-north-1`

### RDS Database
- **Host:** `babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com`
- **Database:** `babyshield_db`
- **Port:** `5432`
- **Engine:** PostgreSQL

### Production API
- **URL:** `https://babyshield.cureviax.ai`
- **Health Check:** `https://babyshield.cureviax.ai/healthz`
- **API Docs:** `https://babyshield.cureviax.ai/docs`

---

## Testing Checklist

After deployment, verify:

- [ ] API health check returns 200 OK
- [ ] No database errors in logs
- [ ] Report generation endpoint works (returns 200/401, not 500)
- [ ] Download report endpoint works
- [ ] Mobile app can generate reports
- [ ] Mobile app can download PDFs
- [ ] User authentication works correctly
- [ ] All endpoints using User model function properly

---

## Affected Endpoints

The following endpoints were broken before this fix:

1. **POST /api/v1/baby/reports/generate** - Report generation (500 error)
2. **GET /api/v1/baby/reports/download/{report_id}** - PDF download
3. Any endpoint that queries the User model with `is_active` column

All should work after deployment! ✅

---

## Rollback Plan

If issues occur after deployment:

### Option 1: Rollback Docker Image

```powershell
# Find previous working image
aws ecr describe-images --repository-name babyshield-backend --region eu-north-1

# Deploy previous image
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:<PREVIOUS_REVISION> `
  --region eu-north-1
```

### Option 2: Remove is_active Column (NOT RECOMMENDED)

```sql
ALTER TABLE users DROP COLUMN IF EXISTS is_active;
```

**Note:** This would break the code, so rollback Option 1 (previous Docker image) is preferred.

---

## Database Migration Status

### Migration Applied ✅
- **Migration:** `20251012_add_is_active`
- **Applied:** October 12, 2025
- **Method:** Direct SQL (manual execution via `add_is_active_column.py`)

### Verify Migration

```sql
-- Check column exists
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'is_active';

-- Expected result:
-- column_name: is_active
-- data_type: boolean
-- is_nullable: NO
-- column_default: true
```

---

## Docker Image Details

### Build Command Used
```powershell
docker build --platform linux/amd64 -f Dockerfile.final -t babyshield-backend:is-active-fix-20251012-1648 .
```

### Image Tags
- `babyshield-backend:is-active-fix-20251012-1648` (local)
- `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:is-active-fix-20251012-1648` (ECR)
- `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest` (ECR)

### Image Contents
- Python 3.11+ runtime
- FastAPI application with all latest fixes
- PostgreSQL client libraries
- All dependencies from `requirements.txt`
- **NEW:** Code that expects `is_active` column in users table

---

## Timeline

| Time        | Event                                         | Status |
| ----------- | --------------------------------------------- | ------ |
| 16:00       | Issue discovered (missing is_active column)   | ❌      |
| 16:10       | Created Alembic migration                     | ✅      |
| 16:15       | Added column to production database           | ✅      |
| 16:20       | Verified column in database                   | ✅      |
| 16:30       | Committed code to GitHub (main + development) | ✅      |
| 16:45       | Built Docker image                            | ✅      |
| 16:48       | Tagged image for ECR                          | ✅      |
| **PENDING** | Push to ECR                                   | ⏳      |
| **PENDING** | Deploy to ECS                                 | ⏳      |
| **PENDING** | Verify in production                          | ⏳      |

---

## Contact & Support

- **Repository:** `BabyShield/babyshield-backend`
- **Commit:** `56b5464`
- **Date:** October 12, 2025
- **AWS Account:** `180703226577`
- **Region:** `eu-north-1`

---

## Quick Reference Commands

```powershell
# Complete deployment (all steps)
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:is-active-fix-20251012-1648
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest
aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1

# Test after deployment
python test_download_report_production.py
curl https://babyshield.cureviax.ai/healthz
```

---

**Status:** ✅ Ready for ECR push and ECS deployment  
**Next Action:** Run the commands in "Next Steps - Manual Deployment Required" section above
