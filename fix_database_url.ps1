# Fix DATABASE_URL and Redeploy ECS Service
# This script updates the DATABASE_URL to point to babyshield_db instead of postgres

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  DATABASE_URL Fix & Redeploy" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Get current task definition
Write-Host "[1/6] Fetching current task definition..." -ForegroundColor Cyan
$taskDefJson = aws ecs describe-task-definition `
    --task-definition babyshield-backend-task `
    --region eu-north-1 | ConvertFrom-Json

$taskDef = $taskDefJson.taskDefinition

# Step 2: Check current DATABASE_URL
Write-Host "[2/6] Checking DATABASE_URL..." -ForegroundColor Cyan
$env = $taskDef.containerDefinitions[0].environment
$dbUrlEnv = $env | Where-Object { $_.name -eq 'DATABASE_URL' }

if (-not $dbUrlEnv) {
    Write-Host "❌ ERROR: DATABASE_URL not found in task definition!" -ForegroundColor Red
    exit 1
}

$oldValue = $dbUrlEnv.value
Write-Host "`nCurrent DATABASE_URL:" -ForegroundColor Yellow
Write-Host $oldValue -ForegroundColor White

# Check if it needs fixing
if ($oldValue -match '/postgres(\?|$)') {
    Write-Host "`n❌ PROBLEM CONFIRMED: Points to 'postgres' database" -ForegroundColor Red
    Write-Host "   Should point to 'babyshield_db' database`n" -ForegroundColor Yellow
    
    # Step 3: Fix DATABASE_URL
    Write-Host "[3/6] Fixing DATABASE_URL..." -ForegroundColor Cyan
    $newValue = $oldValue -replace '/postgres(\?|$)', '/babyshield_db$1'
    
    Write-Host "New DATABASE_URL:" -ForegroundColor Green
    Write-Host $newValue -ForegroundColor White
    
    # Update the value
    for ($i = 0; $i -lt $env.Count; $i++) {
        if ($env[$i].name -eq 'DATABASE_URL') {
            $env[$i].value = $newValue
            break
        }
    }
    
    # Step 4: Remove read-only fields
    Write-Host "`n[4/6] Preparing new task definition..." -ForegroundColor Cyan
    $taskDef.PSObject.Properties.Remove('taskDefinitionArn')
    $taskDef.PSObject.Properties.Remove('revision')
    $taskDef.PSObject.Properties.Remove('status')
    $taskDef.PSObject.Properties.Remove('requiresAttributes')
    $taskDef.PSObject.Properties.Remove('compatibilities')
    $taskDef.PSObject.Properties.Remove('registeredAt')
    $taskDef.PSObject.Properties.Remove('registeredBy')
    
    # Save to file
    $taskDef | ConvertTo-Json -Depth 20 | Out-File -FilePath "task-def-fixed.json" -Encoding utf8
    Write-Host "✅ Saved to task-def-fixed.json" -ForegroundColor Green
    
    # Step 5: Register new task definition
    Write-Host "`n[5/6] Registering new task definition..." -ForegroundColor Cyan
    $registerResult = aws ecs register-task-definition `
        --cli-input-json file://task-def-fixed.json `
        --region eu-north-1 | ConvertFrom-Json
    
    $newRevision = $registerResult.taskDefinition.revision
    Write-Host "✅ Registered revision: $newRevision" -ForegroundColor Green
    
    # Step 6: Update ECS service
    Write-Host "`n[6/6] Updating ECS service with new task definition..." -ForegroundColor Cyan
    aws ecs update-service `
        --cluster babyshield-cluster `
        --service babyshield-backend-task-service-0l41s2a9 `
        --task-definition babyshield-backend-task:$newRevision `
        --force-new-deployment `
        --region eu-north-1 | Out-Null
    
    Write-Host "✅ Service update initiated!" -ForegroundColor Green
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  ✅ DEPLOYMENT STARTED" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Write-Host "The ECS service is now deploying with the fixed DATABASE_URL." -ForegroundColor White
    Write-Host "`nDeployment will take 2-3 minutes." -ForegroundColor Yellow
    Write-Host "`nTo monitor deployment:" -ForegroundColor Cyan
    Write-Host "  aws ecs describe-services --cluster babyshield-cluster --services babyshield-backend-task-service-0l41s2a9 --region eu-north-1 --query 'services[0].deployments'" -ForegroundColor Gray
    
    Write-Host "`nAfter deployment completes, test search:" -ForegroundColor Cyan
    Write-Host '  curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced -H "Content-Type: application/json" -d ''{"query":"baby","limit":5}''' -ForegroundColor Gray
    Write-Host "`nExpected result: 'total' > 0 (should be around 12,000+)`n" -ForegroundColor Green
    
}
elseif ($oldValue -match '/babyshield_db(\?|$)') {
    Write-Host "`n✅ DATABASE_URL is already correct!" -ForegroundColor Green
    Write-Host "   Points to 'babyshield_db' database`n" -ForegroundColor White
    
    Write-Host "If search still returns 0, the issue might be:" -ForegroundColor Yellow
    Write-Host "  1. Search code not using similarity() correctly" -ForegroundColor Gray
    Write-Host "  2. Cached connections to old database" -ForegroundColor Gray
    Write-Host "  3. Application not restarted after pg_trgm enablement`n" -ForegroundColor Gray
    
    Write-Host "Try forcing a restart:" -ForegroundColor Cyan
    Write-Host "  aws ecs update-service --cluster babyshield-cluster --service babyshield-backend-task-service-0l41s2a9 --force-new-deployment --region eu-north-1`n" -ForegroundColor Gray
    
}
else {
    Write-Host "`n⚠️ WARNING: DATABASE_URL has unexpected format" -ForegroundColor Yellow
    Write-Host "   Manual review required`n" -ForegroundColor White
}

Write-Host "========================================`n" -ForegroundColor Cyan
