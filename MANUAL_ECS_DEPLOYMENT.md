# Deployment Status & Manual ECS Deployment Guide

**Date:** October 8, 2025, 19:30  
**Image Built:** ✅ `production-20251008-1828`  
**Pushed to ECR:** ✅ Confirmed

---

## ✅ What Was Completed (ECR Deployment)

### **1. Docker Image Built**
- **Tag:** `production-20251008-1828`
- **Image ID:** `db503d12d35a`
- **Size:** 13.7 GB
- **Built:** 2025-10-08 18:29:10
- **Dockerfile:** `Dockerfile.final` (production version)

### **2. ECR Authentication**
- **Region:** `eu-north-1`
- **Account:** `180703226577`
- **Repository:** `babyshield-backend`
- **Status:** ✅ Login Succeeded

### **3. Image Pushed to ECR**
- **Full URI:** `180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20251008-1828`
- **Also Tagged:** `latest`
- **Digest:** `sha256:db503d12d35a9d5d45288bdb16e7534f11cd540d52c3c8c61743d0735b0d0f33`
- **Push Status:** ✅ Complete

### **4. Code Included in Image**
- All system scan fixes (117 errors fixed)
- Boolean comparison fixes (90 instances)
- Undefined name error fixes (8 instances)
- Updated search service with better error handling
- Database configuration validation
- Latest Alembic migrations

---

## 🚀 Manual ECS Deployment Steps

### **Option 1: Update Service (Force New Deployment)**

This will redeploy using the same task definition but pull the `:latest` tag from ECR.

```powershell
# Update ECS service to use latest image
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --force-new-deployment `
  --region eu-north-1 `
  --query 'service.{Status:status,DesiredCount:desiredCount,RunningCount:runningCount}' `
  --output table
```

**Pros:**
- ✅ Quick and simple
- ✅ Uses existing task definition
- ✅ Pulls `:latest` tag automatically

**Cons:**
- ⚠️ Doesn't change task definition revision
- ⚠️ Won't update if image tag in task def is not `:latest`

---

### **Option 2: Register New Task Definition (Recommended)**

Create a new task definition revision with the specific image tag.

#### **Step 1: Get Current Task Definition**

```powershell
# Download current task definition
aws ecs describe-task-definition `
  --task-definition babyshield-backend-task `
  --region eu-north-1 `
  --query 'taskDefinition' > task-definition-current.json
```

#### **Step 2: Edit Task Definition**

Open `task-definition-current.json` and update:

1. **Remove these fields** (AWS adds them automatically):
   - `taskDefinitionArn`
   - `revision`
   - `status`
   - `requiresAttributes`
   - `compatibilities`
   - `registeredAt`
   - `registeredBy`

2. **Update image URI** in `containerDefinitions`:
   ```json
   {
     "containerDefinitions": [
       {
         "name": "babyshield-backend",
         "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20251008-1828",
         ...
       }
     ]
   }
   ```

3. **Save as** `task-definition-new.json`

#### **Step 3: Register New Task Definition**

```powershell
# Register the new task definition
aws ecs register-task-definition `
  --cli-input-json file://task-definition-new.json `
  --region eu-north-1 `
  --query 'taskDefinition.revision' `
  --output text
```

**Output:** Will show new revision number (e.g., `161`)

#### **Step 4: Update Service with New Task Definition**

```powershell
# Replace :161 with your actual revision number from Step 3
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:161 `
  --force-new-deployment `
  --region eu-north-1
```

---

### **Monitoring Deployment**

#### **Check Deployment Status**

```powershell
# Monitor deployment progress (run every 30 seconds)
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'services[0].{rolloutState:deployments[0].rolloutState,runningCount:runningCount,desiredCount:desiredCount}' `
  --output table
```

**Expected Progression:**
1. `IN_PROGRESS` - Deployment starting
2. `COMPLETED` - Deployment successful

#### **Check Task Status**

```powershell
# Get running task details
aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'taskArns[0]' `
  --output text

# Get task health status
aws ecs describe-tasks `
  --cluster babyshield-cluster `
  --tasks <TASK_ARN> `
  --region eu-north-1 `
  --query 'tasks[0].{Status:lastStatus,Health:healthStatus,StartedAt:startedAt}' `
  --output table
```

#### **Check CloudWatch Logs**

```powershell
# Get recent logs (last 5 minutes)
$startTime = [DateTimeOffset]::UtcNow.AddMinutes(-5).ToUnixTimeMilliseconds()
aws logs filter-log-events `
  --log-group-name "/ecs/babyshield-backend" `
  --start-time $startTime `
  --region eu-north-1 `
  --query 'events[*].message' `
  --output text | Select-Object -First 50
```

**Look for:**
- ✅ "Starting BabyShield API"
- ✅ "Database tables ready"
- ✅ "Application startup complete"
- ❌ No "ERROR" or "500" messages

---

## ✅ Verification Steps After Deployment

### **1. Health Checks**

```powershell
# Test health endpoints
Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/healthz"
Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/readyz"
Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/api/v1/version"
```

**Expected:** All return HTTP 200

### **2. Test Search Endpoint (The Failing One)**

```powershell
# Test the failing query
$body = @{
    product = "Triacting Night Time Cold"
    agencies = @("FDA")
    limit = 5
} | ConvertTo-Json

Invoke-WebRequest -Uri "https://babyshield.cureviax.ai/api/v1/search/advanced" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

**Expected:** HTTP 200 (not 500)

### **3. Re-run Smoke Tests**

Navigate to GitHub Actions and manually trigger the smoke test workflow:

```
https://github.com/BabyShield/babyshield-backend/actions/workflows/api-smoke.yml
```

Click **"Run workflow"** and verify all 8 tests pass.

---

## 📊 Deployment Timeline

| Step | Status | Time |
|------|--------|------|
| Build Docker image | ✅ Complete | 18:29 |
| Push to ECR | ✅ Complete | 18:30 |
| Manual ECS deployment | ⏳ **Pending** | - |
| Verify health checks | ⏳ Pending | - |
| Test search endpoint | ⏳ Pending | - |
| Re-run smoke tests | ⏳ Pending | - |

---

## 🔧 Troubleshooting

### If Deployment Fails

```powershell
# Check stopped tasks for errors
aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --desired-status STOPPED `
  --region eu-north-1 `
  --max-items 1

# Get stopped task details
aws ecs describe-tasks `
  --cluster babyshield-cluster `
  --tasks <STOPPED_TASK_ARN> `
  --region eu-north-1 `
  --query 'tasks[0].stoppedReason'
```

### Rollback if Needed

```powershell
# Rollback to previous task definition (replace :160 with previous revision)
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:160 `
  --force-new-deployment `
  --region eu-north-1
```

---

## 📝 Quick Reference

**ECR Image URI:**
```
180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20251008-1828
```

**ECS Resources:**
- Cluster: `babyshield-cluster`
- Service: `babyshield-backend-task-service-0l41s2a9`
- Task Definition: `babyshield-backend-task`
- Log Group: `/ecs/babyshield-backend`

**Region:** `eu-north-1` (Stockholm)

---

**Status:** ✅ Ready for manual ECS deployment  
**Next Action:** Run Option 1 or Option 2 commands above
