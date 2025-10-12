# ECS Deployment Troubleshooting
## Image Successfully Pushed but Old Container Still Running

## Evidence:
- ✅ Image pushed to ECR: `is-active-fix-20251012-1648`
- ✅ Pushed at: October 12, 2025, 16:49:55 (UTC+02)
- ✅ Last pulled: October 12, 2025, 16:52:05 (UTC+02)
- ✅ Image digest: `sha256:a737ea774794a1326760c993c41603103​6bfea1131505060200f308df162e36f`
- ❌ Production API still returning: "column users.is_active does not exist"

## Issue:
The ECS service was told to force new deployment, but it may still be using an old task definition that references an older image tag or hasn't completed the deployment rollout yet.

## Solutions:

### Option 1: Update Task Definition with Specific Image Digest (RECOMMENDED)

```powershell
# Get current task definition
$taskDef = aws ecs describe-task-definition `
  --task-definition babyshield-backend-task `
  --region eu-north-1 `
  --query 'taskDefinition' `
  --output json | ConvertFrom-Json

# Update with new image digest
$taskDef.containerDefinitions[0].image = "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend@sha256:a737ea774794a1326760c993c416031036bfea1131505060200f308df162e36f"

# Register new task definition (remove unnecessary fields first)
# Then update service to use new task definition revision
```

### Option 2: Force Stop All Running Tasks (FASTEST)

```powershell
# List running tasks
aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1

# Stop each task (ECS will automatically start new ones with latest image)
aws ecs stop-task `
  --cluster babyshield-cluster `
  --task <TASK_ARN> `
  --region eu-north-1
```

### Option 3: Wait for Deployment to Complete

```powershell
# Check deployment status
aws ecs describe-services `
  --cluster babyshield-cluster `
  --services babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'services[0].deployments'

# Look for:
# - PRIMARY deployment with desiredCount matching runningCount
# - Old deployment being drained
```

### Option 4: Update Service with Specific Task Definition

```powershell
# Register new task definition with latest image
# (Create task-definition.json with updated image)

aws ecs register-task-definition --cli-input-json file://task-definition.json --region eu-north-1

# Update service to use new revision
aws ecs update-service `
  --cluster babyshield-cluster `
  --service babyshield-backend-task-service-0l41s2a9 `
  --task-definition babyshield-backend-task:<NEW_REVISION> `
  --force-new-deployment `
  --region eu-north-1
```

## Quick Fix (Recommended):

**Stop all running tasks to force immediate refresh:**

```powershell
# 1. Get task IDs
$tasks = aws ecs list-tasks `
  --cluster babyshield-cluster `
  --service-name babyshield-backend-task-service-0l41s2a9 `
  --region eu-north-1 `
  --query 'taskArns' `
  --output json | ConvertFrom-Json

# 2. Stop each task
foreach ($task in $tasks) {
    aws ecs stop-task `
      --cluster babyshield-cluster `
      --task $task `
      --region eu-north-1
    Write-Host "Stopped task: $task"
}

# 3. Wait 30 seconds for new tasks to start
Start-Sleep -Seconds 30

# 4. Test the API
python test_download_report_production.py
```

## Why This Happens:
1. **Force new deployment** tells ECS to gradually replace tasks
2. ECS uses a rolling deployment strategy (drain old, start new)
3. If using `:latest` tag, ECS might have cached the image reference
4. Task definition might still reference old image digest
5. Deployment might not have completed yet

## Verification After Fix:

```bash
# Check that new containers are running
aws ecs describe-tasks `
  --cluster babyshield-cluster `
  --tasks $(aws ecs list-tasks --cluster babyshield-cluster --service-name babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'taskArns[0]' --output text) `
  --region eu-north-1 `
  --query 'tasks[0].containers[0].image'

# Should return: 
# 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:is-active-fix-20251012-1648
# OR the sha256 digest
```

---

**Next Action:** Stop all running ECS tasks to force immediate deployment of new image.
