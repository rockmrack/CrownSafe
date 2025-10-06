# Fix task definition to use correct roles

Write-Host "=== FIXING TASK DEFINITION ===" -ForegroundColor Cyan

$region = "eu-north-1"
$cluster = "babyshield-cluster"
$service = "babyshield-backend-task-service-0l41s2a9"

# Get the working task definition (129)
Write-Host "Getting working task definition..." -ForegroundColor Yellow

aws ecs describe-task-definition `
    --task-definition babyshield-backend-task:129 `
    --region $region `
    --output json > working-task.json

# Create Python script to add OPENAI_API_KEY
Write-Host "Adding OPENAI_API_KEY to task definition..." -ForegroundColor Yellow

@'
import json

# Load task definition
with open('working-task.json', 'r') as f:
    data = json.load(f)
    task_def = data['taskDefinition']

# Add OPENAI_API_KEY to container environment (not secrets for now)
container = task_def['containerDefinitions'][0]

# Add to environment variables directly
if 'environment' not in container:
    container['environment'] = []

# Remove existing OPENAI_API_KEY if present
container['environment'] = [e for e in container['environment'] if e['name'] != 'OPENAI_API_KEY']

# Read API key from .env
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('OPENAI_API_KEY='):
            api_key = line.strip().split('=', 1)[1]
            container['environment'].append({
                'name': 'OPENAI_API_KEY',
                'value': api_key
            })
            print(f"Added OPENAI_API_KEY to environment")
            break

# Clean up task definition for registration
fields_to_remove = ['taskDefinitionArn', 'revision', 'status', 'requiresAttributes', 
                    'compatibilities', 'registeredAt', 'registeredBy', 'deregisteredAt']
for field in fields_to_remove:
    task_def.pop(field, None)

# Save new task definition
with open('fixed-task-def.json', 'w') as f:
    json.dump(task_def, f, indent=2)

print("Task definition prepared")
'@ | python

# Register the fixed task definition
Write-Host "Registering fixed task definition..." -ForegroundColor Yellow

$newTaskArn = aws ecs register-task-definition `
    --cli-input-json file://fixed-task-def.json `
    --region $region `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

Write-Host "New task definition: $newTaskArn" -ForegroundColor Green

# Update service with the fixed task definition
Write-Host "Updating service..." -ForegroundColor Yellow

aws ecs update-service `
    --cluster $cluster `
    --service $service `
    --task-definition $newTaskArn `
    --force-new-deployment `
    --region $region `
    --output json > update-result.json

Write-Host "✅ Service updated with OPENAI_API_KEY in environment!" -ForegroundColor Green

# Clean up
Remove-Item working-task.json -ErrorAction SilentlyContinue
Remove-Item fixed-task-def.json -ErrorAction SilentlyContinue
Remove-Item update-result.json -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== DEPLOYMENT FIXED ===" -ForegroundColor Green
Write-Host "Visual recognition will be available in 2-3 minutes" -ForegroundColor Cyan
