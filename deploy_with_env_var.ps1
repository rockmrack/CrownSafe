# Deploy with OPENAI_API_KEY as environment variable

Write-Host "=== DEPLOYING WITH OPENAI_API_KEY ===" -ForegroundColor Cyan

# Get API key from .env
$openaiKey = Get-Content .env | Where-Object { $_ -match '^OPENAI_API_KEY=' } | ForEach-Object {
    $_ -replace '^OPENAI_API_KEY=', ''
}

Write-Host "Found API key" -ForegroundColor Green

# Stop the problematic deployment
Write-Host "Stopping problematic deployment..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --task-definition babyshield-backend-task:129 `
    --force-new-deployment `
    --region eu-north-1 `
    --output json > rollback.json

Write-Host "Rolled back to stable version" -ForegroundColor Green

# Wait for rollback
Start-Sleep -Seconds 10

# Now create a simple working task definition with env var
$taskDef = @"
{
  "family": "babyshield-backend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::180703226577:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::180703226577:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "babyshield-backend",
      "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20251006-v3",
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "API_HOST",
          "value": "0.0.0.0"
        },
        {
          "name": "API_PORT",
          "value": "8001"
        },
        {
          "name": "DATABASE_URL",
          "value": "sqlite:///./babyshield_dev.db"
        },
        {
          "name": "ENABLE_AGENTS",
          "value": "true"
        },
        {
          "name": "IS_PRODUCTION",
          "value": "true"
        },
        {
          "name": "OPENAI_API_KEY",
          "value": "$openaiKey"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/babyshield-backend",
          "awslogs-region": "eu-north-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8001/healthz || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
"@

# Save task definition
$taskDef | Set-Content -Path "simple-task-def.json"

Write-Host "Registering task definition with OPENAI_API_KEY..." -ForegroundColor Yellow

$newTaskArn = aws ecs register-task-definition `
    --cli-input-json file://simple-task-def.json `
    --region eu-north-1 `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

Write-Host "Registered: $newTaskArn" -ForegroundColor Green

# Deploy the new task definition
Write-Host "Deploying..." -ForegroundColor Yellow

aws ecs update-service `
    --cluster babyshield-cluster `
    --service babyshield-backend-task-service-0l41s2a9 `
    --task-definition $newTaskArn `
    --force-new-deployment `
    --region eu-north-1 `
    --output json > deploy.json

Write-Host "✅ DEPLOYMENT STARTED!" -ForegroundColor Green

# Clean up
Remove-Item simple-task-def.json -ErrorAction SilentlyContinue
Remove-Item rollback.json -ErrorAction SilentlyContinue
Remove-Item deploy.json -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Visual recognition will be available in 2-3 minutes!" -ForegroundColor Cyan
