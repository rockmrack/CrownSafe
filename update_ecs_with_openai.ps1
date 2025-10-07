# Update ECS task definition with OPENAI_API_KEY from Secrets Manager

Write-Host "=== UPDATING ECS WITH OPENAI_API_KEY ===" -ForegroundColor Cyan

$region = "eu-north-1"
$cluster = "babyshield-cluster"
$service = "babyshield-backend-task-service-0l41s2a9"
$secretArn = "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/openai-key-s1qspJ"

# Get the current running task definition
Write-Host "Getting current task definition..." -ForegroundColor Yellow

$currentTaskDefArn = aws ecs describe-services `
    --cluster $cluster `
    --services $service `
    --region $region `
    --query 'services[0].taskDefinition' `
    --output text

Write-Host "Current task definition: $currentTaskDefArn" -ForegroundColor White

# Extract the task definition family name
$taskFamily = $currentTaskDefArn -replace '.*\/([^:]+):.*', '$1'
Write-Host "Task family: $taskFamily" -ForegroundColor White

# Create a new task definition with OPENAI_API_KEY
Write-Host "Creating new task definition JSON..." -ForegroundColor Yellow

# Create the task definition JSON
$taskDefJson = @'
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
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/openai-key-s1qspJ:OPENAI_API_KEY::"
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
'@

# Save to file
$taskDefJson | Set-Content -Path "task-def-with-openai.json"

Write-Host "Registering new task definition..." -ForegroundColor Yellow

# Register the new task definition
$newTaskDefArn = aws ecs register-task-definition `
    --cli-input-json file://task-def-with-openai.json `
    --region $region `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ New task definition registered: $newTaskDefArn" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to register task definition" -ForegroundColor Red
    exit 1
}

Write-Host "Updating ECS service..." -ForegroundColor Yellow

# Update the service with the new task definition
aws ecs update-service `
    --cluster $cluster `
    --service $service `
    --task-definition $newTaskDefArn `
    --force-new-deployment `
    --region $region `
    --output json > update-result.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Service update initiated!" -ForegroundColor Green
} else {
    Write-Host "ERROR: Failed to update service" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item task-def-with-openai.json -ErrorAction SilentlyContinue
Remove-Item update-result.json -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== DEPLOYMENT INITIATED ===" -ForegroundColor Green
Write-Host ""
Write-Host "OPENAI_API_KEY has been added to the ECS task!" -ForegroundColor Cyan
Write-Host "Visual recognition will be available in 3-5 minutes." -ForegroundColor Yellow
Write-Host ""
Write-Host "Check deployment status:" -ForegroundColor White
Write-Host "aws ecs wait services-stable --cluster $cluster --services $service --region $region" -ForegroundColor Gray
Write-Host ""
Write-Host "View deployment progress:" -ForegroundColor White
Write-Host "aws ecs describe-services --cluster $cluster --services $service --region $region --query 'services[0].deployments' --output table" -ForegroundColor Gray
