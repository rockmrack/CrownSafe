# Production Deployment Guide - Phase 1
**BabyShield Backend - Complete Deployment Instructions**

## 🎯 Overview

This guide covers the complete production deployment process for Phase 1 improvements.

---

## ✅ Pre-Deployment Checklist

### 1. Verify Local Environment
```powershell
# Test all API endpoints
powershell -ExecutionPolicy Bypass -File scripts/test_api_endpoints.ps1

# Expected: 8/8 tests PASS
```

### 2. Verify Docker Stack
```powershell
# Check container health
docker ps --filter "name=babyshield"

# Expected: All containers show "healthy" or "running"
```

### 3. Check Configuration
```powershell
# Validate production config
python scripts/config_manager.py validate production

# Expected: All configuration valid
```

---

## 📋 Step 1: Create Pull Request

### Option A: Using GitHub Web UI

1. **Navigate to GitHub:**
   ```
   https://github.com/BabyShield/babyshield-backend/pull/new/release/phase-1-production-ready
   ```

2. **Fill in PR Details:**
   - **Title:** `Release: Phase 1 Complete - Production Ready`
   - **Description:** Copy contents from `PR_RELEASE_PHASE1.md`
   - **Base branch:** `main`
   - **Compare branch:** `release/phase-1-production-ready`

3. **Add Labels:**
   - `release`
   - `production`
   - `phase-1`

4. **Create Pull Request**

### Option B: Using GitHub CLI (if installed)
```powershell
gh pr create `
  --base main `
  --head release/phase-1-production-ready `
  --title "Release: Phase 1 Complete - Production Ready" `
  --body-file PR_RELEASE_PHASE1.md `
  --label "release,production,phase-1"
```

---

## 🔍 Step 2: Monitor CI Checks

### Required CI Checks
Your repository requires these checks to pass:

1. **Smoke — Account Deletion**
2. **Smoke — Barcode Search**
3. **Unit — Account Deletion**

### Check Status Manually

1. **Go to GitHub Actions:**
   ```
   https://github.com/BabyShield/babyshield-backend/actions
   ```

2. **Look for Latest Workflow Run** on `release/phase-1-production-ready` branch

3. **Wait for Green Checkmarks:** ✅✅✅

### Using the Monitor Script
```powershell
# Monitor CI checks (auto-refresh every 30 seconds)
powershell -ExecutionPolicy Bypass -File scripts/monitor_ci_checks.ps1 -Branch "release/phase-1-production-ready"

# Check once and exit
powershell -ExecutionPolicy Bypass -File scripts/monitor_ci_checks.ps1 -Branch "release/phase-1-production-ready" -Once
```

---

## ✅ Step 3: Merge Pull Request

### Once All Checks Pass:

1. **Review the Changes:**
   - Check the "Files changed" tab
   - Verify all commits are correct
   - Ensure no unexpected changes

2. **Get Approval** (if required by repo rules)

3. **Merge Strategy:**
   - **Use:** "Squash and merge"
   - **Merge commit message:** Keep the PR title
   - **Merge commit description:** Include key changes

4. **Click "Squash and merge"**

5. **Confirm merge**

### Post-Merge Actions
```powershell
# Switch to main and pull latest
git checkout main
git pull origin main

# Verify merged commit
git log --oneline -5

# Tag the release
git tag -a v2.4.0-phase1 -m "Phase 1: Configuration & Infrastructure Complete"
git push origin v2.4.0-phase1
```

---

## 🚀 Step 4: Production Deployment

### Method A: Using Deployment Script

```powershell
# Navigate to project root
cd C:\path\to\babyshield-backend-clean

# Run production deployment script
.\deploy_prod_digest_pinned.ps1

# This script will:
# 1. Build Docker image from Dockerfile.final
# 2. Tag with digest-pinned format
# 3. Push to AWS ECR
# 4. Update ECS task definition
# 5. Force new deployment
```

### Method B: Manual Deployment

#### 1. Build Production Image
```powershell
# Login to AWS ECR
aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com

# Build with production Dockerfile
$buildDate = Get-Date -Format "yyyyMMdd"
docker build -f Dockerfile.final -t 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-$buildDate .
```

#### 2. Push to ECR
```powershell
docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-fixed-$buildDate
```

#### 3. Get Image Digest
```powershell
$digest = aws ecr describe-images `
  --repository-name babyshield-backend `
  --image-ids imageTag=production-fixed-$buildDate `
  --region eu-north-1 `
  --query "imageDetails[0].imageDigest" `
  --output text

Write-Host "Image Digest: $digest" -ForegroundColor Green
```

#### 4. Update ECS Task Definition
```powershell
# Export current task definition
aws ecs describe-task-definition `
  --task-definition babyshield-backend-task `
  --region eu-north-1 `
  --query "taskDefinition.{family:family,taskRoleArn:taskRoleArn,executionRoleArn:executionRoleArn,networkMode:networkMode,requiresCompatibilities:requiresCompatibilities,cpu:cpu,memory:memory,containerDefinitions:containerDefinitions}" `
  --output json > td.json

# Update the image field in td.json to:
# 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend@$digest

# Register new task definition
aws ecs register-task-definition --cli-input-json file://td.json --region eu-north-1
```

#### 5. Force New Deployment
```powershell
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --force-new-deployment `
  --region eu-north-1
```

---

## 🔍 Step 5: Verify Production Deployment

### Automated Verification
```powershell
# Run verification against production
powershell -ExecutionPolicy Bypass -File scripts/deploy_and_verify.ps1 `
  -ProductionUrl "https://babyshield.cureviax.ai" `
  -VerifyOnly

# Expected: All tests PASS
```

### Manual Verification

#### 1. Check Health Endpoint
```powershell
curl https://babyshield.cureviax.ai/healthz

# Expected response:
# {"status":"ok"}
```

#### 2. Check Readiness
```powershell
curl https://babyshield.cureviax.ai/readyz

# Expected response:
# {"status":"ready","message":"Service is ready to handle requests",...}
```

#### 3. Check API Documentation
```
Open in browser: https://babyshield.cureviax.ai/docs
```

#### 4. Run Full API Tests
```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_api_endpoints.ps1 -BaseUrl "https://babyshield.cureviax.ai"

# Expected: 8/8 tests PASS
```

#### 5. Check ECS Service
```powershell
# Verify running tasks
aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --desired-status RUNNING `
  --region eu-north-1

# Check task health
aws ecs describe-tasks `
  --cluster babyshield-cluster `
  --tasks <task-arn-from-above> `
  --region eu-north-1 `
  --query "tasks[].{Status:lastStatus,Health:healthStatus,Image:containers[0].image}"
```

#### 6. Monitor Logs
```powershell
# Tail CloudWatch logs
aws logs tail /ecs/babyshield-backend --region eu-north-1 --follow

# Check for:
# - "Application startup complete"
# - "registered successfully"
# - No ERROR messages
```

---

## 📊 Step 6: Post-Deployment Monitoring

### First 15 Minutes
- ✅ Health endpoints responding
- ✅ No error spikes in logs
- ✅ Response times normal
- ✅ All containers healthy

### First Hour
- ✅ Check Prometheus metrics
- ✅ Monitor error rates
- ✅ Verify database connections
- ✅ Check Redis connectivity

### First 24 Hours
- ✅ Monitor API usage
- ✅ Check for any regression
- ✅ Verify all endpoints functional
- ✅ Review CloudWatch logs

---

## 🚨 Rollback Procedure

### If Issues Occur:

#### Quick Rollback
```powershell
# Revert to previous task definition
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:<previous-revision> `
  --force-new-deployment `
  --region eu-north-1
```

#### Full Rollback with Git
```powershell
# Revert the merge commit on main
git revert <merge-commit-sha> -m 1
git push origin main

# Then redeploy
.\deploy_prod_digest_pinned.ps1
```

---

## 📝 Deployment Log Template

Keep a record of each deployment:

```
Deployment Date: 2025-10-03
Deployment Time: [TIME]
Deployed By: [YOUR NAME]
Branch: release/phase-1-production-ready
Commit SHA: [COMMIT SHA]
Docker Tag: production-fixed-20251003
Image Digest: sha256:[DIGEST]
PR Number: #[NUMBER]

Pre-Deployment Tests: PASS
CI Checks: PASS
Deployment Method: [Script/Manual]
Deployment Duration: [MINUTES]

Post-Deployment Verification:
- Health Check: PASS
- Readiness Check: PASS
- API Tests: PASS (8/8)
- Container Health: PASS
- Logs: Normal

Issues Encountered: None / [Description]
Rollback Performed: No / [Details]

Notes: [Any additional notes]
```

---

## 🎯 Success Criteria

**Deployment is considered successful when:**

✅ All CI checks passing
✅ PR merged to main
✅ Docker image built and pushed
✅ ECS service updated
✅ All containers healthy
✅ Health endpoint responding
✅ API tests passing (100%)
✅ No error spikes in logs
✅ Response times normal

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue:** Container fails health check
**Solution:** Check logs, verify environment variables, ensure port 8000 exposed

**Issue:** Import errors in logs
**Solution:** Verify all service files copied to correct locations

**Issue:** Database connection errors
**Solution:** Check DATABASE_URL environment variable, verify RDS/DB accessibility

### Documentation References

- `PRODUCTION_READINESS_CHECKLIST.md` - Pre-deployment checklist
- `CONFIG_DOCUMENTATION.md` - Configuration help
- `DEPLOYMENT_PROCEDURES.md` - Detailed deployment steps
- `PR_RELEASE_PHASE1.md` - Phase 1 changes summary

---

## ✅ Completion

Once all steps are complete and verified:

1. ✅ Update deployment log
2. ✅ Notify team of successful deployment
3. ✅ Monitor for 24 hours
4. ✅ Document any issues/learnings
5. ✅ Celebrate! 🎉

**Phase 1 deployment is now complete and production is running the latest code!**

