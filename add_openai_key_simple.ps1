# Simple script to add OPENAI_API_KEY to AWS ECS Production

Write-Host "=== ADDING OPENAI_API_KEY TO PRODUCTION ===" -ForegroundColor Cyan

# Load the .env file and get OPENAI_API_KEY
$openaiKey = Get-Content .env | Where-Object { $_ -match '^OPENAI_API_KEY=' } | ForEach-Object {
    $_ -replace '^OPENAI_API_KEY=', ''
}

if (-not $openaiKey) {
    Write-Host "ERROR: OPENAI_API_KEY not found in .env!" -ForegroundColor Red
    exit 1
}

Write-Host "Found OPENAI_API_KEY in .env" -ForegroundColor Green

# AWS Configuration
$region = "eu-north-1"
$cluster = "babyshield-cluster"  
$service = "babyshield-backend-task-service-0l41s2a9"

# Step 1: Create/Update secret in Secrets Manager
Write-Host "Creating secret in AWS Secrets Manager..." -ForegroundColor Yellow

$secretJson = "{`"OPENAI_API_KEY`":`"$openaiKey`"}"

# Try to create secret
aws secretsmanager create-secret `
    --name "babyshield/openai-key" `
    --secret-string $secretJson `
    --region $region 2>$null

# If create fails, try update
if ($LASTEXITCODE -ne 0) {
    aws secretsmanager update-secret `
        --secret-id "babyshield/openai-key" `
        --secret-string $secretJson `
        --region $region
}

Write-Host "Secret created/updated" -ForegroundColor Green

# Step 2: Get current task definition
Write-Host "Getting current task definition..." -ForegroundColor Yellow

# Get task definition and save to file
aws ecs describe-task-definition `
    --task-definition babyshield-backend-task `
    --region $region `
    --query taskDefinition `
    --output json > current-task-def.json

Write-Host "Task definition downloaded" -ForegroundColor Green

# Step 3: Update task definition with Python script
Write-Host "Updating task definition..." -ForegroundColor Yellow

# Create Python script to modify JSON
@'
import json

# Load current task definition
with open('current-task-def.json', 'r') as f:
    task_def = json.load(f)

# Get secret ARN
import subprocess
result = subprocess.run(['aws', 'secretsmanager', 'describe-secret', '--secret-id', 'babyshield/openai-key', '--region', 'eu-north-1', '--query', 'ARN', '--output', 'text'], capture_output=True, text=True)
secret_arn = result.stdout.strip()

# Add OPENAI_API_KEY to container secrets
container = task_def['containerDefinitions'][0]
if 'secrets' not in container:
    container['secrets'] = []

# Remove existing OPENAI_API_KEY if present
container['secrets'] = [s for s in container['secrets'] if s['name'] != 'OPENAI_API_KEY']

# Add new secret
container['secrets'].append({
    'name': 'OPENAI_API_KEY',
    'valueFrom': f"{secret_arn}:OPENAI_API_KEY::"
})

# Clean up task definition for registration
fields_to_remove = ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 'compatibilities', 'registeredAt', 'registeredBy']
for field in fields_to_remove:
    task_def.pop(field, None)

# Save new task definition
with open('new-task-def.json', 'w') as f:
    json.dump(task_def, f, indent=2)

print("Task definition updated")
'@ | python

# Step 4: Register new task definition
Write-Host "Registering new task definition..." -ForegroundColor Yellow

aws ecs register-task-definition `
    --cli-input-json file://new-task-def.json `
    --region $region > $null

Write-Host "New task definition registered" -ForegroundColor Green

# Step 5: Update service
Write-Host "Updating ECS service..." -ForegroundColor Yellow

aws ecs update-service `
    --cluster $cluster `
    --service $service `
    --task-definition babyshield-backend-task `
    --force-new-deployment `
    --region $region > $null

Write-Host "Service updated!" -ForegroundColor Green

# Clean up
Remove-Item current-task-def.json -ErrorAction SilentlyContinue
Remove-Item new-task-def.json -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
Write-Host "Visual recognition will be available in 2-3 minutes" -ForegroundColor Cyan
Write-Host ""
Write-Host "Monitor deployment status:" -ForegroundColor Yellow
Write-Host "aws ecs describe-services --cluster $cluster --services $service --region $region --query 'services[0].deployments'" -ForegroundColor Gray
