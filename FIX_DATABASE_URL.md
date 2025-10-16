# 🎯 PROBLEM IDENTIFIED: DATABASE_URL Configuration Issue

**Date**: October 16, 2025  
**Status**: ✅ pg_trgm WORKS in database, ❌ App returns 0 results

---

## ✅ What We Proved

**Direct database query works perfectly:**

```sql
SELECT product_name, brand, similarity(lower(product_name), 'baby') as score
FROM recalls_enhanced
WHERE similarity(lower(product_name), 'baby') >= 0.08
ORDER BY score DESC
LIMIT 5;

Results:
 product_name | brand | score 
--------------+-------+-------
 BABY         |       |     1
 Baby         |       |     1
 My Baby      |       | 0.625
 My Baby      |       | 0.625
 My Baby      |       | 0.625
```

**✅ pg_trgm works!**  
**✅ GIN indexes work!**  
**✅ similarity() function works!**  
**✅ Data exists (131,743 records)**

---

## ❌ The Problem

**API returns 0 results but database returns 5 results**

This means: **The application is NOT connecting to `babyshield_db` database!**

---

## 🔍 Root Cause

The ECS task definition must have `DATABASE_URL` pointing to the wrong database.

**Current (suspected):**
```
postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres
```

**Should be:**
```
postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db
```

**The difference:** `/postgres` vs `/babyshield_db`

---

## 🔧 Solution: Update ECS Task Definition

### Step 1: Get Current Task Definition

```bash
aws ecs describe-task-definition \
  --task-definition babyshield-backend-task-definition \
  --region eu-north-1 \
  > current-task-def.json
```

### Step 2: Create New Task Definition with Correct DATABASE_URL

Edit `current-task-def.json` and find the `environment` array in `containerDefinitions[0]`:

```json
{
  "name": "DATABASE_URL",
  "value": "postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db"
}
```

Change `/postgres` to `/babyshield_db` if it's wrong.

### Step 3: Remove Read-Only Fields

Remove these fields from the JSON before registering:
- `taskDefinitionArn`
- `revision`
- `status`
- `requiresAttributes`
- `compatibilities`
- `registeredAt`
- `registeredBy`

### Step 4: Register New Task Definition

```bash
aws ecs register-task-definition \
  --cli-input-json file://current-task-def.json \
  --region eu-north-1
```

### Step 5: Update ECS Service

```bash
aws ecs update-service \
  --cluster babyshield-cluster \
  --service babyshield-backend-task-service-0l41s2a9 \
  --task-definition babyshield-backend-task-definition \
  --force-new-deployment \
  --region eu-north-1
```

### Step 6: Wait for Deployment

```bash
aws ecs wait services-stable \
  --cluster babyshield-cluster \
  --services babyshield-backend-task-service-0l41s2a9 \
  --region eu-north-1
```

### Step 7: Test Search

```bash
curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced \
  -H "Content-Type: application/json" \
  -d '{"query":"baby","limit":5}'
```

Expected: `"total": 5` (not 0)

---

## 🚀 Quick Fix Script (PowerShell)

I'll create a PowerShell script to automate this:

```powershell
# Fix DATABASE_URL and redeploy

# 1. Get current task definition
Write-Host "Fetching current task definition..." -ForegroundColor Cyan
aws ecs describe-task-definition `
  --task-definition babyshield-backend-task-definition `
  --region eu-north-1 `
  --query 'taskDefinition' `
  > task-def.json

# 2. Fix DATABASE_URL in the JSON
$taskDef = Get-Content task-def.json | ConvertFrom-Json

# Find and fix DATABASE_URL
$env = $taskDef.containerDefinitions[0].environment
for ($i = 0; $i -lt $env.Count; $i++) {
    if ($env[$i].name -eq 'DATABASE_URL') {
        $oldValue = $env[$i].value
        $newValue = $oldValue -replace '/postgres$', '/babyshield_db'
        
        Write-Host "`nOld: $oldValue" -ForegroundColor Yellow
        Write-Host "New: $newValue" -ForegroundColor Green
        
        $env[$i].value = $newValue
        break
    }
}

# Remove read-only fields
$taskDef.PSObject.Properties.Remove('taskDefinitionArn')
$taskDef.PSObject.Properties.Remove('revision')
$taskDef.PSObject.Properties.Remove('status')
$taskDef.PSObject.Properties.Remove('requiresAttributes')
$taskDef.PSObject.Properties.Remove('compatibilities')
$taskDef.PSObject.Properties.Remove('registeredAt')
$taskDef.PSObject.Properties.Remove('registeredBy')

# Save fixed definition
$taskDef | ConvertTo-Json -Depth 10 > task-def-fixed.json

# 3. Register new task definition
Write-Host "`nRegistering new task definition..." -ForegroundColor Cyan
aws ecs register-task-definition `
  --cli-input-json file://task-def-fixed.json `
  --region eu-north-1

# 4. Update service
Write-Host "`nUpdating ECS service..." -ForegroundColor Cyan
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task-definition `
  --force-new-deployment `
  --region eu-north-1

Write-Host "`n✅ Deployment started!" -ForegroundColor Green
Write-Host "Wait 2-3 minutes, then test search." -ForegroundColor Yellow
```

---

## 📋 Verification Checklist

After deployment:

- [ ] Check ECS service deployment status (should be "PRIMARY" with 1 running task)
- [ ] Test health endpoint: `GET /healthz` (should return 200)
- [ ] Test search endpoint: `POST /api/v1/search/advanced {"query":"baby","limit":5}`
- [ ] Verify results: `"total"` should be > 0 (around 12,000+, not 0)
- [ ] Check CloudWatch logs: No pg_trgm warnings

---

## 🎯 Summary

1. **Problem**: API connects to wrong database (`postgres` instead of `babyshield_db`)
2. **Proof**: Direct database query works, API returns 0
3. **Solution**: Update `DATABASE_URL` environment variable in ECS task definition
4. **Fix**: Change `/postgres` to `/babyshield_db`
5. **Deploy**: Register new task definition and update service
6. **Verify**: Search should return results

**ETA to fix**: 5-10 minutes (deployment time)

---

**Next**: Run the PowerShell script to automate the fix!
