# Script to add OPENAI_API_KEY to AWS ECS Production
# This script securely adds the OpenAI API key from .env to AWS Secrets Manager and ECS

Write-Host "=== ADDING OPENAI_API_KEY TO PRODUCTION ===" -ForegroundColor Cyan
Write-Host ""

# Load the .env file
$envFile = ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    exit 1
}

# Read the OPENAI_API_KEY from .env
$openaiKey = Get-Content $envFile | Where-Object { $_ -match '^OPENAI_API_KEY=' } | ForEach-Object {
    $_ -replace '^OPENAI_API_KEY=', ''
}

if (-not $openaiKey) {
    Write-Host "ERROR: OPENAI_API_KEY not found in .env!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Found OPENAI_API_KEY in .env" -ForegroundColor Green
Write-Host ""

# AWS Configuration
$region = "eu-north-1"
$cluster = "babyshield-cluster"
$service = "babyshield-backend-task-service-0l41s2a9"
$secretName = "babyshield/production/openai-api-key"

Write-Host "Step 1: Creating/Updating secret in AWS Secrets Manager..." -ForegroundColor Yellow

# Create or update the secret in AWS Secrets Manager
$secretValue = @{
    OPENAI_API_KEY = $openaiKey
} | ConvertTo-Json -Compress

# Try to update existing secret first
$updateResult = aws secretsmanager update-secret `
    --secret-id $secretName `
    --secret-string $secretValue `
    --region $region 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Updated existing secret" -ForegroundColor Green
} else {
    # Create new secret if it doesn't exist
    $createResult = aws secretsmanager create-secret `
        --name $secretName `
        --secret-string $secretValue `
        --region $region 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Created new secret" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to create/update secret" -ForegroundColor Red
        Write-Host $createResult -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Step 2: Getting current task definition..." -ForegroundColor Yellow

# Get the current task definition
$taskDefArn = aws ecs describe-services `
    --cluster $cluster `
    --services $service `
    --region $region `
    --query 'services[0].taskDefinition' `
    --output text

if (-not $taskDefArn) {
    Write-Host "ERROR: Could not get task definition ARN" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Current task definition: $taskDefArn" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Getting task definition details..." -ForegroundColor Yellow

# Get the task definition JSON
$taskDef = aws ecs describe-task-definition `
    --task-definition $taskDefArn `
    --region $region `
    --output json | ConvertFrom-Json

# Extract family name
$family = $taskDef.taskDefinition.family

Write-Host "✓ Task definition family: $family" -ForegroundColor Green
Write-Host ""

Write-Host "Step 4: Creating new task definition with OPENAI_API_KEY..." -ForegroundColor Yellow

# Get the secret ARN
$secretArn = aws secretsmanager describe-secret `
    --secret-id $secretName `
    --region $region `
    --query 'ARN' `
    --output text

# Prepare the container definition with the new environment variable
$containerDef = $taskDef.taskDefinition.containerDefinitions[0]

# Check if secrets array exists, if not create it
if (-not $containerDef.PSObject.Properties['secrets']) {
    $containerDef | Add-Member -NotePropertyName 'secrets' -NotePropertyValue @()
}

# Add OPENAI_API_KEY to secrets (remove if exists first)
$containerDef.secrets = @($containerDef.secrets | Where-Object { $_.name -ne 'OPENAI_API_KEY' })
$containerDef.secrets += @{
    name = "OPENAI_API_KEY"
    valueFrom = "${secretArn}:OPENAI_API_KEY::"
}

# Also add as environment variable for compatibility
if (-not $containerDef.PSObject.Properties['environment']) {
    $containerDef | Add-Member -NotePropertyName 'environment' -NotePropertyValue @()
}

# Remove existing OPENAI_API_KEY from environment if present
$containerDef.environment = @($containerDef.environment | Where-Object { $_.name -ne 'OPENAI_API_KEY' })

# Create new task definition JSON
$newTaskDef = @{
    family = $family
    taskRoleArn = $taskDef.taskDefinition.taskRoleArn
    executionRoleArn = $taskDef.taskDefinition.executionRoleArn
    networkMode = $taskDef.taskDefinition.networkMode
    containerDefinitions = @($containerDef)
    requiresCompatibilities = $taskDef.taskDefinition.requiresCompatibilities
    cpu = $taskDef.taskDefinition.cpu
    memory = $taskDef.taskDefinition.memory
}

# Save to temporary file
$tempFile = "temp-task-def.json"
$newTaskDef | ConvertTo-Json -Depth 10 | Set-Content $tempFile

Write-Host "✓ Task definition prepared with OPENAI_API_KEY" -ForegroundColor Green
Write-Host ""

Write-Host "Step 5: Registering new task definition..." -ForegroundColor Yellow

# Register the new task definition
$newTaskDefArn = aws ecs register-task-definition `
    --cli-input-json file://$tempFile `
    --region $region `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

if (-not $newTaskDefArn) {
    Write-Host "ERROR: Failed to register new task definition" -ForegroundColor Red
    Remove-Item $tempFile
    exit 1
}

Write-Host "✓ New task definition registered: $newTaskDefArn" -ForegroundColor Green
Write-Host ""

Write-Host "Step 6: Updating ECS service with new task definition..." -ForegroundColor Yellow

# Update the service to use the new task definition
aws ecs update-service `
    --cluster $cluster `
    --service $service `
    --task-definition $newTaskDefArn `
    --force-new-deployment `
    --region $region `
    --output json > $null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Service updated successfully!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to update service" -ForegroundColor Red
    Remove-Item $tempFile
    exit 1
}

# Clean up
Remove-Item $tempFile

Write-Host ""
Write-Host "=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host ""
Write-Host "The OPENAI_API_KEY has been added to production!" -ForegroundColor Cyan
Write-Host "Visual recognition will be available in 2-3 minutes." -ForegroundColor Yellow
Write-Host ""
Write-Host "Monitor deployment:" -ForegroundColor White
Write-Host "aws ecs describe-services --cluster $cluster --services $service --region $region --query 'services[0].deployments'" -ForegroundColor Gray
Write-Host ""
Write-Host "Test visual recognition after deployment:" -ForegroundColor White
Write-Host 'Invoke-RestMethod -Uri "https://babyshield.cureviax.ai/api/v1/safety-check" -Method Post -Body ''{"user_id":1,"image_url":"https://example.com/test.jpg"}'' -ContentType "application/json"' -ForegroundColor Gray
