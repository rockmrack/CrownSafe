# 🚀 QUICK FIX: Update DATABASE_URL (MANUAL STEPS)

## ✅ Problem Confirmed

**Current DATABASE_URL**: `postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/postgres`

**Correct DATABASE_URL**: `postgresql://babyshield_user:MandarunLabadiena25!@babyshield-prod-db.cx4o4w2uqorf.eu-north-1.rds.amazonaws.com:5432/babyshield_db`

**Change needed**: `/postgres` → `/babyshield_db`

---

## 📝 Manual Fix Steps

### Step 1: Edit task-def.json

1. Open `task-def.json` in VS Code
2. Find the `environment` array in `containerDefinitions[0]`
3. Find the entry with `"name": "DATABASE_URL"`
4. Change the value from `/postgres` to `/babyshield_db`
5. Remove these fields from the JSON:
   - `"taskDefinitionArn"`
   - `"revision"`
   - `"status"`
   - `"requiresAttributes"`
   - `"compatibilities"`
   - `"registeredAt"`
   - `"registeredBy"`
6. Save the file

### Step 2: Register new task definition

```powershell
aws ecs register-task-definition --cli-input-json file://task-def.json --region eu-north-1
```

### Step 3: Get the new revision number

The output from Step 2 will show:
```json
{
  "taskDefinition": {
    "revision": 186,  ← THIS NUMBER
    ...
  }
}
```

### Step 4: Update the ECS service

```powershell
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --task-definition babyshield-backend-task:186 `  ← USE THE REVISION NUMBER
    --force-new-deployment `
    --region eu-north-1
```

### Step 5: Wait for deployment (2-3 minutes)

Monitor status:
```powershell
aws ecs describe-services `
    --cluster babyshield-cluster `
    --services babyshield-backend-task-service-0l41s2a9 `
    --region eu-north-1 `
    --query "services[0].deployments"
```

Look for:
- `"status": "PRIMARY"` with `"desiredCount": 1, "runningCount": 1`

### Step 6: Test search

```powershell
curl.exe -X POST "https://babyshield.cureviax.ai/api/v1/search/advanced" `
    -H "Content-Type: application/json" `
    -d '{\"query\":\"baby\",\"limit\":5}'
```

**Expected**: `"total": 5` or more (NOT 0!)

---

## 🚀 EVEN FASTER: One-Line AWS Console Fix

1. Go to: https://eu-north-1.console.aws.amazon.com/ecs/v2/task-definitions/babyshield-backend-task?region=eu-north-1
2. Click latest revision (probably :185)
3. Click "Create new revision"
4. Scroll to "Environment variables"
5. Find `DATABASE_URL`
6. Change `/postgres` to `/babyshield_db`
7. Click "Create" at bottom
8. Go to: Services → babyshield-backend-task-service-0l41s2a9
9. Click "Update service"
10. Select the new revision
11. Check "Force new deployment"
12. Click "Update"

Done! Wait 2-3 minutes and test search.

---

## 📊 What This Fixes

- ✅ API will connect to `babyshield_db` (131,743 records) instead of `postgres` (0 records)
- ✅ Search will use pg_trgm extension (already enabled on correct database)
- ✅ Search will return results (currently returns 0)

**After this fix, search should work perfectly!** 🎉
