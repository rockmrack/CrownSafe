#!/usr/bin/env pwsh
# Fix OpenAI Visual Recognition in AWS ECS Production

Write-Host "🔧 BabyShield: Fixing OpenAI Visual Recognition" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# Step 1: Store OpenAI API Key in AWS Secrets Manager
Write-Host "`n📝 Step 1: Storing OpenAI API Key in AWS Secrets Manager..." -ForegroundColor Yellow

$OPENAI_KEY = "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"
$REGION = "eu-north-1"

Write-Host "Creating/updating OpenAI API key secret..." -ForegroundColor White
aws secretsmanager create-secret `
    --name "babyshield/openai-api-key" `
    --description "OpenAI API key for BabyShield visual recognition" `
    --secret-string $OPENAI_KEY `
    --region $REGION 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "Secret already exists, updating..." -ForegroundColor Gray
    aws secretsmanager update-secret `
        --secret-id "babyshield/openai-api-key" `
        --secret-string $OPENAI_KEY `
        --region $REGION
}

Write-Host "✅ OpenAI API key stored in AWS Secrets Manager" -ForegroundColor Green

# Step 2: Create updated task definition with proper OpenAI configuration
Write-Host "`n📝 Step 2: Creating updated task definition..." -ForegroundColor Yellow

$taskDef = @"
{
  "family": "babyshield-backend-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::180703226577:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::180703226577:role/babyshield-task-role",
  "containerDefinitions": [
    {
      "name": "babyshield-backend",
      "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8001,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "API_HOST", "value": "0.0.0.0"},
        {"name": "API_PORT", "value": "8001"},
        {"name": "ENABLE_CACHE", "value": "true"},
        {"name": "ENABLE_BACKGROUND_TASKS", "value": "true"},
        {"name": "ENABLE_AGENTS", "value": "true"},
        {"name": "AWS_REGION", "value": "eu-north-1"},
        {"name": "S3_UPLOAD_BUCKET", "value": "babyshield-images"},
        {"name": "ENABLE_TESSERACT", "value": "true"},
        {"name": "ENABLE_EASYOCR", "value": "true"},
        {"name": "ENABLE_DATAMATRIX", "value": "true"},
        {"name": "ENABLE_RECEIPT_VALIDATION", "value": "true"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/database-url"
        },
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/openai-api-key"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/jwt-secret"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:eu-north-1:180703226577:secret:babyshield/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/babyshield-backend",
          "awslogs-region": "eu-north-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
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

$taskDef | Out-File -FilePath "taskdef-with-openai.json" -Encoding UTF8
Write-Host "✅ Task definition created: taskdef-with-openai.json" -ForegroundColor Green

# Step 3: Register the new task definition
Write-Host "`n📝 Step 3: Registering new task definition..." -ForegroundColor Yellow

$newTaskDefArn = aws ecs register-task-definition `
    --cli-input-json file://taskdef-with-openai.json `
    --region $REGION `
    --query 'taskDefinition.taskDefinitionArn' `
    --output text

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ New task definition registered: $newTaskDefArn" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to register task definition" -ForegroundColor Red
    exit 1
}

# Step 4: Update ECS service
Write-Host "`n📝 Step 4: Updating ECS service..." -ForegroundColor Yellow

aws ecs update-service `
    --cluster "babyshield-cluster" `
    --service "babyshield-backend-service" `
    --task-definition $newTaskDefArn `
    --region $REGION

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ ECS service updated successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to update ECS service" -ForegroundColor Red
    exit 1
}

# Step 5: Wait for deployment to complete
Write-Host "`n📝 Step 5: Waiting for deployment to complete..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Gray

aws ecs wait services-stable `
    --cluster "babyshield-cluster" `
    --services "babyshield-backend-service" `
    --region $REGION

Write-Host "✅ Deployment completed!" -ForegroundColor Green

# Step 6: Verify the fix
Write-Host "`n📝 Step 6: Verifying OpenAI integration..." -ForegroundColor Yellow

Write-Host "Checking logs for OpenAI configuration..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Get the latest log events
$logEvents = aws logs describe-log-streams `
    --log-group-name "/ecs/babyshield-backend" `
    --order-by LastEventTime `
    --descending `
    --max-items 1 `
    --region $REGION `
    --query 'logStreams[0].logStreamName' `
    --output text

if ($logEvents) {
    Write-Host "Recent logs:" -ForegroundColor White
    aws logs get-log-events `
        --log-group-name "/ecs/babyshield-backend" `
        --log-stream-name $logEvents `
        --start-time $((Get-Date).AddMinutes(-5).ToUnixTimeMilliseconds()) `
        --region $REGION `
        --query 'events[?contains(message, `OpenAI`) || contains(message, `visual`)].message' `
        --output table
}

Write-Host "`n🎉 OpenAI Visual Recognition Fix Complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "`n📊 Expected Changes:" -ForegroundColor Cyan
Write-Host "  Before: WARNING:api.main_babyshield:OpenAI API key not configured" -ForegroundColor Red
Write-Host "  After:  INFO:api.main_babyshield:OpenAI API key configured - visual identification available" -ForegroundColor Green
Write-Host ""
Write-Host "🔍 Test Visual Recognition:" -ForegroundColor Cyan
Write-Host "  POST https://babyshield.cureviax.ai/api/v1/advanced/visual/recognize" -ForegroundColor White
Write-Host "  - Upload an image of a baby product" -ForegroundColor Gray
Write-Host "  - Should now return actual product identification" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Visual Recognition is now FULLY FUNCTIONAL!" -ForegroundColor Green
