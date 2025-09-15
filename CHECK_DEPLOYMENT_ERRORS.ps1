# PowerShell Script to Check ECS Deployment Errors
# ==================================================

param(
    [string]$ClusterName = "default",
    [string]$ServiceName = "babyshield-backend-service",
    [string]$TaskFamily = "babyshield-backend-task",
    [string]$Region = "eu-north-1"
)

Write-Host "`n🔍 CHECKING DEPLOYMENT ERRORS" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# 1. Check running tasks
Write-Host "`n📋 Checking ECS Tasks..." -ForegroundColor Cyan
$tasks = aws ecs list-tasks --cluster $ClusterName --family $TaskFamily --region $Region --output json | ConvertFrom-Json

if ($tasks.taskArns.Count -eq 0) {
    Write-Host "❌ No running tasks found!" -ForegroundColor Red
    
    # Check stopped tasks
    Write-Host "`n🔍 Checking stopped tasks..." -ForegroundColor Yellow
    $stoppedTasks = aws ecs list-tasks --cluster $ClusterName --family $TaskFamily --desired-status STOPPED --region $Region --output json | ConvertFrom-Json
    
    if ($stoppedTasks.taskArns.Count -gt 0) {
        Write-Host "Found $($stoppedTasks.taskArns.Count) stopped task(s)" -ForegroundColor Yellow
        
        # Get details of the most recent stopped task
        $taskDetails = aws ecs describe-tasks --cluster $ClusterName --tasks $stoppedTasks.taskArns[0] --region $Region --output json | ConvertFrom-Json
        
        Write-Host "`n❌ TASK STOP REASON:" -ForegroundColor Red
        Write-Host $taskDetails.tasks[0].stoppedReason -ForegroundColor White
        
        if ($taskDetails.tasks[0].containers[0].reason) {
            Write-Host "`n❌ CONTAINER EXIT REASON:" -ForegroundColor Red
            Write-Host $taskDetails.tasks[0].containers[0].reason -ForegroundColor White
        }
    }
} else {
    Write-Host "✅ Found $($tasks.taskArns.Count) running task(s)" -ForegroundColor Green
}

# 2. Check service events (if using a service)
Write-Host "`n📊 Checking Service Events..." -ForegroundColor Cyan
try {
    $service = aws ecs describe-services --cluster $ClusterName --services $ServiceName --region $Region --output json 2>$null | ConvertFrom-Json
    
    if ($service.services.Count -gt 0) {
        Write-Host "`nLast 5 Service Events:" -ForegroundColor Yellow
        $service.services[0].events | Select-Object -First 5 | ForEach-Object {
            $eventDate = $_.createdAt
            $message = $_.message
            Write-Host "[$eventDate] $message" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "No service found or error checking service" -ForegroundColor Gray
}

# 3. Check CloudWatch Logs
Write-Host "`n📝 Recent CloudWatch Logs:" -ForegroundColor Cyan
Write-Host "Run this command to see live logs:" -ForegroundColor Yellow
Write-Host "aws logs tail /ecs/babyshield-backend --follow --region $Region" -ForegroundColor White

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# 4. Common issues and solutions
Write-Host "`n💡 COMMON DEPLOYMENT ISSUES:" -ForegroundColor Yellow
Write-Host @"
1. Image not found → Check ECR image tag exists
2. Task role error → Verify IAM roles are correct
3. Port already in use → Check security groups/target groups
4. Out of memory → Increase task memory allocation
5. Environment variables → Check secrets and env vars in task definition
"@ -ForegroundColor Gray

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
