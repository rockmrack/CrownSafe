# Simple DATABASE_URL Fix
# Downloads, fixes, and redeploys task definition

Write-Host "`n🔧 Fixing DATABASE_URL and redeploying...`n" -ForegroundColor Cyan

# 1. Get current task def and save  
Write-Host "[1/4] Downloading task definition..." -ForegroundColor Yellow
aws ecs describe-task-definition --task-definition babyshield-backend-task --region eu-north-1 > task-def-raw.json

# 2. Extract just the taskDefinition part and fix DATABASE_URL
Write-Host "[2/4] Fixing DATABASE_URL (postgres → babyshield_db)..." -ForegroundColor Yellow
$taskDefRaw = Get-Content task-def-raw.json | ConvertFrom-Json
$taskDef = $taskDefRaw.taskDefinition

# Fix DATABASE_URL
$container = $taskDef.containerDefinitions[0]
for ($i = 0; $i < $container.environment.Count; $i++) {
    if ($container.environment[$i].name -eq 'DATABASE_URL') {
        $oldUrl = $container.environment[$i].value
        $newUrl = $oldUrl -replace '/postgres(\?|$)', '/babyshield_db$1'
        $container.environment[$i].value = $newUrl
        Write-Host "  Old: $oldUrl" -ForegroundColor Red
        Write-Host "  New: $newUrl" -ForegroundColor Green
    }
}

# Remove AWS-managed fields
$taskDef.PSObject.Properties.Remove('taskDefinitionArn')
$taskDef.PSObject.Properties.Remove('revision')
$taskDef.PSObject.Properties.Remove('status')
$taskDef.PSObject.Properties.Remove('requiresAttributes')
$taskDef.PSObject.Properties.Remove('compatibilities')
$taskDef.PSObject.Properties.Remove('registeredAt')
$taskDef.PSObject.Properties.Remove('registeredBy')

# Save cleaned definition
$taskDef | ConvertTo-Json -Depth 20 -Compress | Out-File task-def-fixed.json -Encoding utf8 -NoNewline

# 3. Register new task definition
Write-Host "`n[3/4] Registering new task definition..." -ForegroundColor Yellow
$newRev = (aws ecs register-task-definition --cli-input-json file://task-def-fixed.json --region eu-north-1 | ConvertFrom-Json).taskDefinition.revision
Write-Host "  ✅ New revision: $newRev" -ForegroundColor Green

# 4. Update service
Write-Host "`n[4/4] Updating ECS service..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --task-definition "babyshield-backend-task:$newRev" `
    --force-new-deployment `
    --region eu-north-1 | Out-Null

Write-Host "`n✅ DEPLOYMENT STARTED!`n" -ForegroundColor Green -BackgroundColor Black
Write-Host "Wait 2-3 minutes, then test:" -ForegroundColor Yellow
Write-Host 'curl -X POST https://babyshield.cureviax.ai/api/v1/search/advanced -H "Content-Type: application/json" -d ''{"query":"baby","limit":5}''' -ForegroundColor Gray
Write-Host "`nExpected: 'total' > 0 (not 0)`n" -ForegroundColor White
