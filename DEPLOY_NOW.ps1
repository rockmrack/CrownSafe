# ============================================
# COMPLETE DEPLOYMENT SCRIPT FOR BABYSHIELD
# ============================================
# Run this script to deploy to AWS
# Usage: .\DEPLOY_NOW.ps1

param(
    [string]$ImageTag = "production-20250831"
)

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "   BABYSHIELD BACKEND DEPLOYMENT" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Image Tag: $ImageTag" -ForegroundColor Yellow
Write-Host ""

# Configuration
$ECR_URI = "180703226577.dkr.ecr.eu-north-1.amazonaws.com"
$ECR_REPO = "babyshield-backend"
$REGION = "eu-north-1"
$LOCAL_TAG = "babyshield-backend:complete"

# Step 1: Build
Write-Host "[1/4] Building Docker image..." -ForegroundColor Yellow
Write-Host "      Using: Dockerfile.final" -ForegroundColor Gray
$buildResult = docker build -f Dockerfile.final -t $LOCAL_TAG . 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Write-Host $buildResult
    exit 1
}
Write-Host "✅ Build successful!" -ForegroundColor Green

# Step 2: Login to ECR
Write-Host "`n[2/4] Logging into AWS ECR..." -ForegroundColor Yellow
$loginCommand = aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ECR login failed!" -ForegroundColor Red
    Write-Host $loginCommand
    exit 1
}
Write-Host "✅ ECR login successful!" -ForegroundColor Green

# Step 3: Tag image
Write-Host "`n[3/4] Tagging image..." -ForegroundColor Yellow
$fullTag = "$ECR_URI/${ECR_REPO}:$ImageTag"
docker tag $LOCAL_TAG $fullTag

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tagging failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Tagged as: $fullTag" -ForegroundColor Green

# Step 4: Push to ECR
Write-Host "`n[4/4] Pushing to ECR..." -ForegroundColor Yellow
Write-Host "      This may take a few minutes..." -ForegroundColor Gray
docker push $fullTag

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "   ✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Image pushed: $fullTag" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 NEXT STEP: Register ECS Task Definition" -ForegroundColor Yellow
Write-Host "   Copy and run this in AWS CloudShell:" -ForegroundColor Gray
Write-Host ""
Write-Host @"
aws ecs register-task-definition \
  --family babyshield-backend-task \
  --task-role-arn arn:aws:iam::180703226577:role/babyshield-task-role \
  --execution-role-arn arn:aws:iam::180703226577:role/ecsTaskExecutionRole \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 1024 \
  --memory 2048 \
  --region $REGION \
  --container-definitions '[{
    "name": "babyshield-backend",
    "image": "$fullTag",
    "essential": true,
    "portMappings": [{"containerPort": 8001, "protocol": "tcp"}],
    "environment": [
      {"name": "DATABASE_URL", "value": "YOUR_DATABASE_URL"},
      {"name": "OPENAI_API_KEY", "value": "YOUR_OPENAI_KEY"},
      {"name": "JWT_SECRET_KEY", "value": "YOUR_JWT_SECRET"},
      {"name": "SECRET_KEY", "value": "YOUR_SECRET_KEY"},
      {"name": "ENCRYPTION_KEY", "value": "YOUR_ENCRYPTION_KEY"}
    ]
  }]'
"@ -ForegroundColor White

Write-Host "`n⚠️  Remember to replace YOUR_* values with actual secrets!" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
