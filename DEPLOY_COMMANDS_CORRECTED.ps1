# CORRECTED DEPLOYMENT COMMANDS FOR BABYSHIELD BACKEND
# PowerShell Version for Windows
# Date: 2025-08-31

Write-Host "`n🚀 CORRECTED DEPLOYMENT COMMANDS" -ForegroundColor Green -BackgroundColor Black
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

# 1. BUILD NEW IMAGE (IMPORTANT: Using Dockerfile.final, not .backend)
Write-Host "`n📦 Step 1: Build NEW image with ALL fixes" -ForegroundColor Yellow
Write-Host "docker build -f Dockerfile.final -t babyshield-backend:complete ." -ForegroundColor White

# 2. LOGIN TO ECR (your command is correct)
Write-Host "`n🔐 Step 2: Login to ECR (YOUR COMMAND IS CORRECT)" -ForegroundColor Yellow
Write-Host "aws ecr get-login-password --region eu-north-1 | docker login --username AWS --password-stdin 180703226577.dkr.ecr.eu-north-1.amazonaws.com" -ForegroundColor White

# 3. TAG with NEW version
Write-Host "`n🏷️ Step 3: Tag with NEW name and date" -ForegroundColor Yellow
Write-Host "docker tag babyshield-backend:complete 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831" -ForegroundColor White

# 4. PUSH
Write-Host "`n📤 Step 4: Push to ECR" -ForegroundColor Yellow
Write-Host "docker push 180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831" -ForegroundColor White

# 5. CREATE NEW TASK DEFINITION
Write-Host "`n📋 Step 5: Register ECS Task (FIXED environment variables)" -ForegroundColor Yellow
Write-Host @'
aws ecs register-task-definition `
  --family babyshield-backend-task `
  --task-role-arn arn:aws:iam::180703226577:role/babyshield-task-role `
  --execution-role-arn arn:aws:iam::180703226577:role/ecsTaskExecutionRole `
  --network-mode awsvpc `
  --requires-compatibilities FARGATE `
  --cpu 1024 `
  --memory 2048 `
  --region eu-north-1 `
  --container-definitions '[{
    "name": "babyshield-backend",
    "image": "180703226577.dkr.ecr.eu-north-1.amazonaws.com/babyshield-backend:production-20250831",
    "essential": true,
    "portMappings": [{"containerPort": 8001, "protocol": "tcp"}],
    "environment": [
      {"name": "DATABASE_URL", "value": "YOUR_PRODUCTION_DB_URL"},
      {"name": "OPENAI_API_KEY", "value": "YOUR_OPENAI_KEY"},
      {"name": "JWT_SECRET_KEY", "value": "YOUR_JWT_SECRET"},
      {"name": "SECRET_KEY", "value": "YOUR_SECRET_KEY"},
      {"name": "ENCRYPTION_KEY", "value": "YOUR_ENCRYPTION_KEY"}
    ]
  }]' `
  --query 'taskDefinition.taskDefinitionArn' `
  --output text
'@ -ForegroundColor Gray

Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "⚠️ WHAT WAS WRONG WITH YOUR COMMANDS:" -ForegroundColor Red
Write-Host "1. ❌ Used OLD image: babyshield-backend:fixed" -ForegroundColor White
Write-Host "   ✅ Should use: babyshield-backend:complete" -ForegroundColor Green
Write-Host ""
Write-Host "2. ❌ Wrong env variable: {""name"": "".env"", ""value"": """"}" -ForegroundColor White
Write-Host "   ✅ Should have proper environment variables" -ForegroundColor Green
Write-Host ""
Write-Host "3. ❌ Used old tag: fixed-20250828" -ForegroundColor White
Write-Host "   ✅ Should use: production-20250831" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
