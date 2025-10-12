# Enable Chat Feature in Production
# This script updates ECS task definition to enable chat feature flags

$ErrorActionPreference = "Stop"

# Configuration
$AWS_REGION = "eu-north-1"
$ECS_CLUSTER = "babyshield-cluster"
$ECS_SERVICE = "babyshield-backend-task-service-0l41s2a9"
$TASK_FAMILY = "babyshield-backend-task"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Enable Chat Feature in Production" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Get current task definition
Write-Host "[1/4] Getting current task definition..." -ForegroundColor Cyan
$currentTaskDefArn = aws ecs describe-services `
    --cluster $ECS_CLUSTER `
    --services $ECS_SERVICE `
    --region $AWS_REGION `
    --query 'services[0].taskDefinition' `
    --output text

if ([string]::IsNullOrEmpty($currentTaskDefArn)) {
    Write-Host "ERROR: Could not get current task definition!" -ForegroundColor Red
    exit 1
}

Write-Host "Current Task Definition: $currentTaskDefArn" -ForegroundColor Yellow

# Step 2: Get task definition JSON
Write-Host ""
Write-Host "[2/4] Retrieving task definition details..." -ForegroundColor Cyan
$taskDefJson = aws ecs describe-task-definition `
    --task-definition $currentTaskDefArn `
    --region $AWS_REGION `
    --query 'taskDefinition' `
    --output json | ConvertFrom-Json

# Step 3: Update environment variables
Write-Host ""
Write-Host "[3/4] Updating environment variables..." -ForegroundColor Cyan

# Get the container definition
$containerDef = $taskDefJson.containerDefinitions[0]

# Find or add chat feature flags
$chatEnabledExists = $false
$chatRolloutExists = $false

foreach ($env in $containerDef.environment) {
    if ($env.name -eq "BS_FEATURE_CHAT_ENABLED") {
        $env.value = "true"
        $chatEnabledExists = $true
        Write-Host "  Updated BS_FEATURE_CHAT_ENABLED = true" -ForegroundColor Green
    }
    if ($env.name -eq "BS_FEATURE_CHAT_ROLLOUT_PCT") {
        $env.value = "1.0"
        $chatRolloutExists = $true
        Write-Host "  Updated BS_FEATURE_CHAT_ROLLOUT_PCT = 1.0" -ForegroundColor Green
    }
}

# Add if they don't exist
if (-not $chatEnabledExists) {
    $containerDef.environment += @{
        name  = "BS_FEATURE_CHAT_ENABLED"
        value = "true"
    }
    Write-Host "  Added BS_FEATURE_CHAT_ENABLED = true" -ForegroundColor Green
}

if (-not $chatRolloutExists) {
    $containerDef.environment += @{
        name  = "BS_FEATURE_CHAT_ROLLOUT_PCT"
        value = "1.0"
    }
    Write-Host "  Added BS_FEATURE_CHAT_ROLLOUT_PCT = 1.0" -ForegroundColor Green
}

# Remove fields that can't be in register-task-definition
$taskDefJson.PSObject.Properties.Remove('taskDefinitionArn')
$taskDefJson.PSObject.Properties.Remove('revision')
$taskDefJson.PSObject.Properties.Remove('status')
$taskDefJson.PSObject.Properties.Remove('requiresAttributes')
$taskDefJson.PSObject.Properties.Remove('compatibilities')
$taskDefJson.PSObject.Properties.Remove('registeredAt')
$taskDefJson.PSObject.Properties.Remove('registeredBy')

# Save to temporary file
$tempFile = "temp_task_def_chat_enabled.json"
$taskDefJson | ConvertTo-Json -Depth 10 | Set-Content $tempFile

# Step 4: Register new task definition
Write-Host ""
Write-Host "[4/4] Registering new task definition..." -ForegroundColor Cyan
$newTaskDefArn = aws ecs register-task-definition `
    --cli-input-json file://$tempFile `
    --region $AWS_REGION `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

if ([string]::IsNullOrEmpty($newTaskDefArn)) {
    Write-Host "ERROR: Failed to register new task definition!" -ForegroundColor Red
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "New Task Definition: $newTaskDefArn" -ForegroundColor Green

# Clean up temp file
Remove-Item $tempFile -ErrorAction SilentlyContinue

# Update service to use new task definition
Write-Host ""
Write-Host "Updating ECS service..." -ForegroundColor Cyan
aws ecs update-service `
    --cluster $ECS_CLUSTER `
    --service $ECS_SERVICE `
    --task-definition $newTaskDefArn `
    --force-new-deployment `
    --region $AWS_REGION | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to update ECS service!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SUCCESS: Chat Feature Enabled!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Environment Variables Set:" -ForegroundColor Yellow
Write-Host "  BS_FEATURE_CHAT_ENABLED = true" -ForegroundColor Cyan
Write-Host "  BS_FEATURE_CHAT_ROLLOUT_PCT = 1.0 (100% rollout)" -ForegroundColor Cyan
Write-Host ""
Write-Host "ECS service is deploying with new configuration..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes to complete." -ForegroundColor Yellow
Write-Host ""
Write-Host "Monitor deployment:" -ForegroundColor White
Write-Host "  aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION" -ForegroundColor Gray
Write-Host ""
Write-Host "Test chat endpoint after deployment:" -ForegroundColor White
Write-Host "  curl https://babyshield.cureviax.ai/api/v1/chat/flags" -ForegroundColor Gray
Write-Host ""
